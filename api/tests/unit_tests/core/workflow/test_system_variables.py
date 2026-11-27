from types import SimpleNamespace

from core.tools.mcp_tool.identity_bindings import identity_text_from_start_inputs
from core.workflow.system_variables import (
    SystemVariableKey,
    build_bootstrap_variables,
    build_system_variables,
    default_system_variables,
    get_node_creation_preload_selectors,
    get_system_text,
    get_system_value,
    system_variables_to_mapping,
)
from core.workflow.variable_pool_initializer import add_node_inputs_to_pool, add_variables_to_pool
from graphon.file import File, FileTransferMethod, FileType
from graphon.nodes import BuiltinNodeTypes
from graphon.runtime import VariablePool


def test_build_system_variables_normalizes_workflow_execution_id() -> None:
    system_variables = build_system_variables(
        user_id="user-id",
        workflow_execution_id="run-id",
        query="hello",
        ignored=None,
    )
    system_values = system_variables_to_mapping(system_variables)

    assert system_values == {
        "user_id": "user-id",
        "workflow_run_id": "run-id",
        "query": "hello",
        "files": [],
    }


def test_build_system_variables_preserves_explicit_workflow_run_id() -> None:
    system_variables = build_system_variables(
        workflow_run_id="explicit-run-id",
        workflow_execution_id="ignored-run-id",
    )
    system_values = system_variables_to_mapping(system_variables)

    assert system_values["workflow_run_id"] == "explicit-run-id"
    assert system_values["files"] == []


def test_build_system_variables_preserves_file_values() -> None:
    file = File(
        file_type=FileType.DOCUMENT,
        transfer_method=FileTransferMethod.LOCAL_FILE,
        related_id="file-id",
        filename="test.txt",
        extension=".txt",
        mime_type="text/plain",
        size=1,
        storage_key="storage-key",
    )

    system_variables = build_system_variables(files=[file])
    system_values = system_variables_to_mapping(system_variables)

    assert system_values["files"] == [file]


def test_default_system_variables_generates_workflow_run_id() -> None:
    system_variables = default_system_variables()
    system_values = system_variables_to_mapping(system_variables)

    assert isinstance(system_values["workflow_run_id"], str)
    assert system_values["workflow_run_id"]
    assert system_values["files"] == []


def test_get_node_creation_preload_selectors_requires_conversation_for_memory_nodes() -> None:
    selectors = get_node_creation_preload_selectors(
        node_type=BuiltinNodeTypes.QUESTION_CLASSIFIER,
        node_data=SimpleNamespace(memory=object()),
    )

    assert selectors == (("sys", "conversation_id"),)


def test_get_node_creation_preload_selectors_skips_non_memory_nodes() -> None:
    selectors = get_node_creation_preload_selectors(
        node_type=BuiltinNodeTypes.START,
        node_data=SimpleNamespace(memory=None),
    )

    assert selectors == ()


def test_get_system_text_reads_advanced_chat_conversation_id_from_the_variable_pool() -> None:
    """Advanced Chat writes sys.conversation_id into the VariablePool.

    Persisted WorkflowRun.inputs deliberately omit that key, so an app-run
    export can look like the session id was never present. The runtime pool
    still has it, and get_system_text is what Agent v2 / WaT forwarding read.
    """

    conversation_id = "fefce082-4886-4b69-9576-4c01e0f987eb"
    variable_pool = VariablePool()
    add_variables_to_pool(
        variable_pool,
        build_bootstrap_variables(
            system_variables=build_system_variables(
                query="hello",
                files=[],
                conversation_id=conversation_id,
                user_id="planit-visitor-7590ac4c36f2c2b6a467fb0d04004c1e",
                dialogue_count=1,
                app_id="app-id",
                workflow_id="workflow-id",
                workflow_execution_id="run-id",
            ),
        ),
    )
    add_node_inputs_to_pool(variable_pool, node_id="start", inputs={"skill_id": "default"})

    assert get_system_text(variable_pool, SystemVariableKey.CONVERSATION_ID) == conversation_id
    assert get_system_value(variable_pool, SystemVariableKey.USER_ID) == (
        "planit-visitor-7590ac4c36f2c2b6a467fb0d04004c1e"
    )
    assert identity_text_from_start_inputs(variable_pool, "conversation") is None
