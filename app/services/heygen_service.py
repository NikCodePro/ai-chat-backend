import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

LIVEAVATAR_API_URL = "https://api.liveavatar.com"


class HeyGenService:
    def __init__(self):
        self.api_key = settings.HEYGEN_API_KEY
        # Store the active session token so we can stop it later
        self._active_session_token: str | None = None

    async def stop_existing_session(self) -> None:
        """Stop any active session. Call this before creating a new one."""
        if not self._active_session_token:
            return
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{LIVEAVATAR_API_URL}/v1/sessions/stop",
                    headers={
                        "Authorization": f"Bearer {self._active_session_token}",
                        "Content-Type": "application/json",
                    },
                )
                logger.info(f"[LiveAvatar] Stopped existing session: {response.status_code}")
        except Exception as e:
            logger.warning(f"[LiveAvatar] Failed to stop existing session: {e}")
        finally:
            self._active_session_token = None

    async def get_session_token(self) -> dict:
        """Get a session token from LiveAvatar API and start the session to get LiveKit credentials."""
        if not self.api_key:
            raise ValueError("HEYGEN_API_KEY is not set in .env")

        avatar_id = settings.LIVEAVATAR_AVATAR_ID
        voice_id = settings.LIVEAVATAR_VOICE_ID

        if not avatar_id:
            raise ValueError(
                "LIVEAVATAR_AVATAR_ID is not set in .env. "
                "Go to https://app.liveavatar.com, open your avatar, and copy its UUID."
            )

        # Always stop any lingering session first to avoid concurrency limit errors
        await self.stop_existing_session()

        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

        # avatar_persona is always required for FULL mode
        avatar_persona: dict = {"language": settings.LIVEAVATAR_LANGUAGE}
        if voice_id:
            avatar_persona["voice_id"] = voice_id

        body: dict = {
            "mode": "FULL",
            "avatar_id": avatar_id,
            "avatar_persona": avatar_persona,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Get Session Token
            logger.info(f"[LiveAvatar] Requesting session token for avatar: {avatar_id}")
            token_response = await client.post(
                f"{LIVEAVATAR_API_URL}/v1/sessions/token",
                headers=headers,
                json=body,
            )

            token_data = token_response.json()
            logger.info(f"[LiveAvatar] Token response ({token_response.status_code}): {token_data}")

            if token_response.status_code != 200 or token_data.get("code") != 1000:
                raise ValueError(f"Failed to get LiveAvatar session token: {token_data}")

            session_token = token_data["data"]["session_token"]
            # Store it so we can stop it later
            self._active_session_token = session_token

            # Step 2: Start Session → returns LiveKit URL + client token
            session_headers = {
                "Authorization": f"Bearer {session_token}",
                "Content-Type": "application/json",
            }

            logger.info("[LiveAvatar] Starting session...")
            start_response = await client.post(
                f"{LIVEAVATAR_API_URL}/v1/sessions/start",
                headers=session_headers,
            )

            start_data = start_response.json()
            logger.info(f"[LiveAvatar] Start response ({start_response.status_code}): {start_data}")

            if not start_response.is_success or start_data.get("code") != 1000:
                self._active_session_token = None
                raise ValueError(f"Failed to start LiveAvatar session: {start_data.get('message', start_data)}")

            # Returns: { session_id, livekit_url, livekit_client_token }
            return start_data["data"]

    async def stop_session(self) -> None:
        """Explicitly stop the current session (called when user ends the video call)."""
        await self.stop_existing_session()


heygen_service = HeyGenService()
