import base64
import logging

logger = logging.getLogger(__name__)

class AudioStreamService:
    @staticmethod
    def process_incoming_chunk(chunk: bytes) -> bytes:
        # If any preprocessing is needed for PCM16 before sending to Gemini, do it here.
        # Currently, Gemini accepts raw 16kHz PCM16, so we return as is.
        return chunk

    @staticmethod
    def format_outgoing_chunk(chunk: bytes) -> bytes:
        # If any postprocessing is needed before sending to client, do it here.
        return chunk

audio_stream_service = AudioStreamService()
