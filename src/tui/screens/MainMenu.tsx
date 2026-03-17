import { Box, Text } from 'ink';
import { Select } from '../components/Select.js';

const menuItems = [
  '1. System Status',
  '2. Configuration',
  '3. Group Management',
  '4. Source Management',
  '5. Fever API',
  '6. LLM Debug',
  '7. TTS Debug',
  '8. Generation',
];

export interface MainMenuProps {
  onExit: () => void;
}

export interface MainMenuProps {
  onExit: () => void;
  onSelect?: (index: number) => void;
}

export function MainMenu({ onExit, onSelect }: MainMenuProps) {
  const handleSelect = (index: number) => {
    onSelect?.(index);
  };

  return (
    <Box flexDirection="column">
      <Select options={menuItems} onSelect={handleSelect} onExit={onExit} />
      <Box marginTop={1}>
        <Text dimColor>↑↓ Navigate  Enter Select  1-8 Quick Select  b/q Quit</Text>
      </Box>
    </Box>
  );
}
