#!/usr/bin/env python3
"""
Episode Asset Manager - Episode 资源管理器

负责管理 Episode 处理过程中的各类资源文件：
- 源级摘要
- 组级摘要
- 播客脚本
- 音频片段
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EpisodeAssetManager:
    """
    Episode 资源管理器
    
    管理单个 Episode 处理过程中的所有资源文件。
    """
    
    # 类级别属性：rss2pod 目录路径
    _rss2pod_dir = None
    
    @classmethod
    def _get_rss2pod_dir(cls) -> str:
        """获取 rss2pod 包目录路径"""
        if cls._rss2pod_dir is None:
            # __file__ = rss2pod/orchestrator/asset_manager.py
            # 向上2层得到 rss2pod 目录
            cls._rss2pod_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return cls._rss2pod_dir
    
    def __init__(self, group_id: str, timestamp: str):
        """
        初始化资源管理器
        
        Args:
            group_id: Group ID
            timestamp: Episode 时间戳 (格式: YYYYMMDDHHMMSS)
        """
        self.group_id = group_id
        self.timestamp = timestamp
        
        # 资源根目录：rss2pod目录/data/media/{group_id}/{timestamp}
        rss2pod_dir = self._get_rss2pod_dir()
        base_dir = os.path.join(rss2pod_dir, 'data', 'media', group_id, timestamp)
        self.assets_dir = base_dir
        
        # 子目录
        self.segments_dir = os.path.join(self.assets_dir, 'segments')
    
    def initialize(self):
        """
        初始化资源目录结构
        
        创建所需的目录结构：
        - data/media/{group_id}/{timestamp}/
        - data/media/{group_id}/{timestamp}/segments/
        """
        os.makedirs(self.segments_dir, exist_ok=True)
        
        # 创建必要的文件占位（可选）
        return self
    
    @property
    def source_summaries_path(self) -> str:
        """源级摘要文件路径"""
        return os.path.join(self.assets_dir, 'source_summaries.json')
    
    @property
    def group_summary_path(self) -> str:
        """组级摘要文件路径"""
        return os.path.join(self.assets_dir, 'group_summary.json')
    
    @property
    def podcast_script_path(self) -> str:
        """播客脚本文件路径"""
        return os.path.join(self.assets_dir, 'podcast_script.json')
    
    @property
    def moss_input_path(self) -> str:
        """MOSS TTS 输入文件路径（兼容旧版本）"""
        return os.path.join(self.assets_dir, 'moss_input.json')
    
    @property
    def llm_prompt_input_path(self) -> str:
        """LLM Prompt 输入文件路径（用于调试）"""
        return os.path.join(self.assets_dir, 'llm_prompt_input.json')
    
    def get_tts_input_path(self, adapter_name: str = 'moss') -> str:
        """
        根据 TTS 适配器名称获取对应的 TTS 输入文件路径
        
        Args:
            adapter_name: TTS 适配器名称 (如 'moss', 'cosyvoice')
            
        Returns:
            TTS 输入文件路径
        """
        filename = f"{adapter_name}_input.json"
        return os.path.join(self.assets_dir, filename)
    
    def save_source_summaries(self, summaries: List[Dict[str, Any]]) -> str:
        """
        保存源级摘要
        
        Args:
            summaries: 源级摘要列表
            
        Returns:
            保存的文件路径
        """
        path = self.source_summaries_path
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)
        return path
    
    def load_source_summaries(self) -> List[Dict[str, Any]]:
        """
        加载源级摘要
        
        Returns:
            源级摘要列表
        """
        path = self.source_summaries_path
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_group_summary(self, summary: Dict[str, Any]) -> str:
        """
        保存组级摘要
        
        Args:
            summary: 组级摘要字典
            
        Returns:
            保存的文件路径
        """
        path = self.group_summary_path
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return path
    
    def load_group_summary(self) -> Optional[Dict[str, Any]]:
        """
        加载组级摘要
        
        Returns:
            组级摘要字典，如果不存在则返回 None
        """
        path = self.group_summary_path
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_podcast_script(self, script: Dict[str, Any], moss_input: Any, tts_input_path: str = None) -> str:
        """
        保存播客脚本
        
        Args:
            script: 播客脚本字典
            moss_input: TTS 输入数据
            tts_input_path: 自定义的 TTS 输入文件路径（可选，如果不传则使用默认的 moss_input_path）
            
        Returns:
            保存的文件路径
        """
        # 保存完整脚本
        script_path = self.podcast_script_path
        with open(script_path, 'w', encoding='utf-8') as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        
        # 保存 TTS 输入（使用自定义路径或默认路径）
        input_path = tts_input_path or self.moss_input_path
        with open(input_path, 'w', encoding='utf-8') as f:
            if isinstance(moss_input, str):
                f.write(moss_input)
            else:
                json.dump(moss_input, f, ensure_ascii=False, indent=2)
        
        return script_path
    
    def save_llm_prompt_input(self, prompt_data: Dict[str, Any]) -> str:
        """
        保存发送给 LLM 的 prompt 输入（用于调试）
        
        Args:
            prompt_data: 包含 prompt、变量等信息的字典
            
        Returns:
            保存的文件路径
        """
        path = self.llm_prompt_input_path
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(prompt_data, f, ensure_ascii=False, indent=2)
        return path
    
    def load_podcast_script(self) -> Optional[Dict[str, Any]]:
        """
        加载播客脚本
        
        Returns:
            播客脚本字典，如果不存在则返回 None
        """
        path = self.podcast_script_path
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_audio_segment(self, segment_num: int, audio_data: bytes, speaker: str) -> str:
        """
        保存音频片段
        
        Args:
            segment_num: 片段编号 (从 1 开始)
            audio_data: 音频数据 (bytes)
            speaker: 发言人 (host/guest)
            
        Returns:
            保存的文件路径
        """
        filename = f"segment_{segment_num}_{speaker}.mp3"
        path = os.path.join(self.segments_dir, filename)
        
        with open(path, 'wb') as f:
            f.write(audio_data)
        
        return path
    
    def get_audio_segment_path(self, segment_num: int, speaker: str) -> str:
        """
        获取音频片段路径
        
        Args:
            segment_num: 片段编号
            speaker: 发言人
            
        Returns:
            音频文件路径
        """
        filename = f"segment_{segment_num}_{speaker}.mp3"
        return os.path.join(self.segments_dir, filename)
    
    def list_audio_segments(self) -> List[str]:
        """
        列出所有音频片段
        
        Returns:
            音频片段文件路径列表
        """
        if not os.path.exists(self.segments_dir):
            return []
        
        segments = []
        for filename in sorted(os.listdir(self.segments_dir)):
            if filename.endswith('.mp3'):
                segments.append(os.path.join(self.segments_dir, filename))
        return segments
    
    def list_assets(self) -> Dict[str, Any]:
        """
        列出当前 Episode 的所有资源
        
        Returns:
            资源详情字典
        """
        assets = {
            'group_id': self.group_id,
            'timestamp': self.timestamp,
            'assets_dir': self.assets_dir,
            'source_summaries': None,
            'group_summary': None,
            'podcast_script': None,
            'audio_segments': []
        }
        
        # 检查源级摘要
        if os.path.exists(self.source_summaries_path):
            assets['source_summaries'] = self.source_summaries_path
        
        # 检查组级摘要
        if os.path.exists(self.group_summary_path):
            assets['group_summary'] = self.group_summary_path
        
        # 检查播客脚本
        if os.path.exists(self.podcast_script_path):
            assets['podcast_script'] = self.podcast_script_path
        
        # 列出音频片段
        assets['audio_segments'] = self.list_audio_segments()
        
        return assets
    
    def cleanup(self):
        """
        清理中间文件
        
        删除以下文件：
        - source_summaries.json (源级摘要)
        - group_summary.json (组级摘要)
        - podcast_script.json (播客脚本)
        - moss_input.json (TTS输入)
        - segments/ (分段音频)
        
        保留：
        - 最终音频文件 (episode，在 data/media/{_*.mp3group_id}/ 下)
        """
        import shutil
        
        files_to_delete = [
            self.source_summaries_path,
            self.group_summary_path,
            self.podcast_script_path,
            self.moss_input_path,
        ]
        
        # 删除中间文件
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"删除文件失败 {file_path}: {e}")
        
        # 删除 segments 目录
        if os.path.exists(self.segments_dir):
            try:
                shutil.rmtree(self.segments_dir)
            except Exception as e:
                print(f"删除目录失败 {self.segments_dir}: {e}")
        
        # 如果 assets_dir 为空，也删除它
        if os.path.exists(self.assets_dir):
            try:
                if not os.listdir(self.assets_dir):
                    os.rmdir(self.assets_dir)
            except Exception as e:
                print(f"删除空目录失败 {self.assets_dir}: {e}")
    
    @classmethod
    def list_episode_assets(cls, group_id: str) -> List[Dict[str, Any]]:
        """
        列出 Group 下所有 Episode 的资源
        
        Args:
            group_id: Group ID
            
        Returns:
            Episode 资源列表
        """
        # 使用类方法获取 rss2pod 目录
        rss2pod_dir = cls._get_rss2pod_dir()
        base_dir = os.path.join(rss2pod_dir, 'data', 'media', group_id)
        
        if not os.path.exists(base_dir):
            return []
        
        episodes = []
        
        for timestamp in sorted(os.listdir(base_dir), reverse=True):
            episode_dir = os.path.join(base_dir, timestamp)
            if not os.path.isdir(episode_dir):
                continue
            
            # 检查是否是有效的 Episode 目录
            segments_dir = os.path.join(episode_dir, 'segments')
            if not os.path.exists(segments_dir):
                continue
            
            # 获取基本信息
            asset_manager = cls(group_id, timestamp)
            assets = asset_manager.list_assets()
            
            # 添加 Episode 元信息
            episode_info = {
                'group_id': group_id,
                'episode_timestamp': timestamp,
                'assets': assets
            }
            
            # 尝试解析时间戳
            try:
                dt = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                episode_info['created_at'] = dt.isoformat()
            except ValueError:
                episode_info['created_at'] = timestamp
            
            episodes.append(episode_info)
        
        return episodes
    
    @classmethod
    def get_latest_episode(cls, group_id: str) -> Optional[Dict[str, Any]]:
        """
        获取最新的 Episode 资源
        
        Args:
            group_id: Group ID
            
        Returns:
            最新 Episode 的资源字典，如果不存在则返回 None
        """
        episodes = cls.list_episode_assets(group_id)
        return episodes[0] if episodes else None
    
    @classmethod
    def cleanup_group_episodes(cls, group_id: str, keep_latest: int = 3):
        """
        清理 Group 下的旧 Episode 资源
        
        Args:
            group_id: Group ID
            keep_latest: 保留最新的 Episode 数量
        """
        episodes = cls.list_episode_assets(group_id)
        
        if len(episodes) <= keep_latest:
            return
        
        # 保留最新的 Episode
        episodes_to_keep = episodes[:keep_latest]
        timestamps_to_keep = {ep['episode_timestamp'] for ep in episodes_to_keep}
        
        # 清理旧的 Episode
        for episode in episodes[keep_latest:]:
            timestamp = episode['episode_timestamp']
            # 使用类方法获取 rss2pod 目录
            rss2pod_dir = cls._get_rss2pod_dir()
            episode_dir = os.path.join(rss2pod_dir, 'data', 'media', group_id, timestamp)
            
            import shutil
            if os.path.exists(episode_dir):
                shutil.rmtree(episode_dir)


# 便捷函数
def get_episode_manager(group_id: str, timestamp: str) -> EpisodeAssetManager:
    """
    获取 Episode 资源管理器实例
    
    Args:
        group_id: Group ID
        timestamp: Episode 时间戳
        
    Returns:
        EpisodeAssetManager 实例
    """
    return EpisodeAssetManager(group_id, timestamp)


def list_group_episodes(group_id: str) -> List[Dict[str, Any]]:
    """
    列出 Group 下所有 Episode
    
    Args:
        group_id: Group ID
        
    Returns:
        Episode 列表
    """
    return EpisodeAssetManager.list_episode_assets(group_id)


def cleanup_group_assets(group_id: str, keep_latest: int = 3):
    """
    清理 Group 下的旧资源
    
    Args:
        group_id: Group ID
        keep_latest: 保留最新的 Episode 数量
    """
    EpisodeAssetManager.cleanup_group_episodes(group_id, keep_latest)
