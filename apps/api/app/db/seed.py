import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session
from app.models.user import User, UserRole


async def seed_admin() -> None:
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == settings.SEED_ADMIN_EMAIL))
        if result.scalar_one_or_none() is not None:
            print(f"Admin {settings.SEED_ADMIN_EMAIL} ja existe, nada a fazer.")
            return
        admin = User(
            email=settings.SEED_ADMIN_EMAIL,
            password_hash=hash_password(settings.SEED_ADMIN_PASSWORD),
            role=UserRole.ADMIN,
            full_name="Administrador",
        )
        db.add(admin)
        await db.commit()
        print(f"Admin {settings.SEED_ADMIN_EMAIL} criado.")


if __name__ == "__main__":
    asyncio.run(seed_admin())
