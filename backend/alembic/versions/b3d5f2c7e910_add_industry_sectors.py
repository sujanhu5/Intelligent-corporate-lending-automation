"""add banking and other industry sectors

Revision ID: b3d5f2c7e910
Revises: a2f1c8e9d4b7
Create Date: 2026-08-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'b3d5f2c7e910'
down_revision: Union[str, None] = 'a2f1c8e9d4b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_INDUSTRY_VALUES = [
    "banking",
    "insurance",
    "pharmaceuticals",
    "education",
    "telecommunications",
    "automotive",
    "food_beverage",
    "media_entertainment",
    "mining",
    "logistics",
    "chemicals",
    "textiles",
    "consulting",
    "e_commerce",
    "renewable_energy",
]


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in
    # older PostgreSQL versions; using autocommit_block is safe on all
    # supported versions.
    with op.get_context().autocommit_block():
        for value in NEW_INDUSTRY_VALUES:
            op.execute(f"ALTER TYPE industry ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values without rebuilding
    # the type. This migration is intentionally not reversible.
    pass
