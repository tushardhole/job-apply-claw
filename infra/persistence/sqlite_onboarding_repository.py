from __future__ import annotations

import json
import sqlite3

from domain.models import CommonAnswers, ResumeData, UserProfile

_DEFAULT_PROFILE_ID = "default"


class SQLiteOnboardingRepository:
    """
    SQLite-backed implementation of ``OnboardingRepositoryPort``.

    All onboarding data (user profile, resume metadata, and common answers)
    lives in a single database file, scoped by ``profile_id``.

    Today only a single profile (``"default"``) is used, but the schema
    supports multiple profiles so that adding a Netflix-style profile
    switcher later requires no migration.
    """

    _SCHEMA_SQL = """\
    CREATE TABLE IF NOT EXISTS user_profile (
        profile_id  TEXT PRIMARY KEY,
        full_name   TEXT NOT NULL,
        email       TEXT NOT NULL,
        phone       TEXT,
        address     TEXT
    );

    CREATE TABLE IF NOT EXISTS resume_data (
        profile_id             TEXT PRIMARY KEY,
        primary_resume_path    TEXT NOT NULL,
        additional_resume_paths TEXT NOT NULL DEFAULT '[]',
        cover_letter_paths     TEXT NOT NULL DEFAULT '[]',
        skills                 TEXT NOT NULL DEFAULT '[]'
    );

    CREATE TABLE IF NOT EXISTS common_answers (
        profile_id TEXT NOT NULL,
        key        TEXT NOT NULL,
        value      TEXT NOT NULL,
        PRIMARY KEY (profile_id, key)
    );

    """

    def __init__(
        self,
        db_path: str = ":memory:",
        profile_id: str = _DEFAULT_PROFILE_ID,
    ) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(self._SCHEMA_SQL)
        self._profile_id = profile_id

    def __enter__(self) -> "SQLiteOnboardingRepository":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    # -- User profile -------------------------------------------------------

    def get_user_profile(self) -> UserProfile | None:
        row = self._conn.execute(
            "SELECT full_name, email, phone, address "
            "FROM user_profile WHERE profile_id = ?",
            (self._profile_id,),
        ).fetchone()
        if row is None:
            return None
        return UserProfile(
            full_name=row[0],
            email=row[1],
            phone=row[2],
            address=row[3],
        )

    def save_user_profile(self, profile: UserProfile) -> None:
        self._conn.execute(
            "INSERT INTO user_profile "
            "(profile_id, full_name, email, phone, address) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(profile_id) DO UPDATE SET "
            "full_name=excluded.full_name, email=excluded.email, "
            "phone=excluded.phone, address=excluded.address",
            (
                self._profile_id,
                profile.full_name,
                profile.email,
                profile.phone,
                profile.address,
            ),
        )
        self._conn.commit()

    # -- Resume data --------------------------------------------------------

    def get_resume_data(self) -> ResumeData | None:
        row = self._conn.execute(
            "SELECT primary_resume_path, additional_resume_paths, "
            "cover_letter_paths, skills "
            "FROM resume_data WHERE profile_id = ?",
            (self._profile_id,),
        ).fetchone()
        if row is None:
            return None
        return ResumeData(
            primary_resume_path=row[0],
            additional_resume_paths=tuple(json.loads(row[1])),
            cover_letter_paths=tuple(json.loads(row[2])),
            skills=tuple(json.loads(row[3])),
        )

    def save_resume_data(self, data: ResumeData) -> None:
        self._conn.execute(
            "INSERT INTO resume_data "
            "(profile_id, primary_resume_path, additional_resume_paths, "
            "cover_letter_paths, skills) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(profile_id) DO UPDATE SET "
            "primary_resume_path=excluded.primary_resume_path, "
            "additional_resume_paths=excluded.additional_resume_paths, "
            "cover_letter_paths=excluded.cover_letter_paths, "
            "skills=excluded.skills",
            (
                self._profile_id,
                data.primary_resume_path,
                json.dumps(list(data.additional_resume_paths)),
                json.dumps(list(data.cover_letter_paths)),
                json.dumps(list(data.skills)),
            ),
        )
        self._conn.commit()

    # -- Common answers -----------------------------------------------------

    def get_common_answers(self) -> CommonAnswers:
        rows = self._conn.execute(
            "SELECT key, value FROM common_answers WHERE profile_id = ?",
            (self._profile_id,),
        ).fetchall()
        return CommonAnswers(answers={k: v for k, v in rows})

    def save_common_answers(self, answers: CommonAnswers) -> None:
        self._conn.execute("BEGIN")
        try:
            self._conn.execute(
                "DELETE FROM common_answers WHERE profile_id = ?",
                (self._profile_id,),
            )
            self._conn.executemany(
                "INSERT INTO common_answers (profile_id, key, value) VALUES (?, ?, ?)",
                [(self._profile_id, k, v) for k, v in answers.answers.items()],
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def close(self) -> None:
        self._conn.close()
