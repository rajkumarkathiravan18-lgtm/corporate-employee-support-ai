from typing import Literal
from pydantic import BaseModel, ConfigDict

AgentName = Literal['hr', 'leave', 'payroll', 'finance', 'it', 'access', 'facilities', 'travel', 'benefits', 'learning', 'procurement', 'company']

class RouteDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    agents: list[AgentName]
    intent: str
    requires_retrieval: bool
    requires_tool: bool
    action: Literal['none', 'leave_balance', 'claim_status', 'ticket_status', 'create_it_ticket']
    needs_clarification: bool
    requires_human: bool
    reason: str

class Review(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['PASS', 'RETRY', 'ASK_USER', 'ESCALATE', 'BLOCK']
    reason: str

class SpecialistResult(BaseModel):
    agent: str
    answer: str
    sources: list[str]
    tool_evidence: str = ''
