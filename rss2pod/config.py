#!/usr/bin/env python3
"""
配置文件 - RSS2Pod 配置管理
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class FeverConfig:
    """Fever API 配置"""
    url: str = ""
    username: str = ""
    api_key: str = ""


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "dashscope"
    api_key: str = ""
    model: str = "qwen-plus"
    base_url: str = "https://dashscope.aliyuncs.com/v1"


@dataclass
class TTSConfig:
    """TTS 配置"""
    provider: str = "edge"  # edge/azure/elevenlabs/aliyun
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: float = 1.0
    api_key: str = ""
    region: str = ""


@dataclass
class FeedConfig:
    """Feed 发布配置"""
    base_url: str = ""
    media_dir: str = "./media"
    feed_dir: str = "./feeds"


@dataclass
class AppConfig:
    """应用配置"""
    debug: bool = False
    db_path: str = "./rss2pod.db"
    data_dir: str = "./data"
    log_level: str = "INFO"
    fever: FeverConfig = field(default_factory=FeverConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    feed: FeedConfig = field(default_factory=FeedConfig)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        data['fever'] = FeverConfig(**data.get('fever', {}))
        data['llm'] = LLMConfig(**data.get('llm', {}))
        data['tts'] = TTSConfig(**data.get('tts', {}))
        data['feed'] = FeedConfig(**data.get('feed', {}))
        return cls(**data)


class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG_FILE = "config.json"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_FILE
        self.config: AppConfig = self._load_or_create()

    def _load_or_create(self) -> AppConfig:
        if os.path.exists(self.config_path):
            return self.load()
        else:
            config = AppConfig()
            self._load_env(config)
            return config

    def _load_env(self, config: AppConfig):
        """从环境变量加载配置"""
        if os.getenv('FEVER_URL'):
            config.fever.url = os.getenv('FEVER_URL')
        if os.getenv('FEVER_API_KEY'):
            config.fever.api_key = os.getenv('FEVER_API_KEY')
        if os.getenv('DASHSCOPE_API_KEY'):
            config.llm.api_key = os.getenv('DASHSCOPE_API_KEY')
        if os.getenv('TTS_PROVIDER'):
            config.tts.provider = os.getenv('TTS_PROVIDER')

    def load(self) -> AppConfig:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return AppConfig.from_dict(data)

    def save(self, config: Optional[AppConfig] = None):
        if config:
            self.config = config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config.to_dict(), f, indent=2, ensure_ascii=False)

    def get(self) -> AppConfig:
        return self.config

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save()


def get_config(config_path: Optional[str] = None) -> AppConfig:
    manager = ConfigManager(config_path)
    return manager.get()


if __name__ == '__main__':
    config = get_config()
    print(f"Config loaded: {config.to_dict()}")
