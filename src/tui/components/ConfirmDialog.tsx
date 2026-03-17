import { Text } from 'ink';

export interface ConfirmDialogProps {
  title: string;
  message: string;
  selected: 'cancel' | 'confirm';
}

export function ConfirmDialog({ title, message, selected }: ConfirmDialogProps) {
  return (
    <>
      <Text bold>{title}</Text>
      <Text>{message}</Text>
      <Text> </Text>
      <Text>
        {selected === 'cancel' ? '▶ ' : '  '}
        <Text color={selected === 'cancel' ? 'green' : 'white'}>Cancel</Text>
        {'  '}
        {selected === 'confirm' ? '▶ ' : '  '}
        <Text color={selected === 'confirm' ? 'red' : 'white'}>Confirm</Text>
      </Text>
    </>
  );
}
