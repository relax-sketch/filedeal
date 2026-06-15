from __future__ import annotations

from fastapi import APIRouter

from config import load_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return load_settings()


@router.post("")
def post_settings(settings: dict):
    return save_settings(settings)
