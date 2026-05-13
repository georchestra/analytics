import os
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from sqlalchemy import pool

from georchestra_analytics_cli.common.models import Base
from georchestra_analytics_cli.config import load_config_from

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    config_file = os.environ.get("GEORCHESTRA_ANALYTICS_CLI_CONFIG_FILE")
    app_config = load_config_from(config_file)
    # render_as_string(hide_password=False) is required: SQLAlchemy's URL.__str__()
    # deliberately redacts the password to "***", which makes psycopg2 fail auth.
    return app_config.get_db_connection_string().render_as_string(hide_password=False)


def include_object(object, name, type_, reflected, compare_to):
    # Skip tables/views that exist only in the DB (TimescaleDB internals, continuous aggregates)
    # to prevent autogenerate from proposing spurious DROP statements.
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="analytics",
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = get_url()
    # Alembic calls _ensure_version_table() before running any migration, so
    # analytics.alembic_version must exist before the first upgrade() runs —
    # even though the initial revision is the one that creates the schema.
    # A separate AUTOCOMMIT connection is used so the CREATE SCHEMA is immediately
    # committed and visible to the migration transaction that follows.
    # Using connection.commit() on the main connection instead breaks downgrade
    # silently: Alembic cannot find alembic_version to update after the migration runs.
    bootstrap_engine = sa.create_engine(url, isolation_level="AUTOCOMMIT", poolclass=pool.NullPool)
    with bootstrap_engine.connect() as conn:
        conn.execute(sa.text("CREATE SCHEMA IF NOT EXISTS analytics"))
    bootstrap_engine.dispose()

    # engine_from_config is not used here: when sqlalchemy.url is set manually via
    # cfg["sqlalchemy.url"], the prefix-stripping logic in engine_from_config produces
    # a broken engine (the key ends up without a scheme). sa.create_engine(url) is simpler.
    connectable = sa.create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="analytics",
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
