from __future__ import with_statement

import os
from logging.config import fileConfig

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Import the application's metadata
try:
    import database_sqlalchemy as db_mod
except Exception:
    db_mod = None

target_metadata = getattr(db_mod, "Base", None).metadata if db_mod is not None else None


def run_migrations_offline():
    url = os.environ.get("SQLALCHEMY_DATABASE_URI") or (getattr(db_mod, "DB_PATH", None) if db_mod else None)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Prefer the application's engine if available
    if db_mod is not None and hasattr(db_mod, "_get_engine"):
        connectable = db_mod._get_engine()
    else:
        # Fallback: use SQLALCHEMY_DATABASE_URI from env or ini
        from sqlalchemy import create_engine
        url = os.environ.get("SQLALCHEMY_DATABASE_URI") or config.get_main_option("sqlalchemy.url")
        connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
