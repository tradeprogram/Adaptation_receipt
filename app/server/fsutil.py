"""원자적 파일 저장 헬퍼 — 무거운 의존성 없이 쓰인다(배포본에서 stac/rasterio를 들이지 않기 위해 분리)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def save_json_atomic(path: Path, obj) -> None:
    """같은 디렉터리의 임시 파일에 쓰고 fsync 후 교체한다. 실패 시 임시 파일을 지운다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
