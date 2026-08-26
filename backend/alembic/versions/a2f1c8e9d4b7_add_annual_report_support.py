"""add annual report support

Revision ID: a2f1c8e9d4b7
Revises: 162bb6a0ba78
Create Date: 2026-08-26 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a2f1c8e9d4b7'
down_revision: Union[str, None] = '162bb6a0ba78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'annual_report' value to the document_type enum
    op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'annual_report'")

    # Add columns for annual report section tracking
    op.add_column('documents', sa.Column(
        'parent_document_id',
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey('documents.id', ondelete='SET NULL'),
        nullable=True,
    ))
    op.add_column('documents', sa.Column(
        'page_range_start', sa.Integer(), nullable=True,
    ))
    op.add_column('documents', sa.Column(
        'page_range_end', sa.Integer(), nullable=True,
    ))
    op.create_index(
        'ix_documents_parent_document_id',
        'documents',
        ['parent_document_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_documents_parent_document_id', table_name='documents')
    op.drop_column('documents', 'page_range_end')
    op.drop_column('documents', 'page_range_start')
    op.drop_column('documents', 'parent_document_id')
    # PostgreSQL does not support removing enum values
