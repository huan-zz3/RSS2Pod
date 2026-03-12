"""
LLM 客户端抽象

支持多种 LLM 提供商：DashScope (通义千问), Mock 等
"""

import os
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# 使用统一的日志配置
def _get_logger():
    """延迟获取 logger，避免循环依赖"""
    if not hasattr(_get_logger, '_logger'):
        try:
            from rss2pod.orchestrator.logging_config import get_logger
            _get_logger._logger = get_logger('rss2pod.llm.llm_client')
        except ImportError:
            # 如果导入失败，使用标准 logging
            _get_logger._logger = logging.getLogger('rss2pod.llm.llm_client')
    return _get_logger._logger

logger = _get_logger()


class LLMClient(ABC):
    """LLM 客户端抽象基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Generate structured JSON response"""
        pass


class DashScopeClient(LLMClient):
    """
    DashScope (通义千问) LLM Client
    
    使用 requests 直接调用 API（兼容 coding.dashscope.aliyuncs.com 端点）
    支持模型：qwen-plus, qwen3.5-plus, qwen-turbo 等
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-plus", 
                 base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model
        self.base_url = base_url
        
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY environment variable not set")
        
        try:
            import requests
            self._session = requests.Session()
        except ImportError:
            raise ImportError("Please install requests: pip install requests")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from prompt using DashScope Chat API
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (temperature, max_tokens, timeout, etc.)
        
        Returns:
            Generated text response
        """
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)
        timeout = kwargs.get("timeout", 120)  # 默认 120 秒超时
        
        try:
            import requests
            
            # 使用 Chat Completions API
            messages = [
                {"role": "system", "content": "你是一个专业的助手。"},
                {"role": "user", "content": prompt}
            ]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            url = f"{self.base_url}/chat/completions"
            
            logger.debug(f"[LLM] 发送请求到：{url}")
            logger.debug(f"[LLM] Prompt 长度：{len(prompt)} 字符")
            
            start_time = time.time()
            response = self._session.post(url, headers=headers, json=data, timeout=timeout)
            elapsed = time.time() - start_time
            
            logger.debug(f"[LLM] 响应状态码：{response.status_code}, 耗时：{elapsed:.2f}秒")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                logger.debug(f"[LLM] 回复长度：{len(content)} 字符")
                return content
            else:
                error_msg = f"DashScope API error: {response.status_code} - {response.text[:200]}"
                logger.error(f"[LLM] {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            logger.error(f"[LLM] 请求超时：{timeout}秒")
            raise Exception(f"LLM generation timeout: {timeout} seconds")
        except requests.exceptions.RequestException as e:
            logger.error(f"[LLM] 网络错误：{e}")
            raise Exception(f"LLM network error: {str(e)}")
        except Exception as e:
            logger.error(f"[LLM] 生成失败：{e}")
            raise Exception(f"LLM generation failed: {str(e)}")
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Generate structured JSON response
        
        Args:
            prompt: Input prompt
            schema: Optional JSON schema for the response
            **kwargs: Additional parameters
        
        Returns:
            Parsed JSON response
        """
        # 添加 JSON 格式要求到 prompt
        if schema:
            schema_str = json.dumps(schema, ensure_ascii=False)
            prompt = f"{prompt}\n\n请以 JSON 格式回复，符合以下 schema:\n{schema_str}"
        else:
            prompt = f"{prompt}\n\n请以 JSON 格式回复。"
        
        # 明确要求 LLM 转义控制字符
        prompt = f"{prompt}\n\n注意：JSON 中的所有换行符必须使用 \\n 转义，制表符使用 \\t 转义，不要使用实际的换行或制表字符。"
        
        response_text = self.generate(prompt, **kwargs)
        
        # [DEBUG] 记录原始响应以便调试
        logger.info(f"[LLM] generate_json 调用完成，响应长度：{len(response_text)} 字符")
        logger.debug(f"[LLM] 原始响应前 500 字符：{response_text[:500]}...")
        
        # 尝试解析 JSON
        try:
            # 清理 markdown 代码块标记
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # [修复] 处理字面意义上的 \t 序列（反斜杠 + t）
            # LLM 可能返回 "\t" 作为缩进（字面意义上的两个字符），而不是真正的制表符
            # 这会导致 JSON 解析失败，需要删除这些字面的 \t 序列
            response_text = response_text.replace('\\t', '')
            
            logger.debug(f"[LLM] 清理后的响应前 500 字符：{response_text[:500]}...")
            
            # 首先尝试直接解析
            try:
                result = json.loads(response_text)
                result_type = type(result).__name__
                logger.info(f"[LLM] JSON 解析成功，结果类型：{result_type}")
                if isinstance(result, dict):
                    logger.debug(f"[LLM] JSON keys: {list(result.keys())}")
                return result
            except json.JSONDecodeError as e:
                logger.debug(f"[LLM] 直接解析失败：{e}")
                pass
            
            # 尝试使用 json5 解析（更宽松）
            try:
                import json5
                logger.debug("使用 json5 解析 JSON")
                result = json5.loads(response_text)
                logger.debug("[LLM] json5 解析成功")
                return result
            except ImportError:
                logger.debug("json5 未安装，跳过")
            except Exception as e:
                logger.debug(f"[LLM] json5 解析失败：{e}")
            
            # 回退到标准 json，使用正则表达式清理控制字符
            import re
            logger.debug("使用正则表达式清理控制字符")
            
            # 方法 1：先尝试将制表符替换为空格（针对 JSON 结构中的制表符）
            # 这可以修复 LLM 使用 \t 作为缩进的问题
            response_text_cleaned = response_text.replace('\t', '  ')
            logger.debug(f"[LLM] 替换制表符后的响应前 500 字符：{response_text_cleaned[:500]}...")
            
            try:
                result = json.loads(response_text_cleaned)
                logger.debug("[LLM] 替换制表符后解析成功")
                return result
            except json.JSONDecodeError:
                pass
            
            # 方法 2：移除字符串字面量内的实际换行符、制表符等控制字符
            # 这个正则匹配双引号内的内容，将实际换行替换为 \n
            def escape_control_chars(match):
                content = match.group(1)
                # 转义控制字符
                content = content.replace('\\n', '__ESCAPED_NEWLINE__')  # 先保护已有的 \n
                content = content.replace('\\t', '__ESCAPED_TAB__')      # 先保护已有的 \t
                content = content.replace('\\r', '__ESCAPED_CR__')       # 先保护已有的 \r
                content = content.replace('\n', '\\n')                   # 实际换行 -> \n
                content = content.replace('\r', '\\r')                   # 回车 -> \r
                content = content.replace('\t', '\\t')                   # 制表符 -> \t
                # 恢复已转义的序列
                content = content.replace('__ESCAPED_NEWLINE__', '\\n')
                content = content.replace('__ESCAPED_TAB__', '\\t')
                content = content.replace('__ESCAPED_CR__', '\\r')
                return '"' + content + '"'
            
            response_text = re.sub(r'"([^"\\]*(\\.[^"\\]*)*)"', escape_control_chars, response_text)
            logger.debug(f"[LLM] 清理控制字符后的响应：{response_text[:500]}...")
            
            result = json.loads(response_text)
            logger.debug("[LLM] 清理后解析成功")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[LLM] JSON 解析失败：{e}")
            logger.error(f"[LLM] 原始响应：{response_text}")
            raise Exception(f"Failed to parse JSON response: {e}\nRaw response: {response_text[:1000]}")
        except Exception as e:
            logger.error(f"[LLM] 处理失败：{e}")
            raise Exception(f"LLM JSON processing failed: {str(e)}")


class MockLLMClient(LLMClient):
    """模拟 LLM 客户端 - 用于测试"""
    
    def __init__(self):
        pass
    
    def generate(self, prompt: str, **kwargs) -> str:
        return f"[Mock Response] 收到：{prompt[:50]}..."
    
    def generate_json(self, prompt: str, schema: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        return {"mock": True, "prompt": prompt[:50]}


def create_llm_client(provider: str = "dashscope", **kwargs) -> LLMClient:
    """
    创建 LLM 客户端实例
    
    Args:
        provider: 提供商名称 (dashscope, mock)
        **kwargs: 提供商特定参数
    
    Returns:
        LLMClient 实例
    """
    providers = {
        "dashscope": DashScopeClient,
        "mock": MockLLMClient,
    }
    
    provider_class = providers.get(provider.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider}")
    
    return provider_class(**kwargs)
