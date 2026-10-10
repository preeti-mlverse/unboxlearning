"""Alembic environment: the database URL comes from the API settings (DATABASE_URL), never from this file."""
from alembic import context
from sqlalchemy import create_engine, pool

from unboxed_api.config import get_settings
from unboxed_api.db import Base
import unboxed_api.models  # noqa: F401  (registers every table)

target_metadata = Base.metadata


def url() -> str:
    return context.config.attributes.get("database_url") or get_settings().database_url


def run_offline() -> None:
    context.configure(url=url(), target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    connectable = context.config.attributes.get("connection")
    if connectable is not None:
        context.configure(connection=connectable, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
