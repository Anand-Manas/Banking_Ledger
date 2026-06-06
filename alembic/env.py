import os
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db.base import Base
target_metadata = Base.metadata


def get_database_url() -> str:
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url.replace("postgresql+asyncpg://", "postgresql://")

    # Railway fallback: individual PG vars
    pg_host = os.environ.get("PGHOST")
    pg_port = os.environ.get("PGPORT", "5432")
    pg_user = os.environ.get("PGUSER")
    pg_password = os.environ.get("PGPASSWORD")
    pg_database = os.environ.get("PGDATABASE")

    if all([pg_host, pg_user, pg_password, pg_database]):
        return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"

    return None


database_url = get_database_url()
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
    print(f"[Alembic] Database URL configured: {database_url[:50]}...")
else:
    print("[Alembic] WARNING: No database URL found.")


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        print("[Alembic] Skipping offline migration — no URL.")
        return
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        print("[Alembic] Skipping online migration — no URL.")
        return
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()