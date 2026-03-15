import { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Input } from '../components/Input.js';
import { getGroup, updateGroup } from '../commands/groups.js';

export interface GroupEditProps {
  groupId: string;
  onBack: () => void;
}

type EditField = 'name' | 'enabled' | 'triggerType' | 'sourceIds';

interface GroupEditData {
  id: string;
  name: string;
  enabled: boolean;
  triggerType: string;
  sourceIds: string[];
  sourceCount: number;
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
          sourceIds: g.sourceIds || [],
          sourceCount: g.sourceCount,
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
      } else if (key.return) {
        handleFieldSubmit();
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
    } else if (input === 's') {
      handleSave();
    }
  });

  const handleFieldSubmit = () => {
    if (!currentField || !group) return;
    
    switch (currentField) {
      case 'name':
        group.name = editValue.trim();
        break;
      case 'enabled':
        group.enabled = editValue.toLowerCase() === 'true';
        break;
      case 'triggerType':
        group.triggerType = editValue.trim();
        break;
      case 'sourceIds':
        group.sourceIds = editValue.split(',').map((s: string) => s.trim()).filter((s: string) => s);
        group.sourceCount = group.sourceIds.length;
        break;
    }
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
    };

    const placeholder = currentField === 'sourceIds' 
      ? 'e.g., 62,48,63' 
      : currentField === 'enabled'
      ? 'true or false'
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
      </Box>
      <Box marginTop={1}>
        <Text dimColor>1-4 Edit field  s Save  b Back</Text>
      </Box>
    </Box>
  );
}
