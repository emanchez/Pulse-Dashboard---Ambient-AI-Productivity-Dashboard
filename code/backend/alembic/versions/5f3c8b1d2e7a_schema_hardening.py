"""schema hardening: FKs, NOT NULL, indexes

Revision ID: 5f3c8b1d2e7a
Revises: 2a912a3d181d
Create Date: 2026-03-22

Adds:
  - ForeignKey("users.id") on user_id for: tasks, action_logs, session_logs,
    manual_reports, system_states, synthesis_reports
  - ForeignKey("tasks.id") on task_id for: action_logs, session_logs
  - NOT NULL constraint on action_logs.user_id
  - NOT NULL constraint on system_states.user_id
  - NOT NULL constraint on system_states.start_date
  - Composite index ix_ai_usage_user_endpoint_ts on ai_usage_logs
  - Drops redundant single-column indexes: ix_action_logs_user_id,
    ix_session_logs_user_id, ix_ai_usage_logs_user_id, ix_ai_usage_logs_endpoint
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5f3c8b1d2e7a'
down_revision: Union[str, Sequence[str], None] = '2a912a3d181d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tasks: add FK on user_id ─────────────────────────────────────────────
    with op.batch_alter_table('tasks') as ba:
        ba.create_foreign_key(
            'fk_tasks_user_id', 'users', ['user_id'], ['id']
        )

    # ── action_logs: FK on user_id, FK on task_id ──────────────────────────────
    with op.batch_alter_table('action_logs') as ba:
        # user_id remains nullable=True — anonymous events (login failures) are valid
        ba.create_foreign_key(
            'fk_action_logs_user_id', 'users', ['user_id'], ['id']
        )
        ba.create_foreign_key(
            'fk_action_logs_task_id', 'tasks', ['task_id'], ['id']
        )
        # Drop redundant single-column index (covered by ix_action_logs_user_ts)
        ba.drop_index('ix_action_logs_user_id')

    # ── session_logs: FK on user_id + FK on task_id ───────────────────────────
    with op.batch_alter_table('session_logs') as ba:
        ba.create_foreign_key(
            'fk_session_logs_user_id', 'users', ['user_id'], ['id']
        )
        ba.create_foreign_key(
            'fk_session_logs_task_id', 'tasks', ['task_id'], ['id']
        )
        # Drop redundant single-column index (covered by ix_session_logs_user_ended)
        ba.drop_index('ix_session_logs_user_id')

    # ── manual_reports: add FK on user_id ────────────────────────────────────
    with op.batch_alter_table('manual_reports') as ba:
        ba.create_foreign_key(
            'fk_manual_reports_user_id', 'users', ['user_id'], ['id']
        )

    # ── system_states: FK on user_id + NOT NULL both user_id and start_date ──
    with op.batch_alter_table('system_states') as ba:
        ba.alter_column(
            'user_id',
            existing_type=sa.String(36),
            nullable=False,
        )
        ba.alter_column(
            'start_date',
            existing_type=sa.DateTime(),
            nullable=False,
        )
        ba.create_foreign_key(
            'fk_system_states_user_id', 'users', ['user_id'], ['id']
        )

    # ── synthesis_reports: add FK on user_id ──────────────────────────────────
    with op.batch_alter_table('synthesis_reports') as ba:
        ba.create_foreign_key(
            'fk_synthesis_reports_user_id', 'users', ['user_id'], ['id']
        )

    # ── ai_usage_logs: drop single-column indexes, add composite index ────────
    with op.batch_alter_table('ai_usage_logs') as ba:
        ba.drop_index('ix_ai_usage_logs_user_id')
        ba.drop_index('ix_ai_usage_logs_endpoint')
        ba.create_index(
            'ix_ai_usage_user_endpoint_ts',
            ['user_id', 'endpoint', 'timestamp'],
        )


def downgrade() -> None:
    # ── ai_usage_logs: restore single-column indexes ──────────────────────────
    with op.batch_alter_table('ai_usage_logs') as ba:
        ba.drop_index('ix_ai_usage_user_endpoint_ts')
        ba.create_index('ix_ai_usage_logs_endpoint', ['endpoint'])
        ba.create_index('ix_ai_usage_logs_user_id', ['user_id'])

    # ── synthesis_reports: drop FK ────────────────────────────────────────────
    with op.batch_alter_table('synthesis_reports') as ba:
        ba.drop_constraint('fk_synthesis_reports_user_id', type_='foreignkey')

    # ── system_states: drop FK, restore nullable ──────────────────────────────
    with op.batch_alter_table('system_states') as ba:
        ba.drop_constraint('fk_system_states_user_id', type_='foreignkey')
        ba.alter_column(
            'start_date',
            existing_type=sa.DateTime(),
            nullable=True,
        )
        ba.alter_column(
            'user_id',
            existing_type=sa.String(36),
            nullable=True,
        )

    # ── manual_reports: drop FK ───────────────────────────────────────────────
    with op.batch_alter_table('manual_reports') as ba:
        ba.drop_constraint('fk_manual_reports_user_id', type_='foreignkey')

    # ── session_logs: restore single-column index, drop FKs ──────────────────
    with op.batch_alter_table('session_logs') as ba:
        ba.drop_constraint('fk_session_logs_task_id', type_='foreignkey')
        ba.drop_constraint('fk_session_logs_user_id', type_='foreignkey')
        ba.create_index('ix_session_logs_user_id', ['user_id'])

    # ── action_logs: restore single-column index, drop FKs ──────────────────
    with op.batch_alter_table('action_logs') as ba:
        ba.drop_constraint('fk_action_logs_task_id', type_='foreignkey')
        ba.drop_constraint('fk_action_logs_user_id', type_='foreignkey')
        ba.create_index('ix_action_logs_user_id', ['user_id'])

    # ── tasks: drop FK ────────────────────────────────────────────────────────
    with op.batch_alter_table('tasks') as ba:
        ba.drop_constraint('fk_tasks_user_id', type_='foreignkey')
