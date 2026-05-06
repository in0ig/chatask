"""create dialogue sessions table

Revision ID: 009_dialogue_sessions
Revises: 008_data_table_design_simplified
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '009_dialogue_sessions'
down_revision = '008_data_table_design_simplified'
branch_labels = None
depends_on = None


def upgrade():
    """创建对话会话表"""
    op.create_table(
        'dialogue_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(100), nullable=False, comment='会话唯一标识'),
        sa.Column('user_id', sa.String(100), nullable=True, comment='用户ID'),
        sa.Column('status', sa.Enum('active', 'paused', 'closed', 'archived', 'error', name='sessionstatus'), 
                  nullable=False, comment='会话状态'),
        
        # 会话元数据
        sa.Column('title', sa.String(200), nullable=True, comment='会话标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='会话描述'),
        
        # 会话上下文（JSON格式存储）
        sa.Column('context_data', sa.JSON(), nullable=True, comment='会话上下文数据'),
        sa.Column('cloud_messages', sa.JSON(), nullable=True, comment='云端历史消息'),
        sa.Column('local_messages', sa.JSON(), nullable=True, comment='本地历史消息'),
        
        # 会话统计
        sa.Column('message_count', sa.Integer(), default=0, comment='消息总数'),
        sa.Column('total_tokens', sa.Integer(), default=0, comment='Token总数'),
        sa.Column('error_count', sa.Integer(), default=0, comment='错误次数'),
        
        # 时间戳
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), 
                  onupdate=sa.func.now(), nullable=False, comment='更新时间'),
        sa.Column('last_activity_at', sa.DateTime(), server_default=sa.func.now(), 
                  nullable=False, comment='最后活动时间'),
        sa.Column('closed_at', sa.DateTime(), nullable=True, comment='关闭时间'),
        sa.Column('archived_at', sa.DateTime(), nullable=True, comment='归档时间'),
        
        # 配置
        sa.Column('auto_archive', sa.Boolean(), default=True, comment='是否自动归档'),
        sa.Column('archive_after_days', sa.Integer(), default=30, comment='多少天后归档'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_session_id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci',
        comment='对话会话表'
    )
    
    # 创建索引
    op.create_index('idx_session_id', 'dialogue_sessions', ['session_id'])
    op.create_index('idx_user_id', 'dialogue_sessions', ['user_id'])
    op.create_index('idx_status', 'dialogue_sessions', ['status'])
    op.create_index('idx_last_activity', 'dialogue_sessions', ['last_activity_at'])
    op.create_index('idx_created_at', 'dialogue_sessions', ['created_at'])


def downgrade():
    """删除对话会话表"""
    op.drop_index('idx_created_at', table_name='dialogue_sessions')
    op.drop_index('idx_last_activity', table_name='dialogue_sessions')
    op.drop_index('idx_status', table_name='dialogue_sessions')
    op.drop_index('idx_user_id', table_name='dialogue_sessions')
    op.drop_index('idx_session_id', table_name='dialogue_sessions')
    op.drop_table('dialogue_sessions')
