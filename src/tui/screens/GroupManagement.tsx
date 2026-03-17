import { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Table } from '../components/Table.js';
import { Input } from '../components/Input.js';
import { ConfirmDialog } from '../components/ConfirmDialog.js';
import {
  listGroups,
  createGroup,
  deleteGroup,
  type GroupInfo,
} from '../commands/groups.js';

export interface GroupManagementProps {
  onBack: () => void;
  onEdit?: (groupId: string) => void;
}

type Mode = 'view' | 'creating' | 'deleting' | 'editing';

export function GroupManagement({ onBack, onEdit }: GroupManagementProps) {
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>('view');
  const [selectedGroup, setSelectedGroup] = useState<GroupInfo | null>(null);
  const [newGroupName, setNewGroupName] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [deleteSelection, setDeleteSelection] = useState<'cancel' | 'confirm'>('cancel');

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const data = await listGroups();
      setGroups(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load groups');
    } finally {
      setLoading(false);
    }
  };

  useInput((input, key) => {
    if (mode === 'view') {
      if (key.escape || input === 'q' || input === 'b') {
        onBack();
      } else if (input === 'c') {
        setMode('creating');
      } else if (input === 'e' && groups.length > 0) {
        const group = groups[selectedIndex];
        if (group) {
          onEdit?.(group.id);
        }
      } else if (input === 'd' && groups.length > 0) {
        const group = groups[selectedIndex];
        if (group) {
          setSelectedGroup(group);
          setMode('deleting');
          setDeleteSelection('cancel');
        }
      } else if (input === 'j' || key.downArrow) {
        setSelectedIndex(prev => Math.min(prev + 1, groups.length - 1));
      } else if (input === 'k' || key.upArrow) {
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      }
    } else if (mode === 'deleting') {
      if (input === 'a' || input === 'h' || key.leftArrow) {
        setDeleteSelection('cancel');
      } else if (input === 'd' || input === 'l' || key.rightArrow) {
        setDeleteSelection('confirm');
      } else if (key.return) {
        if (deleteSelection === 'confirm') {
          handleDeleteConfirm();
        } else {
          handleDeleteCancel();
        }
      } else if (key.escape || input === 'q' || input === 'b') {
        handleDeleteCancel();
      }
    }
  });

  const handleCreateConfirm = async () => {
    if (!newGroupName.trim()) {
      return;
    }
    try {
      await createGroup(newGroupName.trim(), {});
      setNewGroupName('');
      setMode('view');
      await loadGroups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create group');
      setMode('view');
    }
  };

  const handleCreateCancel = () => {
    setNewGroupName('');
    setMode('view');
  };



  const handleDeleteConfirm = async () => {
    if (!selectedGroup) {
      return;
    }
    try {
      await deleteGroup(selectedGroup.id);
      setMode('view');
      setSelectedGroup(null);
      await loadGroups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete group');
      setMode('view');
    }
  };

  const handleDeleteCancel = () => {
    setMode('view');
    setSelectedGroup(null);
  };

  if (mode === 'creating') {
    return (
      <Box flexDirection="column">
        <Text bold>Create New Group</Text>
        <Box marginTop={1}>
          <Input
            label="Group Name: "
            value={newGroupName}
            onChange={setNewGroupName}
            onSubmit={handleCreateConfirm}
            onCancel={handleCreateCancel}
          />
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Enter to confirm, Esc to cancel</Text>
        </Box>
      </Box>
    );
  }



  if (mode === 'deleting' && selectedGroup) {
    return (
      <Box flexDirection="column">
        <ConfirmDialog
          title="Delete Group"
          message={`Are you sure you want to delete "${selectedGroup.name}"?`}
          selected={deleteSelection}
        />
        <Box marginTop={1}>
          <Text dimColor>a/h ← Cancel  d/l → Confirm  Enter</Text>
        </Box>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box flexDirection="column">
        <Text bold>Group Management</Text>
        <Box marginTop={1}>
          <Text dimColor>Loading groups...</Text>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box flexDirection="column">
        <Text bold color="red">Group Management</Text>
        <Box marginTop={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Press 'r' to retry, 'b' or 'q' to go back</Text>
        </Box>
      </Box>
    );
  }

  const columns = [
    { header: 'ID', accessor: (g: GroupInfo) => g.id.slice(-8), width: 10 },
    { header: 'Name', accessor: (g: GroupInfo) => g.name.slice(0, 15), width: 17 },
    { header: 'Enabled', accessor: (g: GroupInfo) => g.enabled ? '✓' : '✗', width: 8 },
    { header: 'Trigger', accessor: (g: GroupInfo) => g.triggerType.slice(0, 8), width: 10 },
    { header: 'Sources', accessor: (g: GroupInfo) => g.sourceCount.toString(), width: 8 },
  ];

  return (
    <Box flexDirection="column">
      <Text bold>Group Management</Text>
      <Box marginTop={1}>
        <Table
          data={groups}
          columns={columns}
          selectedIndex={selectedIndex}
        />
      </Box>
      <Box marginTop={1}>
        <Text dimColor>c Create  e Edit  d Delete  ↑↓ Navigate  b Back</Text>
      </Box>
    </Box>
  );
}
