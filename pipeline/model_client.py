"""
    Model Client for Pipeline
    
    Client for interacting with the model.

    Supported Models: Deepseek, Qwen, GPT, GLM, MinMax, and more. Switch easily between models through environment variables.
    Response Format: 
    {
        "content": "The model's content to the input query.",
        "usage": {
            "prompt_tokens": "The number of tokens in the prompt.",
            "completion_tokens": "The number of tokens in the completion."
        }
    }
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import os
import time
from typing import Any
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    

    @property
    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens
        }

    def __str__(self) -> str:
        return f"Token Usage: {{'prompt_tokens': {self.prompt_tokens}, 'completion_tokens': {self.completion_tokens}, 'total_tokens': {self.total_tokens}}}"

@dataclass
class ModelResponse:
    content: str
    token_usage : TokenUsage = field(default_factory=TokenUsage)

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "token_usage": self.token_usage.to_dict
        }


# Abstract Base Class for Model Clients
class LLMClient(ABC):
    def __init__(self, api_url: str, api_key: str, model_name: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.client = httpx.Client(timeout=httpx.Timeout(60.0))

    @abstractmethod
    def generate_text(self, message: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> ModelResponse:
        raise NotImplementedError("This method should be overridden by subclasses.")

    def close(self) -> None:
        self.client.close()

class OpenAICompatibleClient(LLMClient):

    def generate_text(self, message: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> ModelResponse:
        url = f"{self.api_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model_name,
            "messages": message,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage_data = data.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0)
        )
        return ModelResponse(content, token_usage)

def chat_with_retries(model_client: LLMClient, message: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000, retries: int = 3, backoff: float = 2.0) -> ModelResponse:
    last_error: Exception | None = None
    for i in range(retries):
        logger.info(f"Request attempt {i+1}/{retries}...")
        try:
            response = model_client.generate_text(message, temperature, max_tokens)
            if i > 0:
                logger.info(f"Request succeeded on attempt {i+1}/{retries}.")
            return response
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError):
                logger.error(f"Request failed with status code {exc.response.status_code}: {exc.response.text}")
            else:
                logger.error(f"Request failed with network error: {exc}")
            if i < retries - 1:
                sleep_time = backoff ** i
                logger.info(f"Retrying in {sleep_time:.1f}s (attempt {i+2}/{retries})...")
                time.sleep(sleep_time)
            else:
                logger.error("Request failed after maximum number of retries.")
    raise last_error if last_error is not None else RuntimeError("chat_with_retries failed with no error captured")
    

def load_model_client() -> LLMClient:
    api_url = os.getenv("API_URL")
    api_key = os.getenv("API_KEY")
    model_name = os.getenv("MODEL_NAME")
    missing = [name for name, value in (
        ("API_URL", api_url), ("API_KEY", api_key), ("MODEL_NAME", model_name)
    ) if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return OpenAICompatibleClient(api_url, api_key, model_name)

def quick_chat(prompt: str, system: str = "你是一名 AI 技术分析助手") -> ModelResponse:
    message = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}
    ]
    model_client = load_model_client()
    try:
        response = chat_with_retries(model_client, message)
        return response
    except Exception as e:
        logger.error(f"Error occurred during chat: {e}")
        return ModelResponse("Error: An error occurred during the chat.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("Testing model client...")
    try:
        response = quick_chat("介绍什么是AI Agent")
        logger.info(f"Response: {response.content}")
        logger.info(f"Token Usage: {response.token_usage}")
    except Exception as e:
        logger.error(f"Error occurred during testing: {e}")
 