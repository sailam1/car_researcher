"""Serve Vite production build with correct MIME types (fixes module script errors)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from starlette.staticfiles import StaticFiles

# Windows / minimal images often guess .js as application/octet-stream
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/wasm", ".wasm")


def frontend_dist_dir() -> Path | None:
    """Path to `frontend/dist` if a production build exists."""
    # app/ -> backend/ -> repo root
    root = Path(__file__).resolve().parent.parent.parent
    dist = root / "frontend" / "dist"
    if dist.is_dir() and (dist / "index.html").is_file():
        return dist
    return None


class FrontendStaticFiles(StaticFiles):
    """StaticFiles that forces JS/CSS MIME types for ES modules."""

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if path.endswith(".js") or path.endswith(".mjs"):
            response.headers["content-type"] = "application/javascript; charset=utf-8"
        elif path.endswith(".css"):
            response.headers["content-type"] = "text/css; charset=utf-8"
        elif path.endswith(".wasm"):
            response.headers["content-type"] = "application/wasm"
        return response
