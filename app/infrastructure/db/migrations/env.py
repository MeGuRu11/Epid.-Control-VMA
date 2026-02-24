from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure project root on sys.path for imports
BASE_DIR = Path(__file__).resolve().parents[4]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.config import settings  # noqa: E402
from app.infrastructure.db.models_sqlalchemy import Base  # noqa: E402

config = context.config

# Prefer runtime database URL from settings; fallback to alembic.ini
if config.get_main_option("sqlalchemy.url") == "sqlite:///./data/dev.db":
    config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name:
    try:
        from logging.config import fileConfig

        fileConfig(config.config_file_name)
    except ModuleNotFoundError:
        logging.getLogger(__name__).warning(
            "logging.config not available; skipping Alembic fileConfig",
        )

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
