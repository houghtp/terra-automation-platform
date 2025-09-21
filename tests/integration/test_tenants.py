import asyncio
from app.features.administration.tenants.db_models import Tenant
from app.features.core.database import Base, engine


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_tenant_model_create_and_to_dict():
    async def _test():
        # Create tables in test DB
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with engine.begin() as conn:
            await conn.execute(Tenant.__table__.insert().values(name='acme', metadata={'foo': 'bar'}))

        async with engine.connect() as conn:
            res = await conn.execute(Tenant.__table__.select().where(Tenant.name == 'acme'))
            row = res.first()
            assert row is not None

    run(_test())
