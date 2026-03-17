import { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Loading } from '../components/Loading.js';
import { getSystemStats, type SystemStats as SystemStatsData } from '../commands/system.js';

export interface SystemStatusProps {
  onBack: () => void;
}

export function SystemStatus({ onBack }: SystemStatusProps) {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<SystemStatsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useInput((input, key) => {
    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    }
    if (input === 'r') {
      setLoading(true);
      setError(null);
      loadStats();
    }
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await getSystemStats();
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading message="Loading system status..." />;
  }

  if (error) {
    return (
      <Box flexDirection="column">
        <Text bold color="red">System Status</Text>
        <Box marginTop={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Press 'r' to retry, 'b' or 'q' to go back</Text>
        </Box>
      </Box>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <Box flexDirection="column">
      <Text bold>System Status</Text>
      <Box flexDirection="column" marginTop={1}>
        <Text>Version: {stats.version}</Text>
        <Text>Database: {stats.database}</Text>
        <Text>Fever API: {stats.fever}</Text>
        <Text>LLM: {stats.llm}</Text>
        <Text>TTS: {stats.tts}</Text>
        <Box flexDirection="column" marginTop={1}>
          <Text>Groups: {stats.groups}</Text>
          <Text>Articles: {stats.articles}</Text>
          <Text>Episodes: {stats.episodes}</Text>
        </Box>
      </Box>
      <Box marginTop={1}>
        <Text dimColor>Press 'r' to refresh, 'b' or 'q' to go back</Text>
      </Box>
    </Box>
  );
}
