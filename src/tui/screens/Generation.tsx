import { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Table } from '../components/Table.js';
import { ProgressBar } from '../components/ProgressBar.js';
import { DatabaseManager } from '../../infrastructure/database/DatabaseManager.js';
import { PipelineOrchestrator } from '../../features/pipeline/PipelineOrchestrator.js';
import { loadConfig } from '../../shared/config/index.js';
import { getPipelineHistory } from '../commands/generation.js';
import { getEventBus } from '../../features/events/EventBus.js';

export interface GenerationProps {
  onBack: () => void;
}

interface Group {
  id: string;
  name: string;
}

interface PipelineRun {
  id: string;
  groupId: string;
  status: string;
  articlesCount: number;
  createdAt: Date;
}

type Mode = 'view' | 'running' | 'history';

export function Generation({ onBack }: GenerationProps) {
  const [groups, setGroups] = useState<Group[]>([]);
  const [history, setHistory] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>('view');
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [progress, setProgress] = useState(0);
  const [currentSegment, setCurrentSegment] = useState(0);
  const [totalSegments, setTotalSegments] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      setLoading(true);
      const config = loadConfig();
      const dbManager = new DatabaseManager(config.database.path);
      dbManager.initialize();
      const db = dbManager.getDb();
      const dbGroups = db.prepare('SELECT * FROM groups WHERE enabled = 1').all() as Array<{
        id: string;
        name: string;
      }>;
      setGroups(dbGroups);
      dbManager.close();
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load groups');
    } finally {
      setLoading(false);
    }
  };

  useInput((input, key) => {
    if (mode === 'running') {
      // Allow 'b' to cancel running pipeline
      if (input === 'b' || input === 'q' || key.escape) {
        setMode('view');
        setStatusMessage('Cancelled');
      }
      return;
    }

    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    } else if (input === 'r' && groups.length > 0) {
      const group = groups[selectedIndex];
      if (group) {
        setSelectedGroup(group);
        runPipelineForGroup(group.id);
      }
    } else if (input === 'h') {
      loadHistory();
    } else if (input === 'j' || key.downArrow) {
      setSelectedIndex(prev => Math.min(prev + 1, groups.length - 1));
    } else if (input === 'k' || key.upArrow) {
      setSelectedIndex(prev => Math.max(prev - 1, 0));
    }
  });

  const runPipelineForGroup = async (groupId: string) => {
    setMode('running');
    setProgress(0);
    setCurrentSegment(0);
    setTotalSegments(0);
    setStatusMessage('Initializing...');
    
    const eventBus = getEventBus();
    let unsubscribeSegment: (() => void) | undefined;
    let unsubscribeStart: (() => void) | undefined;
    let unsubscribeComplete: (() => void) | undefined;
    let dbManager: DatabaseManager | undefined;
    
    try {
      const config = loadConfig();
      dbManager = new DatabaseManager(config.database.path);
      dbManager.initialize();
      const orchestrator = new PipelineOrchestrator(dbManager, {
        maxConcurrentGroups: config.scheduler.maxConcurrentGroups,
      });
      
      unsubscribeSegment = eventBus.subscribe('pipeline:audio:segment-completed', (event) => {
        const payload = event.payload;
        if (payload?.groupId === groupId) {
          const segmentIndex = payload.segmentIndex ?? 0;
          const totalSegments = payload.totalSegments ?? 0;
          setCurrentSegment(segmentIndex);
          setTotalSegments(totalSegments);
          if (totalSegments > 0) {
            const newProgress = Math.round((segmentIndex / totalSegments) * 100);
            setProgress(newProgress);
            setStatusMessage(`Synthesizing segment ${segmentIndex}/${totalSegments}`);
          }
        }
      });
      
      unsubscribeStart = eventBus.subscribe('pipeline:audio:started', () => {
        setStatusMessage('Starting audio synthesis...');
        setProgress(0);
      });
      
      unsubscribeComplete = eventBus.subscribe('pipeline:audio:completed', (event) => {
        const payload = event.payload;
        if (payload?.groupId === groupId) {
          setStatusMessage('Audio synthesis completed!');
          setProgress(100);
          setTimeout(() => {
            setMode('view');
          }, 1500);
        }
      });
      
      await orchestrator.runForGroup(groupId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Pipeline failed';
      const errorStack = err instanceof Error ? err.stack : undefined;
      
      setError(errorMessage);
      setProgress(0);
      setStatusMessage('Failed');
      
      console.error('Pipeline error:', {
        message: errorMessage,
        stack: errorStack,
        timestamp: new Date().toISOString(),
      });
    } finally {
      // Always cleanup and switch back to view mode
      if (unsubscribeSegment) unsubscribeSegment();
      if (unsubscribeStart) unsubscribeStart();
      if (unsubscribeComplete) unsubscribeComplete();
      
      if (dbManager) dbManager.close();
      
      // Fallback: ensure we switch back to view mode even if event didn't fire
      setMode('view');
    }
  };

  const loadHistory = async () => {
    try {
      const runs = await getPipelineHistory(20);
      setHistory(runs);
      setMode('history');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    }
  };

  if (mode === 'history') {
    const columns = [
      { header: 'ID', accessor: (r: PipelineRun) => r.id },
      { header: 'Group', accessor: (r: PipelineRun) => r.groupId },
      { header: 'Status', accessor: (r: PipelineRun) => r.status },
      { header: 'Articles', accessor: (r: PipelineRun) => r.articlesCount.toString() },
      { header: 'Time', accessor: (r: PipelineRun) => r.createdAt.toLocaleString() },
    ];

    return (
      <Box flexDirection="column">
        <Text bold>Pipeline History</Text>
        <Box marginTop={1}>
          <Table data={history} columns={columns} />
        </Box>
        <Box marginTop={1}>
          <Text dimColor>b Back</Text>
        </Box>
      </Box>
    );
  }

  if (mode === 'running' && selectedGroup) {
    return (
      <Box flexDirection="column">
        <Text bold>Running Pipeline</Text>
        <Box marginTop={1}>
          <Text>Group: {selectedGroup.name}</Text>
        </Box>
        <Box marginTop={1}>
          <ProgressBar progress={progress} label="Overall Progress" />
        </Box>
        {totalSegments > 0 && (
          <Box marginTop={1}>
            <Text dimColor>
              Segment: {currentSegment}/{totalSegments}
            </Text>
          </Box>
        )}
        <Box marginTop={1}>
          <Text color={progress === 100 ? 'green' : 'yellow'}>
            {statusMessage}
          </Text>
        </Box>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box flexDirection="column">
        <Text bold>Generation</Text>
        <Box marginTop={1}>
          <Text dimColor>Loading groups...</Text>
        </Box>
      </Box>
    );
  }

  if (error && mode !== 'view') {
    return (
      <Box flexDirection="column">
        <Text bold color="red">Pipeline Failed</Text>
        <Box marginTop={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>
            Time: {new Date().toISOString()}
          </Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Press 'b' or 'q' to go back</Text>
        </Box>
      </Box>
    );
  }

  const columns = [
    { header: 'ID', accessor: (g: Group) => g.id },
    { header: 'Name', accessor: (g: Group) => g.name },
  ];

  return (
    <Box flexDirection="column">
      <Text bold>Generation</Text>
      <Box marginTop={1}>
        <Table
          data={groups}
          columns={columns}
          selectedIndex={selectedIndex}
        />
      </Box>
      <Box marginTop={1}>
        <Text dimColor>r Run  h History  ↑↓ Navigate  b Back</Text>
      </Box>
    </Box>
  );
}
