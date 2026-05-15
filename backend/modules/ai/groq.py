import os
import asyncio
import logging
from groq import Groq
from typing import Optional
from .base import AIProvider

logger = logging.getLogger(__name__)

class GroqProvider(AIProvider):
    def __init__(self, api_key: str, model_name: str = "llama-3.1-8b-instant"):
        self.client = Groq(api_key=api_key)
        self.model_name = model_name
        self.max_retries = 3

    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        for attempt in range(self.max_retries):
            try:
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})

                loop = asyncio.get_event_loop()
                completion = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1024,
                    top_p=1,
                    stream=False,
                    stop=None,
                ))
                return completion.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq API attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) + 1  # Exponential backoff
                    await asyncio.sleep(wait_time)
                else:
                    return f"Error connecting to Groq: {str(e)}"
        return "Failed to generate response from Groq after multiple attempts."
