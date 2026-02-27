from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from domain.models import JobApplicationRecord
from domain.ports import ConfigRepositoryPort, CredentialRepositoryPort, JobApplicationRepositoryPort


@dataclass(frozen=True)
class CredentialView:
    portal: str
    tenant: str
    email: str
    password_masked: str


class ApplicationFacade:
    """
    UI-facing facade for tabs: applied jobs, stored credentials, config.
    """

    def __init__(
        self,
        *,
        job_repo: JobApplicationRepositoryPort,
        credential_repo: CredentialRepositoryPort,
        config_repo: ConfigRepositoryPort,
    ) -> None:
        self._job_repo = job_repo
        self._credential_repo = credential_repo
        self._config_repo = config_repo

    def get_applied_jobs(self) -> Sequence[JobApplicationRecord]:
        return self._job_repo.list_all()

    def get_credentials(self) -> Sequence[CredentialView]:
        items = []
        for cred in self._credential_repo.list_all():
            items.append(
                CredentialView(
                    portal=cred.portal,
                    tenant=cred.tenant,
                    email=cred.email,
                    password_masked=self._mask_secret(cred.password),
                )
            )
        return items

    def get_config(self, key: str) -> str | None:
        return self._config_repo.get_config_value(key)

    def update_config(self, key: str, value: str) -> None:
        self._config_repo.set_config_value(key, value)

    @staticmethod
    def _mask_secret(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 3:
            return "*" * len(value)
        return value[0] + ("*" * (len(value) - 2)) + value[-1]
