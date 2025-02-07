from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Boolean, Enum, ForeignKey,
    Index, UniqueConstraint, Text, CheckConstraint, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..core.base import BaseModel


class Team(BaseModel):
    """Model for managing teams and organizational groups."""
    __tablename__ = 'teams'

    name = Column(String(255), nullable=False)
    description = Column(Text)
    owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL')
    )

    # Team configuration
    type = Column(
        Enum('department', 'project', 'workgroup', name='team_type'),
        default='workgroup'
    )
    visibility = Column(
        Enum('public', 'private', 'restricted', name='team_visibility'),
        default='private'
    )

    # Team metadata
    settings = Column(JSONB, default=dict)
    member_limit = Column(Integer)
    expiration_date = Column(DateTime)

    # Team status
    status = Column(
        Enum('active', 'inactive', 'archived', name='team_status'),
        default='active'
    )
    archived_at = Column(DateTime)
    archived_reason = Column(String(255))

    # Relationships
    owner = relationship(
        "User",
        foreign_keys=[owner_id]
    )
    members = relationship(
        "TeamMember",
        back_populates="team",
        cascade="all, delete-orphan"
    )
    resources = relationship(
        "TeamResource",
        back_populates="team",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('ix_teams_name', 'name'),
        Index('ix_teams_owner', 'owner_id'),
        Index('ix_teams_status', 'status'),
        CheckConstraint(
            'member_limit IS NULL OR member_limit > 0',
            name='ck_member_limit_positive'
        )
    )


class TeamMember(BaseModel):
    """Model for managing team memberships."""
    __tablename__ = 'team_members'

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey('teams.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Role and permissions
    role = Column(
        Enum('admin', 'editor', 'viewer', name='team_member_role'),
        default='viewer',
        nullable=False
    )
    custom_permissions = Column(JSONB)

    # Membership status
    status = Column(
        Enum('active', 'inactive', 'pending', name='team_member_status'),
        default='active',
        nullable=False
    )
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    invited_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    invitation_message = Column(Text)
    expiration_date = Column(DateTime)

    # Activity tracking
    last_active = Column(DateTime)
    contribution_count = Column(Integer, default=0)

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="team_memberships"
    )
    team = relationship(
        "Team",
        foreign_keys=[team_id],
        back_populates="members"
    )
    inviter = relationship(
        "User",
        foreign_keys=[invited_by]
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'team_id', name='uq_user_team'),
        Index('ix_team_members_status', 'status'),
        Index('ix_team_members_role', 'role'),
        CheckConstraint(
            'contribution_count >= 0',
            name='ck_contribution_count_valid'
        )
    )

    def has_permission(self, permission: str) -> bool:
        """Check if member has specific permission."""
        role_permissions = {
            'admin': ['read', 'write', 'manage', 'invite'],
            'editor': ['read', 'write'],
            'viewer': ['read']
        }

        # Check custom permissions first
        if self.custom_permissions and permission in self.custom_permissions:
            return self.custom_permissions[permission]

        # Fall back to role-based permissions
        return permission in role_permissions.get(self.role, [])


class TeamResource(BaseModel):
    """Model for managing team resources and assets."""
    __tablename__ = 'team_resources'

    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey('teams.id', ondelete='CASCADE'),
        nullable=False
    )

    # Resource details
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    location = Column(String(255))
    meta_data = Column(JSONB)

    # Access control
    visibility = Column(
        Enum('public', 'team', 'restricted', name='resource_visibility'),
        default='team'
    )
    access_permissions = Column(JSONB)

    # Resource status
    status = Column(
        Enum('active', 'archived', 'pending', name='resource_status'),
        default='active'
    )
    archived_at = Column(DateTime)
    last_accessed = Column(DateTime)
    access_count = Column(Integer, default=0)

    # Relationships
    team = relationship(
        "Team",
        back_populates="resources"
    )

    __table_args__ = (
        Index('ix_team_resources_team', 'team_id'),
        Index('ix_team_resources_type', 'type'),
        Index('ix_team_resources_status', 'status'),
        CheckConstraint(
            'access_count >= 0',
            name='ck_access_count_valid'
        )
    )


class TeamInvitation(BaseModel):
    """Model for managing team invitations."""
    __tablename__ = 'team_invitations'

    team_id = Column(
        UUID(as_uuid=True),
        ForeignKey('teams.id', ondelete='CASCADE'),
        nullable=False
    )
    email = Column(String(255), nullable=False)
    role = Column(
        Enum('admin', 'editor', 'viewer', name='invitation_role'),
        default='viewer'
    )

    # Invitation details
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    message = Column(Text)

    # Status tracking
    status = Column(
        Enum('pending', 'accepted', 'rejected', 'expired', name='invitation_status'),
        default='pending'
    )
    responded_at = Column(DateTime)
    accepted_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=True
    )

    __table_args__ = (
        Index('ix_team_invitations_email', 'email'),
        Index('ix_team_invitations_status', 'status'),
        CheckConstraint(
            'expires_at > created_at',
            name='ck_invitation_expiry_valid'
        )
    )

    def is_valid(self) -> bool:
        """Check if invitation is still valid."""
        return (
                self.status == 'pending' and
                self.expires_at > datetime.utcnow()
        )