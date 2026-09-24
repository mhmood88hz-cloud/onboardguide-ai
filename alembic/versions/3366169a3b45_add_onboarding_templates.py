"""add onboarding templates

Revision ID: 3366169a3b45
Revises: 0d9922379e8f
Create Date: 2026-09-24 11:22:35.673153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3366169a3b45'
down_revision: Union[str, Sequence[str], None] = '0d9922379e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('onboarding_templates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('organization_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('department', sa.String(length=100), nullable=True),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onboarding_templates_id'), 'onboarding_templates', ['id'], unique=False)
    op.create_table('onboarding_template_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('template_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('task_type', sa.String(length=20), server_default=sa.text("'Onboarding'"), nullable=False),
    sa.Column('order_index', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.ForeignKeyConstraint(['template_id'], ['onboarding_templates.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_onboarding_template_items_id'), 'onboarding_template_items', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_onboarding_template_items_id'), table_name='onboarding_template_items')
    op.drop_table('onboarding_template_items')
    op.drop_index(op.f('ix_onboarding_templates_id'), table_name='onboarding_templates')
    op.drop_table('onboarding_templates')
