"""Trusted user and conversation bindings for MCP tool arguments.

Some MCP tools declare arguments that mean the authenticated end user or the
current conversation. Those values are session facts. Agent v2 keeps them out
of the model-facing schema and supplies them as form/runtime values so a model
argument cannot invent or replace them.

The recognized names, after lowercasing and removing non-alphanumeric
characters, are:

- user: ``user``, ``userid``, ``enduserid``, ``currentuser``, ``currentuserid``
  (so ``user_id``, ``userId``, ``end_user_id``, and ``current_user_id`` match)
- conversation: ``conversationid`` and ``currentconversationid``
  (so ``conversation_id`` and ``conversationId`` match)

Only string and unconstrained arguments are bound. A parameter named ``user``
that is an object or number stays model-visible, because coercing it to an id
would change its contract. ``username`` and ``conversation`` do not match.

The same name set is mirrored by the Agent v2 tool settings UI.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from core.tools.__base.tool import Tool
from core.tools.entities.tool_entities import ToolParameter

type McpIdentityParameterKind = Literal["user", "conversation"]

_USER_PARAMETER_NAMES = frozenset(
    {
        "user",
        "userid",
        "enduserid",
        "currentuser",
        "currentuserid",
    }
)
_CONVERSATION_PARAMETER_NAMES = frozenset(
    {
        "conversationid",
        "currentconversationid",
    }
)
_BINDABLE_PARAMETER_TYPES = frozenset(
    {
        ToolParameter.ToolParameterType.STRING,
        ToolParameter.ToolParameterType.ANY,
    }
)


def mcp_identity_parameter_kind(name: str) -> McpIdentityParameterKind | None:
    """Return which trusted session value ``name`` denotes, if any.

    Preconditions: ``name`` is the declared MCP argument name.
    Postconditions: returns ``"user"`` or ``"conversation"`` for a recognized
    identity argument, and ``None`` for every other name.
    """

    normalized = "".join(character for character in name.lower() if character.isalnum())
    if normalized in _USER_PARAMETER_NAMES:
        return "user"
    if normalized in _CONVERSATION_PARAMETER_NAMES:
        return "conversation"
    return None


def present_text(value: object) -> str | None:
    """Return a stripped string, or ``None`` when ``value`` is blank or not text.

    Preconditions: none. Non-strings, including numbers, are absent.
    Postconditions: the result is a non-empty string or ``None``.
    """

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped


def first_present_text(*values: object) -> str | None:
    """Return the first non-blank string in ``values``.

    Preconditions: none.
    Postconditions: returns that string, or ``None`` when every value is absent.
    """

    for value in values:
        text = present_text(value)
        if text is not None:
            return text
    return None


def apply_mcp_identity_bindings(
    tool: Tool,
    *,
    user_id: str | None,
    conversation_id: str | None,
    configured_parameters: Mapping[str, Any] | None = None,
) -> None:
    """Bind identity arguments on ``tool`` from configuration, then the session.

    Preconditions: ``tool.runtime`` exists. ``configured_parameters`` are values
    saved by the app builder or already resolved for this run, never model
    arguments. ``user_id`` and ``conversation_id`` come from the trusted
    session. The tool entity may be shared with a provider cache, so this
    replaces it with a detached copy before changing declarations.

    Postconditions: each bindable identity argument has form ``FORM`` and is
    optional. Its runtime value is the configured text when one is present,
    otherwise the matching session text, otherwise ``""``. That runtime value
    is what invocation merges over model arguments. Unrelated parameters and
    runtime keys are unchanged. A missing runtime leaves the tool untouched.
    """

    if tool.runtime is None:
        return

    configured = configured_parameters or {}
    trusted: dict[McpIdentityParameterKind, str | None] = {
        "user": present_text(user_id),
        "conversation": present_text(conversation_id),
    }
    detached = tool.entity.model_copy(deep=True)
    parameters = [_bind_identity_parameter(tool, parameter, configured, trusted) for parameter in detached.parameters]
    detached.parameters = parameters
    tool.entity = detached


def _bind_identity_parameter(
    tool: Tool,
    parameter: ToolParameter,
    configured: Mapping[str, Any],
    trusted: Mapping[McpIdentityParameterKind, str | None],
) -> ToolParameter:
    """Return ``parameter`` rebound to a form value, or the original declaration.

    Preconditions: ``tool.runtime`` exists. ``configured`` and ``trusted`` follow
    :func:`apply_mcp_identity_bindings`.
    Postconditions: a bindable identity argument is returned as an optional
    form parameter and its chosen text is stored on the tool runtime. Every
    other argument is returned unchanged.
    """

    kind = mcp_identity_parameter_kind(parameter.name)
    if kind is None or parameter.type not in _BINDABLE_PARAMETER_TYPES:
        return parameter
    assert tool.runtime is not None
    chosen = present_text(configured.get(parameter.name))
    if chosen is None:
        chosen = trusted[kind] or ""
    tool.runtime.runtime_parameters[parameter.name] = chosen
    return parameter.model_copy(
        update={
            "form": ToolParameter.ToolParameterForm.FORM,
            "required": False,
        }
    )
