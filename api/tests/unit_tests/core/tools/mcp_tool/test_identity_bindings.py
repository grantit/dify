from types import SimpleNamespace

from core.tools.mcp_tool.identity_bindings import (
    identity_text_from_mapping,
    identity_text_from_start_inputs,
    mcp_identity_parameter_kind,
    present_text,
    present_variable_text,
    resolve_workflow_conversation_id,
)


def test_identity_parameter_names_cover_the_common_user_and_conversation_forms() -> None:
    assert [mcp_identity_parameter_kind(name) for name in ("user", "user_id", "userId", "userid", "user-id")] == [
        "user"
    ] * 5
    assert [
        mcp_identity_parameter_kind(name) for name in ("end_user_id", "endUserId", "current_user", "current_user_id")
    ] == ["user"] * 4
    assert [
        mcp_identity_parameter_kind(name)
        for name in ("conversation_id", "conversationId", "conversation-id", "current_conversation_id")
    ] == ["conversation"] * 4
    assert [mcp_identity_parameter_kind(name) for name in ("username", "user_name", "conversation", "query")] == [
        None
    ] * 4


def test_present_text_ignores_blank_and_non_text_values() -> None:
    assert present_text("  session  ") == "session"
    assert present_text("   ") is None
    assert present_text(None) is None
    assert present_text(7) is None


def test_present_variable_text_reads_segment_text_and_value() -> None:
    assert present_variable_text(SimpleNamespace(text="  session  ")) == "session"
    assert present_variable_text(SimpleNamespace(value="conversation-9")) == "conversation-9"
    assert present_variable_text(SimpleNamespace(text="  ", value="  ")) is None
    assert present_variable_text(SimpleNamespace(value=7)) is None


def test_identity_text_from_mapping_selects_the_matching_kind() -> None:
    inputs = {"user_id": "end-user", "conversationId": "  conversation-9  ", "query": "hello"}
    assert identity_text_from_mapping(inputs, "user") == "end-user"
    assert identity_text_from_mapping(inputs, "conversation") == "conversation-9"
    assert identity_text_from_mapping({"conversation": "not-an-id"}, "conversation") is None
    assert identity_text_from_mapping({"conversation_id": "  "}, "conversation") is None


def test_identity_text_from_start_inputs_reads_legacy_and_snippet_prefixes() -> None:
    class _Pool:
        def __init__(self, values: dict[str, dict[str, object]]) -> None:
            self.values = values

        def get_by_prefix(self, prefix: str) -> dict[str, object]:
            return self.values.get(prefix, {})

    start_pool = _Pool({"start": {"conversation_id": "from-start", "userId": "from-start-user"}})
    assert identity_text_from_start_inputs(start_pool, "conversation") == "from-start"
    assert identity_text_from_start_inputs(start_pool, "user") == "from-start-user"

    snippet_pool = _Pool({"__snippet_virtual_start__": {"conversation_id": "from-snippet"}})
    assert identity_text_from_start_inputs(snippet_pool, "conversation") == "from-snippet"
    assert identity_text_from_start_inputs(_Pool({"agent": {"conversation_id": "from-agent"}}), "conversation") is None


def test_resolve_workflow_conversation_id_prefers_a_forwarded_parent_even_when_blank() -> None:
    inputs = {"conversation_id": "from-start"}
    assert (
        resolve_workflow_conversation_id(
            forwarded_conversation_id="parent-conversation",
            forwarded=True,
            inputs=inputs,
        )
        == "parent-conversation"
    )
    assert (
        resolve_workflow_conversation_id(
            forwarded_conversation_id="  ",
            forwarded=True,
            inputs=inputs,
        )
        is None
    )
    assert (
        resolve_workflow_conversation_id(
            forwarded_conversation_id=None,
            forwarded=False,
            inputs=inputs,
        )
        == "from-start"
    )
    assert resolve_workflow_conversation_id(forwarded=False, inputs={"query": "hello"}) is None
