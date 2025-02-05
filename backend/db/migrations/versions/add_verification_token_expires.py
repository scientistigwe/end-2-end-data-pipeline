# backend/db/migrations/versions/add_verification_token_expires.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add verification_token_expires_at column
    op.add_column('users',
        sa.Column('verification_token_expires_at', sa.DateTime(), nullable=True)
    )

def downgrade():
    # Remove verification_token_expires_at column
    op.drop_column('users', 'verification_token_expires_at')