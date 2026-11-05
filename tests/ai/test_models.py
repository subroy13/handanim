"""Unit tests for LLM providers (MockModel, BedrockModel, OpenRouterModel, and get_model)."""

from unittest.mock import MagicMock

from handanim_ai.models import BedrockModel, MockModel, get_model


def test_mock_model():
    mock = MockModel(responses=['{"title": "Custom Scene"}'])
    res = mock.invoke(messages=[{"role": "user", "content": "hi"}], system_message="sys")
    assert res == '{"title": "Custom Scene"}'
    assert len(mock.call_history) == 1
    assert mock.call_history[0]["system_message"] == "sys"


def test_mock_model_response_fn():
    mock = MockModel(response_fn=lambda msgs, sys: f"Echo: {msgs[0]['content']}")
    res = mock.invoke(messages=[{"role": "user", "content": "hello"}])
    assert res == "Echo: hello"


def test_get_model_resolution(monkeypatch):
    monkeypatch.setenv("HANDANIM_AI_PROVIDER", "mock")
    m = get_model()
    assert isinstance(m, MockModel)


def test_bedrock_bearer_token_detection(monkeypatch):
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-bearer-token")
    monkeypatch.delenv("HANDANIM_AI_PROVIDER", raising=False)
    # Boto3 client mock
    mock_boto3 = MagicMock()
    monkeypatch.setattr("boto3.client", mock_boto3)
    bedrock = BedrockModel(model_id="global.anthropic.claude-opus-4-5-20251101-v1:0")
    assert bedrock.model_id == "global.anthropic.claude-opus-4-5-20251101-v1:0"
    mock_boto3.assert_called_with("bedrock-runtime", region_name="us-east-1")


def test_bedrock_model_converse_invocation():
    # Mock boto3 bedrock client
    mock_client = MagicMock()
    mock_client.converse.return_value = {"output": {"message": {"content": [{"text": "Bedrock response"}]}}}
    bedrock = BedrockModel(client=mock_client)
    res = bedrock.invoke(
        messages=[{"role": "user", "content": "test prompt"}],
        system_message="system instruction",
    )
    assert res == "Bedrock response"
    mock_client.converse.assert_called_once()
    kwargs = mock_client.converse.call_args[1]
    assert kwargs["messages"][0]["role"] == "user"
    assert kwargs["messages"][0]["content"][0]["text"] == "test prompt"
    assert kwargs["system"][0]["text"] == "system instruction"
