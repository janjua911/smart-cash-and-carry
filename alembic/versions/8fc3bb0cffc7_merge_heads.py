"""merge_heads

Revision ID: 8fc3bb0cffc7
Revises: 0002, a7575c01b3c1
Create Date: 2026-08-08 17:49:46.674362
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8fc3bb0cffc7'
down_revision: Union[str, None] = ('0002', 'a7575c01b3c1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
