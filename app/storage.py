import aiosqlite
from app.config import settings
from app.models import INIT_SCRIPT

async def init_db():
    """Run migration on startup."""
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(INIT_SCRIPT)
        await db.commit()

async def insert_message(msg_data: dict) -> bool:
    """
    Returns True if inserted, False if duplicate (idempotent).
    """
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                VALUES (:message_id, :from, :to, :ts, :text, :created_at)
                """,
                msg_data
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:

        return False