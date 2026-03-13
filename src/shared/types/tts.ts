export interface TTSConfig {
  provider: 'siliconflow';
  apiKey: string;
  model: string;
  voice: string;
  baseUrl: string;
  speed?: number;
}

export interface TTSResponse {
  audioPath: string;
  duration: number;
  segments?: TTSResponse[];
}

export interface TTSService {
  synthesize(text: string, outputPath: string, options?: TTSOptions): Promise<TTSResponse>;
  testConnection(): Promise<boolean>;
}

export interface TTSOptions {
  voice?: string;
  speed?: number;
  segment?: boolean;
}
