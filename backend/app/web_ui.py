"""Explicit built-UI routes; unknown API/asset paths never receive the SPA."""

from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

SPA_PATHS = ("home", "project", "datasets", "graphs", "reports", "help", "manage", "analysis")
MODULE_IDS = {"exploration", "hypothesis", "categorical", "regression", "quality", "doe"}
PUBLIC_ASSETS = {"favicon.ico", "favicon.svg", "statistical-twin-favicon-v1.svg", "robots.txt"}


def safe_static_file(root: Path, relative: str) -> Path:
    decoded = unquote(relative)
    parts = decoded.split("/")
    if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
        raise HTTPException(404, "Static file not found")
    if "\\" in decoded or ":" in decoded or "\x00" in decoded:
        raise HTTPException(404, "Static file not found")
    candidate = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise HTTPException(404, "Static file not found")
    if not candidate.is_file() or root not in candidate.resolve().parents:
        raise HTTPException(404, "Static file not found")
    return candidate


def built_ui_router(frontend_dist: Path) -> APIRouter:
    root = frontend_dist.resolve()
    safe_static_file(root, "index.html")
    router = APIRouter(include_in_schema=False)

    @router.get("/")
    def root_redirect() -> RedirectResponse:
        return RedirectResponse("/home", status_code=307)

    def index() -> FileResponse:
        return FileResponse(
            safe_static_file(root, "index.html"), headers={"Cache-Control": "no-store"}
        )

    for path in SPA_PATHS:
        router.add_api_route(f"/{path}", index, methods=["GET"])

    @router.get("/analysis/{module_id}/{method_id}")
    def analysis(module_id: str, method_id: str) -> FileResponse:
        if module_id not in MODULE_IDS or not all(c.isalnum() or c in "._-" for c in method_id):
            raise HTTPException(404, "Analysis route not found")
        return index()

    @router.get("/assets/{asset_path:path}")
    def asset(asset_path: str) -> FileResponse:
        return FileResponse(
            safe_static_file(root, f"assets/{asset_path}"),
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    @router.get("/{public_asset}")
    def public_file(public_asset: str) -> FileResponse:
        if public_asset not in PUBLIC_ASSETS:
            raise HTTPException(404, "Static file not found")
        return FileResponse(
            safe_static_file(root, public_asset), headers={"Cache-Control": "no-cache"}
        )

    return router
