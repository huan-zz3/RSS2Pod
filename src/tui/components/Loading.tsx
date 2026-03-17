import { useState, useEffect } from 'react';
import { Text } from 'ink';

export interface LoadingProps {
  message?: string;
}

const frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

export function Loading({ message = 'Loading...' }: LoadingProps) {
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setFrameIndex(prev => (prev + 1) % frames.length);
    }, 80);

    return () => clearInterval(interval);
  }, []);

  return (
    <Text>
      {frames[frameIndex]} {message}
    </Text>
  );
}
