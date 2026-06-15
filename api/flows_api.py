from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.preview import build_preview
from core.registry import get_flow, list_flows
from core.runner import start_task

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.get("")
def flows():
    return list_flows()


@router.get("/{flow_id}")
def flow_detail(flow_id: str):
    flow = get_flow(flow_id)
    if flow is None:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow


@router.post("/{flow_id}/preview")
def preview_flow(flow_id: str, params: dict):
    try:
        return build_preview("flow", flow_id, params)
    except KeyError:
        raise HTTPException(status_code=404, detail="Flow not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{flow_id}/run")
def run_flow(flow_id: str, params: dict):
    try:
        return start_task("flow", flow_id, params)
    except KeyError:
        raise HTTPException(status_code=404, detail="Flow not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
