from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from app.config import settings


def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def get_engine() -> Engine:
    # SQLite needs check_same_thread=False for use across threads (Qt).
    engine = create_engine(
        settings.database_url,
        echo=settings.echo_sql,
        future=True,
        connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    )
    if settings.database_url.startswith("sqlite"):
        event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine
