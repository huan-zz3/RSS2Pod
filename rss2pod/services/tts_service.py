"""
TTS 服务 - 封装文本转语音相关操作
"""

import os
import sys
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_service import BaseService, ServiceResult


class TTSService(BaseService):
    """
    TTS 服务
    
    提供文本转语音相关的业务逻辑封装
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        super().__init__(config_path, db_path)
        self._client = None
    
    def _get_tts_provider_config(self) -> Dict[str, Any]:
        """获取当前 TTS provider 的配置"""
        tts_config = self.config.get('tts', {})
        active_provider = tts_config.get('active_provider', 'siliconflow')
        providers = tts_config.get('providers', {})
        return providers.get(active_provider, {})
    
    def _get_active_adapter_config(self) -> Dict[str, Any]:
        """获取当前 adapter 的配置"""
        tts_config = self.config.get('tts', {})
        active_provider = tts_config.get('active_provider', 'siliconflow')
        active_adapter = tts_config.get('active_adapter', 'moss')
        providers = tts_config.get('providers', {})
        provider_config = providers.get(active_provider, {})
        adapters_config = provider_config.get('adapters', {})
        adapter_config = adapters_config.get(active_adapter, {})
        # 添加 adapter_name 到配置中，方便调用方识别
        adapter_config['adapter_name'] = active_adapter
        return adapter_config
    
    def _get_client(self):
        """获取 TTS 客户端"""
        if self._client is None:
            from tts.siliconflow_provider import SiliconFlowClient
            
            # 使用新的 providers 配置结构
            provider_config = self._get_tts_provider_config()
            adapter_config = self._get_active_adapter_config()
            
            self._client = SiliconFlowClient(
                api_key=provider_config.get('api_key', ''),
                base_url=provider_config.get('base_url', 'https://api.siliconflow.cn/v1'),
                model=adapter_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
            )
        
        return self._client
    
    def test_connection(self) -> ServiceResult:
        """
        测试 TTS 连接
        
        Returns:
            ServiceResult 实例
        """
        try:
            # 使用新的 providers 配置结构
            provider_config = self._get_tts_provider_config()
            adapter_config = self._get_active_adapter_config()
            
            if not provider_config.get('api_key'):
                return ServiceResult(
                    success=False,
                    error_message='TTS API Key 未配置'
                )
            
            tts_config = self.config.get('tts', {})
            active_provider = tts_config.get('active_provider', 'siliconflow')
            active_adapter = tts_config.get('active_adapter', 'moss')
            
            return ServiceResult(
                success=True,
                data={
                    'provider': active_provider,
                    'adapter': active_adapter,
                    'model': adapter_config.get('model', 'fnlp/MOSS-TTSD-v0.5'),
                    'configured': True
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def list_voices(self, model: Optional[str] = None) -> ServiceResult:
        """
        列出可用音色
        
        Args:
            model: 可选，指定模型名称
            
        Returns:
            ServiceResult 实例
        """
        try:
            from tts.siliconflow_provider import SiliconFlowClient
            
            if not model:
                tts_config = self.config.get('tts', {})
                model = tts_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
            
            voices = SiliconFlowClient.get_available_voices(model)
            
            return ServiceResult(
                success=True,
                data=voices,
                metadata={'model': model, 'count': len(voices)}
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> ServiceResult:
        """
        将文本转换为音频
        
        Args:
            text: 输入文本
            voice: 音色（不指定则使用配置中的默认音色）
            output_path: 输出文件路径（不指定则自动生成）
            
        Returns:
            ServiceResult 实例
        """
        try:
            # 使用新的 providers 配置结构
            provider_config = self._get_tts_provider_config()
            adapter_config = self._get_active_adapter_config()
            
            if not provider_config.get('api_key'):
                return ServiceResult(
                    success=False,
                    error_message='TTS API Key 未配置'
                )
            
            # 获取客户端
            client = self._get_client()
            
            # 获取模型
            model = adapter_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
            
            # 确定音色
            if not voice:
                # 从 adapter 配置获取默认音色
                if 'CosyVoice' in model:
                    voice = adapter_config.get('voice', 'claire')
                    voice = f"{model}:{voice}"
                else:
                    voice_host = adapter_config.get('voice_host', 'alex')
                    voice = f"fnlp/MOSS-TTSD-v0.5:{voice_host}"
            
            # 生成输出文件路径
            if not output_path:
                import hashlib
                import time
                timestamp = int(time.time())
                text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
                output_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'data', 'media', 'tts'
                )
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"output_{text_hash}_{timestamp}.mp3")
            
            # 同步执行 TTS 合成
            async def _synthesize():
                # 检测模型类型
                if 'CosyVoice' in model:
                    # CosyVoice 单人模式
                    audio_data = await client.synthesize(text, voice=voice)
                else:
                    # MOSS 模型 - 使用 voice 参数
                    audio_data = await client.synthesize(text, voice=voice)
                
                return audio_data
            
            audio_data = asyncio.run(_synthesize())
            
            # 保存文件
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_data)
            
            # 计算文件信息
            file_size = len(audio_data)
            duration_estimate = file_size / 16000  # 粗略估算
            
            return ServiceResult(
                success=True,
                data={
                    'audio_path': str(output_path.resolve()),
                    'file_size': file_size,
                    'file_size_kb': file_size / 1024,
                    'estimated_duration': duration_estimate
                }
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    async def synthesize_segments(
        self,
        segments: List[Dict],
        voice: str = None,
        output_dir: str = None
    ) -> 'ServiceResult':
        """
        分段合成音频
        
        将播客脚本按段落拆分，逐段调用 TTS API，然后拼接所有音频片段。
        解决 SiliconFlow TTS 时长限制问题（最多 2 分 43 秒）。
        
        Args:
            segments: 段落列表，每个段落包含 speaker 和 content
            voice: 音色（不指定则使用配置中的默认音色）
            output_dir: 输出目录（不指定则使用默认目录）
            
        Returns:
            ServiceResult 实例，包含 audio_path, audio_duration
        """
        try:
            from tts.audio_assembler import AudioAssembler, AudioRole, AssemblyConfig
            from tts.adapter import get_adapter_from_tts_config
            
            # 获取配置
            provider_config = self._get_tts_provider_config()
            adapter_config = self._get_active_adapter_config()
            tts_config = self.config.get('tts', {})
            
            if not provider_config.get('api_key'):
                return ServiceResult(
                    success=False,
                    error_message='TTS API Key 未配置'
                )
            
            # 获取客户端
            client = self._get_client()
            
            # 获取模型和适配器
            model = adapter_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
            adapter = get_adapter_from_tts_config(tts_config)
            
            # 确定音色
            if not voice:
                if 'CosyVoice' in model:
                    voice = adapter_config.get('voice', 'claire')
                    voice = f"{model}:{voice}"
                else:
                    voice_host = adapter_config.get('voice_host', 'alex')
                    voice = f"fnlp/MOSS-TTSD-v0.5:{voice_host}"
            
            # 生成输出目录
            if not output_dir:
                import time
                timestamp = int(time.time())
                output_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'data', 'media', 'tts', str(timestamp)
                )
            os.makedirs(output_dir, exist_ok=True)
            
            # 逐段合成
            segment_paths = []
            for i, seg in enumerate(segments):
                speaker = seg.get('speaker', 'host')
                
                # 使用适配器转换
                single_segment = [seg]
                tts_input = adapter.convert_to_tts_input(single_segment)
                
                # 调用 TTS
                audio_data = await client.synthesize(tts_input, voice=voice)
                
                # 保存分段音频
                segment_path = os.path.join(output_dir, f"segment_{i+1:03d}_{speaker}.mp3")
                with open(segment_path, 'wb') as f:
                    f.write(audio_data)
                segment_paths.append((segment_path, speaker))
            
            # 拼接音频
            assembler = AudioAssembler(config=AssemblyConfig(
                output_format="mp3",
                bitrate="192k",
                sample_rate=44100,
                channels=2,
                gap_between_segments_ms=200,
                normalize_volume=True,
                target_volume_db=-16.0,
                crossfade_ms=0
            ))
            
            await assembler.initialize()
            if not assembler._ffmpeg_available:
                await client.close()
                return ServiceResult(
                    success=False,
                    error_message="FFmpeg 不可用，无法进行音频拼接"
                )
            
            # 添加所有片段
            for path, speaker in segment_paths:
                role = AudioRole.HOST if speaker == 'host' else AudioRole.GUEST
                assembler.add_segment(
                    path=path,
                    role=role,
                    fade_in_ms=0,
                    fade_out_ms=0
                )
            
            # 最终输出文件
            final_audio_path = os.path.join(output_dir, "final_output.mp3")
            assembled_path = await assembler.assemble(final_audio_path)
            
            # 计算时长
            audio_duration = os.path.getsize(assembled_path) // 16000
            
            return ServiceResult(
                success=True,
                data={
                    'audio_path': assembled_path,
                    'audio_duration': audio_duration,
                    'segment_count': len(segments),
                    'output_dir': output_dir
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def synthesize_segments_sync(
        self,
        segments: List[Dict],
        voice: str = None,
        output_dir: str = None
    ) -> 'ServiceResult':
        """
        同步版本：分段合成音频
        
        Args:
            segments: 段落列表
            voice: 音色
            output_dir: 输出目录
            
        Returns:
            ServiceResult 实例
        """
        return asyncio.run(self.synthesize_segments(segments, voice, output_dir))
    
    def get_adapter(self, config_path: str = None):
        """
        获取 TTS 适配器
        
        Args:
            config_path: 可选的配置文件路径
            
        Returns:
            TTSAdapter 实例
        """
        from tts.adapter import get_adapter_from_tts_config
        
        if config_path:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            tts_config = config.get('tts', {})
        else:
            tts_config = self.config.get('tts', {})
        
        return get_adapter_from_tts_config(tts_config)
    
    def synthesize_with_speed(
        self,
        segments: List[Dict],
        speed: float = 1.0,
        output_dir: str = None
    ) -> 'ServiceResult':
        """
        带速度控制的分段合成音频
        
        Args:
            segments: 段落列表
            speed: 播放速度 (0.5-2.0)
            output_dir: 输出目录
            
        Returns:
            ServiceResult 实例
        """
        # 先进行标准合成
        result = self.synthesize_segments_sync(segments, output_dir=output_dir)
        
        if not result.success:
            return result
        
        # 如果速度不是 1.0，进行调速处理
        if speed != 1.0 and result.data.get('audio_path'):
            from tts.audio_speed import AudioSpeedProcessor
            
            audio_path = result.data['audio_path']
            speed_processor = AudioSpeedProcessor()
            
            try:
                speed_adjusted_path = audio_path.replace('.mp3', f'_speed{speed}.mp3')
                adjusted_path = asyncio.run(speed_processor.adjust_speed(
                    audio_path,
                    speed_adjusted_path,
                    speed
                ))
                
                if adjusted_path and os.path.exists(adjusted_path):
                    # 删除原始文件
                    if audio_path != adjusted_path and os.path.exists(audio_path):
                        os.remove(audio_path)
                    result.data['audio_path'] = adjusted_path
                    result.data['audio_duration'] = int(result.data.get('audio_duration', 0) / speed)
            except Exception as e:
                result.error_message = f"音频调速失败: {e}"
        
        return result
    
    def synthesize_segments_advanced(
        self,
        segments: List[Dict],
        config: Dict = None
    ) -> 'ServiceResult':
        """
        高级分段合成 - 支持自定义配置
        
        Args:
            segments: 段落列表
            config: 高级配置，包含：
                - voice: 音色
                - output_dir: 输出目录
                - speed: 播放速度
                - normalize_volume: 是否标准化音量
                - gap_between_segments: 段落间隔（毫秒）
                
        Returns:
            ServiceResult 实例
        """
        config = config or {}
        
        voice = config.get('voice')
        output_dir = config.get('output_dir')
        speed = config.get('speed', 1.0)
        
        # 如果指定了速度，使用 synthesize_with_speed
        if speed != 1.0:
            return self.synthesize_with_speed(segments, speed, output_dir)
        
        # 否则使用标准合成
        return self.synthesize_segments_sync(segments, voice, output_dir)
    
    def _create_audio_assembler(self):  # -> AudioAssembler (imported at runtime)
        """
        创建配置好的 AudioAssembler 实例
        
        Returns:
            AudioAssembler 实例
        """
        from tts.audio_assembler import AudioAssembler, AssemblyConfig
        
        return AudioAssembler(config=AssemblyConfig(
            output_format="mp3",
            bitrate="192k",
            sample_rate=44100,
            channels=2,
            gap_between_segments_ms=200,
            normalize_volume=True,
            target_volume_db=-16.0,
            crossfade_ms=0
        ))
    
    async def _adjust_audio_speed(
        self,
        audio_path: str,
        speed: float,
        logger=None
    ) -> str:
        """
        音频调速处理
        
        Args:
            audio_path: 原始音频路径
            speed: 目标播放速度
            logger: 可选的日志记录器
            
        Returns:
            调速后的文件路径
        """
        if speed == 1.0:
            return audio_path
        
        from tts.audio_speed import AudioSpeedProcessor
        
        speed_processor = AudioSpeedProcessor()
        
        try:
            speed_adjusted_path = audio_path.replace('.mp3', f'_speed{speed}.mp3')
            adjusted_path = await speed_processor.adjust_speed(
                audio_path,
                speed_adjusted_path,
                speed
            )
            
            if adjusted_path and os.path.exists(adjusted_path):
                # 删除原始文件
                if audio_path != adjusted_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                return adjusted_path
            else:
                if logger:
                    logger.warning("[speed] 音频调速失败，使用原始文件")
                return audio_path
                
        except Exception as e:
            if logger:
                logger.warning(f"[speed] 音频调速异常: {e}，使用原始文件")
            return audio_path
    
    async def synthesize_segments_with_asset_manager(
        self,
        segments: List[Dict],
        asset_manager,
        speed: float = 1.0,
        logger=None
    ) -> 'ServiceResult':
        """
        分段合成音频并保存到资源管理器
        
        完整的 TTS 流程：分段合成 -> 拼接 -> 调速
        
        Args:
            segments: 段落列表，每个段落包含 speaker 和 content
            asset_manager: AssetManager 实例，需要有 segments_dir 属性
            speed: 播放速度 (0.5-2.0, 1.0 为正常速度)
            logger: 可选的日志记录器
            
        Returns:
            ServiceResult 实例，包含:
            - audio_path: str - 最终音频路径
            - audio_duration: int - 音频时长（秒）
        """
        try:
            from tts.audio_assembler import AudioRole
            
            if logger:
                logger.info(f"[tts] 开始分段合成，共 {len(segments)} 个段落")
            
            # 获取配置
            provider_config = self._get_tts_provider_config()
            adapter_config = self._get_active_adapter_config()
            
            if not provider_config.get('api_key'):
                return ServiceResult(
                    success=False,
                    error_message='TTS API Key 未配置'
                )
            
            # 获取客户端和适配器
            client = self._get_client()
            adapter = self.get_adapter()
            model = adapter_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
            
            # 确定音色
            if 'CosyVoice' in model:
                voice = adapter_config.get('voice', 'claire')
                voice = f"{model}:{voice}"
            else:
                voice_host = adapter_config.get('voice_host', 'alex')
                voice = f"fnlp/MOSS-TTSD-v0.5:{voice_host}"
            
            # 逐段合成
            segment_paths = []
            
            for i, seg in enumerate(segments):
                speaker = seg.get('speaker', 'host')
                
                # 使用适配器转换
                single_segment = [seg]
                tts_input = adapter.convert_to_tts_input(single_segment)
                
                # 调用 TTS
                audio_data = await client.synthesize(tts_input, voice=voice)
                
                # 保存分段音频
                segment_path = asset_manager.save_audio_segment(i + 1, audio_data, speaker)
                segment_paths.append((segment_path, speaker))
            
            if logger:
                logger.info(f"[tts] ✓ 音频片段已保存到: {asset_manager.segments_dir}")
                for path, speaker in segment_paths:
                    logger.info(f"[tts]   - {os.path.basename(path)}")
            
            # 拼接音频
            assembler = self._create_audio_assembler()
            
            await assembler.initialize()
            if not assembler._ffmpeg_available:
                await client.close()
                return ServiceResult(
                    success=False,
                    error_message="FFmpeg 不可用，无法进行音频拼接"
                )
            
            # 添加所有片段
            for path, speaker in segment_paths:
                role = AudioRole.HOST if speaker == 'host' else AudioRole.GUEST
                assembler.add_segment(
                    path=path,
                    role=role,
                    fade_in_ms=0,
                    fade_out_ms=0
                )
            
            # 创建最终输出路径
            final_audio_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'data', 'media'
            )
            os.makedirs(final_audio_dir, exist_ok=True)
            
            # 生成带速度标识的文件名
            speed_suffix = f"_speed{speed}" if speed != 1.0 else ""
            final_filename = f"episode_temp{speed_suffix}.mp3"
            final_audio_path = os.path.join(final_audio_dir, final_filename)
            
            assembled_path = await assembler.assemble(final_audio_path)
            
            if not assembled_path or not os.path.exists(assembled_path):
                await client.close()
                return ServiceResult(
                    success=False,
                    error_message="音频拼接失败"
                )
            
            # 计算时长
            audio_duration = os.path.getsize(assembled_path) // 16000
            
            await client.close()
            
            # 调速处理
            if speed != 1.0:
                if logger:
                    logger.info(f"[speed] 开始音频调速，目标速度: {speed}x")
                
                adjusted_path = await self._adjust_audio_speed(
                    str(assembled_path),
                    speed,
                    logger
                )
                
                if adjusted_path and os.path.exists(adjusted_path):
                    assembled_path = adjusted_path
                    audio_duration = int(audio_duration / speed)
                    if logger:
                        logger.info(f"[speed] ✓ 音频调速完成: {adjusted_path}")
            
            return ServiceResult(
                success=True,
                data={
                    'audio_path': str(assembled_path),
                    'audio_duration': audio_duration,
                    'segment_count': len(segments)
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error_message=str(e)
            )
    
    def close(self):
        """关闭服务，释放资源"""
        if self._client:
            try:
                # 尝试获取当前运行的事件循环
                loop = asyncio.get_running_loop()
                # 如果已有事件循环，创建一个 task 来关闭客户端
                loop.create_task(self._client.close())
            except RuntimeError:
                # 没有运行中的事件循环，可以安全使用 asyncio.run()
                asyncio.run(self._client.close())
        super().close()
