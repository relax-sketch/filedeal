from __future__ import annotations

import csv
import importlib
import io
import json
import os
import time
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from config import load_settings
from core.logger import TaskLogger
from core.path_utils import ensure_base_dirs, make_task_id, task_dir
from core.registry import get_flow, get_tool

TERMINAL_STATUSES = {"success", "failed", "canceled"}
executor = ThreadPoolExecutor(max_workers=2)
running_futures: dict[str, Future] = {}


class TaskCanceled(Exception):
    pass


def resolve_entry(entry: str) -> Callable[[dict, dict], dict]:
    module_name, func_name = entry.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, func_name)


def task_paths(task_id: str) -> tuple[Path, Path, Path]:
    directory = task_dir(task_id)
    return directory, directory / "task.json", directory / "log.txt"


def read_task(task_id: str) -> dict[str, Any]:
    _, task_path, _ = task_paths(task_id)
    if not task_path.exists():
        raise FileNotFoundError(task_id)
    last_error: Exception | None = None
    for _ in range(5):
        try:
            text = task_path.read_text(encoding="utf-8")
            if text.strip():
                return json.loads(text)
        except json.JSONDecodeError as exc:
            last_error = exc
        time.sleep(0.02)
    if last_error:
        raise last_error
    raise json.JSONDecodeError("empty task file", "", 0)


def write_task(task: dict[str, Any]) -> None:
    _, task_path, _ = task_paths(task["task_id"])
    task_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = task_path.with_name(f"{task_path.name}.{uuid.uuid4().hex}.tmp")
    tmp_path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, task_path)


def update_task(task_id: str, **updates: Any) -> dict[str, Any]:
    task = read_task(task_id)
    task.update(updates)
    write_task(task)
    return task


def list_tasks() -> list[dict[str, Any]]:
    ensure_base_dirs()
    tasks = []
    for path in sorted(task_dir("").glob("task_*/task.json"), reverse=True):
        try:
            tasks.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return tasks


def read_log(task_id: str) -> str:
    _, _, log_path = task_paths(task_id)
    if not log_path.exists():
        raise FileNotFoundError(task_id)
    return log_path.read_text(encoding="utf-8")


def records_csv() -> str:
    output = io.StringIO()
    fieldnames = [
        "task_id",
        "type",
        "name",
        "status",
        "started_at",
        "finished_at",
        "duration_seconds",
        "input_path",
        "output_path",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for task in list_tasks():
        writer.writerow({key: task.get(key, "") for key in fieldnames})
    return output.getvalue()


def request_cancel(task_id: str) -> dict[str, Any]:
    task = read_task(task_id)
    if task.get("status") in TERMINAL_STATUSES:
        return task
    task["cancel_requested"] = True
    write_task(task)
    return task


def check_cancel(context: dict[str, Any]) -> None:
    task = read_task(context["task_id"])
    if task.get("cancel_requested"):
        raise TaskCanceled("Task cancellation requested")


def set_current_step(context: dict[str, Any], step: str, index: int | None = None) -> None:
    task = read_task(context["task_id"])
    task["current_step"] = step
    if index is not None:
        task["current_step_index"] = index
    write_task(task)
    context["logger"].info("Step", step=step)


def set_current_target(context: dict[str, Any], input_path: str) -> None:
    task = read_task(context["task_id"])
    task["current_target_path"] = input_path
    write_task(task)


def _duration(started_at: str, finished_at: str) -> float:
    start = datetime.fromisoformat(started_at)
    finish = datetime.fromisoformat(finished_at)
    return round((finish - start).total_seconds(), 3)


def _execute_task(task_id: str, entry: str, params: dict[str, Any]) -> None:
    directory, _, log_path = task_paths(task_id)
    logger = TaskLogger(log_path)
    settings = load_settings()
    context = {
        "task_id": task_id,
        "logger": logger,
        "settings": settings,
        "preview": bool(params.get("preview")),
        "check_cancel": None,
        "set_current_step": None,
        "set_current_target": None,
    }
    context["check_cancel"] = lambda: check_cancel(context)
    context["set_current_step"] = lambda step, index=None: set_current_step(
        context, step, index
    )
    context["set_current_target"] = lambda input_path: set_current_target(context, input_path)
    try:
        logger.info("Task started", preview=context["preview"])
        update_task(task_id, status="running")
        result = resolve_entry(entry)(params, context) or {}
        finished_at = datetime.now().isoformat(timespec="seconds")
        status = "success" if result.get("success", True) else "failed"
        logger.success("Task finished" if status == "success" else "Task failed")
        task = read_task(task_id)
        task.update(
            {
                "status": status,
                "finished_at": finished_at,
                "duration_seconds": _duration(task["started_at"], finished_at),
                "message": result.get("message", ""),
                "output_path": result.get("output") or task.get("output_path", ""),
                "stats": result.get("stats", {}),
                "error": result.get("error", ""),
                "file_operations": result.get("file_operations", []),
            }
        )
        write_task(task)
    except TaskCanceled as exc:
        finished_at = datetime.now().isoformat(timespec="seconds")
        logger.warning(str(exc))
        task = read_task(task_id)
        task.update(
            {
                "status": "canceled",
                "finished_at": finished_at,
                "duration_seconds": _duration(task["started_at"], finished_at),
                "error": str(exc),
            }
        )
        write_task(task)
    except Exception as exc:
        finished_at = datetime.now().isoformat(timespec="seconds")
        logger.error(str(exc))
        logger.error(traceback.format_exc())
        task = read_task(task_id)
        task.update(
            {
                "status": "failed",
                "finished_at": finished_at,
                "duration_seconds": _duration(task["started_at"], finished_at),
                "error": str(exc),
            }
        )
        write_task(task)
    finally:
        running_futures.pop(task_id, None)


def start_task(kind: str, item_id: str, params: dict[str, Any]) -> dict[str, Any]:
    ensure_base_dirs()
    item = get_tool(item_id) if kind == "tool" else get_flow(item_id)
    if item is None:
        raise KeyError(item_id)
    if params.get("preview") and not item.get("supports_preview"):
        raise ValueError("Preview is unsupported for this item")

    task_id = make_task_id()
    directory, task_path, log_path = task_paths(task_id)
    directory.mkdir(parents=True, exist_ok=True)
    input_path = params.get("input_dir") or params.get("input_file") or ""
    output_path = params.get("output_dir") or params.get("output_file") or ""
    now = datetime.now().isoformat(timespec="seconds")
    task = {
        "task_id": task_id,
        "type": kind,
        "item_id": item_id,
        "name": item["name"],
        "status": "queued",
        "params": params,
        "started_at": now,
        "finished_at": "",
        "duration_seconds": "",
        "input_path": input_path,
        "output_path": output_path,
        "error": "",
        "message": "",
        "stats": {},
        "steps": item.get("steps", []),
        "current_step": "",
        "current_step_index": None,
        "cancel_requested": False,
        "log_path": str(log_path),
        "current_target_path": "",
        "resumed_from_task_id": params.get("_resumed_from_task_id", ""),
    }
    write_task(task)
    log_path.write_text("", encoding="utf-8")
    future = executor.submit(_execute_task, task_id, item["entry"], params)
    running_futures[task_id] = future
    return {"task_id": task_id, "status": "running"}


def _extract_last_batch_child_from_log(task_id: str) -> str:
    try:
        text = read_log(task_id)
    except FileNotFoundError:
        return ""
    marker = "Batch media folder | input_dir="
    for line in reversed(text.splitlines()):
        if marker not in line:
            continue
        tail = line.split(marker, 1)[1]
        return tail.split(" output_dir=", 1)[0].strip()
    return ""


def _prepare_resume_params(task: dict[str, Any]) -> dict[str, Any]:
    params = dict(task.get("params") or {})
    params.pop("preview", None)
    params["_resumed_from_task_id"] = task["task_id"]

    if task.get("item_id") != "media_clean_standard":
        return params

    current_step = str(task.get("current_step") or "").strip()
    current_target = str(task.get("current_target_path") or "").strip() or _extract_last_batch_child_from_log(task["task_id"])
    if current_target:
        params["input_dir"] = current_target
        params["batch_subfolders"] = False
    if current_step:
        params["_resume_step"] = current_step
    return params


def resume_task(task_id: str) -> dict[str, Any]:
    task = read_task(task_id)
    if task.get("status") == "success":
        raise ValueError("Successful task does not need resume")

    future = running_futures.get(task_id)
    if task.get("status") == "running" and future is not None and not future.done():
        return {"task_id": task_id, "status": "running", "message": "Task is already running"}

    params = _prepare_resume_params(task)
    resumed = start_task(task["type"], task["item_id"], params)

    if task.get("status") == "running":
        finished_at = datetime.now().isoformat(timespec="seconds")
        task.update(
            {
                "status": "canceled",
                "finished_at": finished_at,
                "duration_seconds": _duration(task["started_at"], finished_at),
                "error": f"Resumed as {resumed['task_id']}",
                "message": "原任务已转为继续执行",
            }
        )
        write_task(task)

    return resumed
