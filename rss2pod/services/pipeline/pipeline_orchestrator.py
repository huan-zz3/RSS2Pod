"""
Pipeline Orchestrator - 管道编排器

负责编排完整的内容处理流程：
1. 获取文章
2. 生成源级摘要
3. 生成组级摘要
4. 生成播客脚本
5. TTS 音频合成
6. 保存 Episode
"""

import os
import sys
import asyncio
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.models import DatabaseManager, Group, Article, SourceSummary as DBSourceSummary
from ..llm_service import LLMService
from ..tts_service import TTSService
from ..fever_service import FeverService
from ..database_service import DatabaseService
from ..asset_service import AssetService
from rss2pod.orchestrator.state_manager import ProcessingState, StateManager
from llm.prompt_manager import get_prompt_manager, PromptManager
from tts.adapter import get_adapter_from_tts_config
from tts.audio_speed import AudioSpeedProcessor
from .models import (
    FetchResult, SummaryResult, GroupSummaryResult, ScriptResult,
    TTSResult, EpisodeResult, PipelineResult
)


class PipelineOrchestrator:
    """
    处理管道编排器
    
    负责编排完整的内容处理流程：
    1. 获取文章
    2. 生成源级摘要
    3. 生成组级摘要
    4. 生成播客脚本
    5. TTS 音频合成
    6. 保存 Episode
    """
    
    def __init__(
        self,
        group: Group,
        state: ProcessingState,
        db: DatabaseManager,
        db_path: str,
        logger: logging.Logger,
        config: Any,
        force: bool = False,
        export_articles: bool = False,
        state_manager: StateManager = None
    ):
        """
        初始化管道编排器
        
        Args:
            group: Group 实例
            state: ProcessingState 实例
            db: DatabaseManager 实例
            db_path: 数据库路径（用于 FeverClient 缓存）
            logger: Logger 实例
            config: 配置对象
            force: 强制模式，忽略文章更新检查，使用最新三篇文章
            export_articles: 导出文章列表到 JSON 文件
            state_manager: StateManager 实例（用于持久化状态）
        """
        self.group = group
        self.state = state
        self.db = db
        self.db_path = db_path
        self.logger = logger
        self.config = config
        self.force = force
        self.export_articles = export_articles
        self.state_manager = state_manager
        
        # 重试配置
        self.max_retries = config.retry_attempts if hasattr(config, 'retry_attempts') else 3
        self.retry_delay = config.retry_delay_seconds if hasattr(config, 'retry_delay_seconds') else 3
        
        # 初始化服务
        self.llm_service = LLMService()
        self.tts_service = TTSService()
        self.asset_service = AssetService()
        
        # 初始化 Prompt Manager
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config.json'
        )
        self.prompt_manager = get_prompt_manager(config_path)
    
    async def _retry_on_failure(
        self,
        func,
        *args,
        max_retries: int = None,
        delay: int = None,
        stage: str = "unknown"
    ):
        """失败重试包装器"""
        max_retries = max_retries or self.max_retries
        delay = delay or self.retry_delay
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await func(*args)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    self.logger.warning(
                        f"[{stage}] 执行失败，{delay}秒后重试 ({attempt + 1}/{max_retries}): {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"[{stage}] 执行失败，已达最大重试次数：{e}")
        
        raise last_error
    
    async def run(self) -> PipelineResult:
        """运行完整处理管道"""
        stages_completed = []
        result = PipelineResult(
            success=False,
            group_id=self.group.id
        )
        
        original_cursor = self.state.last_fetch_cursor
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # 创建资源管理器
        asset_manager = self.asset_service.get_episode_manager(self.group.id, timestamp)
        asset_manager.initialize()
        self.logger.info(f"[assets] 资源目录已创建：{asset_manager.assets_dir}")
        
        try:
            # 阶段 1：获取文章
            self.logger.info(f"[fetch] 开始获取文章，Group: {self.group.id}")
            fetch_result = await self._retry_on_failure(
                self._fetch_articles,
                stage="fetch"
            )
            if not fetch_result.success:
                raise Exception(f"获取文章失败：{fetch_result.error_message}")
            
            if not fetch_result.articles:
                self.logger.info(f"[fetch] 没有新文章，跳过处理")
                result.success = True
                result.stages_completed = ["fetch_skipped"]
                return result
            
            result.articles_fetched = len(fetch_result.articles)
            stages_completed.append("fetch")
            self.logger.info(f"[fetch] 获取到 {len(fetch_result.articles)} 篇文章")
            
            # 阶段 2：生成源级摘要
            self.logger.info(f"[summarize] 开始生成源级摘要")
            summary_result = await self._retry_on_failure(
                lambda: self._generate_source_summaries(fetch_result.articles),
                stage="summarize"
            )
            if not summary_result.success:
                raise Exception(f"生成源级摘要失败：{summary_result.error_message}")
            
            if not summary_result.summaries:
                raise Exception("[summarize] 生成了 0 个源级摘要，无法继续处理。")
            
            source_summaries_path = asset_manager.save_source_summaries(summary_result.summaries)
            stages_completed.append("summarize")
            self.logger.info(f"[summarize] 生成 {len(summary_result.summaries)} 个源级摘要")
            self.logger.info(f"[summarize] ✓ 源级摘要已保存: {source_summaries_path}")
            
            # 阶段 3：生成组级摘要
            self.logger.info(f"[aggregate] 开始生成组级摘要")
            group_summary_result = await self._retry_on_failure(
                lambda: self._generate_group_summary(summary_result.summaries),
                stage="aggregate"
            )
            if not group_summary_result.success:
                raise Exception(f"生成组级摘要失败：{group_summary_result.error_message}")
            
            if not group_summary_result.summary:
                raise Exception("[aggregate] 组级摘要为空，无法继续处理。")
            
            group_summary_path = asset_manager.save_group_summary(group_summary_result.summary)
            stages_completed.append("aggregate")
            self.logger.info(f"[aggregate] 组级摘要生成完成")
            self.logger.info(f"[aggregate] ✓ 组级摘要已保存: {group_summary_path}")
            
            # 阶段 4：生成播客脚本
            self.logger.info(f"[script] 开始生成播客脚本")
            script_result = await self._retry_on_failure(
                lambda: self._generate_script(group_summary_result.summary),
                stage="script"
            )
            if not script_result.success:
                raise Exception(f"生成播客脚本失败：{script_result.error_message}")
            
            if not script_result.script or not script_result.script.get('segments'):
                raise Exception("[script] 播客脚本为空或无段落，无法继续处理。")
            
            if not script_result.moss_input:
                raise Exception("[script] MOSS 格式输入为空，无法进行 TTS 合成。")
            
            # 获取当前 TTS 适配器名称
            adapter_config = self.tts_service._get_active_adapter_config()
            adapter_name = adapter_config.get('adapter_name', 'moss') if isinstance(adapter_config, dict) else 'moss'
            
            # 使用动态文件名保存 TTS 输入
            tts_input_path = asset_manager.get_tts_input_path(adapter_name)
            podcast_script_path = asset_manager.save_podcast_script(script_result.script, script_result.moss_input, tts_input_path)
            stages_completed.append("script")
            self.logger.info(f"[script] 播客脚本生成完成，共 {len(script_result.script.get('segments', []))} 个段落")
            self.logger.info(f"[script] ✓ 播客脚本已保存: {podcast_script_path}")
            self.logger.info(f"[script] ✓ {adapter_name.upper()} TTS 输入已保存: {tts_input_path}")
            
            # 阶段 5：TTS 音频合成
            self.logger.info(f"[tts] 开始 TTS 音频合成")
            tts_result = await self._retry_on_failure(
                lambda: self._synthesize_audio(script_result, asset_manager, timestamp),
                stage="tts"
            )
            if not tts_result.success:
                raise Exception(f"TTS 音频合成失败：{tts_result.error_message}")
            
            if not tts_result.audio_path or not os.path.exists(tts_result.audio_path):
                raise Exception(f"[tts] 音频文件不存在：{tts_result.audio_path}")
            
            audio_size = os.path.getsize(tts_result.audio_path)
            if audio_size == 0:
                raise Exception("[tts] 音频文件大小为 0，TTS 合成可能失败。")
            
            stages_completed.append("tts")
            result.audio_path = tts_result.audio_path
            result.audio_duration = tts_result.audio_duration
            self.logger.info(f"[tts] 音频合成完成：{tts_result.audio_path} ({audio_size} 字节)")
            
            # 阶段 6：保存 Episode
            self.logger.info(f"[save] 开始保存 Episode")
            episode_result = await self._retry_on_failure(
                lambda: self._save_episode(tts_result, script_result, summary_result),
                stage="save"
            )
            if not episode_result.success:
                raise Exception(f"保存 Episode 失败：{episode_result.error_message}")
            
            if not episode_result.episode_id:
                raise Exception("[save] Episode ID 为空，无法继续处理。")
            
            stages_completed.append("save")
            result.episode_id = episode_result.episode_id
            self.logger.info(f"[save] Episode 保存完成：{episode_result.episode_id}")
            
            # 阶段 7：更新 RSS Feed
            self.logger.info(f"[feed] 开始更新 RSS Feed")
            feed_result = await self._retry_on_failure(
                lambda: self._update_feed(episode_result, tts_result),
                stage="feed"
            )
            if feed_result.get('success'):
                stages_completed.append("feed")
                self.logger.info(f"[feed] RSS Feed 更新完成")
            
            # 更新文章状态
            await self._update_article_status(fetch_result.articles)
            
            # 更新 cursor
            if fetch_result.fetch_cursor and fetch_result.fetch_cursor != original_cursor:
                self.state.last_fetch_cursor = fetch_result.fetch_cursor
                self.logger.info(f"[fetch] ✓ 管道成功完成，更新 cursor: {original_cursor} -> {fetch_result.fetch_cursor}")
            
            result.success = True
            result.stages_completed = stages_completed
            result.metadata = {
                'assets_dir': str(asset_manager.assets_dir),
                'timestamp': timestamp,
            }
            
        except Exception as e:
            self.logger.error(f"管道执行失败：{e}")
            result.success = False
            result.error_message = str(e)
            result.failed_stage = stages_completed[-1] if stages_completed else "init"
            result.stages_completed = stages_completed
        
        return result
    
    async def _fetch_articles(self) -> FetchResult:
        """阶段 1：获取文章"""
        from fetcher.fever_client import FeverClient, FeverCredentials
        
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'config.json'
            )
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            fever_config = config.get('fever', {})
            username = fever_config.get('username', '')
            password = fever_config.get('password', '')
            api_key = hashlib.md5(f"{username}:{password}".encode()).hexdigest()
            
            api_url = fever_config.get('url', '').rstrip('/')
            credentials = FeverCredentials(api_url=api_url, api_key=api_key)
            client = FeverClient(credentials, db_path=self.db_path)
            
            rss_sources = self.group.rss_sources or []
            if not rss_sources:
                return FetchResult(success=True, articles=[])
            
            feeds = client.get_feeds()
            feed_map = {}
            for source_url in rss_sources:
                feed_id = self._get_source_id_by_url_from_feeds(source_url, feeds)
                if feed_id:
                    feed_map[source_url] = feed_id
            
            if not feed_map:
                return FetchResult(success=True, articles=[])
            
            target_feed_ids = set(feed_map.values())
            since_id = self.state.last_fetch_cursor
            
            if self.force:
                self.logger.info("[fetch] --force 模式启用")
                since_id = None
            
            fetch_limit = 1500 if since_id is None else 100
            all_items = self._get_items_since(client, since_id, limit=fetch_limit)
            
            filtered_items = [item for item in all_items if item.get('feed_id') in target_feed_ids]
            
            if self.force and len(filtered_items) > 3:
                filtered_items.sort(key=lambda x: int(x.get('created_on_time', 0)), reverse=True)
                filtered_items = filtered_items[:3]
            
            all_articles = []
            for item in filtered_items:
                feed_id = item.get('feed_id')
                source_url = None
                for url, fid in feed_map.items():
                    if fid == feed_id:
                        source_url = url
                        break
                
                if source_url:
                    article = self._convert_item_to_article(item, source_url)
                    if article:
                        all_articles.append(article)
            
            for article in all_articles:
                self.db.add_article(article)
            
            if all_articles and filtered_items:
                max_item_id = max(int(item.get('id', 0)) for item in filtered_items)
                new_cursor = str(max_item_id)
            else:
                new_cursor = since_id
            
            return FetchResult(
                success=True,
                articles=all_articles,
                fetch_cursor=new_cursor
            )
            
        except Exception as e:
            self.logger.error(f"[fetch] 获取文章失败：{e}")
            return FetchResult(success=False, error_message=str(e))
    
    def _get_source_id_by_url_from_feeds(self, url: str, feeds: List[Dict]) -> Optional[int]:
        """根据 URL 从 feeds 列表获取源 ID"""
        if feeds is None:
            return None
        
        # 精确匹配
        for feed in feeds:
            if feed.get('url') == url:
                return int(feed.get('id'))
        
        # 模糊匹配
        import re
        target_parts = set()
        domain_match = re.search(r'://([^/]+)', url)
        if domain_match:
            target_parts.add(domain_match.group(1))
        
        for feed in feeds:
            feed_url = feed.get('url', '')
            feed_domain = re.search(r'://([^/]+)', feed_url)
            if feed_domain and feed_domain.group(1) in target_parts:
                return int(feed.get('id'))
        
        return None
    
    def _get_items_since(self, client, since_id: Optional[str], limit: int) -> List[Dict]:
        """从缓存获取文章"""
        since_id_int = int(since_id) if since_id else None
        items = client.get_items(since_id=since_id_int, limit=limit)
        items.sort(key=lambda x: int(x.get('id', 0)), reverse=True)
        return items
    
    def _convert_item_to_article(self, item: Dict, source_url: str) -> Optional[Article]:
        """将 Fever API item 转换为 Article"""
        try:
            import html
            import re
            
            item_id = str(item.get('id', ''))
            title = item.get('title', 'Untitled')
            link = item.get('url', item.get('link', ''))
            published = datetime.fromtimestamp(int(item.get('created_on_time', 0))).isoformat()
            content = item.get('content', '')
            
            text_content = html.unescape(content)
            text_content = re.sub(r'<[^>]+>', '', text_content)
            
            article_id = f"art-{hashlib.md5(f'{source_url}-{title}'.encode()).hexdigest()[:12]}"
            
            return Article(
                id=article_id,
                title=title,
                source=source_url,
                source_url=source_url,
                link=link,
                published=published,
                content=content,
                text_content=text_content[:10000],
                status='pending'
            )
        except Exception as e:
            self.logger.error(f"转换文章失败：{e}")
            return None
    
    async def _generate_source_summaries(self, articles: List[Article]) -> SummaryResult:
        """阶段 2：生成源级摘要"""
        try:
            articles_by_source: Dict[str, List[Article]] = {}
            for article in articles:
                if article.source not in articles_by_source:
                    articles_by_source[article.source] = []
                articles_by_source[article.source].append(article)
            
            summaries = []
            group_overrides = self.group.prompt_overrides if hasattr(self.group, 'prompt_overrides') else {}
            prompt_template = self.prompt_manager.get_prompt_template(
                "source_summarizer",
                group_id=self.group.id,
                group_overrides=group_overrides
            )
            
            for source, source_articles in articles_by_source.items():
                try:
                    summary = self.llm_service.generate_source_summary(
                        source=source,
                        articles=source_articles,
                        prompt_template=prompt_template
                    )
                    
                    # 验证字段
                    if summary.get('source_name') and summary.get('summary'):
                        summary['source'] = source
                        summaries.append(summary)
                        self._save_source_summary(summary)
                        
                except Exception as e:
                    self.logger.error(f"生成源级摘要失败 ({source}): {e}")
                    continue
            
            if not summaries:
                return SummaryResult(
                    success=False,
                    error_message=f"所有 {len(articles_by_source)} 个源的摘要生成失败"
                )
            
            return SummaryResult(success=True, summaries=summaries)
            
        except Exception as e:
            self.logger.error(f"生成源级摘要失败：{e}")
            return SummaryResult(success=False, error_message=str(e))
    
    def _save_source_summary(self, summary: Dict[str, Any]):
        """保存源级摘要到数据库"""
        summary_str = f"{summary['source']}-{datetime.now().isoformat()}"
        summary_id = f"sum-{hashlib.md5(summary_str.encode()).hexdigest()[:12]}"
        
        db_summary = DBSourceSummary(
            id=summary_id,
            source=summary['source'],
            summary=summary.get('summary', ''),
            article_count=summary.get('article_count', 0),
            key_topics=summary.get('key_topics', []),
            highlights=summary.get('highlights', []),
            group_id=self.group.id
        )
        
        self.db.add_source_summary(db_summary)
    
    async def _generate_group_summary(self, source_summaries: List[Dict]) -> GroupSummaryResult:
        """阶段 3：生成组级摘要"""
        try:
            group_summary = self.llm_service.generate_group_summary(
                source_summaries=source_summaries,
                group_name=self.group.name
            )
            
            return GroupSummaryResult(success=True, summary=group_summary)
            
        except Exception as e:
            self.logger.error(f"生成组级摘要失败：{e}")
            return GroupSummaryResult(success=False, error_message=str(e))
    
    async def _generate_script(self, group_summary: Dict) -> ScriptResult:
        """阶段 4：生成播客脚本"""
        try:
            group_overrides = self.group.prompt_overrides if hasattr(self.group, 'prompt_overrides') else {}
            prompt_template = self.prompt_manager.get_prompt_template(
                "script_generator",
                group_id=self.group.id,
                group_overrides=group_overrides
            )
            
            podcast_structure = self.group.podcast_structure or 'single'
            english_learning_mode = self.group.english_learning_mode or 'off'
            
            script_json = self.llm_service.generate_script(
                group_summary=group_summary,
                prompt_template=prompt_template,
                podcast_structure=podcast_structure,
                english_learning_mode=english_learning_mode
            )
            
            # 转换为 TTS 输入格式
            adapter = self._get_tts_adapter()
            segments = script_json.get('segments', [])
            tts_input = adapter.convert_to_tts_input(segments)
            
            return ScriptResult(
                success=True,
                script=script_json,
                moss_input=tts_input
            )
            
        except Exception as e:
            self.logger.error(f"生成播客脚本失败：{e}")
            return ScriptResult(success=False, error_message=str(e))
    
    def _get_tts_adapter(self):
        """获取 TTS 适配器"""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'config.json'
        )
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        tts_config = config.get('tts', {})
        return get_adapter_from_tts_config(tts_config)
    
    async def _synthesize_audio(self, script_result: ScriptResult, asset_manager, timestamp: str) -> TTSResult:
        """阶段 5：TTS 音频合成"""
        try:
            script_json = script_result.script or {}
            segments = script_json.get('segments', [])
            
            if not segments:
                return TTSResult(success=False, error_message="播客脚本段落为空")
            
            self.logger.info(f"[tts] 开始分段合成，共 {len(segments)} 个段落")
            
            # 获取 TTS 配置
            tts_config = self.config.get('tts', {}) if hasattr(self.config, 'get') else {}
            adapter = self._get_tts_adapter()
            
            # 逐段合成
            segment_paths = []
            provider_config = self.tts_service._get_tts_provider_config()
            adapter_config = self.tts_service._get_active_adapter_config()
            model = adapter_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
            
            client = self.tts_service._get_client()
            
            for i, seg in enumerate(segments):
                speaker = seg.get('speaker', 'host')
                content = seg.get('content', '')
                
                single_segment = [seg]
                tts_input = adapter.convert_to_tts_input(single_segment)
                
                # 确定音色
                if 'CosyVoice' in model:
                    voice = adapter_config.get('voice', 'claire')
                    voice = f"{model}:{voice}"
                else:
                    voice_host = adapter_config.get('voice_host', 'alex')
                    voice = f"fnlp/MOSS-TTSD-v0.5:{voice_host}"
                
                audio_data = await client.synthesize(tts_input, voice=voice)
                segment_path = asset_manager.save_audio_segment(i + 1, audio_data, speaker)
                segment_paths.append((segment_path, speaker))
            
            # 拼接音频
            from tts.audio_assembler import AudioAssembler, AudioRole, AssemblyConfig
            
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
                return TTSResult(success=False, error_message="FFmpeg 不可用")
            
            for path, speaker in segment_paths:
                role = AudioRole.HOST if speaker == 'host' else AudioRole.GUEST
                assembler.add_segment(path=path, role=role, fade_in_ms=0, fade_out_ms=0)
            
            # 输出音频片段保存路径
            self.logger.info(f"[tts] ✓ 音频片段已保存到: {asset_manager.segments_dir}")
            for path, speaker in segment_paths:
                self.logger.info(f"[tts]   - {os.path.basename(path)}")
            
            final_audio_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'data', 'media', self.group.id
            )
            os.makedirs(final_audio_dir, exist_ok=True)
            final_audio_path = os.path.join(final_audio_dir, f"episode_{timestamp}.mp3")
            
            assembled_path = await assembler.assemble(final_audio_path)
            audio_duration = os.path.getsize(assembled_path) // 16000
            
            await client.close()
            
            # 阶段 5.1: 音频调速处理
            audio_speed = getattr(self.group, 'audio_speed', 1.0) or 1.0
            if audio_speed != 1.0:
                self.logger.info(f"[speed] 开始音频调速，目标速度: {audio_speed}x")
                speed_processor = AudioSpeedProcessor()
                try:
                    # 调速后的文件路径
                    speed_adjusted_path = str(assembled_path).replace('.mp3', f'_speed{audio_speed}.mp3')
                    adjusted_path = await speed_processor.adjust_speed(
                        assembled_path,
                        speed_adjusted_path,
                        audio_speed
                    )
                    
                    if adjusted_path and os.path.exists(adjusted_path):
                        # 删除原始未调速文件，用调速后的文件替代
                        if assembled_path != adjusted_path:
                            os.remove(assembled_path)
                        assembled_path = adjusted_path
                        audio_duration = int(audio_duration / audio_speed)  # 调整时长估算
                        self.logger.info(f"[speed] ✓ 音频调速完成: {adjusted_path}")
                    else:
                        self.logger.warning(f"[speed] 音频调速失败，使用原始文件")
                        
                except Exception as e:
                    self.logger.warning(f"[speed] 音频调速异常: {e}，使用原始文件")
            
            return TTSResult(
                success=True,
                audio_path=str(assembled_path),
                audio_duration=audio_duration
            )
            
        except Exception as e:
            self.logger.error(f"TTS 音频合成失败：{e}")
            return TTSResult(success=False, error_message=str(e))
    
    async def _save_episode(self, tts_result: TTSResult, script_result: ScriptResult, summary_result: SummaryResult) -> EpisodeResult:
        """阶段 6：保存 Episode"""
        try:
            episode_number = self.state.last_episode_number + 1
            episode_id = f"ep-{self.group.id}-{episode_number:04d}"
            guid = f"rss2pod-{self.group.id}-{episode_number}"
            
            script_json = script_result.script or {}
            title = script_json.get('title', f"{self.group.name} Episode {episode_number}")
            
            from database.models import Episode
            
            episode = Episode(
                id=episode_id,
                group_id=self.group.id,
                title=title,
                episode_number=episode_number,
                script=str(script_json),
                audio_path=tts_result.audio_path,
                audio_duration=tts_result.audio_duration,
                guid=guid,
                source_summaries=[s.get('source', '') for s in summary_result.summaries]
            )
            
            if self.db.add_episode(episode):
                self.state.last_episode_number = episode_number
                self.state.last_run_at = datetime.now().isoformat()
                
                if self.state_manager:
                    self.state_manager.update_episode_number(self.group.id, episode_number)
                
                return EpisodeResult(success=True, episode_id=episode_id)
            else:
                return EpisodeResult(success=False, error_message="保存 Episode 到数据库失败")
            
        except Exception as e:
            self.logger.error(f"保存 Episode 失败：{e}")
            return EpisodeResult(success=False, error_message=str(e))
    
    async def _update_article_status(self, articles: List[Article]):
        """更新文章状态为已处理"""
        for article in articles:
            try:
                self.db.update_article_status(article.id, 'processed')
            except Exception as e:
                self.logger.warning(f"更新文章状态失败 ({article.id}): {e}")
    
    async def _update_feed(self, episode_result: EpisodeResult, tts_result: TTSResult) -> Dict[str, Any]:
        """阶段 7：更新 RSS Feed"""
        try:
            # 使用 FeedService（底层委托给 FeedManager）
            from services.feed_service import FeedService
            
            service = FeedService()
            
            # 创建或获取 Group
            group = service.get_group(self.group.id)
            if not group:
                group_result = service.create_group(
                    group_id=self.group.id,
                    title=self.group.name,
                    link=f"https://rss2pod.example.com/groups/{self.group.id}",
                    description=self.group.description or f"{self.group.name} 播客订阅",
                    author="RSS2Pod",
                    language="zh-cn",
                    category="Technology"
                )
                if not group_result.success:
                    raise Exception(f"创建 Group 失败: {group_result.error_message}")
            
            # 准备 Episode 数据
            episode_id = episode_result.episode_id
            audio_path = tts_result.audio_path
            audio_length = os.path.getsize(audio_path) if audio_path and os.path.exists(audio_path) else 0
            audio_url = f"/media/{self.group.id}/{os.path.basename(audio_path)}" if audio_path else ""
            
            db_episode = self.db.get_episode(episode_id)
            title = db_episode.title if db_episode else f"Episode {episode_id}"
            
            # 构建 Episode 数据字典
            episode_data = {
                'id': episode_id,
                'title': title,
                'link': f"https://rss2pod.example.com/episodes/{episode_id}",
                'audio_url': audio_url,
                'audio_length': audio_length,
                'audio_type': 'audio/mpeg',
                'description': db_episode.script if db_episode else "",
                'content_html': "<p>Generated by RSS2Pod</p>",
                'pub_date': datetime.now().isoformat(),
                'duration': f"{tts_result.audio_duration // 60}:{tts_result.audio_duration % 60:02d}",
                'episode_number': db_episode.episode_number if db_episode else None
            }
            
            # 添加 Episode
            add_result = service.add_episode(self.group.id, episode_data)
            if not add_result.success:
                raise Exception(f"添加 Episode 失败: {add_result.error_message}")
            
            # 生成 Feed（写入文件）
            feed_result = service.generate_feed(self.group.id)
            if not feed_result.success:
                raise Exception(f"生成 Feed 失败: {feed_result.error_message}")
            
            feed_path = feed_result.data.get('feed_path')
            
            return {"success": True, "feed_path": feed_path, "episode_id": episode_id}
            
        except Exception as e:
            self.logger.error(f"[feed] 更新 Feed 失败: {e}")
            return {"success": False, "error": str(e)}
    
    def close(self):
        """关闭服务，释放资源"""
        self.llm_service.close()
        self.tts_service.close()
