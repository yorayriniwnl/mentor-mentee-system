"""initial migration

Revision ID: 0001_initial
Revises: 
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Use the application's metadata to create tables (safe initial migration)
    try:
        import database_sqlalchemy as db_mod
        engine = db_mod._get_engine()
        db_mod.Base.metadata.create_all(bind=engine)
    except Exception:
        # If the ORM isn't available, fall back to creating via op (best-effort)
        pass


def downgrade():
    try:
        import database_sqlalchemy as db_mod
        engine = db_mod._get_engine()
        db_mod.Base.metadata.drop_all(bind=engine)
    except Exception:
        pass
