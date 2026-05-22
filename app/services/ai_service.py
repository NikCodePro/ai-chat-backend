import logging
from typing import AsyncGenerator, List, Dict

from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import settings

logger = logging.getLogger(__name__)

class AIService:
    @staticmethod
    def get_model(provider: str = "mistral"):
        if provider == "openai":
            return ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model="gpt-4-turbo-preview",
                streaming=True
            )
        elif provider == "gemini":
            return ChatGoogleGenerativeAI(
                google_api_key=settings.GOOGLE_API_KEY,
                model="gemini-pro",
                streaming=True
            )
        else: # Default to Mistral
            return ChatMistralAI(
                api_key=settings.MISTRAL_API_KEY,
                model="mistral-large-latest",
                streaming=True
            )

    @classmethod
    async def stream_chat(
        cls, 
        message: str, 
        history: List[Dict[str, str]], 
        provider: str = "mistral"
    ) -> AsyncGenerator[str, None]:
        model = cls.get_model(provider)
        
        # Convert history to LangChain messages
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current message
        messages.append(HumanMessage(content=message))

        try:
            async for chunk in model.astream(messages):
                yield chunk.content
        except Exception as e:
            logger.error(f"Error in AI stream: {str(e)}")
            yield f"Error: {str(e)}"

    @classmethod
    async def generate_chat_title(cls, user_message: str, provider: str = "mistral") -> str:
        model = cls.get_model(provider)
        prompt = f"Generate a very short, concise title (maximum 3-4 words) for a chat conversation that begins with the following message. Do not use quotes in your response. Just the title itself.\n\nMessage: {user_message}"
        messages = [HumanMessage(content=prompt)]
        
        try:
            # For titles, we don't need streaming
            response = await model.ainvoke(messages)
            return response.content.strip().strip('"').strip("'")
        except Exception as e:
            logger.error(f"Error generating chat title: {str(e)}")
            return "New Chat"

    @classmethod
    async def transcribe_audio(cls, base64_audio: str) -> str:
        import base64
        import asyncio
        from google import genai
        from google.genai import types
        import os
        from app.config import settings

        try:
            audio_bytes = base64.b64decode(base64_audio)
        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            raise ValueError("Invalid base64 audio data")

        api_key = settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not configured for transcription")
            raise ValueError("Google API key is not configured on the server")

        client = genai.Client(api_key=api_key)

        loop = asyncio.get_running_loop()

        def call_gemini():
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type="audio/wav",
                    ),
                    "Provide a highly accurate transcription of this audio. Output only the transcription, nothing else."
                ]
            )
            return response.text.strip() if response.text else ""

        try:
            transcription = await loop.run_in_executor(None, call_gemini)
            return transcription
        except Exception as e:
            logger.error(f"Error in Gemini transcription: {e}")
            raise e
