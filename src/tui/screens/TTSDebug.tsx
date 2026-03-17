import { useState } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Input } from '../components/Input.js';
import { testTTSConnection } from '../commands/tts.js';
import { SiliconFlowService } from '../../services/tts/SiliconFlowService.js';
import { loadConfig } from '../../shared/config/index.js';
import { join } from 'path';

export interface TTSDebugProps {
  onBack: () => void;
}

type Mode = 'idle' | 'testing' | 'synthesizing' | 'input' | 'success' | 'error';

export function TTSDebug({ onBack }: TTSDebugProps) {
  const [status, setStatus] = useState<Mode>('idle');
  const [result, setResult] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [audioFile, setAudioFile] = useState<string | null>(null);
  const [timing, setTiming] = useState<number | null>(null);

  useInput((input, key) => {
    if (status === 'testing' || status === 'synthesizing') {
      return;
    }

    if (status === 'input') {
      return;
    }

    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    } else if (input === 't') {
      testConnection();
    } else if (input === 's') {
      setStatus('input');
      setText('');
    }
  });

  const testConnection = async () => {
    setStatus('testing');
    try {
      const success = await testTTSConnection();
      setResult(success ? 'Connection successful!' : 'Connection failed');
      setStatus(success ? 'success' : 'error');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Connection failed');
      setStatus('error');
    }
  };

  const handleTextSubmit = async () => {
    if (!text.trim()) {
      return;
    }
    if (text.length > 500) {
      setResult('Text too long (max 500 characters)');
      setStatus('error');
      return;
    }
    setStatus('synthesizing');
    try {
      const config = loadConfig();
      const service = new SiliconFlowService(config.tts);
      const startTime = Date.now();
      
      const mediaDir = join(process.cwd(), 'data', 'media', 'tts-test');
      const audioPath = join(mediaDir, `test_${Date.now()}.mp3`);
      
      await service.synthesize(text.trim(), audioPath);
      const elapsed = Date.now() - startTime;
      
      setAudioFile(audioPath);
      setTiming(elapsed);
      setStatus('success');
      setText('');
    } catch (err) {
      setResult(err instanceof Error ? err.message : 'Synthesis failed');
      setStatus('error');
    }
  };

  const handleTextCancel = () => {
    setText('');
    setStatus('idle');
  };

  if (status === 'input') {
    return (
      <Box flexDirection="column">
        <Text bold>TTS Synthesis</Text>
        <Box marginTop={1}>
          <Input
            label="Text (max 500): "
            value={text}
            onChange={setText}
            onSubmit={handleTextSubmit}
            onCancel={handleTextCancel}
          />
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Enter to synthesize, Esc to cancel</Text>
        </Box>
      </Box>
    );
  }

  return (
    <Box flexDirection="column">
      <Text bold>TTS Debug</Text>
      <Box flexDirection="column" marginTop={1}>
        <Text>Status: {status === 'idle' ? 'Ready' : status}</Text>
        {result && (
          <Box marginTop={1}>
            <Text color={status === 'error' ? 'red' : 'green'}>
              {result}
            </Text>
          </Box>
        )}
        {audioFile && (
          <Box flexDirection="column" marginTop={1}>
            <Text bold>Audio generated:</Text>
            <Text dimColor>{audioFile}</Text>
            {timing !== null && (
              <Text dimColor>Synthesis time: {timing}ms</Text>
            )}
            <Box marginTop={1}>
              <Text color="yellow">To play: run `afplay {audioFile}` (macOS) or `aplay {audioFile}` (Linux)</Text>
            </Box>
          </Box>
        )}
      </Box>
      <Box marginTop={1}>
        <Text dimColor>t Test  s Synthesize  b Back</Text>
      </Box>
    </Box>
  );
}
