#!/usr/bin/env python3
"""
音频调速处理器

使用 FFmpeg atempo 滤镜调整音频播放速度。
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class AudioSpeedProcessor:
    """
    音频调速处理器
    
    使用 FFmpeg atempo 滤镜调整音频播放速度。
    支持 0.5x - 2.0x 的速度调整。
    """
    
    # 最小和最大速度限制
    MIN_SPEED = 0.5
    MAX_SPEED = 2.0
    
    def __init__(self):
        """初始化音频调速处理器"""
        self._ffmpeg_available = False
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否可用"""
        try:
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
    
    @staticmethod
    def validate_speed(speed: float) -> bool:
        """
        验证速度值是否在有效范围内
        
        Args:
            speed: 速度值
            
        Returns:
            是否有效
        """
        return AudioSpeedProcessor.MIN_SPEED <= speed <= AudioSpeedProcessor.MAX_SPEED
    
    @staticmethod
    def normalize_speed(speed: float) -> float:
        """
        规范化速度值
        
        如果速度超出范围，将其限制在有效范围内。
        
        Args:
            speed: 原始速度值
            
        Returns:
            规范化后的速度值
        """
        if speed < AudioSpeedProcessor.MIN_SPEED:
            return AudioSpeedProcessor.MIN_SPEED
        if speed > AudioSpeedProcessor.MAX_SPEED:
            return AudioSpeedProcessor.MAX_SPEED
        return speed
    
    async def adjust_speed(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        speed: float = 1.0
    ) -> Optional[str]:
        """
        调整音频播放速度
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径（可选，默认覆盖原文件）
            speed: 播放速度 (0.5-2.0)
            
        Returns:
            输出文件路径，失败返回 None
        """
        # 验证 FFmpeg 可用性
        if not self._ffmpeg_available:
            if not self._check_ffmpeg():
                raise RuntimeError("FFmpeg 不可用，无法调整音频速度")
        
        # 验证速度值
        if not self.validate_speed(speed):
            raise ValueError(f"速度值 {speed} 超出有效范围 ({self.MIN_SPEED}-{self.MAX_SPEED})")
        
        # 1.0 速度不需要处理
        if speed == 1.0:
            return input_path
        
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        # 确定输出路径
        if output_path is None:
            # 使用临时文件
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False
            )
            output_path = temp_file.name
            temp_file.close()
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用 FFmpeg atempo 滤镜调整速度
        # 注意：atempo 滤镜支持 0.5-2.0 的速度范围
        # 如果需要更大范围的速度调整，需要链多个 atempo
        cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-i", str(input_path),
            "-af", f"atempo={speed}",
            "-ar", "44100",  # 重采样到 44.1kHz
            "-b:a", "192k",  # 比特率
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg 执行失败: {result.stderr}")
            
            return str(output_path)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("音频调速超时")
        except Exception:
            # 清理临时文件
            if output_path and Path(output_path).exists():
                Path(output_path).unlink(missing_ok=True)
            raise
    
    async def adjust_speed_chain(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        speed: float = 1.0
    ) -> Optional[str]:
        """
        使用链式 atempo 调整音频速度
        
        当速度超出 atempo 滤镜的单次限制范围时，使用多个 atempo 滤镜链。
        atempo 滤镜支持 0.5-2.0 的速度范围。
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径
            speed: 播放速度
            
        Returns:
            输出文件路径
        """
        if not self._ffmpeg_available:
            if not self._check_ffmpeg():
                raise RuntimeError("FFmpeg 不可用，无法调整音频速度")
        
        # 1.0 速度不需要处理
        if speed == 1.0:
            return input_path
        
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        # 确定输出路径
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False
            )
            output_path = temp_file.name
            temp_file.close()
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 构建 atempo 滤镜链
        # atempo 每次只能处理 0.5-2.0 范围
        # 如果 speed > 2.0 或 speed < 0.5，需要链多个 atempo
        atempo_parts = []
        remaining_speed = speed
        
        while remaining_speed > 2.0:
            atempo_parts.append("2.0")
            remaining_speed /= 2.0
        while remaining_speed < 0.5:
            atempo_parts.append("0.5")
            remaining_speed /= 0.5
        
        if remaining_speed != 1.0:
            atempo_parts.append(str(remaining_speed))
        
        filter_chain = ",".join([f"atempo={p}" for p in atempo_parts])
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-af", filter_chain,
            "-ar", "44100",
            "-b:a", "192k",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg 执行失败: {result.stderr}")
            
            return str(output_path)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("音频调速超时")
        except Exception:
            if output_path and Path(output_path).exists():
                Path(output_path).unlink(missing_ok=True)
            raise


# 便捷函数
async def adjust_audio_speed(
    input_path: str,
    output_path: Optional[str] = None,
    speed: float = 1.0
) -> Optional[str]:
    """
    便捷函数：调整音频播放速度
    
    Args:
        input_path: 输入音频文件路径
        output_path: 输出音频文件路径
        speed: 播放速度 (0.5-2.0)
        
    Returns:
        输出文件路径
    """
    processor = AudioSpeedProcessor()
    return await processor.adjust_speed(input_path, output_path, speed)


if __name__ == "__main__":
    import asyncio
    
    # 测试
    async def test():
        processor = AudioSpeedProcessor()
        
        # 测试速度验证
        print("测试速度验证:")
        print(f"  0.5 有效: {processor.validate_speed(0.5)}")
        print(f"  1.0 有效: {processor.validate_speed(1.0)}")
        print(f"  2.0 有效: {processor.validate_speed(2.0)}")
        print(f"  0.3 无效: {processor.validate_speed(0.3)}")
        print(f"  2.5 无效: {processor.validate_speed(2.5)}")
        
        # 测试规范化
        print("\n测试速度规范化:")
        print(f"  0.3 -> {processor.normalize_speed(0.3)}")
        print(f"  2.5 -> {processor.normalize_speed(2.5)}")
        print(f"  1.5 -> {processor.normalize_speed(1.5)}")
        
        print("\nFFmpeg 可用:", processor._ffmpeg_available)
    
    asyncio.run(test())
