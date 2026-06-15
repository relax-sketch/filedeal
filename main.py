from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from api.flows_api import router as flows_router
from api.records_api import router as records_router
from api.settings_api import router as settings_router
from api.tools_api import router as tools_router
from core.path_utils import ensure_base_dirs

FRONTEND_DIR = APP_DIR / "frontend"

ensure_base_dirs()
app = FastAPI(title="Proton Local Toolkit")
app.include_router(tools_router)
app.include_router(flows_router)
app.include_router(records_router)
app.include_router(settings_router)

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

PINGFANG_FONTS = {
    "PingFang-Regular.ttf",
    "PingFang-Medium.ttf",
    "PingFang-Bold.ttf",
    "PingFang-Light.ttf",
}


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/manifest.json")
def manifest():
    return FileResponse(FRONTEND_DIR / "manifest.json")


@app.get("/app-fonts/{font_name}")
def app_font(font_name: str):
    if font_name not in PINGFANG_FONTS:
        return FileResponse(FRONTEND_DIR / "assets" / "fonts" / "material-symbols.css")
    return FileResponse(APP_DIR / font_name)


@app.get("/{page_name}.html")
def page(page_name: str):
    path = FRONTEND_DIR / f"{page_name}.html"
    if path.exists():
        return FileResponse(path)
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {"ok": True}
