"""add intervention replies and attachments

Adds ONLY two new tables. No existing table or row is changed.

Revision ID: b1c2d3e4f5a6
Revises: a96268e34773
Create Date: 2026-10-09 01:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a96268e34773'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'intervention_replies',
        sa.Column('replyID', sa.Integer(), nullable=False),
        sa.Column('interventionID', sa.Integer(), nullable=False),
        sa.Column('authorID', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['authorID'], ['users.userID']),
        sa.ForeignKeyConstraint(['interventionID'], ['intervention_notes.interventionID'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('replyID'),
    )
    op.create_index(op.f('ix_intervention_replies_replyID'), 'intervention_replies', ['replyID'], unique=False)
    op.create_index(op.f('ix_intervention_replies_interventionID'), 'intervention_replies', ['interventionID'], unique=False)

    op.create_table(
        'intervention_attachments',
        sa.Column('attachmentID', sa.Integer(), nullable=False),
        sa.Column('interventionID', sa.Integer(), nullable=False),
        sa.Column('replyID', sa.Integer(), nullable=True),
        sa.Column('fileName', sa.String(length=255), nullable=False),
        sa.Column('fileType', sa.String(length=100), nullable=False),
        sa.Column('fileSize', sa.Integer(), nullable=False),
        sa.Column('fileData', sa.LargeBinary(), nullable=False),
        sa.Column('uploadedBy', sa.Integer(), nullable=False),
        sa.Column('uploadedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['interventionID'], ['intervention_notes.interventionID'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['replyID'], ['intervention_replies.replyID'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploadedBy'], ['users.userID']),
        sa.PrimaryKeyConstraint('attachmentID'),
    )
    op.create_index(op.f('ix_intervention_attachments_attachmentID'), 'intervention_attachments', ['attachmentID'], unique=False)
    op.create_index(op.f('ix_intervention_attachments_interventionID'), 'intervention_attachments', ['interventionID'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_intervention_attachments_interventionID'), table_name='intervention_attachments')
    op.drop_index(op.f('ix_intervention_attachments_attachmentID'), table_name='intervention_attachments')
    op.drop_table('intervention_attachments')
    op.drop_index(op.f('ix_intervention_replies_interventionID'), table_name='intervention_replies')
    op.drop_index(op.f('ix_intervention_replies_replyID'), table_name='intervention_replies')
    op.drop_table('intervention_replies')