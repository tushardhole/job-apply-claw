from __future__ import annotations

from datetime import datetime, timezone

from app import ApplicationFacade
from domain.models import AccountCredential, JobApplicationRecord, JobApplicationStatus
from test.mocks import InMemoryConfigRepository, InMemoryCredentialRepository, InMemoryJobApplicationRepository


def test_facade_exposes_jobs_credentials_and_config() -> None:
    jobs = InMemoryJobApplicationRepository()
    creds = InMemoryCredentialRepository()
    config = InMemoryConfigRepository()

    jobs.add(
        JobApplicationRecord(
            id="j1",
            company_name="Acme",
            job_title="Engineer",
            job_url="https://example/jobs/1",
            status=JobApplicationStatus.APPLIED,
            applied_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
    )
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    creds.upsert(
        AccountCredential(
            id="c1",
            portal="greenhouse",
            tenant="acme",
            email="ada@example.com",
            password="secret-pass",
            created_at=now,
            updated_at=now,
        )
    )
    config.set_config_value("BOT_TOKEN", "abc")

    facade = ApplicationFacade(job_repo=jobs, credential_repo=creds, config_repo=config)
    listed_jobs = facade.get_applied_jobs()
    listed_creds = facade.get_credentials()

    assert len(listed_jobs) == 1
    assert listed_jobs[0].company_name == "Acme"
    assert listed_creds[0].password_masked.startswith("s")
    assert facade.get_config("BOT_TOKEN") == "abc"
    facade.update_config("BOT_TOKEN", "xyz")
    assert facade.get_config("BOT_TOKEN") == "xyz"
