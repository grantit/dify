"""Trusted user and conversation bindings for MCP and Workflow tool arguments.

Some MCP and Workflow-as-Tool tools declare arguments that mean the
authenticated end user or the current conversation. Those values are session
facts. Agent v2 keeps them out of the model-facing schema and supplies them as
form/runtime values so a model argument cannot invent or replace them.

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


def present_variable_text(value: object) -> str | None:
    """Return a stripped string from a raw value or a variable-pool segment.

    Preconditions: none.
    Postconditions: the result is a non-empty string or ``None``. Numbers and
    other non-text values are absent, matching :func:`present_text`.
    """

    text = present_text(value)
    if text is not None:
        return text
    for attribute in ("text", "value"):
        text = present_text(getattr(value, attribute, None))
        if text is not None:
            return text
    return None


def identity_text_from_mapping(
    mapping: Mapping[str, Any] | None,
    kind: McpIdentityParameterKind,
) -> str | None:
    """Return the first present identity value of ``kind`` in ``mapping``.

    Preconditions: ``mapping`` is Start inputs, runtime parameters, or another
    trusted key/value document. Model arguments must not be passed here.
    Postconditions: returns the first non-blank text whose key matches ``kind``,
    or ``None`` when no such value is present.
    """

    if not mapping:
        return None
    for name, value in mapping.items():
        if mcp_identity_parameter_kind(str(name)) != kind:
            continue
        text = present_variable_text(value)
        if text is not None:
            return text
    return None


_START_INPUT_PREFIXES = ("start", "__snippet_virtual_start__")


def identity_text_from_start_inputs(
    variable_pool: Any,
    kind: McpIdentityParameterKind,
) -> str | None:
    """Return a Start-input identity value of ``kind`` from ``variable_pool``.

    Preconditions: ``variable_pool`` implements ``get_by_prefix``. Only the
    legacy ``start`` node and the snippet virtual Start node are read, so a
    mid-graph output with the same name is ignored.
    Postconditions: returns that Start text, or ``None`` when it is absent.
    """

    get_by_prefix = getattr(variable_pool, "get_by_prefix", None)
    if get_by_prefix is None:
        return None
    for prefix in _START_INPUT_PREFIXES:
        text = identity_text_from_mapping(get_by_prefix(prefix), kind)
        if text is not None:
            return text
    return None


def resolve_workflow_conversation_id(
    *,
    forwarded_conversation_id: object = None,
    forwarded: bool = False,
    inputs: Mapping[str, Any] | None = None,
) -> str | None:
    """Choose the trusted conversation id for a workflow run.

    Preconditions: ``forwarded`` is true when a parent session already decided
    the value, including when that value is blank (Workflow-as-Tool). ``inputs``
    are trusted Start inputs from a direct workflow run such as
    ``/v1/workflows/run``. They must not be model-invented tool arguments.
    Postconditions: a forwarded parent value is returned as present text, or
    ``None`` when it is blank, and Start inputs are not consulted. When nothing
    was forwarded, the first conversation Start input is used. An empty result
    stays empty; it is never invented.
    """

    if forwarded:
        return present_text(forwarded_conversation_id)
    return identity_text_from_mapping(inputs, "conversation")
