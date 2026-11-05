"""Multi-provider LLM interface supporting AWS Bedrock, OpenRouter, and Mock providers."""

import json
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class BaseLLMModel(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def invoke(
        self,
        messages: list[dict[str, str]],
        system_message: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Invoke the LLM with messages and optional system message/response format.

        Args:
            messages: List of dicts with 'role' ('user', 'assistant') and 'content'.
            system_message: Optional system prompt instructions.
            response_format: Optional format constraint, e.g. {"type": "json_object"}.

        Returns:
            The generated text response string.
        """
        pass


class BedrockModel(BaseLLMModel):
    """AWS Bedrock model provider using the unified Bedrock Converse API.

    Supports Claude 3.5 Sonnet, Nova, Llama 3, and any model hosted on Bedrock.
    """

    DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    def __init__(
        self,
        model_id: str | None = None,
        region_name: str | None = None,
        profile_name: str | None = None,
        client: Any = None,
    ):
        """Initialize AWS Bedrock client.

        Args:
            model_id: AWS Bedrock model ID. Defaults to Claude 3.5 Sonnet v2.
            region_name: AWS region (e.g. 'us-east-1', 'us-west-2').
            profile_name: Optional AWS credentials profile name.
            client: Optional pre-configured boto3 bedrock-runtime client.
        """
        self.model_id = model_id or os.environ.get("AWS_BEDROCK_MODEL_ID", self.DEFAULT_MODEL_ID)
        self.region_name = region_name or os.environ.get(
            "AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1")
        )

        if client is not None:
            self.client = client
        else:
            try:
                import boto3
            except ImportError as e:
                raise ImportError(
                    "boto3 is required to use AWS Bedrock. Install with: poetry install --extras ai"
                ) from e

            # Support modern Amazon Bedrock API Key (Bearer Token)
            bearer_token = (
                os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
                or os.environ.get("BEDROCK_API_KEY")
                or os.environ.get("AWS_BEDROCK_API_KEY")
            )
            if bearer_token:
                os.environ["AWS_BEARER_TOKEN_BEDROCK"] = bearer_token
                # Boto3 natively authenticates with AWS_BEARER_TOKEN_BEDROCK
                self.client = boto3.client("bedrock-runtime", region_name=self.region_name)
            else:
                session_kwargs: dict[str, Any] = {}
                if profile_name or os.environ.get("AWS_PROFILE"):
                    session_kwargs["profile_name"] = profile_name or os.environ.get("AWS_PROFILE")
                if self.region_name:
                    session_kwargs["region_name"] = self.region_name

                # Prioritize credentials from .env / environment variables over default files
                access_key = os.environ.get("AWS_ACCESS_KEY_ID")
                secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
                session_token = os.environ.get("AWS_SESSION_TOKEN")
                if access_key and secret_key:
                    session_kwargs["aws_access_key_id"] = access_key
                    session_kwargs["aws_secret_access_key"] = secret_key
                    if session_token:
                        session_kwargs["aws_session_token"] = session_token

                session = boto3.Session(**session_kwargs)
                self.client = session.client("bedrock-runtime", region_name=self.region_name)

    def invoke(
        self,
        messages: list[dict[str, str]],
        system_message: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Invoke model via AWS Bedrock Converse API."""
        bedrock_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            # Bedrock converse supports 'user' and 'assistant' roles
            if role not in ("user", "assistant"):
                role = "user"
            bedrock_messages.append(
                {
                    "role": role,
                    "content": [{"text": msg.get("content", "")}],
                }
            )

        converse_kwargs: dict[str, Any] = {
            "modelId": self.model_id,
            "messages": bedrock_messages,
        }

        if system_message:
            # Bedrock converse expects system as a list of dicts with text
            sys_prompt = system_message
            if response_format and response_format.get("type") == "json_object":
                sys_prompt += "\nIMPORTANT: You must respond ONLY with valid JSON conforming to the requested schema. Do not include markdown code block wrappers or extraneous commentary."
            converse_kwargs["system"] = [{"text": sys_prompt}]
        elif response_format and response_format.get("type") == "json_object":
            converse_kwargs["system"] = [
                {"text": "You must respond ONLY with valid JSON. Do not include markdown code blocks or explanations."}
            ]

        response = self.client.converse(**converse_kwargs)
        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        if not content_blocks:
            raise RuntimeError(f"Empty response from Bedrock model {self.model_id}")

        return content_blocks[0].get("text", "")


class OpenRouterModel(BaseLLMModel):
    """OpenRouter LLM provider for OpenAI-compatible completions."""

    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model_name: str = "anthropic/claude-3.5-sonnet", api_key: str | None = None):
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/subroy13/handanim",
            "X-Title": "handanim",
            "Content-Type": "application/json",
        }

    def invoke(
        self,
        messages: list[dict[str, str]],
        system_message: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        try:
            import requests
        except ImportError as e:
            raise ImportError("requests is required for OpenRouter. Install with: poetry install --extras ai") from e

        message_list = []
        if system_message:
            message_list.append({"role": "system", "content": system_message})
        message_list.extend(messages)

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": message_list,
        }
        if response_format:
            payload["response_format"] = response_format

        response = requests.post(
            self.BASE_URL,
            headers=self.headers,
            json=payload,  # Send dictionary directly, avoid json.dumps double-encoding
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter API Error: {response.status_code} - {response.text}")

        response_data = response.json()
        if "choices" not in response_data or len(response_data["choices"]) == 0:
            raise RuntimeError("No choices found in OpenRouter response.")
        return response_data["choices"][0]["message"]["content"]


class MockModel(BaseLLMModel):
    """Deterministic mock model for testing and offline runs."""

    def __init__(
        self,
        responses: list[str] | None = None,
        response_fn: Callable[[list[dict[str, str]], str | None], str] | None = None,
    ):
        self.responses = list(responses) if responses else []
        self.response_fn = response_fn
        self.call_history: list[dict[str, Any]] = []

    def invoke(
        self,
        messages: list[dict[str, str]],
        system_message: str | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        self.call_history.append(
            {
                "messages": messages,
                "system_message": system_message,
                "response_format": response_format,
            }
        )
        if self.response_fn:
            return self.response_fn(messages, system_message)
        if self.responses:
            return self.responses.pop(0)
        return json.dumps(
            {
                "title": "Mock Scene",
                "scenes": [
                    {
                        "id": 1,
                        "title": "Introduction",
                        "duration": 3.0,
                        "drawables": [{"id": "text_1", "type": "Text", "params": {"text": "Hello World"}}],
                        "animations": [
                            {"drawable_id": "text_1", "type": "SketchAnimation", "start_time": 0.0, "duration": 2.0}
                        ],
                    }
                ],
            }
        )


def get_model(
    provider: str | None = None,
    model_name: str | None = None,
    **kwargs: Any,
) -> BaseLLMModel:
    """Factory to instantiate the appropriate LLM provider.

    Resolution order:
    1. Explicit `provider` argument ('bedrock', 'openrouter', 'mock').
    2. Environment variable `HANDANIM_AI_PROVIDER`.
    3. If AWS credentials exist, defaults to Bedrock.
    4. If OPENROUTER_API_KEY exists, defaults to OpenRouter.
    5. Fallback to MockModel.
    """
    selected_provider = (
        provider
        or os.environ.get("HANDANIM_AI_PROVIDER")
        or (
            "bedrock"
            if os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
            or os.environ.get("BEDROCK_API_KEY")
            or os.environ.get("AWS_BEDROCK_API_KEY")
            or os.environ.get("AWS_PROFILE")
            or os.environ.get("AWS_ACCESS_KEY_ID")
            else None
        )
        or ("openrouter" if os.environ.get("OPENROUTER_API_KEY") else None)
        or "mock"
    ).lower()

    if selected_provider == "bedrock":
        return BedrockModel(model_id=model_name, **kwargs)
    elif selected_provider == "openrouter":
        return OpenRouterModel(model_name=model_name or "anthropic/claude-3.5-sonnet", **kwargs)
    elif selected_provider == "mock":
        return MockModel(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider '{selected_provider}'. Supported: 'bedrock', 'openrouter', 'mock'.")
