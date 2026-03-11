"""
音频拼接模块

支持双人对话拼接、音量统一、无断层处理。
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union, Tuple, Dict, Any
from enum import Enum
import tempfile
import hashlib


class AudioRole(str, Enum):
    """音频角色类型"""
    HOST = "host"  # 主持人
    GUEST = "guest"  # 嘉宾
    NARRATOR = "narrator"  # 旁白
    ADVERTISEMENT = "advertisement"  # 广告
    MUSIC = "music"  # 背景音乐


@dataclass
class AudioSegment:
    """音频片段"""
    path: Path
    role: AudioRole = AudioRole.NARRATOR
    duration_ms: int = 0
    volume_db: float = 0.0  # 音量（分贝）
    start_time_ms: int = 0  # 在最终音频中的起始位置
    fade_in_ms: int = 0  # 淡入时长
    fade_out_ms: int = 0  # 淡出时长
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.path, str):
            self.path = Path(self.path)


@dataclass
class AssemblyConfig:
    """音频拼接配置"""
    output_format: str = "mp3"  # mp3, wav, m4a
    bitrate: str = "192k"  # 比特率
    sample_rate: int = 44100  # 采样率
    channels: int = 2  # 声道数（1=mono, 2=stereo）
    gap_between_segments_ms: int = 200  # 片段间间隔
    normalize_volume: bool = True  # 是否统一音量
    target_volume_db: float = -16.0  # 目标音量（LUFS）
    crossfade_ms: int = 0  # 交叉淡入淡出时长
    silence_threshold_db: float = -50.0  # 静音阈值


class AudioAssembler:
    """
    音频拼接器
    
    支持多角色音频拼接、音量统一、无缝过渡。
    """

    def __init__(self, config: Optional[AssemblyConfig] = None):
        self.config = config or AssemblyConfig()
        self._segments: List[AudioSegment] = []
        self._ffmpeg_available = False

    async def initialize(self) -> bool:
        """检查并初始化依赖"""
        try:
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._ffmpeg_available = result.returncode == 0
            return self._ffmpeg_available
        except Exception:
            self._ffmpeg_available = False
            return False

    def add_segment(
        self,
        path: Union[str, Path],
        role: AudioRole = AudioRole.NARRATOR,
        fade_in_ms: int = 0,
        fade_out_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "AudioAssembler":
        """
        添加音频片段
        
        Args:
            path: 音频文件路径
            role: 音频角色
            fade_in_ms: 淡入时长
            fade_out_ms: 淡出时长
            metadata: 额外元数据
            
        Returns:
            self for chaining
        """
        segment = AudioSegment(
            path=Path(path),
            role=role,
            fade_in_ms=fade_in_ms,
            fade_out_ms=fade_out_ms,
            metadata=metadata or {}
        )
        self._segments.append(segment)
        return self

    def add_segments(self, segments: List[AudioSegment]) -> "AudioAssembler":
        """批量添加音频片段"""
        self._segments.extend(segments)
        return self

    def clear_segments(self) -> "AudioAssembler":
        """清空所有片段"""
        self._segments.clear()
        return self

    async def assemble(
        self,
        output_path: Union[str, Path],
        config: Optional[AssemblyConfig] = None
    ) -> Optional[Path]:
        """
        拼接所有音频片段
        
        Args:
            output_path: 输出文件路径
            config: 可选的拼接配置
            
        Returns:
            输出文件路径或 None（失败）
        """
        if not self._segments:
            return None

        config = config or self.config
        
        if not self._ffmpeg_available:
            await self.initialize()
            if not self._ffmpeg_available:
                raise RuntimeError("FFmpeg is required for audio assembly")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 1. 分析所有音频片段
            await self._analyze_segments()
            
            # 2. 统一音量
            if config.normalize_volume:
                await self._normalize_volumes(config.target_volume_db)
            
            # 3. 生成拼接脚本
            filter_complex, inputs = self._build_filter_complex(config)
            
            # 4. 执行 FFmpeg 拼接
            await self._run_ffmpeg(inputs, filter_complex, output_path, config)
            
            return output_path
            
        except Exception as e:
            print(f"Audio assembly failed: {e}")
            return None

    async def assemble_dialogue(
        self,
        host_segments: List[Union[str, Path, AudioSegment]],
        guest_segments: List[Union[str, Path, AudioSegment]],
        output_path: Union[str, Path],
        host_name: str = "主持人",
        guest_name: str = "嘉宾",
        config: Optional[AssemblyConfig] = None
    ) -> Optional[Path]:
        """
        拼接双人对话音频
        
        自动交替主持人和嘉宾的音频片段，创建自然的对话流程。
        
        Args:
            host_segments: 主持人音频片段列表
            guest_segments: 嘉宾音频片段列表
            output_path: 输出文件路径
            host_name: 主持人名称（用于元数据）
            guest_name: 嘉宾名称（用于元数据）
            config: 拼接配置
            
        Returns:
            输出文件路径或 None
        """
        self.clear_segments()
        
        # 交替添加主持人和嘉宾片段
        max_len = max(len(host_segments), len(guest_segments))
        
        for i in range(max_len):
            if i < len(host_segments):
                seg = host_segments[i]
                if isinstance(seg, (str, Path)):
                    self.add_segment(seg, AudioRole.HOST, metadata={"speaker": host_name})
                else:
                    self._segments.append(seg)
            
            if i < len(guest_segments):
                seg = guest_segments[i]
                if isinstance(seg, (str, Path)):
                    self.add_segment(seg, AudioRole.GUEST, metadata={"speaker": guest_name})
                else:
                    self._segments.append(seg)
        
        return await self.assemble(output_path, config)

    async def _analyze_segments(self):
        """分析所有音频片段的时长和音量"""
        import subprocess
        
        for segment in self._segments:
            if not segment.path.exists():
                raise FileNotFoundError(f"Audio file not found: {segment.path}")
            
            # 使用 ffprobe 获取音频信息
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(segment.path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # 获取时长
                if "format" in data:
                    duration_sec = float(data["format"].get("duration", 0))
                    segment.duration_ms = int(duration_sec * 1000)
                
                # 获取音量信息
                if "streams" in data:
                    for stream in data["streams"]:
                        if stream.get("codec_type") == "audio":
                            # 可以提取音量信息用于后续处理
                            pass

    async def _normalize_volumes(self, target_db: float):
        """统一所有片段的音量"""
        import subprocess
        import tempfile
        
        for segment in self._segments:
            # 使用 FFmpeg loudnorm 滤镜统一音量
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            cmd = [
                "ffmpeg",
                "-y",
                "-i", str(segment.path),
                "-af", f"loudnorm=I={target_db}:TP=-1.5:LRA=11",
                "-ar", str(self.config.sample_rate),
                str(temp_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if result.returncode == 0:
                # 保留原始文件，仅更新路径引用用于拼接
                segment.path = temp_path
            else:
                temp_path.unlink(missing_ok=True)

    def _build_filter_complex(self, config: AssemblyConfig) -> Tuple[str, List[str]]:
        """构建 FFmpeg filter_complex 参数"""
        inputs = []
        filters = []
        
        for i, segment in enumerate(self._segments):
            inputs.append(str(segment.path))
            
            # 应用淡入淡出
            filter_parts = []
            
            if segment.fade_in_ms > 0:
                fade_in_sec = segment.fade_in_ms / 1000.0
                filter_parts.append(f"afade=t=in:st=0:d={fade_in_sec}")
            
            if segment.fade_out_ms > 0 and segment.duration_ms > segment.fade_out_ms:
                fade_out_start = (segment.duration_ms - segment.fade_out_ms) / 1000.0
                fade_out_sec = segment.fade_out_ms / 1000.0
                filter_parts.append(f"afade=t=out:st={fade_out_start}:d={fade_out_sec}")
            
            if filter_parts:
                filters.append(f"[{i}:a]{''.join(filter_parts)}[a{i}]")
            else:
                filters.append(f"[{i}:a]anull[a{i}]")
        
        # 连接所有片段
        concat_inputs = "".join([f"[a{i}]" for i in range(len(self._segments))])
        
        if config.gap_between_segments_ms > 0:
            # 添加间隔静音
            gap_sec = config.gap_between_segments_ms / 1000.0
            # 这里简化处理，实际需要在每个片段后添加静音
            filters.append(f"{concat_inputs}concat=n={len(self._segments)}:v=0:a=1[out]")
        else:
            filters.append(f"{concat_inputs}concat=n={len(self._segments)}:v=0:a=1[out]")
        
        filter_complex = ";".join(filters)
        
        return filter_complex, inputs

    async def _run_ffmpeg(
        self,
        inputs: List[str],
        filter_complex: str,
        output_path: Path,
        config: AssemblyConfig
    ):
        """执行 FFmpeg 拼接命令"""
        import subprocess
        
        cmd = ["ffmpeg", "-y"]
        
        # 添加输入文件
        for input_file in inputs:
            cmd.extend(["-i", input_file])
        
        # 添加滤镜
        cmd.extend(["-filter_complex", filter_complex])
        
        # 输出参数
        cmd.extend([
            "-map", "[out]",
            "-ar", str(config.sample_rate),
            "-b:a", config.bitrate,
        ])
        
        if config.channels == 1:
            cmd.extend(["-ac", "1"])
        elif config.channels == 2:
            cmd.extend(["-ac", "2"])
        
        # 输出格式
        if config.output_format.lower() == "mp3":
            cmd.extend(["-f", "mp3"])
        
        cmd.append(str(output_path))
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

    async def crossfade_segments(
        self,
        segment1: Union[str, Path],
        segment2: Union[str, Path],
        output_path: Union[str, Path],
        crossfade_ms: int = 2000
    ) -> Optional[Path]:
        """
        交叉淡入淡出两个音频片段
        
        Args:
            segment1: 第一个音频片段
            segment2: 第二个音频片段
            output_path: 输出路径
            crossfade_ms: 交叉淡入淡出时长
            
        Returns:
            输出文件路径或 None
        """
        if not self._ffmpeg_available:
            await self.initialize()
            if not self._ffmpeg_available:
                return None

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        crossfade_sec = crossfade_ms / 1000.0
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(segment1),
            "-i", str(segment2),
            "-filter_complex",
            f"[0:a][1:a]crossfade=d={crossfade_sec}:c1=tri:c2=tri[aout]",
            "-map", "[aout]",
            "-ar", str(self.config.sample_rate),
            "-b:a", self.config.bitrate,
            str(output_path)
        ]
        
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return output_path
        else:
            print(f"Crossfade failed: {result.stderr}")
            return None

    def get_total_duration_ms(self) -> int:
        """获取所有片段的总时长（毫秒）"""
        return sum(seg.duration_ms for seg in self._segments)

    def get_segment_count(self) -> int:
        """获取片段数量"""
        return len(self._segments)

    def get_segments_by_role(self, role: AudioRole) -> List[AudioSegment]:
        """按角色获取片段"""
        return [seg for seg in self._segments if seg.role == role]
