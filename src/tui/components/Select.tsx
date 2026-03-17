import { useState } from 'react';
import { Text, useInput } from 'ink';

export interface SelectProps {
  options: string[];
  onSelect?: (index: number) => void;
  onExit?: () => void;
}

export function Select({ options, onSelect, onExit }: SelectProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  useInput((input, key) => {
    if (key.downArrow || input === 'j') {
      setSelectedIndex(prev => (prev + 1) % options.length);
    } else if (key.upArrow || input === 'k') {
      setSelectedIndex(prev => (prev - 1 + options.length) % options.length);
    } else if (key.return) {
      onSelect?.(selectedIndex);
    } else if (input === 'q' || input === 'b' || key.escape) {
      onExit?.();
    }

    const num = parseInt(input, 10);
    if (!isNaN(num) && num >= 1 && num <= options.length) {
      setSelectedIndex(num - 1);
      onSelect?.(num - 1);
    }
  });

  return (
    <>
      {options.map((option, index) => (
        <Text key={`${index}-${option}`} color={index === selectedIndex ? 'green' : 'white'}>
          {index === selectedIndex ? '▶ ' : '  '}{option}
        </Text>
      ))}
    </>
  );
}
