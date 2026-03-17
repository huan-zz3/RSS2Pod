import { useState, useEffect } from 'react';
import { Text, useInput } from 'ink';

export interface InputProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  onCancel?: () => void;
}

export function Input({ label, value, onChange, onSubmit, onCancel }: InputProps) {
  const [cursorVisible, setCursorVisible] = useState(true);

  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setCursorVisible(prev => !prev);
    }, 500);

    return () => {
      clearInterval(blinkInterval);
    };
  }, []);

  useInput((input, key) => {
    if (key.return) {
      onSubmit?.();
    } else if (key.escape || input === 'b' || input === 'B') {
      onCancel?.();
    } else if (key.backspace || key.delete) {
      onChange(value.slice(0, -1));
    } else if (input && input.length === 1 && input >= ' ') {
      onChange(value + input);
    }
  });

  const displayValue = value || ' ';
  const cursor = cursorVisible ? '█' : ' ';

  return (
    <Text>
      {label}: [{displayValue}{cursor}]
    </Text>
  );
}
