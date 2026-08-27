"""법령·판례·가이드와 근거 관계를 보존하는 SQLite DB."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@dataclass(frozen=True)
class DatabaseSummary:
    path: Path
    schema_version: int
    tables: tuple[str, ...]


def connect_database(path: Path) -> sqlite3.Connection:
    """외래키 검사를 활성화한 연결을 반환한다."""

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_relational_database(path: Path) -> DatabaseSummary:
    """멱등적으로 스키마를 생성하고 생성 결과를 반환한다."""

    database_path = path.expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with connect_database(database_path) as connection:
        connection.executescript(schema)
        version = connection.execute(
            "SELECT MAX(version) AS version FROM schema_migrations"
        ).fetchone()["version"]
        table_rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

    return DatabaseSummary(
        path=database_path,
        schema_version=int(version),
        tables=tuple(row["name"] for row in table_rows),
    )
