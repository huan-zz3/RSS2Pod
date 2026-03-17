import { DashScopeService } from '../../services/llm/DashScopeService.js';
import { loadConfig } from '../../shared/config/index.js';

export async function testLLMConnection(): Promise<boolean> {
  const config = loadConfig();
  const service = new DashScopeService(config.llm);
  return await service.testConnection();
}

export async function chatWithLLM(prompt: string): Promise<string> {
  const config = loadConfig();
  const service = new DashScopeService(config.llm);
  const response = await service.generateScript(prompt);
  return response.content;
}
