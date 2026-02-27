from __future__ import annotations

from domain import AccountCredential, CredentialRepositoryPort


class InMemoryCredentialRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], AccountCredential] = {}

    def upsert(self, credential: AccountCredential) -> None:
        key = (credential.portal, credential.tenant, credential.email)
        self._records[key] = credential

    def get(
        self,
        portal: str,
        tenant: str,
        email: str,
    ) -> AccountCredential | None:
        return self._records.get((portal, tenant, email))

    def list_all(self) -> list[AccountCredential]:
        return list(self._records.values())


_repo_protocol_check: CredentialRepositoryPort
_repo_protocol_check = InMemoryCredentialRepository()
