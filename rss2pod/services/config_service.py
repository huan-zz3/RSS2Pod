"""
配置服务 - 封装配置管理相关操作
"""

import os
import sys
import json
import subprocess
from typing import Optional, Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class ConfigService(BaseService):
    """
    配置服务
    
    提供配置管理相关的业务逻辑封装
    """
    
    # 默认配置值
    DEFAULT_VALUES = {
        "llm.model": "qwen3.5-plus",
        "llm.base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "tts.provider": "siliconflow",
        "tts.voice": "FunAudioLLM/CosyVoice2-0.5B:claire",
        "tts.model": "fnlp/MOSS-TTSD-v0.5",
        "db_path": "rss2pod.db",
        "orchestrator.check_interval_seconds": 60,
        "orchestrator.sync_articles_interval_minutes": 30,
        "orchestrator.sync_feeds_interval_minutes": 60,
        "orchestrator.check_groups_interval_minutes": 1,
        "orchestrator.max_concurrent_groups": 3,
        "orchestrator.retry_attempts": 3,
        "orchestrator.retry_delay_seconds": 3,
        "logging.level": "INFO",
        "logging.file": "logs/orchestrator.log",
        "logging.rotation": "daily",
        "logging.retention_days": 7
    }
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path, None)
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        return self._load_config()
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        保存配置文件
        
        Args:
            config: 配置字典
            
        Returns:
            是否成功
        """
        try:
            config_path = self.config_path or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config.json'
            )
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """
        获取嵌套配置值
        
        Args:
            config: 配置字典
            path: 配置路径（点号分隔，如 llm.api_key）
            
        Returns:
            配置值，不存在返回 None
        """
        keys = path.split('.')
        current = config
        for key in keys:
            if key not in current:
                return None
            current = current[key]
        return current
    
    def set_nested_value(self, config: Dict[str, Any], path: str, value: Any) -> bool:
        """
        设置嵌套配置值
        
        Args:
            config: 配置字典
            path: 配置路径（点号分隔）
            value: 配置值
            
        Returns:
            是否成功
        """
        keys = path.split('.')
        current = config
        for key in keys[:-1]:
            if key not in current:
                return False
            current = current[key]
        if keys[-1] not in current:
            return False
        current[keys[-1]] = value
        return True
    
    def get_safe_config(self) -> Dict[str, Any]:
        """
        获取脱敏后的配置（隐藏敏感信息）
        
        Returns:
            脱敏后的配置字典
        """
        config = self.load_config()
        safe_config = json.loads(json.dumps(config))
        
        if 'fever' in safe_config:
            safe_config['fever']['password'] = '***'
        if 'llm' in safe_config:
            safe_config['llm']['api_key'] = safe_config['llm']['api_key'][:10] + '...'
        if 'tts' in safe_config:
            # 支持新的 providers 结构
            tts_config = safe_config.get('tts', {})
            providers = tts_config.get('providers', {})
            for provider_name, provider_data in providers.items():
                if 'api_key' in provider_data:
                    provider_data['api_key'] = provider_data['api_key'][:10] + '...'
        
        return safe_config
    
    def edit_config_with_editor(self) -> ServiceResult:
        """
        使用系统编辑器编辑配置文件
        
        Returns:
            ServiceResult 实例
        """
        try:
            config_path = self.config_path or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'config.json'
            )
            
            editors = ['nano', 'vim', 'vi', 'code']
            editor = os.environ.get('EDITOR', None)
            
            if editor:
                editors.insert(0, editor)
            
            for ed in editors:
                try:
                    subprocess.run([ed, config_path], check=True)
                    
                    # 验证 JSON 格式
                    try:
                        self.load_config()
                        return ServiceResult(
                            success=True,
                            data={'message': '配置已保存', 'valid': True}
                        )
                    except json.JSONDecodeError as e:
                        return ServiceResult(
                            success=False,
                            error_message=f'配置格式错误：{e}'
                        )
                except FileNotFoundError:
                    continue
            
            return ServiceResult(
                success=False,
                error_message='未找到可用的编辑器，请设置 EDITOR 环境变量'
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def set_config_value(self, key: str, value: str) -> ServiceResult:
        """
        设置配置项
        
        Args:
            key: 配置键（点号路径）
            value: 配置值
            
        Returns:
            ServiceResult 实例
        """
        try:
            config = self.load_config()
            
            if not self.set_nested_value(config, key, value):
                return ServiceResult(
                    success=False,
                    error_message=f'无效的配置键：{key}'
                )
            
            if self.save_config(config):
                return ServiceResult(
                    success=True,
                    data={'key': key, 'value': value}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='保存配置失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def reset_config_value(self, key: str) -> ServiceResult:
        """
        重置配置项到默认值
        
        Args:
            key: 配置键（点号路径）
            
        Returns:
            ServiceResult 实例
        """
        try:
            if key not in self.DEFAULT_VALUES:
                return ServiceResult(
                    success=False,
                    error_message=f'未知配置键：{key}'
                )
            
            config = self.load_config()
            
            if not self.set_nested_value(config, key, self.DEFAULT_VALUES[key]):
                return ServiceResult(
                    success=False,
                    error_message=f'无效的配置键：{key}'
                )
            
            if self.save_config(config):
                return ServiceResult(
                    success=True,
                    data={'key': key, 'value': self.DEFAULT_VALUES[key]}
                )
            else:
                return ServiceResult(
                    success=False,
                    error_message='保存配置失败'
                )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def get_default_keys(self) -> List[str]:
        """
        获取可重置的配置键列表
        
        Returns:
            配置键列表
        """
        return list(self.DEFAULT_VALUES.keys())


def load_config() -> Dict[str, Any]:
    """
    便捷函数：加载配置文件
    
    Returns:
        配置字典
    """
    service = ConfigService()
    return service.load_config()


def save_config(config: Dict[str, Any]) -> bool:
    """
    便捷函数：保存配置文件
    
    Args:
        config: 配置字典
        
    Returns:
        是否成功
    """
    service = ConfigService()
    return service.save_config(config)


def get_nested_value(config: Dict[str, Any], path: str) -> Any:
    """
    便捷函数：获取嵌套配置值
    
    Args:
        config: 配置字典
        path: 配置路径
        
    Returns:
        配置值
    """
    service = ConfigService()
    return service.get_nested_value(config, path)


def set_nested_value(config: Dict[str, Any], path: str, value: Any) -> bool:
    """
    便捷函数：设置嵌套配置值
    
    Args:
        config: 配置字典
        path: 配置路径
        value: 配置值
        
    Returns:
        是否成功
    """
    service = ConfigService()
    return service.set_nested_value(config, path, value)
