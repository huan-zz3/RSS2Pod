import { useState } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { testFeverConnection, listFeeds, syncFeeds, syncArticles, cacheArticles } from '../commands/fever.js';

export interface FeverAPIProps {
  onBack: () => void;
}

export function FeverAPI({ onBack }: FeverAPIProps) {
  const [status, setStatus] = useState<'idle' | 'testing' | 'listing' | 'syncing' | 'caching' | 'syncing-articles' | 'success' | 'error'>('idle');
  const [result, setResult] = useState<string | null>(null);
  const [feeds, setFeeds] = useState<Array<{ id: number; title: string; url: string }>>([]);

  useInput((input, key) => {
    if (status === 'testing' || status === 'listing' || status === 'syncing' || status === 'caching' || status === 'syncing-articles') {
      return;
    }

    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    } else if (input === 't') {
      testConnection();
    } else if (input === 'l') {
      listAllFeeds();
    } else if (input === 's') {
      syncAllFeeds();
    } else if (input === 'a') {
      syncAllArticles();
    } else if (input === 'c') {
      cacheAllArticles();
    }
  });

  const testConnection = async () => {
    setStatus('testing');
    try {
      const success = await testFeverConnection();
      setResult(success ? 'Connection successful!' : 'Connection failed');
      setStatus(success ? 'success' : 'error');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Connection failed');
      setStatus('error');
    }
  };

  const listAllFeeds = async () => {
    setStatus('listing');
    try {
      const feedList = await listFeeds();
      setFeeds(feedList);
      setResult(`Found ${feedList.length} feeds`);
      setStatus('success');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Failed to list feeds');
      setStatus('error');
    }
  };

  const syncAllFeeds = async () => {
    setStatus('syncing');
    try {
      const count = await syncFeeds();
      setResult(`Synced ${count} feeds`);
      setStatus('success');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Sync failed');
      setStatus('error');
    }
  };

  const syncAllArticles = async () => {
    setStatus('syncing-articles');
    try {
      const result = await syncArticles();
      if (result.synced) {
        setResult(`✅ Synced ${result.articlesSynced} articles in ${result.duration}ms`);
        setStatus('success');
      } else {
        setResult('❌ Sync failed');
        setStatus('error');
      }
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Sync failed');
      setStatus('error');
    }
  };

  const cacheAllArticles = async () => {
    setStatus('caching');
    try {
      const count = await cacheArticles(100);
      setResult(`Cached ${count} articles`);
      setStatus('success');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Cache failed');
      setStatus('error');
    }
  };

  return (
    <Box flexDirection="column">
      <Text bold>Fever API</Text>
      <Box flexDirection="column" marginTop={1}>
        <Text>Status: {status === 'idle' ? 'Ready' : status}</Text>
        {result && (
          <Box marginTop={1}>
            <Text color={status === 'error' ? 'red' : 'green'}>
              {result}
            </Text>
          </Box>
        )}
        {feeds.length > 0 && (
          <Box flexDirection="column" marginTop={1}>
            {feeds.map(feed => (
              <Text key={feed.id} dimColor>
                • {feed.title} ({feed.url})
              </Text>
            ))}
          </Box>
        )}
      </Box>
      <Box marginTop={1}>
        <Text dimColor>t Test  l List  s Sync  a Articles  c Cache  b Back</Text>
      </Box>
    </Box>
  );
}
