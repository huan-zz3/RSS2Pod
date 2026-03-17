import { useState } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Input } from '../components/Input.js';
import { testLLMConnection, chatWithLLM } from '../commands/llm.js';

export interface LLMDebugProps {
  onBack: () => void;
}

type Mode = 'idle' | 'testing' | 'chatting' | 'input' | 'waiting' | 'success' | 'error';

export function LLMDebug({ onBack }: LLMDebugProps) {
  const [status, setStatus] = useState<Mode>('idle');
  const [result, setResult] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState<string | null>(null);
  const [timing, setTiming] = useState<number | null>(null);

  useInput((input, key) => {
    if (status === 'testing' || status === 'waiting') {
      return;
    }

    if (status === 'input') {
      return;
    }

    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    } else if (input === 't') {
      testConnection();
    } else if (input === 'c') {
      setStatus('input');
      setPrompt('');
    }
  });

  const testConnection = async () => {
    setStatus('testing');
    try {
      const success = await testLLMConnection();
      setResult(success ? 'Connection successful!' : 'Connection failed');
      setStatus(success ? 'success' : 'error');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Connection failed');
      setStatus('error');
    }
  };

  const handlePromptSubmit = async () => {
    if (!prompt.trim()) {
      return;
    }
    setStatus('waiting');
    try {
      const startTime = Date.now();
      const responseText = await chatWithLLM(prompt.trim());
      const elapsed = Date.now() - startTime;
      setResponse(responseText);
      setTiming(elapsed);
      setStatus('success');
      setPrompt('');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Chat failed');
      setStatus('error');
    }
  };

  const handlePromptCancel = () => {
    setPrompt('');
    setStatus('idle');
  };

  if (status === 'input') {
    return (
      <Box flexDirection="column">
        <Text bold>Chat with LLM</Text>
        <Box marginTop={1}>
          <Input
            label="Prompt: "
            value={prompt}
            onChange={setPrompt}
            onSubmit={handlePromptSubmit}
            onCancel={handlePromptCancel}
          />
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Enter to send, Esc to cancel</Text>
        </Box>
      </Box>
    );
  }

  return (
    <Box flexDirection="column">
      <Text bold>LLM Debug</Text>
      <Box flexDirection="column" marginTop={1}>
        <Text>Status: {status === 'idle' ? 'Ready' : status}</Text>
        {result && (
          <Box marginTop={1}>
            <Text color={status === 'error' ? 'red' : 'green'}>
              {result}
            </Text>
          </Box>
        )}
        {response && (
          <Box flexDirection="column" marginTop={1}>
            <Text bold>Response:</Text>
            <Text dimColor>{response}</Text>
            {timing !== null && (
              <Text dimColor>Response time: {timing}ms</Text>
            )}
          </Box>
        )}
      </Box>
      <Box marginTop={1}>
        <Text dimColor>t Test  c Chat  b Back</Text>
      </Box>
    </Box>
  );
}
