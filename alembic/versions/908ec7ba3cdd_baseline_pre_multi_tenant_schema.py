"""baseline (pre multi-tenant schema)

Revision ID: 908ec7ba3cdd
Revises:
Create Date: 2026-09-23 10:42:43.700987

Creates the original schema (users, documents, document_images,
chat_messages, tasks, document_chunks, leave_requests) as it existed
before multi-tenancy. On a database that already has these tables
(e.g. an existing dev DB) this revision is applied via `alembic stamp`
instead of `upgrade`, so it never actually runs there. On a fresh
database (e.g. a new Docker container) `upgrade head` runs it for real,
so the schema can be built from nothing.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '908ec7ba3cdd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('username', sa.String(length=100), unique=True, nullable=False),
        sa.Column('email', sa.String(length=100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(length=60), nullable=False),
        sa.Column('user_role', sa.String(length=20), nullable=False),
        sa.Column('assigned_project', sa.String(length=100), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('reports_to', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('progress_percent', sa.Integer(), server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('filepath', sa.String(length=512), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'document_images',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('filepath', sa.String(length=512), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'chat_messages',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_question', sa.Text(), nullable=False),
        sa.Column('ai_response', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('task_type', sa.String(length=20), nullable=False),
        sa.Column('project_name', sa.String(length=100), nullable=True),
        sa.Column('assigned_to', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_completed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('chunk_metadata', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'leave_requests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('leave_type', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'Ausstehend'")),
        sa.Column('substitute_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('decided_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade() -> None:
    op.drop_table('leave_requests')
    op.drop_table('document_chunks')
    op.drop_table('tasks')
    op.drop_table('chat_messages')
    op.drop_table('document_images')
    op.drop_table('documents')
    op.drop_table('users')
