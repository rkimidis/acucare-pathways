"""Database initialization utilities."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def drop_tables() -> None:
    """Drop all database tables (use with caution)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped")


async def create_initial_admin(session: AsyncSession) -> User | None:
    """Create initial admin user if none exists.

    Args:
        session: Database session

    Returns:
        Created admin user or None if admin already exists
    """
    from sqlalchemy import select

    # Check if any admin exists
    result = await session.execute(
        select(User).where(User.role == UserRole.ADMIN).limit(1)
    )
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        logger.info("Admin user already exists, skipping creation")
        return None

    # Create default admin (credentials should be changed immediately)
    admin = User(
        email="admin@acucare.local",
        hashed_password=hash_password("CHANGE_ME_IMMEDIATELY"),
        role=UserRole.ADMIN,
        first_name="System",
        last_name="Admin",
        is_active=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)

    logger.warning(
        "Created initial admin user with default password. "
        "CHANGE THE PASSWORD IMMEDIATELY!"
    )
    return admin


async def init_db(session: AsyncSession) -> None:
    """Initialize database with required data.

    Args:
        session: Database session
    """
    await create_initial_admin(session)
    logger.info("Database initialization complete")
