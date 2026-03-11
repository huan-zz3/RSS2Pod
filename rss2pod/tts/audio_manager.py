"""
音频管理模块

负责音频文件的生命周期管理：保留策略、清理流程、存储优化。
"""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Union
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib
import os
import shutil


class CleanupStrategy(str, Enum):
    """清理策略"""
    AGE_BASED = "age_based"  # 基于时间
    COUNT_BASED = "count_based"  # 基于数量
    SIZE_BASED = "size_based"  # 基于大小
    CUSTOM = "custom"  # 自定义规则


@dataclass
class AudioCleanupPolicy:
    """音频清理策略"""
    strategy: CleanupStrategy = CleanupStrategy.AGE_BASED
    max_age_days: int = 30  # 最大保留天数
    max_count: int = 100  # 最大保留数量
    max_size_mb: float = 1000.0  # 最大总大小（MB）
    keep_recent_count: int = 10  # 始终保留最近 N 个文件
    min_age_days: int = 1  # 最小保留天数（防止误删）
    dry_run: bool = False  # 仅预览，不实际删除
    verbose: bool = True  # 详细日志
    
    # 按目录的自定义策略
    directory_policies: Dict[str, "AudioCleanupPolicy"] = field(default_factory=dict)
    
    # 文件模式排除（不会被清理）
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "*.final.*",
        "*published*",
        "*archive*"
    ])


@dataclass
class AudioFileInfo:
    """音频文件信息"""
    path: Path
    size_bytes: int
    created_at: datetime
    modified_at: datetime
    accessed_at: datetime
    duration_ms: int = 0
    format: str = ""
    sample_rate: int = 0
    channels: int = 0
    bitrate: str = ""
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def age_days(self) -> int:
        return (datetime.now() - self.created_at).days

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": str(self.path),
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_mb, 2),
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "age_days": self.age_days,
            "duration_ms": self.duration_ms,
            "format": self.format,
            "checksum": self.checksum
        }


class AudioManager:
    """
    音频文件管理器
    
    提供音频文件的存储、检索、清理和统计功能。
    """

    def __init__(
        self,
        base_directory: Union[str, Path],
        policy: Optional[AudioCleanupPolicy] = None
    ):
        self.base_directory = Path(base_directory)
        self.policy = policy or AudioCleanupPolicy()
        self._file_cache: Dict[str, AudioFileInfo] = {}
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化音频管理器"""
        self.base_directory.mkdir(parents=True, exist_ok=True)
        await self.scan_directory()

    async def scan_directory(self, recursive: bool = True) -> int:
        """
        扫描目录中的所有音频文件
        
        Args:
            recursive: 是否递归扫描子目录
            
        Returns:
            扫描到的文件数量
        """
        self._file_cache.clear()
        
        patterns = ["*.mp3", "*.wav", "*.m4a", "*.aac", "*.ogg", "*.flac"]
        count = 0
        
        for pattern in patterns:
            if recursive:
                files = self.base_directory.rglob(pattern)
            else:
                files = self.base_directory.glob(pattern)
            
            for file_path in files:
                if file_path.is_file():
                    info = await self.get_file_info(file_path)
                    if info:
                        self._file_cache[str(file_path)] = info
                        count += 1
        
        return count

    async def get_file_info(self, file_path: Union[str, Path]) -> Optional[AudioFileInfo]:
        """获取音频文件详细信息"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return None
        
        try:
            stat = file_path.stat()
            
            info = AudioFileInfo(
                path=file_path,
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                accessed_at=datetime.fromtimestamp(stat.st_atime),
            )
            
            # 获取音频元数据
            await self._extract_audio_metadata(info)
            
            # 计算校验和
            info.checksum = await self._calculate_checksum(file_path)
            
            return info
            
        except Exception as e:
            print(f"Error getting file info for {file_path}: {e}")
            return None

    async def _extract_audio_metadata(self, info: AudioFileInfo):
        """提取音频元数据"""
        try:
            import subprocess
            
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(info.path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                if "format" in data:
                    fmt = data["format"]
                    info.format = fmt.get("format_name", "")
                    info.duration_ms = int(float(fmt.get("duration", 0)) * 1000)
                    info.bitrate = fmt.get("bit_rate", "")
                
                if "streams" in data:
                    for stream in data["streams"]:
                        if stream.get("codec_type") == "audio":
                            info.sample_rate = int(stream.get("sample_rate", 0))
                            info.channels = int(stream.get("channels", 0))
                            break
                            
        except Exception:
            pass  # 静默失败，使用默认值

    async def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件 MD5 校验和"""
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    async def cleanup(self, policy: Optional[AudioCleanupPolicy] = None) -> Dict[str, Any]:
        """
        执行清理操作
        
        Args:
            policy: 可选的清理策略，不指定则使用默认策略
            
        Returns:
            清理结果统计
        """
        policy = policy or self.policy
        
        async with self._lock:
            # 重新扫描获取最新状态
            await self.scan_directory()
            
            # 获取待清理文件列表
            files_to_delete = await self._identify_files_to_delete(policy)
            
            # 执行清理
            deleted_count = 0
            deleted_size = 0
            errors = []
            
            for file_info in files_to_delete:
                if policy.dry_run:
                    if policy.verbose:
                        print(f"[DRY RUN] Would delete: {file_info.path}")
                    deleted_count += 1
                    deleted_size += file_info.size_bytes
                else:
                    try:
                        file_info.path.unlink()
                        deleted_count += 1
                        deleted_size += file_info.size_bytes
                        
                        # 从缓存移除
                        self._file_cache.pop(str(file_info.path), None)
                        
                        if policy.verbose:
                            print(f"Deleted: {file_info.path} ({file_info.size_mb:.2f} MB)")
                    except Exception as e:
                        errors.append(str(e))
                        if policy.verbose:
                            print(f"Error deleting {file_info.path}: {e}")
            
            # 清理空目录
            if not policy.dry_run:
                await self._remove_empty_directories()
            
            return {
                "deleted_count": deleted_count,
                "deleted_size_bytes": deleted_size,
                "deleted_size_mb": round(deleted_size / (1024 * 1024), 2),
                "errors": errors,
                "dry_run": policy.dry_run,
                "strategy": policy.strategy.value
            }

    async def _identify_files_to_delete(self, policy: AudioCleanupPolicy) -> List[AudioFileInfo]:
        """识别需要删除的文件"""
        candidates = list(self._file_cache.values())
        
        # 排除受保护的文件
        candidates = [
            f for f in candidates
            if not self._is_protected(f, policy)
        ]
        
        # 保留最近的文件
        if policy.keep_recent_count > 0:
            sorted_by_date = sorted(
                candidates,
                key=lambda x: x.modified_at,
                reverse=True
            )
            protected_recent = set(str(f.path) for f in sorted_by_date[:policy.keep_recent_count])
            candidates = [f for f in candidates if str(f.path) not in protected_recent]
        
        # 应用清理策略
        files_to_delete = []
        
        if policy.strategy == CleanupStrategy.AGE_BASED:
            files_to_delete = [
                f for f in candidates
                if f.age_days > policy.max_age_days and f.age_days >= policy.min_age_days
            ]
        
        elif policy.strategy == CleanupStrategy.COUNT_BASED:
            sorted_by_date = sorted(
                candidates,
                key=lambda x: x.modified_at,
                reverse=True
            )
            files_to_delete = sorted_by_date[policy.max_count:]
        
        elif policy.strategy == CleanupStrategy.SIZE_BASED:
            total_size = sum(f.size_bytes for f in candidates)
            max_size_bytes = policy.max_size_mb * 1024 * 1024
            
            if total_size > max_size_bytes:
                # 按年龄排序，删除最老的文件直到满足大小限制
                sorted_by_age = sorted(candidates, key=lambda x: x.age_days, reverse=True)
                current_size = total_size
                
                for f in sorted_by_age:
                    if current_size <= max_size_bytes:
                        break
                    files_to_delete.append(f)
                    current_size -= f.size_bytes
        
        return files_to_delete

    def _is_protected(self, file_info: AudioFileInfo, policy: AudioCleanupPolicy) -> bool:
        """检查文件是否受保护"""
        import fnmatch
        
        for pattern in policy.exclude_patterns:
            if fnmatch.fnmatch(file_info.path.name, pattern):
                return True
        
        # 检查目录特定策略
        for dir_pattern, dir_policy in policy.directory_policies.items():
            if dir_pattern in str(file_info.path):
                # 应用目录特定的保护规则
                if file_info.age_days < dir_policy.min_age_days:
                    return True
        
        return False

    async def _remove_empty_directories(self):
        """删除空目录"""
        for dirpath, dirnames, filenames in os.walk(str(self.base_directory), topdown=False):
            dir_path = Path(dirpath)
            if dir_path != self.base_directory:
                try:
                    if not any(dir_path.iterdir()):
                        dir_path.rmdir()
                except Exception:
                    pass

    async def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        await self.scan_directory()
        
        if not self._file_cache:
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "oldest_file": None,
                "newest_file": None,
                "average_duration_ms": 0,
                "by_format": {}
            }
        
        files = list(self._file_cache.values())
        total_size = sum(f.size_bytes for f in files)
        total_duration = sum(f.duration_ms for f in files)
        
        # 按格式统计
        format_stats = {}
        for f in files:
            fmt = f.format or "unknown"
            if fmt not in format_stats:
                format_stats[fmt] = {"count": 0, "size_bytes": 0}
            format_stats[fmt]["count"] += 1
            format_stats[fmt]["size_bytes"] += f.size_bytes
        
        # 转换为 MB
        for fmt in format_stats:
            format_stats[fmt]["size_mb"] = round(format_stats[fmt]["size_bytes"] / (1024 * 1024), 2)
        
        sorted_by_date = sorted(files, key=lambda x: x.modified_at)
        
        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file": sorted_by_date[0].to_dict() if sorted_by_date else None,
            "newest_file": sorted_by_date[-1].to_dict() if sorted_by_date else None,
            "average_duration_ms": int(total_duration / len(files)) if files else 0,
            "total_duration_hours": round(total_duration / (1000 * 3600), 2),
            "by_format": format_stats
        }

    async def find_duplicates(self) -> Dict[str, List[Path]]:
        """查找重复的音频文件（基于校验和）"""
        await self.scan_directory()
        
        checksum_map: Dict[str, List[Path]] = {}
        
        for file_info in self._file_cache.values():
            if file_info.checksum:
                if file_info.checksum not in checksum_map:
                    checksum_map[file_info.checksum] = []
                checksum_map[file_info.checksum].append(file_info.path)
        
        # 只返回有重复的文件
        duplicates = {
            checksum: paths
            for checksum, paths in checksum_map.items()
            if len(paths) > 1
        }
        
        return duplicates

    async def move_to_archive(
        self,
        file_paths: List[Union[str, Path]],
        archive_directory: Optional[Union[str, Path]] = None
    ) -> List[Path]:
        """
        移动文件到归档目录
        
        Args:
            file_paths: 要归档的文件路径列表
            archive_directory: 归档目录，不指定则使用 base_directory/archive
            
        Returns:
            归档后的文件路径列表
        """
        if archive_directory is None:
            archive_directory = self.base_directory / "archive"
        
        archive_dir = Path(archive_directory)
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        archived_paths = []
        
        for file_path in file_paths:
            file_path = Path(file_path)
            if not file_path.exists():
                continue
            
            try:
                dest_path = archive_dir / file_path.name
                
                # 如果目标已存在，添加时间戳
                if dest_path.exists():
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    dest_path = archive_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
                
                shutil.move(str(file_path), str(dest_path))
                archived_paths.append(dest_path)
                
                # 从缓存移除
                self._file_cache.pop(str(file_path), None)
                
            except Exception as e:
                print(f"Error archiving {file_path}: {e}")
        
        return archived_paths

    async def delete_file(self, file_path: Union[str, Path], force: bool = False) -> bool:
        """
        删除单个文件
        
        Args:
            file_path: 文件路径
            force: 是否强制删除（忽略保护规则）
            
        Returns:
            是否成功删除
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False
        
        # 检查保护规则
        if not force:
            file_info = await self.get_file_info(file_path)
            if file_info and self._is_protected(file_info, self.policy):
                print(f"Cannot delete protected file: {file_path}")
                return False
        
        try:
            file_path.unlink()
            self._file_cache.pop(str(file_path), None)
            return True
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
            return False

    async def get_recent_files(self, count: int = 10) -> List[AudioFileInfo]:
        """获取最近的文件"""
        await self.scan_directory()
        
        sorted_files = sorted(
            self._file_cache.values(),
            key=lambda x: x.modified_at,
            reverse=True
        )
        
        return sorted_files[:count]

    async def get_files_by_age(
        self,
        min_age_days: int = 0,
        max_age_days: Optional[int] = None
    ) -> List[AudioFileInfo]:
        """按年龄获取文件"""
        await self.scan_directory()
        
        files = self._file_cache.values()
        
        if max_age_days is not None:
            return [f for f in files if min_age_days <= f.age_days <= max_age_days]
        else:
            return [f for f in files if f.age_days >= min_age_days]

    async def export_inventory(self, output_path: Union[str, Path]) -> Path:
        """导出文件清单到 JSON"""
        await self.scan_directory()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        inventory = {
            "exported_at": datetime.now().isoformat(),
            "base_directory": str(self.base_directory),
            "total_files": len(self._file_cache),
            "files": [info.to_dict() for info in self._file_cache.values()]
        }
        
        output_path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False))
        
        return output_path

    def get_cache_size(self) -> int:
        """获取缓存中的文件数量"""
        return len(self._file_cache)
