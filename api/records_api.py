from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from core.runner import list_tasks, read_log, read_task, records_csv, request_cancel, resume_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def tasks():
    return list_tasks()


@router.get("/export.csv")
def export_tasks():
    return Response(
        records_csv(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=records.csv"},
    )


@router.get("/{task_id}")
def task_detail(task_id: str):
    try:
        return read_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")


@router.get("/{task_id}/logs")
def task_logs(task_id: str):
    try:
        return Response(read_log(task_id), media_type="text/plain; charset=utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task log not found")


@router.get("/{task_id}/logs/export")
def task_logs_export(task_id: str):
    try:
        return Response(
            read_log(task_id),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={task_id}.log"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task log not found")


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str):
    try:
        return request_cancel(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/resume")
def resume_task_api(task_id: str):
    try:
        return resume_task(task_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Task not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
