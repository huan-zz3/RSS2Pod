import { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { useInput } from 'ink';
import { Input } from '../components/Input.js';
import { loadConfig } from '../../shared/config/index.js';
import { writeFileSync } from 'fs';
import { resolve } from 'path';

export interface ConfigurationProps {
  onBack: () => void;
}

type EditMode = 'none' | 'editing';

export function Configuration({ onBack }: ConfigurationProps) {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<EditMode>('none');
  const [selectedKey, setSelectedKey] = useState(0);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    loadConfigData();
  }, []);

  const loadConfigData = () => {
    try {
      const cfg = loadConfig();
      setConfig(cfg);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config');
    } finally {
      setLoading(false);
    }
  };

  useInput((input, key) => {
    if (mode === 'editing') {
      // Allow 'b' to cancel editing
      if (input === 'b' || key.escape) {
        handleCancel();
      }
      return;
    }

    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    } else if (input === 'e') {
      const section = getSections()[0];
      if (section && section.keys[selectedKey]) {
        const currentValue = getNestedValue(config, section.keys[selectedKey]);
        setEditValue(String(currentValue || ''));
        setMode('editing');
      }
    } else if (input === 'j' || key.downArrow) {
      const sections = getSections();
      const totalKeys = sections.reduce((sum, s) => sum + s.keys.length, 0);
      setSelectedKey(prev => {
        const next = prev + 1;
        if (next >= totalKeys) return 0;
        return next;
      });
    } else if (input === 'k' || key.upArrow) {
      const sections = getSections();
      const totalKeys = sections.reduce((sum, s) => sum + s.keys.length, 0);
      setSelectedKey(prev => {
        const next = prev - 1;
        if (next < 0) return totalKeys - 1;
        return next;
      });
    }
  });

  const getSections = () => [
    { name: 'Fever API', keys: ['fever.baseUrl', 'fever.username', 'fever.password'] },
    { name: 'LLM', keys: ['llm.provider', 'llm.model', 'llm.apiKey', 'llm.baseUrl'] },
    { name: 'TTS', keys: ['tts.provider', 'tts.model', 'tts.apiKey', 'tts.voice'] },
    { name: 'Database', keys: ['database.path'] },
    { name: 'Scheduler', keys: ['scheduler.maxConcurrentGroups'] },
  ];

  const getNestedValue = (obj: any, path: string): any => {
    return path.split('.').reduce((acc, key) => acc?.[key], obj);
  };

  const setNestedValue = (obj: any, path: string, value: any): any => {
    const keys = path.split('.');
    const lastKey = keys.pop()!;
    const target = keys.reduce((acc, key) => acc[key], obj);
    if (target) {
      target[lastKey] = value;
    }
    return obj;
  };

  const handleSave = () => {
    if (!config) return;
    try {
      const sections = getSections();
      let keyIndex = 0;
      for (const section of sections) {
        for (const key of section.keys) {
          if (keyIndex === selectedKey) {
            const newConfig = { ...config };
            setNestedValue(newConfig, key, editValue);
            const configPath = resolve(process.cwd(), 'config.json');
            writeFileSync(configPath, JSON.stringify(newConfig, null, 2));
            setConfig(newConfig);
            setMode('none');
            setEditValue('');
            return;
          }
          keyIndex++;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save config');
      setMode('none');
    }
  };

  const handleCancel = () => {
    setMode('none');
    setEditValue('');
  };

  if (loading) {
    return (
      <Box flexDirection="column">
        <Text bold>Configuration</Text>
        <Box marginTop={1}>
          <Text dimColor>Loading configuration...</Text>
        </Box>
      </Box>
    );
  }

  if (error) {
    return (
      <Box flexDirection="column">
        <Text bold color="red">Configuration</Text>
        <Box marginTop={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Press 'r' to retry, 'b' or 'q' to go back</Text>
        </Box>
      </Box>
    );
  }

  if (mode === 'editing') {
    return (
      <Box flexDirection="column">
        <Text bold>Edit Configuration</Text>
        <Box marginTop={1}>
          <Input
            label="New Value: "
            value={editValue}
            onChange={setEditValue}
            onSubmit={handleSave}
            onCancel={handleCancel}
          />
        </Box>
        <Box marginTop={1}>
          <Text dimColor>Enter to save, Esc to cancel</Text>
        </Box>
      </Box>
    );
  }

  const sections = getSections();
  let keyIndex = 0;

  return (
    <Box flexDirection="column">
      <Text bold>Configuration</Text>
      <Box flexDirection="column" marginTop={1}>
        {sections.map((section, sIdx) => (
          <Box key={section.name} flexDirection="column" marginTop={sIdx > 0 ? 1 : 0}>
            <Text color="cyan" bold>{section.name}</Text>
            {section.keys.map(keyPath => {
              const value = getNestedValue(config, keyPath);
              const isMasked = keyPath.includes('Key') || keyPath.includes('word');
              const displayValue = isMasked && value ? '********' : String(value || 'N/A');
              const isSelected = keyIndex === selectedKey;
              const keyName = keyPath.split('.').pop() || keyPath;
              
              const line = `${keyName}: ${displayValue}`;
              keyIndex++;
              
              return (
                <Text key={keyPath} color={isSelected ? 'green' : 'white'}>
                  {isSelected ? '▶ ' : '  '}{line}
                </Text>
              );
            })}
          </Box>
        ))}
      </Box>
      <Box marginTop={1}>
        <Text dimColor>e Edit  ↑↓ Navigate  b Back</Text>
      </Box>
    </Box>
  );
}
