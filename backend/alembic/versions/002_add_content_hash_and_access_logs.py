"""add content_hash and file_access_logs

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add content_hash column to files table
    op.add_column('files', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_files_content_hash', 'files', ['content_hash'], unique=False)
    op.create_index('idx_files_user_hash', 'files', ['user_id', 'content_hash'], unique=False)

    # Create file_access_logs table
    op.create_table(
        'file_access_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('accessed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_file_access_logs_id'), 'file_access_logs', ['id'], unique=False)
    op.create_index(op.f('ix_file_access_logs_file_id'), 'file_access_logs', ['file_id'], unique=False)
    op.create_index(op.f('ix_file_access_logs_user_id'), 'file_access_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_file_access_logs_accessed_at'), 'file_access_logs', ['accessed_at'], unique=False)


def downgrade() -> None:
    # Drop file_access_logs table
    op.drop_index(op.f('ix_file_access_logs_accessed_at'), table_name='file_access_logs')
    op.drop_index(op.f('ix_file_access_logs_user_id'), table_name='file_access_logs')
    op.drop_index(op.f('ix_file_access_logs_file_id'), table_name='file_access_logs')
    op.drop_index(op.f('ix_file_access_logs_id'), table_name='file_access_logs')
    op.drop_table('file_access_logs')

    # Drop content_hash column from files table
    op.drop_index('idx_files_user_hash', table_name='files')
    op.drop_index('ix_files_content_hash', table_name='files')
    op.drop_column('files', 'content_hash')
