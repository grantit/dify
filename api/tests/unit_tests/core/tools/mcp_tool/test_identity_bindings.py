from core.tools.mcp_tool.identity_bindings import mcp_identity_parameter_kind, present_text


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
