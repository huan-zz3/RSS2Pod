import { Box, Text } from 'ink';

export interface TableColumn<T> {
  header: string;
  accessor: (item: T) => string;
  width?: number;
}

export interface TableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
  selectedIndex?: number;
}

export function Table<T>({ data, columns, selectedIndex = 0 }: TableProps<T>) {
  return (
    <Box flexDirection="column">
      <Box>
        {columns.map((col, idx) => (
          <Box key={idx} width={col.width} paddingRight={2}>
            <Text bold>{col.header}</Text>
          </Box>
        ))}
      </Box>
      <Box>
        <Text>{'─'.repeat(columns.reduce((sum, col) => sum + (col.width ?? 15) + 2, 0))}</Text>
      </Box>
      {data.map((item, index) => (
        <Box key={index}>
          {columns.map((col, idx) => (
            <Box key={idx} width={col.width} paddingRight={2}>
              <Text color={index === selectedIndex ? 'green' : 'white'}>
                {(col.accessor(item) || '').slice(0, (col.width ?? 15) - 1)}
              </Text>
            </Box>
          ))}
        </Box>
      ))}
    </Box>
  );
}
