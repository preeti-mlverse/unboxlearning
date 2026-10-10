"""Email codes (OTP) on auth tokens, a system_events table for admin counters, and the two course->version
foreign keys that 0001 left out (Alembic skips use_alter keys inside create_table).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-10 12:22:27.378054
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('system_events',
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('code', sa.String(length=60), nullable=False),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('path', sa.String(length=300), nullable=True),
    sa.Column('request_id', sa.String(length=40), nullable=True),
    sa.Column('user_id', sa.String(length=40), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_system_events'))
    )
    op.create_index('ix_system_events_kind_time', 'system_events', ['kind', 'created_at'], unique=False)
    op.add_column('auth_tokens', sa.Column('code_hash', sa.String(length=64), nullable=True))
    op.add_column('auth_tokens', sa.Column('attempts', sa.Integer(), server_default='0', nullable=False))
    # 0001 created these columns without their foreign keys
    op.create_foreign_key(op.f('fk_courses_current_published_version_id_course_versions'), 'courses', 'course_versions', ['current_published_version_id'], ['id'], ondelete='SET NULL', use_alter=True)
    op.create_foreign_key(op.f('fk_courses_current_draft_version_id_course_versions'), 'courses', 'course_versions', ['current_draft_version_id'], ['id'], ondelete='SET NULL', use_alter=True)


def downgrade() -> None:
    op.drop_constraint(op.f('fk_courses_current_draft_version_id_course_versions'), 'courses', type_='foreignkey')
    op.drop_constraint(op.f('fk_courses_current_published_version_id_course_versions'), 'courses', type_='foreignkey')
    op.drop_column('auth_tokens', 'attempts')
    op.drop_column('auth_tokens', 'code_hash')
    op.drop_index('ix_system_events_kind_time', table_name='system_events')
    op.drop_table('system_events')
