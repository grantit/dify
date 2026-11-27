import type { ToolParameter } from '@/app/components/tools/types'
import type { ToolWithProvider } from '@/app/components/workflow/types'
import { CollectionType } from '@/app/components/tools/types'
import { mcpIdentityParameterKind, withMcpIdentityFormBindings } from '../identity-bindings'

const hints = {
  user: 'Current user',
  conversation: 'Current conversation',
}

function parameter(name: string, type = 'string', form = 'llm'): ToolParameter {
  return {
    name,
    label: { en_US: name, zh_Hans: name },
    human_description: { en_US: name, zh_Hans: name },
    type,
    form,
    llm_description: name,
    required: true,
    multiple: false,
  }
}

function collection(type: ToolWithProvider['type'], parameters: ToolParameter[]): ToolWithProvider {
  return {
    type,
    tools: [
      {
        name: 'lookup',
        author: 'mcp',
        label: { en_US: 'Lookup', zh_Hans: 'Lookup' },
        description: { en_US: 'Lookup', zh_Hans: 'Lookup' },
        parameters,
        labels: [],
        output_schema: {},
      },
    ],
  } as unknown as ToolWithProvider
}

describe('mcp identity form bindings', () => {
  it('recognizes the common user and conversation argument names', () => {
    expect(
      ['user', 'user_id', 'userId', 'userid', 'end_user_id', 'current_user_id'].map(
        mcpIdentityParameterKind,
      ),
    ).toEqual(['user', 'user', 'user', 'user', 'user', 'user'])
    expect(
      ['conversation_id', 'conversationId', 'current_conversation_id'].map(
        mcpIdentityParameterKind,
      ),
    ).toEqual(['conversation', 'conversation', 'conversation'])
    expect(['username', 'conversation', 'query'].map(mcpIdentityParameterKind)).toEqual([
      null,
      null,
      null,
    ])
  })

  it('moves text identity arguments into the settings form and leaves other arguments for the model', () => {
    const result = withMcpIdentityFormBindings(
      collection(CollectionType.mcp, [
        parameter('query'),
        parameter('user_id'),
        parameter('conversationId'),
        parameter('username'),
        parameter('user', 'object'),
      ]),
      hints,
      'ja_JP',
    )

    const parameters = result.tools[0]!.parameters
    expect(parameters.map((item) => [item.name, item.form, item.required])).toEqual([
      ['query', 'llm', true],
      ['user_id', 'form', false],
      ['conversationId', 'form', false],
      ['username', 'llm', true],
      ['user', 'llm', true],
    ])
    expect(parameters[1]!.human_description.ja_JP).toBe('Current user')
    expect(parameters[2]!.human_description.en_US).toBe('Current conversation')
  })

  it('leaves non-MCP tools unchanged', () => {
    const builtin = collection(CollectionType.builtIn, [parameter('user_id')])
    expect(withMcpIdentityFormBindings(builtin, hints, 'en_US')).toBe(builtin)
  })
})
