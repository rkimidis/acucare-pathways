"""Scheduled task for abandoned intake recovery.

This module provides a scheduled job that runs the intake recovery service
to send reminders to patients who haven't completed their intake questionnaires.

Usage:
    # Run directly
    python -m app.tasks.intake_recovery

    # Or via cron (recommended to run hourly)
    0 * * * * cd /path/to/project && python -m app.tasks.intake_recovery

    # Environment variables:
    DATABASE_URL - PostgreSQL connection string
    RECOVERY_CHANNEL - "email" (default) or "sms"
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.messaging import MessageChannel
from app.services.intake_recovery import IntakeRecoveryService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_intake_recovery_task(
    database_url: str | None = None,
    channel: MessageChannel = MessageChannel.EMAIL,
) -> dict:
    """Run the intake recovery job.

    Args:
        database_url: Database connection string. If not provided, uses DATABASE_URL env var.
        channel: Communication channel for reminders (email or sms)

    Returns:
        Job results summary
    """
    db_url = database_url or os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Convert sync URL to async if needed
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    logger.info(f"Starting intake recovery task at {datetime.now().isoformat()}")
    logger.info(f"Using channel: {channel}")

    # Create async engine and session
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            service = IntakeRecoveryService(session)

            # First get stats
            stats = await service.get_recovery_stats()
            logger.info(f"Current recovery stats: {stats}")

            # Run the recovery job
            results = await service.run_recovery_job(channel=channel)
            logger.info(f"Recovery job complete: {results}")

            return results

    finally:
        await engine.dispose()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run abandoned intake recovery job")
    parser.add_argument(
        "--channel",
        choices=["email", "sms"],
        default=os.getenv("RECOVERY_CHANNEL", "email"),
        help="Communication channel for reminders",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (overrides DATABASE_URL env var)",
    )
    args = parser.parse_args()

    channel = MessageChannel(args.channel)

    try:
        results = asyncio.run(
            run_intake_recovery_task(
                database_url=args.database_url,
                channel=channel,
            )
        )
        print(f"Job completed successfully: {results}")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Job failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
