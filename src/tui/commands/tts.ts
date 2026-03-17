import { SiliconFlowService } from '../../services/tts/SiliconFlowService.js';
import { loadConfig } from '../../shared/config/index.js';

export async function testTTSConnection(): Promise<boolean> {
  const config = loadConfig();
  const service = new SiliconFlowService(config.tts);
  return await service.testConnection();
}
