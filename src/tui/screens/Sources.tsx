import { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Table } from '../components/Table.js';
import { listFeeds } from '../commands/fever.js';

export interface Source {
  id: string;
  title: string;
  url: string;
}

export interface SourcesProps {
  onBack: () => void;
}

const PAGE_SIZE = 15;

export function Sources({ onBack }: SourcesProps) {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      setLoading(true);
      const feeds = await listFeeds();
      const allSources = feeds
        .map(f => ({
          id: f.id.toString(),
          title: f.title,
          url: f.url,
        }))
        .sort((a, b) => parseInt(a.id) - parseInt(b.id));
      setSources(allSources);
      setTotalPages(Math.ceil(allSources.length / PAGE_SIZE));
      setCurrentPage(0);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sources');
    } finally {
      setLoading(false);
    }
  };

  const paginatedSources = sources.slice(
    currentPage * PAGE_SIZE,
    (currentPage + 1) * PAGE_SIZE
  );

  useInput((input, key) => {
    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    } else if (input === 'r') {
      loadSources();
    } else if (input === 'n' || input === 'j' || key.downArrow) {
      setCurrentPage(prev => Math.min(prev + 1, totalPages - 1));
    } else if (input === 'p' || input === 'k' || key.upArrow) {
      setCurrentPage(prev => Math.max(prev - 1, 0));
    }
  });

  if (loading) {
    return (
      <Box flexDirection="column">
        <Text bold>Source Management</Text>
        <Box marginTop={1}>
          <Text dimColor>Loading sources...</Text>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box flexDirection="column">
        <Text bold color="red">Source Management</Text>
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
    { header: 'ID', accessor: (s: Source) => s.id, width: 8 },
    { header: 'Title', accessor: (s: Source) => (s.title || 'Unknown').slice(0, 40), width: 42 },
    { header: 'URL', accessor: (s: Source) => (s.url || '').slice(0, 40), width: 42 },
  ];

  return (
    <Box flexDirection="column">
      <Text bold>Source Management (Read-Only)</Text>
      <Box marginTop={1}>
        <Text>Page {currentPage + 1} of {totalPages} ({sources.length} total sources)</Text>
        <Box marginTop={1}>
          <Table data={paginatedSources} columns={columns} />
        </Box>
      </Box>
      <Box marginTop={1}>
        <Text dimColor>r Refresh  ↓/n Next  ↑/p Prev  b Back</Text>
      </Box>
    </Box>
  );
}
