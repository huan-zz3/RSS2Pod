import { Text } from 'ink';

export interface ProgressBarProps {
  progress: number;
  label?: string;
}

export function ProgressBar({ progress, label }: ProgressBarProps) {
  const percentage = Math.min(100, Math.max(0, progress));
  const filled = Math.round(percentage / 5);
  const empty = 20 - filled;

  const bar = '█'.repeat(filled) + '░'.repeat(empty);

  return (
    <Text>
      {label && `${label} `}[{bar}] {percentage.toFixed(0)}%
    </Text>
  );
}
