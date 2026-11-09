"""add_hnsw_indexes

Revision ID: fd06b0e03654
Revises: 66be31a18f93
Create Date: 2026-11-02 22:30:35.854524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy.vector


# revision identifiers, used by Alembic.
revision: str = 'fd06b0e03654'
down_revision: Union[str, Sequence[str], None] = '66be31a18f93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Build HNSW (Hierarchical Navigable Small World) index for fast approximate nearest neighbor search.
    - vector_cosine_ops: Optimized for Cosine Distance (<=>)
    - m = 16: Max bidirectional links per node in the multi-layer graph
    - ef_construction = 64: Exploration depth during index build
    """
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_jobs_embedding_hnsw 
        ON jobs USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cv_profiles_embedding_hnsw 
        ON cv_profiles USING hnsw (embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_jobs_embedding_hnsw;")
    op.execute("DROP INDEX IF EXISTS ix_cv_profiles_embedding_hnsw;")
