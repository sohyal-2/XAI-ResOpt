"""API router exposing modular tools and MCP tool definitions."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.rate_limit import RateLimiter
from app.core.security import get_current_user
from app.integrations.base import ToolResult
from app.integrations.registry import get_mcp_manifest, get_tool_registry
from app.models import User

router = APIRouter(prefix="/api/tools", tags=["tools"])

tools_limiter = RateLimiter(times=30, seconds=60, key_prefix="tools:exec")


class ToolExecuteRequest(BaseModel):
    """Request payload for executing a modular tool."""
    params: dict[str, Any] = Field(default_factory=dict)


@router.get("", response_model=list[dict[str, Any]])
async def list_available_tools() -> list[dict[str, Any]]:
    """Returns the Model Context Protocol (MCP) definitions of all 9 modular tools."""
    return get_mcp_manifest()


@router.post("/{tool_name}/execute", response_model=ToolResult, dependencies=[Depends(tools_limiter)])
async def execute_tool(
    tool_name: str,
    req: ToolExecuteRequest,
    current_user: User = Depends(get_current_user),
) -> ToolResult:
    """Executes a modular tool by name with provided parameters and returns structured ToolResult."""
    registry = get_tool_registry()
    tool = registry.get(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found. Available: {[t.name for t in registry.list_tools()]}",
        )

    context = {"user_id": str(current_user.id)}
    result = await registry.execute(tool_name, req.params, context=context)
    return result
