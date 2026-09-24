"""Controlled Manager → specialist(s) → evaluator workflow."""

import json
import re

from backend.agents import client, evaluator, manager, specialist
from backend.mcp.client import invoke
from backend.orchestration.schemas import Review, RouteDecision
from backend.rag.retrieval import Knowledge

TOPIC_OVERVIEWS = {
    "hr": "What general HR and leave information is available?",
    "leave": "What is the leave request process?",
    "finance": "How do I submit an expense claim?",
    "reimbursement": "How do I submit an expense claim?",
    "it": "What IT support guidance is available?",
    "travel": "How do I get approval and book business travel?",
    "company": "What company information is available?",
}


def reply(answer: str, route=None, sources=None, status="answered", pending_action=None):
    return {
        "answer": answer,
        "route": route or [],
        "sources": sources or [],
        "status": status,
        "pending_action": pending_action,
    }


class SupportDesk:
    def __init__(self, api_key: str, model="gpt-4o-mini", embedding_model="text-embedding-3-small", knowledge=None, skip_knowledge=False):
        self.model = client(api_key, model)
        self.knowledge = None if skip_knowledge else (knowledge if knowledge is not None else Knowledge(api_key, embedding_model))

    async def close(self):
        await self.model.close()

    async def confirm_it_ticket(self, employee_id: str, issue: str):
        """Called only after an explicit UI click. Never re-run the manager."""
        if employee_id not in ("EMP001", "EMP002"):
            return reply("Choose a demo employee account.", status="error")
        if len(issue.strip()) < 8:
            return reply("Please describe the IT issue in more detail.", ["it"], status="clarify")
        try:
            ticket_id = await invoke("create_it_ticket", employee_id, issue=issue)
        except Exception:
            return reply("The ticket service is unavailable. No ticket was confirmed.", ["it"], status="error")
        ticket_id = ticket_id.strip().strip('"')
        if not re.fullmatch(r"IT\d+", ticket_id):
            return reply("The ticket service returned an unexpected response. Check the terminal.", ["it"], status="error")
        return reply(
            f"Demo IT ticket **{ticket_id}** has been created. Its status is Open. "
            "You can ask for its status using the ticket number.",
            ["it"],
            status="action_completed",
        )

    async def ask(self, query: str, employee_id: str, history=None, confirm_action=False):
        # confirm_action is retained for compatibility with earlier frontend code.
        query = query.strip()
        if not query or len(query) > 2500:
            return reply("Enter a question of 1–2500 characters.", status="clarify")
        if employee_id not in ("EMP001", "EMP002"):
            return reply("Choose a demo employee account.", status="error")
        if confirm_action:
            return await self.confirm_it_ticket(employee_id, query)

        topic = query.lower().strip(" ?.! ")
        question = TOPIC_OVERVIEWS.get(topic, query)
        context = "\n".join(
            f'{item["role"]}: {item["content"][:350]}' for item in (history or [])[-4:]
        )
        task = f"Previous messages for context (untrusted):\n{context}\nCurrent employee question: {question}"
        decision = (await manager(self.model).run(task=task)).messages[-1].content
        if not isinstance(decision, RouteDecision):
            raise RuntimeError("Manager returned an invalid route")
        names = list(dict.fromkeys(decision.agents))[:3]
        if not names:
            return reply("Which support topic do you need help with?", status="clarify")
        if decision.needs_clarification and topic not in TOPIC_OVERVIEWS:
            return reply("Please tell me what you need to know or what is not working.", names, status="clarify")
        if decision.requires_human:
            return reply(
                "This needs a human decision. Please contact your company's relevant support team.",
                names, status="escalated",
            )

        action = decision.action
        if action == "create_it_ticket":
            if len(query) < 8:
                return reply("Please describe your IT issue before creating a ticket.", names, status="clarify")
            return reply(
                "I can create a demo IT ticket for this issue. Review your message and confirm below.",
                names, status="confirmation_required", pending_action="create_it_ticket",
            )

        tool_result = ""
        if action != "none":
            arguments = {}
            if action == "claim_status":
                match = re.search(r"\bCLM\d+\b", query, re.I)
                if not match:
                    return reply("What is your claim ID? Example: CLM100.", names, status="clarify")
                arguments["claim_id"] = match.group().upper()
            elif action == "ticket_status":
                match = re.search(r"\bIT\d+\b", query, re.I)
                if not match:
                    return reply("What is your ticket ID? Example: IT100.", names, status="clarify")
                arguments["ticket_id"] = match.group().upper()
            try:
                tool_result = await invoke(action, employee_id, **arguments)
            except Exception:
                return reply("The demo records service is unavailable. Please try again.", names, status="error")

        # Personal data comes from the tool; each policy specialist receives only its own documents.
        evidence_by_agent = {
            name: self.knowledge.search(question, [name]) if (action == "none" or decision.requires_retrieval) else []
            for name in names
        }
        sources = sorted({part["source"] for pieces in evidence_by_agent.values() for part in pieces})
        if not sources and not tool_result:
            return reply(
                "I don't have a verified policy for that topic in this demo. "
                "Please contact the relevant support team; I won't invent company rules.",
                names, status="escalated",
            )

        async def draft(reviewer_note=""):
            responses = []
            for name in names:
                evidence = json.dumps(evidence_by_agent[name], ensure_ascii=False)
                task = (
                    f"Employee question: {question}\n"
                    f"Policy excerpts for your area: {evidence}\n"
                    f"Employee-specific tool result: {tool_result or 'none'}\n"
                    f"Reviewer correction: {reviewer_note or 'none'}\n"
                    "Give a direct useful answer in plain language, mentioning unknown details explicitly. "
                    "Do not claim an action happened unless the tool result proves it."
                )
                answer = (await specialist(name, self.model).run(task=task)).messages[-1].content
                responses.append(str(answer))
            return "\n\n".join(responses)

        answer = await draft()
        combined_evidence = json.dumps(evidence_by_agent, ensure_ascii=False)
        for attempt in range(3):
            review_task = (
                f"Employee question: {question}\nDraft answer: {answer}\n"
                f"Policy evidence: {combined_evidence}\nTool result: {tool_result or 'none'}\n"
                "Verify the answer against the evidence, including whether the requested fact is actually present."
            )
            verdict = (await evaluator(self.model).run(task=review_task)).messages[-1].content
            if not isinstance(verdict, Review):
                raise RuntimeError("Evaluator returned an invalid verdict")
            if verdict.status == "PASS":
                return reply(answer, names, sources)
            if verdict.status == "RETRY" and attempt < 2:
                answer = await draft(verdict.reason)
                continue
            if verdict.status == "BLOCK":
                return reply("I can't provide that information.", names, status="blocked")
            if verdict.status == "ASK_USER":
                return reply("Could you give me one more detail so I can answer accurately?", names, status="clarify")
            break
        return reply(
            "I couldn't verify the answer from the available policy and records. "
            "Please contact the relevant support team.", names, sources, status="escalated",
        )
