"""Add ChatBI enhanced tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create prompt_config table
    op.create_table(
        'prompt_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('prompt_type', mysql.ENUM('intent_recognition', 'table_selection', 'sql_generation', 'sql_error_recovery', 'data_interpretation', 'fluctuation_attribution', 'follow_up_handling', 'analysis_strategy_application'), nullable=False),
        sa.Column('prompt_category', sa.String(100), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('user_prompt_template', sa.Text(), nullable=False),
        sa.Column('examples', sa.JSON(), nullable=True),
        sa.Column('temperature', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create session_context table
    op.create_table(
        'session_context',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('context_type', mysql.ENUM('local_model', 'aliyun_model'), nullable=False),
        sa.Column('messages', sa.JSON(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('last_summary_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['session_id'], ['query_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create conversation_messages table
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('turn', sa.Integer(), nullable=False),
        sa.Column('role', mysql.ENUM('user', 'assistant', 'system'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_message_id', sa.String(100), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('model_used', mysql.ENUM('aliyun', 'local', 'none'), nullable=True),
        sa.Column('intent', sa.String(100), nullable=True),
        sa.Column('query_id', sa.String(100), nullable=True),
        sa.Column('analysis_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['session_id'], ['query_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_session_turn', 'session_id', 'turn'),
        sa.Index('idx_parent', 'parent_message_id')
    )

    # Create token_usage_stats table
    op.create_table(
        'token_usage_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False),
        sa.Column('model_type', mysql.ENUM('local', 'aliyun'), nullable=False),
        sa.Column('turn', sa.Integer(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['session_id'], ['query_sessions.session_id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('token_usage_stats')
    op.drop_table('conversation_messages')
    op.drop_table('session_context')
    op.drop_table('prompt_config')
