from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from dotenv import load_dotenv

load_dotenv()

config = context.config

database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL is not set")

config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from db import Base
import models  # noqa: F401

target_metadata = Base.metadata


def _should_compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    dialect_name = context.dialect.name

    if dialect_name == "sqlite":
        inspected_name = inspected_type.__class__.__name__.upper()
        metadata_name = metadata_type.__class__.__name__.upper()

        inspected_str = str(inspected_type).upper()
        metadata_str = str(metadata_type).upper()

        sqlite_uuid_noise = (
            ("NUMERIC" in inspected_str and metadata_name == "UUID")
            or (inspected_name == "NUMERIC" and "UUID" in metadata_str)
        )
        if sqlite_uuid_noise:
            return False

    return None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=_should_compare_type,
        compare_server_default=True,
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
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=_should_compare_type,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
