"""Add product_variants table

Revision ID: 0002_add_product_variants
Revises: 0001_initial
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# ✅ FIX: Must match the revision ID of 0001_initial_schema.py
revision = "0002_add_product_variants"
down_revision = "0001_initial"  # ✅ Was probably "0002" — WRONG
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("sku", sa.String(50), unique=True, nullable=True),
        sa.Column("price_adjustment", sa.Numeric(10, 2), default=0.0),
        sa.Column("stock_quantity", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])

def downgrade() -> None:
    op.drop_table("product_variants")