"""add invoices and organization billing fields

Revision ID: 6aee8a5ab01b
Revises: 3366169a3b45
Create Date: 2026-09-24 18:07:44.773747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6aee8a5ab01b'
down_revision: Union[str, Sequence[str], None] = '3366169a3b45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('invoices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('invoice_number', sa.String(length=30), nullable=False),
    sa.Column('period_start', sa.Date(), nullable=False),
    sa.Column('period_end', sa.Date(), nullable=True),
    sa.Column('employee_count', sa.Integer(), nullable=False),
    sa.Column('unit_price_eur', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total_eur', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('pdf_storage_key', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('invoice_number')
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.add_column('organizations', sa.Column('billing_contact_name', sa.String(length=150), nullable=True))
    op.add_column('organizations', sa.Column('billing_email', sa.String(length=100), nullable=True))
    op.add_column('organizations', sa.Column('billing_address', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organizations', 'billing_address')
    op.drop_column('organizations', 'billing_email')
    op.drop_column('organizations', 'billing_contact_name')
    op.drop_index(op.f('ix_invoices_id'), table_name='invoices')
    op.drop_table('invoices')
