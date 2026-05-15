from abc import ABC, abstractmethod
from typing import Optional

class AIProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generates a text response based on the provided prompt."""
        pass
