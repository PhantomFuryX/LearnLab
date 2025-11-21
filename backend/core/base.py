from __future__ import annotations
from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field


class Step(BaseModel):
    name: str
    detail: str
    output: Optional[Dict[str, Any]] = None


class AgentState(BaseModel):
    session_id: str
    message: str
    preferred_agent: Optional[str] = None
    namespace: Optional[str] = None
    k: int = 4
    context: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)

    # Runtime/outputs
    steps: List[Step] = Field(default_factory=list)
    result: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class BaseAgent(Protocol):
    name: str

    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ...

    # Optional metadata
    tools: List[str] | None
    input_model: Optional[type[BaseModel]]
    output_model: Optional[type[BaseModel]]
