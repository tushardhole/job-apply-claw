from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class StructuredLogger:
    def info(self, message: str, **fields: Any) -> None:
        self._emit("info", message, fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit("warning", message, fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit("error", message, fields)

    def _emit(self, level: str, message: str, fields: dict[str, Any]) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "fields": fields,
        }
        print(json.dumps(payload, sort_keys=True))
