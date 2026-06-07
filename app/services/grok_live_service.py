import asyncio
import base64
import json
import logging
import os
import time
from typing import Callable

import websockets

from app.config import settings

logger = logging.getLogger(__name__)

GROK_REALTIME_URL = "wss://api.x.ai/v1/realtime?model=grok-voice-latest"


class GrokLiveService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.XAI_API_KEY or os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.warning("XAI_API_KEY not set. Grok Live Service will fail if used.")

    async def run_session(
        self,
        receive_from_client: Callable,
        send_to_client_json: Callable,
        send_to_client_bytes: Callable,
        system_instruction: str = "You are a helpful voice assistant. Keep responses conversational and brief.",
    ):
        if not self.api_key:
            logger.error("Cannot run Grok Live Session: No XAI_API_KEY configured.")
            await send_to_client_json(
                {"type": "error", "message": "Backend missing xAI API key"}
            )
            return

        # Queue decouples client WebSocket reads from Grok sends,
        # surviving reconnects without losing user audio.
        audio_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        client_disconnected = False

        # Task 1: client reader — lives for the full connection duration.
        async def ws_reader():
            nonlocal client_disconnected
            try:
                while True:
                    data = await receive_from_client()
                    if data is None:
                        logger.info("[WS-READER] Client disconnected")
                        client_disconnected = True
                        break
                    if isinstance(data, dict) and data.get("type") == "client_stop_stream":
                        logger.info("[WS-READER] Client requested stop")
                        client_disconnected = True
                        break
                    try:
                        audio_queue.put_nowait(data)
                    except asyncio.QueueFull:
                        try:
                            audio_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                        audio_queue.put_nowait(data)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"[WS-READER] Error: {e}")
                client_disconnected = True

        reader_task = asyncio.create_task(ws_reader())

        reconnect_count = 0
        max_reconnects = 5

        try:
            while not client_disconnected and reconnect_count < max_reconnects:
                try:
                    connection_start_time = time.time()

                    async with websockets.connect(
                        GROK_REALTIME_URL,
                        additional_headers={"Authorization": f"Bearer {self.api_key}"},
                        ping_interval=20,
                        ping_timeout=20,
                    ) as grok_ws:
                        logger.info(
                            f"[GROK] Connected to xAI Realtime API"
                            + (f" (reconnect #{reconnect_count})" if reconnect_count else "")
                        )
                        reconnect_count = 0  # reset on every clean connect

                        # Send session config immediately — audio must not be sent
                        # until the server acknowledges via session.updated.
                        await grok_ws.send(json.dumps({
                            "type": "session.update",
                            "session": {
                                "voice": "Eve",
                                "instructions": system_instruction,
                                "turn_detection": {"type": "server_vad"},
                                "input_audio_transcription": {"model": "grok-2-audio"},
                                "audio": {
                                    # Mobile app records at 16 kHz PCM16
                                    "input": {"format": {"type": "audio/pcm", "rate": 16000}},
                                    # Frontend playback expects 24 kHz PCM16
                                    "output": {"format": {"type": "audio/pcm", "rate": 24000}},
                                },
                            },
                        }))

                        session_ready = asyncio.Event()
                        ai_is_speaking = False
                        ai_chunk_counter = 0

                        # ── Grok → client ──────────────────────────────────
                        async def grok_receiver():
                            nonlocal ai_is_speaking, ai_chunk_counter
                            try:
                                async for raw_msg in grok_ws:
                                    if client_disconnected:
                                        break

                                    try:
                                        event = json.loads(raw_msg)
                                    except json.JSONDecodeError:
                                        continue

                                    event_type = event.get("type")

                                    if event_type == "session.updated":
                                        session_ready.set()
                                        logger.info("[GROK-RX] Session ready — audio stream open")

                                    elif event_type == "response.output_audio.delta":
                                        delta: str = event.get("delta", "")
                                        if not delta:
                                            continue

                                        if not ai_is_speaking:
                                            ai_is_speaking = True
                                            ai_chunk_counter = 0
                                            await send_to_client_json({
                                                "type": "ai_started_speaking",
                                                "timestamp": time.time() * 1000,
                                            })

                                        ai_chunk_counter += 1
                                        send_ts = time.time() * 1000
                                        logger.debug(
                                            f"[GROK-RX] server_audio #{ai_chunk_counter} "
                                            f"b64_len={len(delta)}"
                                        )
                                        await send_to_client_json({
                                            "type": "server_audio",
                                            "chunk_id": ai_chunk_counter,
                                            "server_timestamp": send_ts,
                                            "timestamp": send_ts,
                                            "audio": delta,
                                            # approximate raw byte count without re-decoding
                                            "chunk_size": len(delta) * 3 // 4,
                                        })

                                    elif event_type == "response.output_audio.done":
                                        ai_is_speaking = False
                                        ai_chunk_counter = 0
                                        await send_to_client_json({"type": "ai_finished_speaking"})
                                        logger.info("[GROK-RX] AI finished speaking")

                                    elif event_type == "input_audio_buffer.speech_started":
                                        # Server VAD detected user speech — interrupt current AI response.
                                        logger.info("[GROK-RX] Speech detected, interrupting AI")
                                        if ai_is_speaking:
                                            ai_is_speaking = False
                                            ai_chunk_counter = 0
                                            await send_to_client_json({"type": "ai_interrupted"})
                                        try:
                                            await grok_ws.send(json.dumps({"type": "response.cancel"}))
                                        except Exception:
                                            pass

                                    elif event_type == "response.output_audio_transcript.done":
                                        transcript = event.get("transcript", "")
                                        if transcript:
                                            await send_to_client_json({
                                                "type": "ai_transcript",
                                                "text": transcript,
                                                "timestamp": time.time() * 1000,
                                            })

                                    elif event_type == "error":
                                        logger.error(f"[GROK-RX] API error: {event}")
                                        await send_to_client_json({
                                            "type": "error",
                                            "message": event.get("message", "xAI API error"),
                                        })

                                logger.info("[GROK-RX] Receive stream ended")

                            except asyncio.CancelledError:
                                logger.info("[GROK-RX] Task cancelled")
                            except Exception as e:
                                logger.error(f"[GROK-RX] Error: {e}", exc_info=True)

                        # ── client → Grok ───────────────────────────────────
                        async def grok_sender():
                            try:
                                # Block until session.updated arrives — Grok drops audio sent before this.
                                await asyncio.wait_for(session_ready.wait(), timeout=10.0)
                                logger.info("[GROK-TX] Session ready, forwarding audio")

                                while not client_disconnected:
                                    try:
                                        data = await asyncio.wait_for(
                                            audio_queue.get(), timeout=0.02
                                        )
                                    except asyncio.TimeoutError:
                                        continue

                                    if isinstance(data, bytes):
                                        if len(data) == 0:
                                            continue
                                        await grok_ws.send(json.dumps({
                                            "type": "input_audio_buffer.append",
                                            "audio": base64.b64encode(data).decode(),
                                        }))

                                    elif isinstance(data, dict):
                                        if data.get("type") == "client_audio":
                                            b64 = data.get("audio", "")
                                            if not b64:
                                                continue
                                            padding = len(b64) % 4
                                            if padding:
                                                b64 += "=" * (4 - padding)
                                            await grok_ws.send(json.dumps({
                                                "type": "input_audio_buffer.append",
                                                "audio": b64,
                                            }))

                                    await asyncio.sleep(0)

                            except asyncio.TimeoutError:
                                logger.error("[GROK-TX] Timed out waiting for session.updated")
                                await send_to_client_json({
                                    "type": "error",
                                    "message": "xAI session setup timed out",
                                })
                            except asyncio.CancelledError:
                                logger.info("[GROK-TX] Task cancelled")
                            except Exception as e:
                                logger.error(f"[GROK-TX] Error: {e}", exc_info=True)

                        receiver_task = asyncio.create_task(grok_receiver())
                        sender_task = asyncio.create_task(grok_sender())

                        done, pending = await asyncio.wait(
                            [receiver_task, sender_task],
                            return_when=asyncio.FIRST_COMPLETED,
                        )

                        for task in done:
                            try:
                                task.result()
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                logger.error(f"[GROK] Task failed: {e}", exc_info=True)

                        for task in pending:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                        if client_disconnected:
                            logger.info("[GROK] Client disconnected, ending session")
                            break

                        # Grok session dropped (network/timeout) but client is still alive.
                        session_duration = time.time() - connection_start_time
                        logger.info(
                            f"[GROK] Session ended after {session_duration:.1f}s. Reconnecting..."
                        )
                        if session_duration < 5.0:
                            reconnect_count += 1
                            await asyncio.sleep(0.3)

                        if not client_disconnected:
                            try:
                                await send_to_client_json({
                                    "type": "warning",
                                    "message": "AI session interrupted. Reconnecting...",
                                })
                            except Exception:
                                pass

                except Exception as e:
                    logger.error(f"[GROK] Connection error: {e}", exc_info=True)
                    reconnect_count += 1
                    if client_disconnected or reconnect_count >= max_reconnects:
                        break
                    try:
                        await send_to_client_json({
                            "type": "warning",
                            "message": "Connection error. Retrying...",
                        })
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)

        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass

        if reconnect_count >= max_reconnects:
            logger.error("[GROK] Max reconnects reached, closing session")
            await send_to_client_json({
                "type": "error",
                "message": "AI session ended after too many reconnections",
            })


grok_live_service = GrokLiveService()
