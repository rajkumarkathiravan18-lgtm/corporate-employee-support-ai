import asyncio
from types import SimpleNamespace

from backend.mcp import storage
from backend.orchestration import workflow
from backend.orchestration.schemas import Review, RouteDecision


class FakeAgent:
    def __init__(self, content):
        self.content = content

    async def run(self, task):
        return SimpleNamespace(messages=[SimpleNamespace(content=self.content)])


class FakeModel:
    async def close(self):
        pass


class FakeKnowledge:
    def search(self, query, domains):
        return [{"source": f"{domains[0]}.md", "text": f"Verified {domains[0]} policy", "score": 0.9}]


def make_desk(monkeypatch, decision):
    monkeypatch.setattr(workflow, "client", lambda *args: FakeModel())
    monkeypatch.setattr(workflow, "manager", lambda model: FakeAgent(decision))
    monkeypatch.setattr(workflow, "specialist", lambda name, model: FakeAgent(f"Verified {name} policy"))
    monkeypatch.setattr(workflow, "evaluator", lambda model: FakeAgent(Review(status="PASS", reason="Supported")))
    return workflow.SupportDesk("demo-key", knowledge=FakeKnowledge())


def route(agents, action="none", requires_retrieval=True):
    return RouteDecision(
        agents=agents, intent="test", requires_retrieval=requires_retrieval,
        requires_tool=action != "none", action=action,
        needs_clarification=False, requires_human=False, reason="test",
    )


def test_one_word_travel_uses_retrieval_even_when_manager_flag_is_false(monkeypatch):
    desk = make_desk(monkeypatch, route(["travel"], requires_retrieval=False))
    result = asyncio.run(desk.ask("travel", "EMP001"))
    assert result["status"] == "answered"
    assert result["sources"] == ["travel.md"]
    assert "travel" in result["answer"]


def test_multi_department_returns_both_sources(monkeypatch):
    desk = make_desk(monkeypatch, route(["travel", "finance"]))
    result = asyncio.run(desk.ask("How do I book and claim?", "EMP001"))
    assert result["route"] == ["travel", "finance"]
    assert result["sources"] == ["finance.md", "travel.md"]


def test_ticket_requires_confirmation_and_is_created_once(monkeypatch):
    desk = make_desk(monkeypatch, route(["it"], action="create_it_ticket"))
    calls = []

    async def fake_invoke(action, employee_id, **kwargs):
        calls.append((action, employee_id, kwargs))
        return "IT102"

    monkeypatch.setattr(workflow, "invoke", fake_invoke)
    first = asyncio.run(desk.ask("Create IT ticket for VPN timeout", "EMP001"))
    assert first["pending_action"] == "create_it_ticket"
    assert calls == []
    confirmed = asyncio.run(desk.confirm_it_ticket("EMP001", "VPN timeout after MFA"))
    assert confirmed["status"] == "action_completed"
    assert "IT102" in confirmed["answer"]
    assert len(calls) == 1


def test_ticket_persists_and_other_employee_cannot_read_it(tmp_path):
    path = tmp_path / "records.sqlite3"
    ticket_id = storage.create_ticket("EMP002", "My laptop cannot connect to VPN", path)
    assert storage.ticket_status("EMP002", ticket_id, path) == "Open"
    assert storage.ticket_status("EMP001", ticket_id, path) == "No ticket found for your account"
    assert storage.leave_balance("EMP001", path) == {"casual": 5, "sick": 7}
    assert storage.claim_status("EMP002", "CLM100", path) == "No claim found for your account"
