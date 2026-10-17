"""Strict CP1 tool registry: validation, authorization, verified result parsing."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from agentic_ai.authorization import authorize


class UnknownToolError(LookupError):
    pass


class UnauthorizedToolError(PermissionError):
    pass


class ToolContractError(ValueError):
    pass


class ToolExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolDefinition:
    fn: Callable[..., Any]
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    read_only: bool


class ToolRegistry:
    def __init__(self, *, allow_write_registration: bool = False) -> None:
        self.allow_write_registration = allow_write_registration
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        fn: Callable[..., Any],
        *,
        input_model: type[BaseModel],
        output_model: type[BaseModel],
        read_only: bool = True,
    ) -> None:
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError("Invalid tool name.")
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        if not callable(fn) or not issubclass(input_model, BaseModel) or not issubclass(output_model, BaseModel):
            raise TypeError("Tools must be callable and supply Pydantic input/output schemas.")
        if not read_only and not self.allow_write_registration:
            raise ValueError("CP1 only supports read-only tools. Approval and writes belong to CP2.")
        self._tools[name] = ToolDefinition(fn, input_model, output_model, read_only)

    def is_read_only(self, name: str) -> bool:
        if name not in self._tools:
            raise UnknownToolError("Unknown tool.")
        return self._tools[name].read_only

    def get(self, name: str) -> Callable:
        """Existing starter compatibility. Never use get() as an execution entrypoint."""
        if name not in self._tools:
            raise UnknownToolError("Unknown tool.")
        return self._tools[name].fn

    def names(self) -> list[str]:
        return sorted(self._tools)

    def execute(self, name: str, arguments: dict[str, Any], *, role: str,
                approval_granted: bool = False) -> dict[str, Any]:
        if name not in self._tools:
            raise UnknownToolError("Unknown tool.")
        if not authorize(role, name):
            raise UnauthorizedToolError("Role is not permitted to run the selected tool.")
        if not isinstance(arguments, dict):
            raise ToolContractError("Tool arguments must be an object.")
        tool = self._tools[name]
        if not tool.read_only and not approval_granted:
            raise UnauthorizedToolError("Write-capable tools need a recorded human approval.")
        try:
            validated = tool.input_model.model_validate(arguments)
        except ValidationError:
            raise ToolContractError("Tool arguments failed schema validation.") from None
        try:
            result = tool.fn(**validated.model_dump())
        except Exception:
            raise ToolExecutionError("The approved tool failed without a verified output.") from None
        try:
            return tool.output_model.model_validate(result).model_dump(mode="json")
        except ValidationError:
            raise ToolContractError("Tool result failed schema validation; no success may be claimed.") from None
