"""add organization active_until for manual billing activation

Revision ID: 0d9922379e8f
Revises: 8c409c40c363
Create Date: 2026-09-23 12:12:35.854529

No Stripe: an org's access is toggled manually after an out-of-band
payment agreement (invoice/direct debit), see app/routers/platform.py.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d9922379e8f'
down_revision: Union[str, Sequence[str], None] = '8c409c40c363'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('active_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('organizations', 'active_until')
