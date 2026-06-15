from __future__ import annotations

import os
import threading

from fastapi import APIRouter

from config import load_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return load_settings()


@router.post("")
def post_settings(settings: dict):
    return save_settings(settings)


def _shutdown_process() -> None:
    os._exit(0)


@router.post("/shutdown")
def shutdown_service():
    timer = threading.Timer(0.5, _shutdown_process)
    timer.daemon = True
    timer.start()
    return {"ok": True, "message": "服务正在关闭"}
