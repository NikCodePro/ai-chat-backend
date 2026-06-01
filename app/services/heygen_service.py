import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

HEYGEN_API_URL = "https://api.heygen.com/v1/streaming"

class HeyGenService:
    def __init__(self):
        self.api_key = settings.HEYGEN_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key
        }

    async def create_session(self, avatar_name: str = "Anna_public_3_20240108"):
        """Create a new WebRTC session with the avatar."""
        if not self.api_key:
            raise ValueError("HEYGEN_API_KEY is not set.")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEYGEN_API_URL}.new",
                headers=self.headers,
                json={"quality": "low", "avatar_name": avatar_name, "voice": {"rate": 1.0}}
            )
            response.raise_for_status()
            return response.json()["data"]

    async def start_session(self, session_id: str, sdp: dict):
        """Send the client's SDP answer to HeyGen to start the WebRTC connection."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEYGEN_API_URL}.start",
                headers=self.headers,
                json={"session_id": session_id, "sdp": sdp}
            )
            response.raise_for_status()
            return response.json()["data"]

    async def send_ice_candidate(self, session_id: str, candidate: dict):
        """Forward ICE candidates from client to HeyGen."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEYGEN_API_URL}.ice",
                headers=self.headers,
                json={"session_id": session_id, "candidate": candidate}
            )
            response.raise_for_status()
            return response.json()["data"]

    async def send_task(self, session_id: str, text: str):
        """Send text for the avatar to speak."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEYGEN_API_URL}.task",
                headers=self.headers,
                json={
                    "session_id": session_id,
                    "text": text,
                    "task_type": "talk"
                }
            )
            response.raise_for_status()
            return response.json()["data"]

    async def stop_session(self, session_id: str):
        """Close the avatar streaming session."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{HEYGEN_API_URL}.stop",
                headers=self.headers,
                json={"session_id": session_id}
            )
            response.raise_for_status()
            return response.json()["data"]

heygen_service = HeyGenService()
