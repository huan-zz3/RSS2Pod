import { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Input } from '../components/Input.js';
import { getGroup, updateGroup } from '../commands/groups.js';

export interface GroupEditProps {
  groupId: string;
  onBack: () => void;
}

type EditField = 'name' | 'enabled' | 'triggerType' | 'sourceIds' | 'triggerCron' | 'triggerThreshold' | 'triggerLlmEnabled' | 'learningMode';

interface GroupEditData {
  id: string;
  name: string;
  enabled: boolean;
  triggerType: string;
  triggerConfig: {
    cron?: string;
    threshold?: number;
    llmEnabled?: boolean;
  };
  sourceIds: string[];
  sourceCount: number;
  learningMode: 'normal' | 'word_explanation' | 'sentence_translation';
}

export function GroupEdit({ groupId, onBack }: GroupEditProps) {
  const [group, setGroup] = useState<GroupEditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentField, setCurrentField] = useState<EditField | null>(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    loadGroup();
  }, []);

  const loadGroup = async () => {
    try {
      setLoading(true);
      const g = await getGroup(groupId);
      if (g) {
        setGroup({
          id: g.id,
          name: g.name,
          enabled: g.enabled,
          triggerType: g.triggerType,
          triggerConfig: {
            cron: g.triggerConfig?.cron || '',
            threshold: g.triggerConfig?.threshold || 10,
            llmEnabled: g.triggerConfig?.llmEnabled ?? false,
          },
          sourceIds: g.sourceIds || [],
          sourceCount: g.sourceCount,
          learningMode: (g as any).learningMode || 'normal',
        });
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load group');
    } finally {
      setLoading(false);
    }
  };

  useInput((input, key) => {
    if (currentField) {
      if (key.escape) {
        setCurrentField(null);
        return;
      }
      if (key.return) {
        handleFieldSubmit();
        return;
      }
      return;
    }

    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    } else if (input === '1' && group) {
      setCurrentField('name');
      setEditValue(group.name);
    } else if (input === '2' && group) {
      setCurrentField('enabled');
      setEditValue(group.enabled ? 'true' : 'false');
    } else if (input === '3' && group) {
      setCurrentField('triggerType');
      setEditValue(group.triggerType);
    } else if (input === '4' && group) {
      setCurrentField('sourceIds');
      setEditValue(group.sourceIds.join(','));
    } else if (input === '5' && group) {
      setCurrentField('triggerCron');
      setEditValue(group.triggerConfig.cron || '');
    } else if (input === '6' && group) {
      setCurrentField('triggerThreshold');
      setEditValue(String(group.triggerConfig.threshold || 10));
    } else if (input === '7' && group) {
      setCurrentField('triggerLlmEnabled');
      setEditValue(group.triggerConfig.llmEnabled ? 'true' : 'false');
    } else if (input === '8' && group) {
      setCurrentField('learningMode');
      setEditValue(group.learningMode);
    } else if (input === 's') {
      handleSave();
    }
  });

  const handleFieldSubmit = () => {
    if (!currentField || !group) return;
    
    let updatedGroup = { ...group };
    
    switch (currentField) {
      case 'name':
        updatedGroup = { ...updatedGroup, name: editValue.trim() };
        break;
      case 'enabled':
        updatedGroup = { ...updatedGroup, enabled: editValue.toLowerCase() === 'true' };
        break;
      case 'triggerType':
        updatedGroup = { ...updatedGroup, triggerType: editValue.trim() };
        break;
      case 'sourceIds': {
        const newSourceIds = editValue.split(',').map((s: string) => s.trim()).filter((s: string) => s);
        updatedGroup = { ...updatedGroup, sourceIds: newSourceIds, sourceCount: newSourceIds.length };
        break;
      }
      case 'triggerCron':
        updatedGroup = { ...updatedGroup, triggerConfig: { ...updatedGroup.triggerConfig, cron: editValue.trim() } };
        break;
      case 'triggerThreshold':
        updatedGroup = { ...updatedGroup, triggerConfig: { ...updatedGroup.triggerConfig, threshold: parseInt(editValue, 10) || 10 } };
        break;
      case 'triggerLlmEnabled':
        updatedGroup = { ...updatedGroup, triggerConfig: { ...updatedGroup.triggerConfig, llmEnabled: editValue.toLowerCase() === 'true' } };
        break;
      case 'learningMode': {
        const modeMap: Record<string, 'normal' | 'word_explanation' | 'sentence_translation'> = {
          'normal': 'normal',
          'n': 'normal',
          'word_explanation': 'word_explanation',
          'word': 'word_explanation',
          'w': 'word_explanation',
          'sentence_translation': 'sentence_translation',
          'sentence': 'sentence_translation',
          's': 'sentence_translation',
        };
        const inputKey = editValue.toLowerCase().trim();
        if (!modeMap[inputKey]) {
          setError(`Invalid learning mode. Valid: normal (n), word (w), sentence (s)`);
          return;
        }
        updatedGroup = { ...updatedGroup, learningMode: modeMap[inputKey] };
        break;
      }
    }
    setGroup(updatedGroup);
    setCurrentField(null);
  };

  const handleSave = async () => {
    if (!group) return;
    try {
      await updateGroup(groupId, {
        name: group.name,
        enabled: group.enabled,
        triggerType: group.triggerType,
        sourceIds: group.sourceIds,
        triggerConfig: {
          cron: group.triggerConfig.cron || undefined,
          threshold: group.triggerConfig.threshold || undefined,
          llmEnabled: group.triggerConfig.llmEnabled !== undefined ? group.triggerConfig.llmEnabled : undefined,
        },
        learningMode: group.learningMode,
      });
      onBack();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save group');
    }
  };

  if (loading) {
    return (
      <Box flexDirection="column">
        <Text bold>Edit Group</Text>
        <Box marginTop={1}>
          <Text dimColor>Loading group...</Text>
        </Box>
      </Box>
    );
  }

  if (error && !currentField) {
    return (
      <Box flexDirection="column">
        <Text bold color="red">Edit Group</Text>
        <Box marginTop={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Press 'b' or 'q' to go back</Text>
        </Box>
      </Box>
    );
  }

  if (!group) {
    return (
      <Box flexDirection="column">
        <Text bold>Edit Group</Text>
        <Box marginTop={1}>
          <Text dimColor>Loading...</Text>
        </Box>
      </Box>
    );
  }

  if (currentField) {
    const fieldLabels: Record<EditField, string> = {
      name: 'Group Name',
      enabled: 'Enabled (true/false)',
      triggerType: 'Trigger Type (time/count/llm/mixed)',
      sourceIds: 'Source IDs (comma-separated)',
      triggerCron: 'Cron Expression (e.g., 0 9 * * *)',
      triggerThreshold: 'Article Threshold',
      triggerLlmEnabled: 'LLM Trigger Enabled (true/false)',
      learningMode: 'Learning Mode (normal/word/sentence)',
    };

    const placeholder = currentField === 'sourceIds' 
      ? 'e.g., 62,48,63' 
      : currentField === 'enabled' || currentField === 'triggerLlmEnabled'
      ? 'true or false'
      : currentField === 'triggerCron'
      ? 'e.g., 0 9 * * * (every day at 9 AM)'
      : currentField === 'triggerThreshold'
      ? 'e.g., 10 (trigger when 10 articles are unprocessed)'
      : currentField === 'learningMode'
      ? 'normal (n), word explanation (w), sentence translation (s)'
      : '';

    return (
      <Box flexDirection="column">
        <Text bold>Edit {fieldLabels[currentField]}</Text>
        <Box marginTop={1}>
          <Input
            label={`${fieldLabels[currentField]}: `}
            value={editValue}
            onChange={setEditValue}
            onSubmit={handleFieldSubmit}
            onCancel={() => setCurrentField(null)}
          />
        </Box>
        <Box marginTop={1}>
          {placeholder && <Text dimColor>Example: {placeholder}</Text>}
          <Text dimColor>Enter to save, Esc to cancel</Text>
        </Box>
      </Box>
    );
  }

  return (
    <Box flexDirection="column">
      <Text bold>Edit Group</Text>
      <Box flexDirection="column" marginTop={1}>
        <Box>
          <Text color="cyan">1. Name:</Text>
          <Text> {group.name}</Text>
        </Box>
        <Box>
          <Text color="cyan">2. Enabled:</Text>
          <Text> {group.enabled ? '✓' : '✗'}</Text>
        </Box>
        <Box>
          <Text color="cyan">3. Trigger Type:</Text>
          <Text> {group.triggerType}</Text>
        </Box>
        <Box>
          <Text color="cyan">4. Sources:</Text>
          <Text> {group.sourceCount} feeds</Text>
        </Box>
        {group.sourceIds.length > 0 && (
          <Box>
            <Text dimColor>   IDs: {group.sourceIds.join(', ')}</Text>
          </Box>
        )}
        <Box>
          <Text color="cyan">5. Cron:</Text>
          <Text> {group.triggerConfig.cron || '(not set)'}</Text>
        </Box>
        <Box>
          <Text color="cyan">6. Threshold:</Text>
          <Text> {group.triggerConfig.threshold ?? 10}</Text>
        </Box>
        <Box>
          <Text color="cyan">7. LLM Enabled:</Text>
          <Text> {group.triggerConfig.llmEnabled ? '✓' : '✗'}</Text>
        </Box>
        <Box>
          <Text color="cyan">8. Learning Mode:</Text>
          <Text> {group.learningMode === 'normal' ? 'Normal' : group.learningMode === 'word_explanation' ? 'Word Explanation' : 'Sentence Translation'}</Text>
        </Box>
      </Box>
      <Box marginTop={1}>
        <Text dimColor>1-8 Edit field  s Save  b Back</Text>
      </Box>
    </Box>
  );
}
