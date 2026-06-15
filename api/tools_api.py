from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.preview import build_preview
from core.registry import get_tool, list_tools
from core.runner import start_task

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
def tools():
    return list_tools()


@router.get("/{tool_id}")
def tool_detail(tool_id: str):
    tool = get_tool(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.post("/{tool_id}/preview")
def preview_tool(tool_id: str, params: dict):
    try:
        return build_preview("tool", tool_id, params)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tool not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{tool_id}/run")
def run_tool(tool_id: str, params: dict):
    try:
        return start_task("tool", tool_id, params)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tool not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
