import type { ToolParameter } from '@/app/components/tools/types'
import type { ToolWithProvider } from '@/app/components/workflow/types'
import { CollectionType } from '@/app/components/tools/types'

/**
 * Names recognized as the current user or conversation on an MCP tool.
 * Keep this set aligned with `api/core/tools/mcp_tool/identity_bindings.py`.
 */
const USER_PARAMETER_NAMES = new Set([
  'user',
  'userid',
  'enduserid',
  'currentuser',
  'currentuserid',
])
const CONVERSATION_PARAMETER_NAMES = new Set(['conversationid', 'currentconversationid'])

export type McpIdentityParameterKind = 'user' | 'conversation'

export function mcpIdentityParameterKind(name: string): McpIdentityParameterKind | null {
  const normalized = name.toLowerCase().replace(/[^a-z0-9]/g, '')
  if (USER_PARAMETER_NAMES.has(normalized)) return 'user'
  if (CONVERSATION_PARAMETER_NAMES.has(normalized)) return 'conversation'
  return null
}

/**
 * Move bindable MCP identity arguments into the tool settings form.
 *
 * The runtime fills a blank value from the current user or conversation and
 * does not let the model replace it. Non-text arguments stay model inputs.
 */
export function withMcpIdentityFormBindings(
  collection: ToolWithProvider,
  hints: Record<McpIdentityParameterKind, string>,
  language: string,
): ToolWithProvider {
  if (collection.type !== CollectionType.mcp) return collection

  return {
    ...collection,
    tools: collection.tools.map((tool) => ({
      ...tool,
      parameters: tool.parameters.map((parameter) =>
        bindIdentityParameter(parameter, hints, language),
      ),
    })),
  }
}

function bindIdentityParameter(
  parameter: ToolParameter,
  hints: Record<McpIdentityParameterKind, string>,
  language: string,
): ToolParameter {
  const kind = mcpIdentityParameterKind(parameter.name)
  if (kind === null || (parameter.type !== 'string' && parameter.type !== 'any')) return parameter

  const hint = hints[kind]
  return {
    ...parameter,
    form: 'form',
    required: false,
    human_description: {
      ...parameter.human_description,
      en_US: hint,
      zh_Hans: hint,
      [language]: hint,
    },
  }
}
