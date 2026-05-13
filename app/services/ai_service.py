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
