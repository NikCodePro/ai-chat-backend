import os
import json
import logging
import asyncio
import time
import base64
from typing import Callable, Any

from google import genai
from google.genai import types

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiLiveService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set. Gemini Live Service will fail if used.")
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

        self.model = "gemini-2.5-flash-native-audio-preview-12-2025"

    async def run_session(
        self,
        receive_from_client: Callable,
        send_to_client_json: Callable,
        send_to_client_bytes: Callable,
        system_instruction: str = "You are a helpful voice assistant. Keep responses conversational and brief.",
    ):
        config = types.LiveConnectConfig(
            system_instruction=types.Content(
                parts=[types.Part.from_text(text=system_instruction)]
            ),
            response_modalities=[types.Modality.AUDIO],
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    silence_duration_ms=600,
                )
            ),
        )

        if not self.client:
            logger.error("Cannot run Gemini Live Session: No API key configured.")
            await send_to_client_json(
                {"type": "error", "message": "Backend missing Gemini API key"}
            )
            return

        # ── Queue to decouple client WebSocket reads from Gemini sends ──
        # This lets us reconnect to Gemini without losing the client connection.
        audio_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        client_disconnected = False

        # ── Task 1: WebSocket reader (lives for the entire client connection) ──
        async def ws_reader():
            nonlocal client_disconnected
            try:
                while True:
                    data = await receive_from_client()
                    if data is None:
                        logger.info("[WS-READER] Client disconnected (received None)")
                        client_disconnected = True
                        break

                    # Check for stop signal
                    if isinstance(data, dict) and data.get("type") == "client_stop_stream":
                        logger.info("[WS-READER] Client requested stop")
                        client_disconnected = True
                        break

                    try:
                        audio_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        # Drop oldest item to prevent unbounded backlog
                        try:
                            audio_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                        audio_queue.put_nowait(data)
            except asyncio.CancelledError:
                logger.info("[WS-READER] Task cancelled")
            except Exception as e:
                logger.error(f"[WS-READER] Error: {e}")
                client_disconnected = True

        reader_task = asyncio.create_task(ws_reader())

        # ── Gemini session loop (reconnects if the API stream closes) ──
        reconnect_count = 0
        max_reconnects = 10

        try:
            while not client_disconnected and reconnect_count < max_reconnects:
                try:
                    async with self.client.aio.live.connect(
                        model=self.model, config=config
                    ) as session:
                        if reconnect_count > 0:
                            logger.info(
                                f"[GEMINI] Reconnected to Gemini Live API (attempt {reconnect_count})"
                            )
                        else:
                            logger.info("[GEMINI] Connected to Gemini Live API.")

                        # Reset reconnect counter on successful connection
                        reconnect_count = 0

                        # ── Shared state for this session ──
                        ai_is_speaking = False
                        dropped_while_speaking = 0

                        # ── Gemini → Client (receiver) ──────────────────
                        async def gemini_receiver():
                            nonlocal ai_is_speaking, dropped_while_speaking

                            is_speaking = False
                            audio_buffer = bytearray()
                            first_chunk_size = 4800
                            subsequent_chunk_size = 4800
                            ai_chunk_counter = 0

                            try:
                                async for response in session.receive():
                                    recv_ts = time.time() * 1000
                                    server_content = response.server_content
                                    if server_content is None:
                                        continue

                                    model_turn = server_content.model_turn
                                    if model_turn is not None:
                                        for part in model_turn.parts:
                                            if part.inline_data and part.inline_data.data:
                                                if not is_speaking:
                                                    logger.info(
                                                        f"[GEMINI-RX] AI started speaking at {recv_ts:.0f}"
                                                    )
                                                    ai_is_speaking = True
                                                    dropped_while_speaking = 0
                                                    await send_to_client_json(
                                                        {
                                                            "type": "ai_started_speaking",
                                                            "timestamp": recv_ts,
                                                        }
                                                    )
                                                    is_speaking = True

                                                audio_buffer.extend(part.inline_data.data)

                                                while True:
                                                    current_target = (
                                                        first_chunk_size
                                                        if ai_chunk_counter == 0
                                                        else subsequent_chunk_size
                                                    )
                                                    if len(audio_buffer) < current_target:
                                                        break

                                                    chunk = bytes(
                                                        audio_buffer[:current_target]
                                                    )
                                                    del audio_buffer[:current_target]

                                                    ai_chunk_counter += 1
                                                    b64_data = base64.b64encode(
                                                        chunk
                                                    ).decode("utf-8")
                                                    send_ts = time.time() * 1000

                                                    logger.info(
                                                        f"[GEMINI-RX] server_audio {ai_chunk_counter} | "
                                                        f"size: {len(chunk)} bytes | "
                                                        f"buffer_delay: {send_ts - recv_ts:.1f}ms"
                                                    )

                                                    await send_to_client_json(
                                                        {
                                                            "type": "server_audio",
                                                            "chunk_id": ai_chunk_counter,
                                                            "server_timestamp": send_ts,
                                                            "timestamp": send_ts,
                                                            "audio": b64_data,
                                                            "chunk_size": len(chunk),
                                                        }
                                                    )
                                                    await asyncio.sleep(0)

                                            if part.text:
                                                await send_to_client_json(
                                                    {
                                                        "type": "ai_transcript",
                                                        "text": part.text,
                                                        "timestamp": recv_ts,
                                                    }
                                                )

                                    if server_content.turn_complete:
                                        if len(audio_buffer) > 0:
                                            ai_chunk_counter += 1
                                            chunk = bytes(audio_buffer)
                                            b64_data = base64.b64encode(chunk).decode(
                                                "utf-8"
                                            )
                                            send_ts = time.time() * 1000
                                            logger.info(
                                                f"[GEMINI-RX] FINAL server_audio {ai_chunk_counter} | "
                                                f"size: {len(chunk)} bytes"
                                            )
                                            await send_to_client_json(
                                                {
                                                    "type": "server_audio",
                                                    "chunk_id": ai_chunk_counter,
                                                    "server_timestamp": send_ts,
                                                    "timestamp": send_ts,
                                                    "audio": b64_data,
                                                    "chunk_size": len(chunk),
                                                }
                                            )
                                            audio_buffer.clear()

                                        is_speaking = False
                                        ai_is_speaking = False
                                        ai_chunk_counter = 0
                                        if dropped_while_speaking:
                                            logger.info(
                                                f"[GEMINI-RX] Dropped {dropped_while_speaking} "
                                                f"client audio chunks while AI was speaking"
                                            )
                                            dropped_while_speaking = 0
                                        await send_to_client_json(
                                            {"type": "ai_finished_speaking"}
                                        )
                                        logger.info(
                                            "[GEMINI-RX] turn_complete processed, "
                                            "waiting for next Gemini response..."
                                        )

                                    if server_content.interrupted:
                                        audio_buffer.clear()
                                        is_speaking = False
                                        ai_is_speaking = False
                                        ai_chunk_counter = 0
                                        dropped_while_speaking = 0
                                        await send_to_client_json(
                                            {"type": "ai_interrupted"}
                                        )

                                # If we reach here, the async for loop ended normally.
                                # This means Gemini closed its receive stream.
                                logger.info(
                                    "[GEMINI-RX] Receive stream ended normally "
                                    "(Gemini closed the session)"
                                )

                            except asyncio.CancelledError:
                                logger.info("[GEMINI-RX] Task cancelled")
                            except Exception as e:
                                logger.error(f"[GEMINI-RX] Error: {e}", exc_info=True)

                        # ── Client → Gemini (sender, reads from queue) ──
                        async def gemini_sender():
                            nonlocal ai_is_speaking, dropped_while_speaking

                            # Drain any stale data left from a previous session
                            while not audio_queue.empty():
                                try:
                                    audio_queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    break

                            try:
                                while not client_disconnected:
                                    try:
                                        data = await asyncio.wait_for(
                                            audio_queue.get(), timeout=0.1
                                        )
                                    except asyncio.TimeoutError:
                                        continue

                                    if isinstance(data, bytes):
                                        await session.send(
                                            input=types.LiveClientRealtimeInput(
                                                media_chunks=[
                                                    types.Blob(
                                                        mime_type="audio/pcm;rate=16000",
                                                        data=data,
                                                    )
                                                ]
                                            )
                                        )

                                    elif isinstance(data, dict):
                                        event_type = data.get("type")

                                        if event_type == "client_audio":
                                            try:
                                                b64_data = data.get("audio", "")
                                                padding = len(b64_data) % 4
                                                if padding > 0:
                                                    b64_data += "=" * (4 - padding)

                                                raw_bytes = base64.b64decode(b64_data)

                                                if len(raw_bytes) == 0:
                                                    continue

                                                await session.send(
                                                    input=types.LiveClientRealtimeInput(
                                                        media_chunks=[
                                                            types.Blob(
                                                                mime_type="audio/pcm;rate=16000",
                                                                data=raw_bytes,
                                                            )
                                                        ]
                                                    )
                                                )
                                            except Exception as inner_e:
                                                logger.error(
                                                    f"[GEMINI-TX] Error sending audio: {inner_e}"
                                                )
                                                # If session.send fails, session is dead
                                                return

                                        elif event_type in (
                                            "client_start_stream",
                                            "client_pause_stream",
                                            "client_resume_stream",
                                        ):
                                            pass  # Handled at protocol level

                                    await asyncio.sleep(0)

                            except asyncio.CancelledError:
                                logger.info("[GEMINI-TX] Task cancelled")
                            except Exception as e:
                                logger.error(f"[GEMINI-TX] Error: {e}", exc_info=True)

                        # ── Launch both tasks for this Gemini session ──
                        receiver_task = asyncio.create_task(gemini_receiver())
                        sender_task = asyncio.create_task(gemini_sender())

                        done, pending = await asyncio.wait(
                            [sender_task, receiver_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        # Log what finished
                        for task in done:
                            try:
                                task.result()
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                logger.error(
                                    f"[GEMINI] Task failed: {e}", exc_info=True
                                )

                        # Cancel remaining task
                        for task in pending:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                        # If the CLIENT disconnected, exit entirely
                        if client_disconnected:
                            logger.info(
                                "[GEMINI] Client disconnected, ending session loop"
                            )
                            break

                        # Otherwise, the Gemini stream ended but client is alive.
                        # Reconnect to Gemini for the next conversational turn.
                        logger.info(
                            "[GEMINI] Session stream ended. Reconnecting for next turn..."
                        )
                        reconnect_count += 1

                except Exception as e:
                    logger.error(f"[GEMINI] Connection error: {e}", exc_info=True)
                    reconnect_count += 1
                    if client_disconnected or reconnect_count >= max_reconnects:
                        break
                    await asyncio.sleep(0.5)

        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass

        if reconnect_count >= max_reconnects:
            logger.error("[GEMINI] Max reconnects reached, closing session")
            await send_to_client_json(
                {
                    "type": "error",
                    "message": "AI session ended after too many reconnections",
                }
            )


gemini_live_service = GeminiLiveService()
