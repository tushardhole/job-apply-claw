from __future__ import annotations

from domain import JobApplicationRecord, JobApplicationRepositoryPort


class InMemoryJobApplicationRepository:
    def __init__(self) -> None:
        self._records: dict[str, JobApplicationRecord] = {}

    def add(self, record: JobApplicationRecord) -> None:
        self._records[record.id] = record

    def update(self, record: JobApplicationRecord) -> None:
        self._records[record.id] = record

    def get(self, record_id: str) -> JobApplicationRecord | None:
        return self._records.get(record_id)

    def list_all(self) -> list[JobApplicationRecord]:
        return list(self._records.values())


_repo_protocol_check: JobApplicationRepositoryPort
_repo_protocol_check = InMemoryJobApplicationRepository()
