from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.web_ui import safe_static_file


def web_files(tmp_path: Path) -> Path:
    root = tmp_path / "web"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text(
        '<html><body><div id="root">built UI</div></body></html>', encoding="utf-8"
    )
    (root / "assets" / "app-123.js").write_text("export const build=1;", encoding="utf-8")
    (root / "assets" / "app-123.css").write_text("body{margin:0}", encoding="utf-8")
    return root


def test_explicit_spa_and_assets_do_not_mask_api_or_unknown_paths(tmp_path: Path) -> None:
    root = web_files(tmp_path)
    with TestClient(
        create_app(Settings(frontend_dist=root, workspace_root=tmp_path / "workspace")),
        base_url="http://127.0.0.1",
    ) as client:
        for path in (
            "/home",
            "/project",
            "/datasets",
            "/graphs",
            "/reports",
            "/help",
            "/manage",
            "/analysis",
            "/analysis/quality/quality.two_variances",
        ):
            response = client.get(path)
            assert response.status_code == 200
            assert 'id="root"' in response.text
            assert response.headers["cache-control"] == "no-store"
        assert client.get("/", follow_redirects=False).headers["location"] == "/home"
        assert client.get("/api/v1/runtime-info").json()["api_contract_version"] == 22
        assert (
            client.get("/api/v1/runtime-info", headers={"Host": "untrusted.example"}).status_code
            == 400
        )
        for path in (
            "/api/v1/does-not-exist",
            "/assets/missing.js",
            "/workspace/metadata.sqlite3",
            "/.env",
            "/unknown",
            "/analysis/no-module/method",
            "/assets/%2e%2e/index.html",
            "/assets/%252e%252e/index.html",
            "/assets/foo%5cbar",
        ):
            response = client.get(path)
            assert response.status_code == 404, path
            assert 'id="root"' not in response.text
        script = client.get("/assets/app-123.js")
        assert script.status_code == 200
        assert "javascript" in script.headers["content-type"]
        assert "immutable" in script.headers["cache-control"]
        assert "text/css" in client.get("/assets/app-123.css").headers["content-type"]


def test_invalid_dist_fails_without_changing_api_only_mode(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="index.html"):
        Settings(frontend_dist=tmp_path / "missing", workspace_root=tmp_path / "workspace")
    root = web_files(tmp_path)
    with pytest.raises(ValueError, match="separate"):
        Settings(frontend_dist=root, workspace_root=root)
    with TestClient(create_app(Settings(workspace_root=tmp_path / "workspace"))) as client:
        assert "application/json" in client.get("/").headers["content-type"]


def test_static_symlink_outside_dist_rejected(tmp_path: Path) -> None:
    root = web_files(tmp_path)
    secret = tmp_path / "private.txt"
    secret.write_text("must not be served", encoding="utf-8")
    link = root / "assets" / "linked.txt"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("This Windows account cannot create symlinks; Linux CI exercises this case")
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        safe_static_file(root, "assets/linked.txt")
