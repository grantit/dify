'use client'

import type { ToolSettingTarget } from '../types'
import type { Tool } from '@/app/components/tools/types'
import type { ToolWithProvider } from '@/app/components/workflow/types'
import type { AgentProviderTool } from '@/features/agent-v2/agent-composer/form-state'
import { useAtomValue, useSetAtom } from 'jotai'
import { useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocale } from '#i18n'
import SettingBuiltInTool from '@/app/components/app/configuration/config/agent/agent-tools/setting-built-in-tool'
import {
  agentComposerToolsAtom,
  agentComposerToolSettingsAtom,
  saveProviderToolActionSettingsAtom,
} from '@/features/agent-v2/agent-composer/store-modules/tools'
import { getPluginLanguage } from '@/i18n/metadata'
import { withMcpIdentityFormBindings } from './identity-bindings'

const localize = (value: string) => ({
  en_US: value,
  zh_Hans: value,
})

const createFallbackToolCollection = (tool: AgentProviderTool): ToolWithProvider =>
  ({
    id: tool.id,
    name: tool.id,
    author: tool.name,
    description: localize(`${tool.name} tools`),
    icon: tool.icon ?? '',
    icon_dark: tool.iconDark,
    label: localize(tool.displayName ?? tool.name),
    type: tool.providerType,
    team_credentials: {},
    is_team_authorization: true,
    allow_delete: tool.allowDelete ?? false,
    labels: [],
    meta: {
      version: '0.0.0',
    },
    tools: tool.actions.map<Tool>((action) => ({
      name: action.toolName,
      author: tool.name,
      label: localize(action.name),
      description: localize(action.description),
      parameters: [],
      labels: [],
      output_schema: {},
    })),
  }) as ToolWithProvider

export function ProviderToolSettingsDialog({
  settingTarget,
  collection,
  onClose,
}: {
  settingTarget: ToolSettingTarget | null
  collection?: ToolWithProvider
  onClose: () => void
}) {
  const tools = useAtomValue(agentComposerToolsAtom)
  const toolSettings = useAtomValue(agentComposerToolSettingsAtom)
  const saveProviderToolActionSettings = useSetAtom(saveProviderToolActionSettingsAtom)
  const locale = useLocale()
  const language = getPluginLanguage(locale)
  const { t } = useTranslation(['agentV2'])
  const identityHints = useMemo(
    () => ({
      user: t(($) => $['agentDetail.configure.tools.identityBinding.user']),
      conversation: t(($) => $['agentDetail.configure.tools.identityBinding.conversation']),
    }),
    [t],
  )
  const currentTarget = useMemo(() => {
    if (!settingTarget) return null

    const tool = tools.find((tool) => tool.kind === 'provider' && tool.id === settingTarget.toolId)
    if (tool?.kind !== 'provider') return null

    const action = tool.actions.find((action) => action.id === settingTarget.actionId)
    if (!action) return null

    return { action, tool }
  }, [settingTarget, tools])
  const toolCollection = useMemo(() => {
    if (!currentTarget) return null

    const resolved = collection ?? createFallbackToolCollection(currentTarget.tool)
    return withMcpIdentityFormBindings(resolved, identityHints, language)
  }, [collection, currentTarget, identityHints, language])
  const handleSave = useCallback(
    (value: Record<string, unknown>) => {
      if (!currentTarget) return

      saveProviderToolActionSettings({
        actionId: currentTarget.action.id,
        value,
      })
      onClose()
    },
    [currentTarget, onClose, saveProviderToolActionSettings],
  )

  if (!currentTarget || !toolCollection) return null

  return (
    <SettingBuiltInTool
      toolName={currentTarget.action.toolName}
      setting={toolSettings[currentTarget.action.id]}
      collection={toolCollection}
      credentialId={currentTarget.tool.credentialId}
      onSave={handleSave}
      onHide={onClose}
    />
  )
}
