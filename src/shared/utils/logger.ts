/**
 * 日志格式化工具函数
 */

/**
 * 格式化长文本以便日志输出
 * @param text 要格式化的文本
 * @param options 格式化选项
 * @returns 格式化后的文本
 */
export function formatLogText(text: string, options: {
  maxLength?: number;
  preserveNewlines?: boolean;
} = {}): string {
  const { maxLength = 200, preserveNewlines = false } = options;
  
  if (text.length <= maxLength) {
    return preserveNewlines ? text : text.replace(/\n/g, ' ');
  }
  
  const truncated = text.substring(0, maxLength);
  
  const boundaries = ['\n\n', '\n', '. ', '! ', '? ', ' '];
  for (const boundary of boundaries) {
    const lastIdx = truncated.lastIndexOf(boundary);
    if (lastIdx > maxLength * 0.5) {
      const result = truncated.substring(0, lastIdx + boundary.length);
      return preserveNewlines ? result + '...' : result.replace(/\n/g, ' ') + '...';
    }
  }
  
  return (preserveNewlines ? truncated : truncated.replace(/\n/g, ' ')) + '...';
}

/**
 * 将 Unix 时间戳转换为 ISO 格式
 * @param unixTimestamp Unix 时间戳（秒或毫秒）
 * @returns ISO 8601 格式的时间戳字符串
 */
export function unixToISO(unixTimestamp: number | string): string {
  const num = typeof unixTimestamp === 'string' ? parseInt(unixTimestamp, 10) : unixTimestamp;
  const ms = num > 1e12 ? num : num * 1000;
  return new Date(ms).toISOString();
}

/**
 * 创建带 ISO 时间戳的日志对象
 * @param data 日志数据对象
 * @returns 添加时间戳的日志对象
 */
export function createLogEntry<T extends Record<string, unknown>>(data: T): T & { timestamp: string } {
  return {
    ...data,
    timestamp: new Date().toISOString(),
  };
}

/**
 * pino logger 的 UTC+8 时间戳函数
 * @returns pino 格式的时间戳字符串
 */
export function utc8Timestamp(): string {
  return `,"time":"${new Date(new Date().getTime() + 8 * 3600 * 1000).toISOString().replace('Z', '+08:00')}"`;
}
