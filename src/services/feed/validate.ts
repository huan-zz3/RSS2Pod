// Basic XML validation utilities for feed XML

export function validateXml(xml: string): boolean {
  if (!xml || typeof xml !== 'string') return false;
  // Minimal checks for well-formed RSS feed wrapper
  const hasRss = /<rss[^>]*>/i.test(xml);
  const hasChannel = /<channel[^>]*>/.test(xml);
  const hasTitle = /<title>[^<]+<\/title>/.test(xml);
  // Ensure at least one item exists
  const hasItem = /<item>/.test(xml);
  return !!(hasRss && hasChannel && hasTitle && hasItem);
}
