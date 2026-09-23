"""add multi-tenant organizations

Revision ID: 8c409c40c363
Revises: 908ec7ba3cdd
Create Date: 2026-09-23 10:42:58.631188

Adds the `organizations` table and an `organization_id` FK to every
tenant-scoped table. Existing rows are backfilled into one "Legacy
Organization" so upgrading a database that already has data doesn't break.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c409c40c363'
down_revision: Union[str, Sequence[str], None] = '908ec7ba3cdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ["users", "documents", "tasks", "chat_messages", "leave_requests"]


def upgrade() -> None:
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('plan', sa.String(length=20), server_default=sa.text("'trial'"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_organizations_id'), 'organizations', ['id'], unique=False)
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)

    # Backfill target for any pre-existing rows.
    conn = op.get_bind()
    legacy_org_id = conn.execute(
        sa.text(
            "INSERT INTO organizations (name, slug, plan) "
            "VALUES ('Legacy Organization', 'legacy', 'trial') RETURNING id"
        )
    ).scalar()

    for table in TENANT_TABLES:
        op.add_column(table, sa.Column('organization_id', sa.Integer(), nullable=True))
        conn.execute(
            sa.text(f"UPDATE {table} SET organization_id = :org_id"),
            {"org_id": legacy_org_id},
        )
        op.alter_column(table, 'organization_id', nullable=False)
        op.create_foreign_key(
            f"fk_{table}_organization_id", table, 'organizations',
            ['organization_id'], ['id'], ondelete='CASCADE',
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.drop_constraint(f"fk_{table}_organization_id", table, type_='foreignkey')
        op.drop_column(table, 'organization_id')

    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_index(op.f('ix_organizations_id'), table_name='organizations')
    op.drop_table('organizations')
