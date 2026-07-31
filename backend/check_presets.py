import asyncio
from database.base import get_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from models.mm_preset import MMPreset

async def main():
    f = get_engine()
    s = async_sessionmaker(f)()
    r = await s.execute(select(MMPreset))
    rows = r.scalars().all()
    print(f"PRESETS COUNT: {len(rows)}")
    for p in rows:
        print(f"  {p.preset_type} | {p.name} | builtin={p.is_builtin} | active={p.is_active} | user_id={p.user_id}")

asyncio.run(main())
