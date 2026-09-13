"""Reset an EMIC user password (run inside backend container or with DATABASE_URL set)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from sqlalchemy import or_, select

from energy_core.auth.datetime_utils import utc_now
from energy_core.auth.passwords import hash_password, validate_password_policy
from energy_core.config import get_settings
from energy_core.db.models import EmicUserModel
from energy_core.db.session import create_engine, create_session_factory


async def reset_password(identifier: str, new_password: str) -> None:
    policy_error = validate_password_policy(new_password)
    if policy_error:
        raise SystemExit(policy_error)

    settings = get_settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            user = await session.scalar(
                select(EmicUserModel).where(
                    or_(EmicUserModel.email == identifier, EmicUserModel.username == identifier),
                )
            )
            if user is None:
                raise SystemExit(f"User not found: {identifier}")

            user.password_hash = hash_password(new_password)
            user.must_change_password = False
            user.password_changed_at = utc_now()
            user.updated_at = utc_now()
            await session.commit()
            print(f"Password updated for {user.username} ({user.email})")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset EMIC user password")
    parser.add_argument("--identifier", default="admin@emic.inacloud.se", help="Email or username")
    parser.add_argument("--password", default="", help="New password (prefer EMIC_NEW_PASSWORD env)")
    args = parser.parse_args()

    password = os.environ.get("EMIC_NEW_PASSWORD") or args.password
    if not password:
        raise SystemExit("Provide --password or EMIC_NEW_PASSWORD")

    asyncio.run(reset_password(args.identifier, password))


if __name__ == "__main__":
    main()
