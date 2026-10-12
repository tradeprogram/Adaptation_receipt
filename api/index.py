"""Vercel 서버리스 진입점. 저장소 루트의 app 패키지를 그대로 ASGI 앱으로 노출한다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.server.main import app  # noqa: E402

__all__ = ["app"]
