"""Comprehensive unit and integration tests for AI provider abstraction and tool architecture."""

import json
import pytest
import httpx
from pydantic import BaseModel

from app.ai.anthropic_adapter import AnthropicProvider
from app.ai.base import (
    ChatMessage,
    LLMProvider,
    LLMResponse,
    LLMToolCall,
    LLMToolResponse,
    TokenUsage,
)
from app.ai.factory import get_ai_status, get_llm_provider
from app.ai.gemini_adapter import GeminiProvider
from app.ai.mock_adapter import DevelopmentMockProvider
from app.ai.ollama_adapter import OllamaProvider
from app.ai.openai_adapter import OpenAIProvider
from app.ai.tool_runner import ToolRunner
from app.integrations.registry import get_tool_registry


class SampleReport(BaseModel):
    summary: str
    score: float


# ==============================================================================
# 1. Base Contracts & Data Structures
# ==============================================================================

def test_token_usage_and_llm_response_structure():
    usage = TokenUsage(prompt_tokens=50, completion_tokens=25, total_tokens=75)
    resp = LLMResponse(
        content="Optimized experience bullet",
        model="gpt-4o-mini",
        provider="openai",
        usage=usage,
        finish_reason="stop",
    )
    assert resp.content == "Optimized experience bullet"
    assert resp.usage.total_tokens == 75
    assert resp.provider == "openai"


def test_tool_call_and_tool_response_structure():
    call = LLMToolCall(
        id="call_123",
        tool_name="github_search",
        arguments={"query": "fastapi"},
    )
    tool_resp = LLMToolResponse(
        content=None,
        tool_calls=[call],
        model="claude-3-5-sonnet-20241022",
        provider="anthropic",
    )
    assert tool_resp.has_tool_calls is True
    assert tool_resp.tool_calls[0].tool_name == "github_search"
    assert tool_resp.tool_calls[0].arguments["query"] == "fastapi"


# ==============================================================================
# 2. Provider Adapters with Mocked Transport
# ==============================================================================

@pytest.mark.asyncio
async def test_openai_adapter_generate_and_tools():
    openai_json_response = {
        "id": "chatcmpl-test",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {
                                "name": "resume_parser",
                                "arguments": "{\"text\": \"Jane Doe\\nSoftware Engineer\"}",
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 30, "total_tokens": 150},
    }

    def mock_handler(request: httpx.Request):
        assert "api.openai.com" in str(request.url)
        assert request.headers.get("Authorization") == "Bearer sk-test-key"
        return httpx.Response(200, json=openai_json_response)

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAIProvider(api_key="sk-test-key", model="gpt-4o-mini", transport=transport)
    registry = get_tool_registry()

    res = await provider.generate_with_tools(
        prompt="Parse this candidate resume",
        tools=registry.list_tools(),
    )

    assert res.has_tool_calls is True
    assert res.tool_calls[0].tool_name == "resume_parser"
    assert res.tool_calls[0].arguments["text"] == "Jane Doe\nSoftware Engineer"
    assert res.usage.total_tokens == 150


@pytest.mark.asyncio
async def test_anthropic_adapter_messages_and_tools():
    anthropic_json_response = {
        "id": "msg_test",
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "tool_use",
        "content": [
            {"type": "text", "text": "I will examine the GitHub repository details."},
            {
                "type": "tool_use",
                "id": "toolu_01",
                "name": "github_repo_reader",
                "input": {"owner": "xai", "repo": "resopt"},
            },
        ],
        "usage": {"input_tokens": 80, "output_tokens": 40},
    }

    def mock_handler(request: httpx.Request):
        assert "api.anthropic.com" in str(request.url)
        assert request.headers.get("x-api-key") == "anthropic-test-key"
        assert request.headers.get("anthropic-version") == "2023-06-01"
        body = json.loads(request.content.decode("utf-8"))
        assert "tools" in body
        return httpx.Response(200, json=anthropic_json_response)

    transport = httpx.MockTransport(mock_handler)
    provider = AnthropicProvider(api_key="anthropic-test-key", transport=transport)
    registry = get_tool_registry()

    res = await provider.generate_with_tools(
        prompt="Check repository details",
        tools=registry.list_tools(),
    )

    assert res.has_tool_calls is True
    assert res.tool_calls[0].tool_name == "github_repo_reader"
    assert res.tool_calls[0].arguments == {"owner": "xai", "repo": "resopt"}
    assert "GitHub repository details" in res.content


@pytest.mark.asyncio
async def test_gemini_adapter_generate_and_tools():
    gemini_json_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "functionCall": {
                                "name": "ats_evaluator",
                                "args": {
                                    "resume_text": "Sample resume",
                                    "job_text": "Sample job",
                                },
                            }
                        }
                    ],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 90,
            "candidatesTokenCount": 35,
            "totalTokenCount": 125,
        },
    }

    def mock_handler(request: httpx.Request):
        assert "generativelanguage.googleapis.com" in str(request.url)
        assert "key=gemini-test-key" in str(request.url)
        return httpx.Response(200, json=gemini_json_response)

    transport = httpx.MockTransport(mock_handler)
    provider = GeminiProvider(api_key="gemini-test-key", model="gemini-1.5-flash", transport=transport)
    registry = get_tool_registry()

    res = await provider.generate_with_tools(
        prompt="Calculate ATS score",
        tools=registry.list_tools(),
    )

    assert res.has_tool_calls is True
    assert res.tool_calls[0].tool_name == "ats_evaluator"
    assert res.tool_calls[0].arguments["resume_text"] == "Sample resume"
    assert res.usage.total_tokens == 125


@pytest.mark.asyncio
async def test_ollama_adapter_generate():
    ollama_json_response = {
        "model": "llama3.2",
        "message": {
            "role": "assistant",
            "content": "Resume matches mandatory skill Python with grounded evidence.",
        },
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 60,
        "eval_count": 20,
    }

    def mock_handler(request: httpx.Request):
        assert "localhost:11434" in str(request.url)
        return httpx.Response(200, json=ollama_json_response)

    transport = httpx.MockTransport(mock_handler)
    provider = OllamaProvider(model="llama3.2", transport=transport)

    res = await provider.generate(prompt="Evaluate skill match")

    assert res.provider == "ollama"
    assert "grounded evidence" in res.content
    assert res.usage.total_tokens == 80


# ==============================================================================
# 3. Development Mode & Offline Mock Provider
# ==============================================================================

@pytest.mark.asyncio
async def test_development_mock_provider_offline_operation():
    """Verifies that the application operates cleanly in development mode when external keys are absent."""
    dev_provider = DevelopmentMockProvider()
    assert dev_provider.is_available() is True
    assert dev_provider.provider_name == "development_mock"

    # 1. Text generation works offline
    res_gen = await dev_provider.generate("Analyze candidate experience for backend role")
    assert "Development Mode" in res_gen.content
    assert res_gen.provider == "development_mock"

    # 2. Structured generation returns typed Pydantic object
    res_struct = await dev_provider.generate_structured(
        prompt="Generate candidate summary report",
        schema=SampleReport,
    )
    assert isinstance(res_struct, SampleReport)
    assert res_struct.score > 0

    # 3. Tool evaluation triggers tool calls matching available tools
    registry = get_tool_registry()
    res_tools = await dev_provider.generate_with_tools(
        prompt="Execute github_search for candidate repositories",
        tools=registry.list_tools(),
    )
    assert res_tools.has_tool_calls is True
    assert res_tools.tool_calls[0].tool_name == "github_search"


# ==============================================================================
# 4. Factory & Model Configuration via Environment Variables
# ==============================================================================

def test_provider_factory_fallback_when_keys_missing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv('GEMINI_API_KEY', '')
    monkeypatch.setenv('GOOGLE_API_KEY', '')
    monkeypatch.setenv('OPENROUTER_API_KEY', '')
    monkeypatch.setenv("AI_PROVIDER", "auto")

    from app.core.config import get_settings
    get_settings.cache_clear()

    provider = get_llm_provider()
    assert isinstance(provider, DevelopmentMockProvider)
    assert provider.provider_name == "development_mock"


def test_provider_model_selection_configurable_via_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-mock-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-custom-2026")
    from app.core.config import get_settings
    get_settings.cache_clear()

    provider = OpenAIProvider()
    assert provider.default_model == "gpt-4o-custom-2026"
    assert provider.is_available() is True


# ==============================================================================
# 5. Modular Tool Converters (OpenAI, Anthropic, Gemini, MCP)
# ==============================================================================

def test_all_9_tools_support_mcp_and_multi_provider_formats():
    registry = get_tool_registry()
    tools = registry.list_tools()
    assert len(tools) >= 9

    expected_names = {
        "github_search",
        "github_repo_reader",
        "portfolio_reader",
        "resume_parser",
        "job_parser",
        "evidence_search",
        "vector_search",
        "ats_evaluator",
        "resume_renderer",
    }
    actual_names = {t.name for t in tools}
    assert expected_names.issubset(actual_names)

    for tool in tools:
        # 1. MCP format
        mcp = tool.to_mcp_tool()
        assert mcp["name"] == tool.name
        assert "description" in mcp
        assert mcp["inputSchema"]["type"] == "object"

        # 2. OpenAI format
        oai = tool.to_openai_tool()
        assert oai["type"] == "function"
        assert oai["function"]["name"] == tool.name
        assert oai["function"]["parameters"]["type"] == "object"

        # 3. Anthropic format
        ant = tool.to_anthropic_tool()
        assert ant["name"] == tool.name
        assert ant["input_schema"]["type"] == "object"

        # 4. Gemini format
        gem = tool.to_gemini_tool()
        assert gem["name"] == tool.name
        assert gem["parameters"]["type"] == "object"


# ==============================================================================
# 6. Multi-turn ToolRunner Execution
# ==============================================================================

@pytest.mark.asyncio
async def test_tool_runner_multi_turn_execution():
    dev_provider = DevelopmentMockProvider()
    registry = get_tool_registry()

    runner = ToolRunner(provider=dev_provider, registry=registry, max_iterations=3)
    result = await runner.run("Please run resume_parser to evaluate the candidate profile")

    assert result.iterations >= 1
    assert result.provider == "development_mock"
    assert len(result.tool_history) >= 1
    assert result.tool_history[0].tool_name == "resume_parser"
    assert result.tool_history[0].result.success is True


# ==============================================================================
# 7. Security: Provider API Keys Never Exposed to Client / Browser
# ==============================================================================

@pytest.mark.asyncio
async def test_security_provider_api_keys_never_exposed(monkeypatch):
    """Guarantees that sensitive provider API keys are NEVER exposed through status APIs."""
    secret_openai = "sk-supersecret-openai-key-999"
    secret_anthropic = "sk-ant-supersecret-anthropic-key-888"
    secret_gemini = "gemini-supersecret-api-key-777"

    monkeypatch.setenv("OPENAI_API_KEY", secret_openai)
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret_anthropic)
    monkeypatch.setenv("GEMINI_API_KEY", secret_gemini)

    from app.core.config import get_settings
    get_settings.cache_clear()

    status_data = get_ai_status()
    serialized = json.dumps(status_data)

    # API keys must NOT appear in the status output
    assert secret_openai not in serialized
    assert secret_anthropic not in serialized
    assert secret_gemini not in serialized

    # But configuration status (boolean flags) is reported
    configured_names = {p["name"] for p in status_data["configured_providers"] if p["configured"]}
    assert "openai" in configured_names
    assert "anthropic" in configured_names
    assert "gemini" in configured_names

    # Test through FastAPI HTTP endpoint
    import httpx
    from app.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/ai/status")
        assert resp.status_code == 200
        resp_text = resp.text
        assert secret_openai not in resp_text
        assert secret_anthropic not in resp_text
        assert secret_gemini not in resp_text
