import requests
import json
from typing import Optional, Dict, Any, List, Generator, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ModelType(Enum):
    QWEN3_4B = "qwen3:4b"
    QWEN3_1_7B = "qwen3:1.7b"


@dataclass
class OllamaResponse:
    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None

# --- Client Class ---
class OllamaClient:

    def __init__(
        self,
        base_url: str,
        model_name: str = ModelType.QWEN3_4B.value
    ):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.api_chat = f"{self.base_url}/api/chat"
        self.chat_history = []

    def test_connection(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def chat(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        use_history: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Sends a single, non-streaming chat request."""
        messages = self._prepare_messages(user_prompt, system_prompt, use_history)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }
        payload["options"].update(kwargs)

        try:
            response = requests.post(self.api_chat, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            if use_history:
                self.chat_history.append(result["message"])
            return result
        except requests.RequestException as e:
            logger.error(f"Failed to chat: {str(e)}")
            raise

    def chat_stream(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        use_history: bool = True,
        **kwargs
    ) -> Generator[str, None, None]:
        """Sends a streaming chat request and yields content chunks."""
        messages = self._prepare_messages(user_prompt, system_prompt, use_history)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature}
        }
        payload["options"].update(kwargs)

        try:
            response = requests.post(
                self.api_chat,
                json=payload,
                stream=True,
                timeout=60
            )
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("done") == True:
                            break # Streaming finished

                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            full_response += chunk
                            yield chunk
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode stream line: {line}")

            if use_history:
                self.chat_history.append({"role": "assistant", "content": full_response})

        except requests.RequestException as e:
            logger.error(f"Failed to generate streaming response: {str(e)}")
            yield f"Stream hatası: {str(e)}"

    def _prepare_messages(self, user_prompt: str, system_prompt: Optional[str], use_history: bool) -> List[Dict[str, str]]:
        """Helper function to construct message list."""
        if use_history:
            messages = self.chat_history.copy()
        else:
            messages = []

        if system_prompt and not any(msg.get("role") == "system" for msg in messages):
            messages.insert(0, {"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_prompt})
        return messages

    def clear_chat_history(self):
        self.chat_history = []

    def set_chat_history(self, history: List[Dict[str, str]]):
        self.chat_history = history
