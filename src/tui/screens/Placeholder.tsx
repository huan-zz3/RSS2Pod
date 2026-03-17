 
import { useInput } from 'ink';
import { Box, Text } from 'ink';

export interface PlaceholderProps {
  title: string;
  onBack: () => void;
}

export function Placeholder({ title, onBack }: PlaceholderProps) {
  useInput((input, key) => {
    if (key.escape || input === 'q' || input === 'b') {
      onBack();
    }
  });

  return (
    <Box flexDirection="column">
      <Text bold>{title}</Text>
      <Box marginTop={1}>
        <Text dimColor>Coming soon...</Text>
      </Box>
      <Box marginTop={1}>
        <Text dimColor>Press 'b' or 'q' to go back</Text>
      </Box>
    </Box>
  );
}
