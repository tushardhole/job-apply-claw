from __future__ import annotations

import uuid


class UuidIdGenerator:
    def new_run_id(self) -> str:
        return f"run-{uuid.uuid4().hex[:12]}"

    def new_correlation_id(self) -> str:
        return f"id-{uuid.uuid4().hex[:12]}"
