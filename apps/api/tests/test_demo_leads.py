"""Integration tests for the demo lead CRUD endpoints (app.api.v1.routers.demo)."""

from app.api.v1.routers.demo import create_demo_lead, list_demo_leads, update_demo_lead
from app.db.session import async_session
from app.schemas.demo import DemoLeadContactedUpdate, DemoLeadCreate


async def test_create_lead_then_list_returns_it_ordered_by_created_at_desc():
    async with async_session() as db:
        older = await create_demo_lead(
            DemoLeadCreate(name="Joao Older", contact="joao@example.com"), db
        )
    async with async_session() as db:
        newer = await create_demo_lead(
            DemoLeadCreate(name="Maria Newer", contact="maria@example.com", business_name="Salao Maria"), db
        )

    async with async_session() as db:
        leads = await list_demo_leads(db)

    ids = [lead.id for lead in leads]
    assert older.id in ids
    assert newer.id in ids
    assert ids.index(newer.id) < ids.index(older.id)


async def test_update_lead_sets_and_clears_contacted_at():
    async with async_session() as db:
        lead = await create_demo_lead(DemoLeadCreate(name="Contato Teste", contact="teste@example.com"), db)
    assert lead.contacted_at is None

    async with async_session() as db:
        contacted = await update_demo_lead(lead.id, DemoLeadContactedUpdate(contacted=True), db)
    assert contacted.contacted_at is not None

    async with async_session() as db:
        uncontacted = await update_demo_lead(lead.id, DemoLeadContactedUpdate(contacted=False), db)
    assert uncontacted.contacted_at is None
