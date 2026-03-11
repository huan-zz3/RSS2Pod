#!/usr/bin/env python3
"""
RSS2Pod 命令行调试工具

仅包含 UI/显示逻辑，所有业务逻辑封装在 services/ 目录下的服务模块中。
"""

# 添加父目录到路径以便导入 rss2pod 模块
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typer
import json
import subprocess
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text

# 初始化
console = Console()
app = typer.Typer(
    name="rss2pod",
    help="RSS2Pod 命令行调试工具",
    add_completion=False,
    pretty_exceptions_enable=False
)

# 全局 verbose 状态
verbose_state = False


def get_verbose() -> bool:
    """获取 verbose 状态"""
    return verbose_state


def get_service(service_class, config_path: Optional[str] = None, db_path: Optional[str] = None):
    """获取服务实例的便捷函数
    
    Args:
        service_class: 服务类
        config_path: 配置文件路径（可选）
        db_path: 数据库路径（可选）
        
    Returns:
        服务实例
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), 'rss2pod.db')
    
    # ConfigService 只需要 config_path，不需要 db_path
    if service_class.__name__ == 'ConfigService':
        return service_class(config_path=config_path)
    else:
        return service_class(config_path=config_path, db_path=db_path)


# ============== 向后兼容的便捷函数 ==============
# 这些函数保留用于向后兼容，最终应该全部迁移到使用服务模块
def load_config():
    """加载配置（向后兼容函数，推荐使用 ConfigService）"""
    from rss2pod.services.config_service import load_config as _load_config
    return _load_config()


def save_config(config):
    """保存配置（向后兼容函数，推荐使用 ConfigService）"""
    from rss2pod.services.config_service import save_config as _save_config
    return _save_config(config)


def get_nested_value(config, path):
    """获取嵌套配置值（向后兼容函数）"""
    from rss2pod.services.config_service import get_nested_value as _get_nested_value
    return _get_nested_value(config, path)


def set_nested_value(config, path, value):
    """设置嵌套配置值（向后兼容函数）"""
    from rss2pod.services.config_service import set_nested_value as _set_nested_value
    return _set_nested_value(config, path, value)


# ============== 全局参数 ==============
@app.callback()
def main(
    verbose: bool = typer.Option(
        False, 
        "--verbose", "-v"
    )
):
    """RSS2Pod 命令行调试工具"""
    global verbose_state
    verbose_state = verbose


# ============== status 命令 ==============
@app.command()
def status():
    """显示系统整体状态"""
    console.print(Panel("[bold blue]RSS2Pod 系统状态[/bold blue]", box=box.DOUBLE))
    
    # 使用 ConfigService 获取配置
    from rss2pod.services import ConfigService
    config_service = get_service(ConfigService)
    config = config_service.get_safe_config()
    
    # Fever API 状态
    console.print("\n[bold]📡 Fever API[/bold]")
    try:
        from rss2pod.services import FeverService
        fever_service = get_service(FeverService)
        result = fever_service.test_connection()
        
        if result.success:
            console.print(f"   [green]✅ 连接正常[/green]")
            console.print(f"   最后刷新：{result.data.get('last_refreshed_on_time', 'unknown')}")
            console.print(f"   订阅源：{result.data.get('feeds_count', 0)} 个")
        else:
            console.print(f"   [red]❌ 连接失败：{result.error_message}[/red]")
        fever_service.close()
    except Exception as e:
        console.print(f"   [red]❌ 错误：{e}[/red]")
    
    # LLM 状态
    console.print("\n[bold]🤖 LLM[/bold]")
    try:
        from rss2pod.services import LLMService
        llm_service = get_service(LLMService)
        result = llm_service.test_connection()
        
        if result.success:
            console.print(f"   [green]✅ {result.data.get('provider')} ({result.data.get('model')})[/green]")
        else:
            console.print(f"   [red]❌ API 错误：{result.error_message}[/red]")
        llm_service.close()
    except Exception as e:
        console.print(f"   [red]❌ 错误：{e}[/red]")
    
    # TTS 状态
    console.print("\n[bold]🔊 TTS[/bold]")
    try:
        tts_config = config.get('tts', {})
        active_provider = tts_config.get('active_provider', 'siliconflow')
        active_adapter = tts_config.get('active_adapter', 'moss')
        providers = tts_config.get('providers', {})
        
        if active_provider == 'siliconflow':
            provider_config = providers.get('siliconflow', {})
            adapter_config = provider_config.get('adapters', {}).get(active_adapter, {})
            model = adapter_config.get('model', 'N/A')
            
            if active_adapter == 'moss':
                voice = adapter_config.get('voice_host', 'N/A')
            else:
                voice = adapter_config.get('voice', 'N/A')
            
            console.print(f"   [green]✅ SiliconFlow ({active_adapter})[/green]")
            console.print(f"   模型：{model}")
            console.print(f"   音色：{voice}")
        else:
            console.print(f"   [yellow]⚠️ 未配置 TTS (provider: {active_provider})[/yellow]")
    except Exception as e:
        console.print(f"   [red]❌ 错误：{e}[/red]")
    
    # 数据库状态
    console.print("\n[bold]📊 数据库[/bold]")
    try:
        from rss2pod.services import StatsService
        stats_service = get_service(StatsService)
        result = stats_service.get_database_stats()
        
        if result.success:
            console.print(f"   [green]✅ 数据库正常[/green]")
            console.print(f"   文章：{result.data.get('total_articles', 0)}")
            console.print(f"   Group: {result.data.get('enabled_groups', 0)}")
            console.print(f"   期数：{result.data.get('total_episodes', 0)}")
        else:
            console.print(f"   [red]❌ 错误：{result.error_message}[/red]")
        stats_service.close()
    except Exception as e:
        console.print(f"   [red]❌ 错误：{e}[/red]")
    
    # Orchestrator 状态
    console.print("\n[bold]⚙️  Orchestrator[/bold]")
    try:
        from rss2pod.services import SchedulerService
        scheduler_service = get_service(SchedulerService)
        result = scheduler_service.get_status()
        
        if result.success:
            states = result.data.get('states_by_status', {})
            console.print(f"   空闲：{states.get('idle', 0)}")
            console.print(f"   运行中：{states.get('running', 0)}")
            console.print(f"   错误：{states.get('error', 0)}")
            console.print(f"   运行中管道：{result.data.get('running_pipelines', 0)}")
        else:
            console.print(f"   [yellow]⚠️ 无法获取状态：{result.error_message}[/red]")
        scheduler_service.close()
    except ImportError:
        console.print(f"   [yellow]⚠️  模块未导入[/yellow]")
    except Exception as e:
        console.print(f"   [red]❌ 错误：{e}[/red]")
    
    console.print()


# ============== config 命令组 ==============
config_app = typer.Typer(help="配置管理")
app.add_typer(config_app, name="config")


@config_app.command()
def show():
    """显示当前配置"""
    console.print(Panel("[bold blue]RSS2Pod 配置[/bold blue]", box=box.DOUBLE))
    
    config = load_config()
    
    # 隐藏敏感信息
    safe_config = json.loads(json.dumps(config))
    if 'fever' in safe_config:
        safe_config['fever']['password'] = '***'
    if 'llm' in safe_config:
        safe_config['llm']['api_key'] = safe_config['llm']['api_key'][:10] + '...'
    if 'tts' in safe_config:
        safe_config['tts']['api_key'] = safe_config['tts']['api_key'][:10] + '...'
    
    console.print(json.dumps(safe_config, indent=2, ensure_ascii=False))


def set_nested_value(config, path, value):
    """设置嵌套配置值，如 llm.api_key"""
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


def get_nested_value(config, path):
    """获取嵌套配置值"""
    keys = path.split('.')
    current = config
    for key in keys:
        if key not in current:
            return None
        current = current[key]
    return current


@config_app.command()
def edit():
    """编辑配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    console.print(f"[bold]正在编辑配置文件：{config_path}[/bold]")
    
    # 尝试使用常见编辑器
    editors = ['nano', 'vim', 'vi', 'code', 'notepad']
    editor = os.environ.get('EDITOR', None)
    
    if editor:
        editors.insert(0, editor)
    
    for ed in editors:
        try:
            subprocess.run([ed, config_path])
            console.print("[green]✅ 配置已保存[/green]")
            
            # 验证 JSON 格式
            try:
                load_config()
                console.print("[green]✅ 配置格式有效[/green]")
            except json.JSONDecodeError as e:
                console.print(f"[red]❌ 配置格式错误：{e}[/red]")
                console.print("[yellow]请重新编辑配置文件[/yellow]")
            return
        except FileNotFoundError:
            continue
    
    console.print("[red]❌ 未找到可用的编辑器[/red]")
    console.print("请设置 EDITOR 环境变量或安装 vim/nano")
    sys.exit(1)


@config_app.command()
def set(key: str = typer.Argument(..., help="配置键（点号路径，如 llm.api_key）"),
        value: str = typer.Argument(..., help="配置值")):
    """设置配置项"""
    console.print(f"[bold]设置配置：{key} = {value[:10]}{'...' if len(value) > 10 else ''}[/bold]")
    
    config = load_config()
    
    if not set_nested_value(config, key, value):
        console.print(f"[red]❌ 无效的配置键：{key}[/red]")
        console.print("可用配置键示例:")
        console.print("   llm.api_key, llm.model, llm.base_url")
        console.print("   tts.provider, tts.api_key, tts.voice, tts.model")
        console.print("   fever.url, fever.username, fever.password")
        console.print("   orchestrator.check_interval_seconds, orchestrator.max_concurrent_groups")
        console.print("   logging.level, logging.file")
        return
    
    save_config(config)
    console.print(f"[green]✅ 配置已更新[/green]")
    console.print(f"   {key} = {value[:10]}{'...' if len(value) > 10 else ''}")


@config_app.command()
def reset(key: str = typer.Argument(..., help="配置键（点号路径）")):
    """重置配置项到默认值"""
    console.print(f"[bold]重置配置：{key}[/bold]")
    
    # 默认值
    defaults = {
        "llm.model": "qwen3.5-plus",
        "llm.base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "tts.provider": "siliconflow",
        "tts.voice": "FunAudioLLM/CosyVoice2-0.5B:claire",
        "tts.model": "fnlp/MOSS-TTSD-v0.5",
        "db_path": "rss2pod.db",
        "orchestrator.check_interval_seconds": 60,
        "orchestrator.max_concurrent_groups": 3,
        "orchestrator.retry_attempts": 3,
        "orchestrator.retry_delay_seconds": 3,
        "logging.level": "INFO",
        "logging.file": "logs/orchestrator.log",
        "logging.rotation": "daily",
        "logging.retention_days": 7
    }
    
    if key not in defaults:
        console.print(f"[yellow]⚠️ 未知配置键：{key}[/yellow]")
        console.print("可用重置项:", list(defaults.keys()))
        return
    
    config = load_config()
    set_nested_value(config, key, defaults[key])
    save_config(config)
    
    console.print(f"[green]✅ 配置已重置[/green]")
    console.print(f"   {key} = {defaults[key]}")


# ============== source 命令组 ==============
source_app = typer.Typer(help="订阅源管理")
app.add_typer(source_app, name="source")


@source_app.command("list")
def source_list():
    """列出本地已保存的订阅源（从 sources.json）"""
    sources_file = os.path.join(os.path.dirname(__file__), 'sources.json')
    
    if not os.path.exists(sources_file):
        console.print("[yellow]本地没有已保存的订阅源[/yellow]")
        console.print("请先运行：[bold]rss2pod fever sync feeds[/bold]")
        return
    
    with open(sources_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sources = data.get('sources', [])
    synced_at = data.get('synced_at', 0)
    
    from datetime import datetime
    sync_time = datetime.fromtimestamp(synced_at).strftime('%Y-%m-%d %H:%M:%S')
    
    console.print(f"[bold]本地订阅源 (同步时间：{sync_time})[/bold]\n")
    
    table = Table(box=box.ROUNDED)
    table.add_column("ID", style="cyan", width=8)
    table.add_column("名称", style="green")
    table.add_column("URL", style="blue")
    
    for source in sources:
        table.add_row(
            source['id'],
            source['title'][:40] + '...' if len(source['title']) > 40 else source['title'],
            source['url'][:50] + '...' if len(source['url']) > 50 else source['url']
        )
    
    console.print(table)
    console.print(f"\n共 {len(sources)} 个订阅源")


@source_app.command()
def show(source_id: str = typer.Argument(..., help="订阅源 ID 或 URL")):
    """查看订阅源详情（从 sources.json）"""
    sources_file = os.path.join(os.path.dirname(__file__), 'sources.json')
    
    if not os.path.exists(sources_file):
        console.print("[red]❌ 本地没有已保存的订阅源[/red]")
        return
    
    with open(sources_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for source in data.get('sources', []):
        if source['id'] == source_id or source['url'] == source_id:
            console.print(Panel(f"[bold]{source['title']}[/bold]", box=box.ROUNDED))
            console.print(f"ID:  {source['id']}")
            console.print(f"URL: {source['url']}")
            return
    
    console.print(f"[red]❌ 未找到 ID 或 URL 为 {source_id} 的订阅源[/red]")


@source_app.command("articles")
def source_articles(
    identifier: str = typer.Argument(..., help="订阅源 ID"),
    limit: int = typer.Option(10, "--limit", "-l", help="显示文章数量"),
    unread: bool = typer.Option(False, "--unread/--all", help="只显示未读文章")
):
    """查看指定订阅源的文章（从本地缓存读取）
    
    注意：此命令从本地 SQLite 缓存读取文章。请先运行 `rss2pod fever sync` 同步数据。
    """
    from datetime import datetime
    
    console.print(f"[bold]正在获取文章...[/bold]")
    console.print(f"订阅源 ID: [green]{identifier}[/green]\n")
    
    try:
        # 使用本地缓存获取文章
        config = load_config()
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        
        from database.models import DatabaseManager
        db = DatabaseManager(db_path)
        
        feed_id = int(identifier)
        
        if unread:
            items = db.get_fever_cache_unread_items(feed_id=feed_id, limit=limit)
        else:
            # 从缓存获取指定 feed_id 的文章
            cursor = db.conn.cursor()
            query = 'SELECT * FROM fever_cache WHERE feed_id = ? ORDER BY id DESC LIMIT ?'
            params = [feed_id, limit]
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            from database.models import FeverCacheItem
            items = []
            for row in rows:
                data = dict(row)
                items.append(FeverCacheItem(
                    id=data['id'],
                    feed_id=data['feed_id'],
                    title=data['title'],
                    author=data.get('author', ''),
                    html=data.get('html', ''),
                    url=data.get('url', ''),
                    is_read=bool(data.get('is_read', 0)),
                    is_saved=bool(data.get('is_saved', 0)),
                    created_on_time=data.get('created_on_time', 0),
                    fetched_at=data.get('fetched_at', '')
                ))
        
        if not items:
            status_text = "未读" if unread else "所有"
            console.print(f"[yellow]没有找到{status_text}文章[/yellow]")
            console.print("[dim]提示：请先运行 `rss2pod fever sync` 同步文章到本地缓存[/dim]")
            db.close()
            return
        
        # 显示文章列表
        table = Table(
            title=f"文章列表 (共 {len(items)} 篇)",
            box=box.ROUNDED,
            show_lines=True
        )
        table.add_column("ID", style="cyan", width=8)
        table.add_column("标题", style="green")
        table.add_column("时间", style="yellow")
        
        for item in items:
            title = item.title[:50]
            if len(item.title) > 50:
                title += '...'
            
            created_time = item.created_on_time
            if created_time:
                pub_time = datetime.fromtimestamp(int(created_time)).strftime('%Y-%m-%d %H:%M')
            else:
                pub_time = '-'
            
            table.add_row(
                str(item.id),
                title,
                pub_time
            )
        
        console.print(table)
        console.print(f"\n共 {len(items)} 篇文章")
        
        db.close()
        
    except ValueError as e:
        console.print(f"[red]❌ 无效的订阅源 ID：{identifier}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        import traceback
        if get_verbose():
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


# ============== group 命令组 ==============
group_app = typer.Typer(help="播客组管理")
app.add_typer(group_app, name="group")


@group_app.command()
def list():
    """列出所有 Group"""
    console.print("[bold]Group 列表[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        groups = db.get_all_groups()
        
        if not groups:
            console.print("[yellow]没有找到 Group[/yellow]")
            console.print("使用 [bold]rss2pod group create[/bold] 创建第一个 Group")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("RSS 源", style="blue")
        table.add_column("触发", style="magenta")
        
        for group in groups:
            table.add_row(
                group.id,
                group.name,
                "✅" if group.enabled else "❌",
                f"{len(group.rss_sources)} 个",
                group.trigger_type
            )
        
        console.print(table)
        console.print(f"\n共 {len(groups)} 个 Group")
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def show(group_id: str = typer.Argument(..., help="Group ID")):
    """查看 Group 详情"""
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        console.print(Panel(f"[bold]{group.name}[/bold]", box=box.DOUBLE))
        console.print(f"ID:          {group.id}")
        console.print(f"描述：       {group.description or '-'}")
        console.print(f"状态：       {'✅ 启用' if group.enabled else '❌ 禁用'}")
        console.print(f"触发类型：   {group.trigger_type}")
        cron = group.trigger_config.get('cron', '-') if group.trigger_config else '-'
        console.print(f"Cron:        {cron}")
        console.print(f"播客结构：   {group.podcast_structure}")
        console.print(f"英语学习：   {group.english_learning_mode}")
        console.print(f"音频调速：   {group.audio_speed}x")
        console.print(f"\n[bold]RSS 源 ({len(group.rss_sources)} 个):[/bold]")
        for i, source in enumerate(group.rss_sources, 1):
            console.print(f"  {i}. {source}")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def create():
    """交互式创建 Group"""
    console.print(Panel("[bold blue]创建新 Group[/bold blue]", box=box.DOUBLE))
    console.print()
    
    # 步骤 1: 输入组名
    console.print("[bold]步骤 1/6: 设置组名[/bold]")
    group_name = Prompt.ask("请输入组名", default="我的播客")
    console.print(f"   组名：[green]{group_name}[/green]\n")
    
    # 步骤 2: 选择订阅源
    console.print("[bold]步骤 2/6: 选择订阅源[/bold]")
    
    sources_file = os.path.join(os.path.dirname(__file__), 'sources.json')
    if not os.path.exists(sources_file):
        console.print("[yellow]本地没有已保存的订阅源[/yellow]")
        console.print("正在从 Fever API 同步...")
        try:
            client = get_fever_client()
            feeds = client.get_feeds()
            
            sources_data = {
                "synced_at": __import__('time').time(),
                "sources": [
                    {"id": str(f.get('id', '')), "title": f.get('title', ''), "url": f.get('url', '')}
                    for f in feeds
                ]
            }
            with open(sources_file, 'w', encoding='utf-8') as f:
                json.dump(sources_data, f, indent=2, ensure_ascii=False)
            console.print(f"[green]✅ 已同步 {len(feeds)} 个订阅源[/green]\n")
        except Exception as e:
            console.print(f"[red]❌ 同步失败：{e}[/red]")
            console.print("你可以稍后手动添加 RSS 源 URL\n")
            sources_file = None
    
    selected_sources = []
    if sources_file and os.path.exists(sources_file):
        with open(sources_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sources = data.get('sources', [])
        
        # 显示订阅源列表供选择
        console.print("可用订阅源列表:")
        for i, source in enumerate(sources, 1):
            title = source['title'][:40] + '...' if len(source['title']) > 40 else source['title']
            console.print(f"  {i:3}. {title}")
        
        console.print()
        console.print("[dim]提示：输入多个数字用逗号分隔，如：1,3,5[/dim]")
        console.print("[dim]      输入 'a' 全选，输入 'n' 跳过[/dim]")
        
        selection = Prompt.ask("请选择订阅源（输入数字）")
        
        if selection.lower() == 'a':
            selected_sources = [s['url'] for s in sources if s.get('url')]
            console.print(f"   已选择 [green]{len(selected_sources)}[/green] 个订阅源\n")
        elif selection.lower() == 'n':
            console.print("   [yellow]跳过，稍后手动添加[/yellow]\n")
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                selected_sources = [sources[i]['url'] for i in indices if 0 <= i < len(sources) and sources[i].get('url')]
                console.print(f"   已选择 [green]{len(selected_sources)}[/green] 个订阅源\n")
            except (ValueError, IndexError) as e:
                console.print(f"[yellow]无效选择，稍后手动添加[/yellow]\n")
    
    # 如果没有选择订阅源，允许手动输入
    if not selected_sources:
        console.print("[bold]手动添加 RSS 源 URL（可选）[/bold]")
        console.print("[dim]每行一个 URL，输入空行结束[/dim]")
        while True:
            url = Prompt.ask(f"RSS 源 URL #{len(selected_sources)+1}", default="")
            if not url:
                break
            selected_sources.append(url)
        console.print()
    
    # 步骤 3: 选择触发类型
    console.print("[bold]步骤 3/?: 设置触发类型[/bold]")
    trigger_type = Prompt.ask(
        "选择触发类型",
        choices=["time", "count", "llm", "combined"],
        default="time"
    )
    console.print(f"   触发类型：[green]{trigger_type}[/green]\n")
    
    # 计算实际步骤总数
    # 步骤1: 组名 (固定)
    # 步骤2: 订阅源 (固定)
    # 步骤3: 触发类型 (固定)
    # 步骤4: Cron表达式 (仅 time/combined)
    # 步骤5: 数量阈值 (仅 count/combined)
    # 步骤6: 播客结构+英语学习 (固定)
    total_steps = 5  # 基础步骤
    if trigger_type in ["count", "combined"]:
        total_steps += 1  # 数量阈值
    if trigger_type in ["time", "combined"]:
        total_steps += 1  # Cron表达式
    # llm 类型没有 time 相关的步骤，所以还是 5 步
    if trigger_type == "llm":
        total_steps = 4
    
    # 步骤 4: 根据触发类型设置参数
    cron_expr = "0 9 * * *"
    count_threshold = 10
    current_step = 4
    
    if trigger_type in ["time", "combined"]:
        console.print(f"[bold]步骤 {current_step}/{total_steps}: 设置 Cron 表达式[/bold]")
        console.print("[dim]默认每天 9:00 触发[/dim]")
        cron_expr = Prompt.ask("Cron 表达式", default="0 9 * * *")
        console.print(f"   Cron: [green]{cron_expr}[/green]\n")
        current_step += 1
    
    if trigger_type in ["count", "combined"]:
        console.print(f"[bold]步骤 {current_step}/{total_steps}: 设置数量阈值[/bold]")
        count_threshold = IntPrompt.ask("文章数量阈值", default=10)
        console.print(f"   阈值：[green]{count_threshold}[/green]\n")
        current_step += 1
    
    # 步骤 5: 选择播客结构
    console.print(f"[bold]步骤 {current_step}/{total_steps}: 设置播客结构[/bold]")
    podcast_structure = Prompt.ask(
        "选择播客结构",
        choices=["single", "dual"],
        default="single"
    )
    console.print(f"   结构：[green]{podcast_structure}[/green]\n")
    
    # 英语学习
    english_learning = Prompt.ask(
        "英语学习功能",
        choices=["off", "vocab", "translation"],
        default="off"
    )
    console.print(f"   英语学习：[green]{english_learning}[/green]\n")
    
    # 音频调速
    from rich.prompt import FloatPrompt
    audio_speed = FloatPrompt.ask(
        "音频调速 (0.5-2.0，1.0为正常速度)",
        default=1.0
    )
    # 验证并规范化范围
    audio_speed = max(0.5, min(2.0, audio_speed))
    console.print(f"   音频调速：[green]{audio_speed}x[/green]\n")
    
    # 描述
    description = Prompt.ask("组描述（可选）", default="")
    
    # 确认创建
    console.print()
    console.print(Panel("[bold]确认创建[/bold]", box=box.ROUNDED))
    console.print(f"组名：         {group_name}")
    console.print(f"RSS 源：       {len(selected_sources)} 个")
    console.print(f"触发类型：     {trigger_type}")
    if trigger_type in ["time", "combined"]:
        console.print(f"Cron 表达式：  {cron_expr}")
    if trigger_type in ["count", "combined"]:
        console.print(f"数量阈值：     {count_threshold}")
    console.print(f"播客结构：     {podcast_structure}")
    console.print(f"英语学习：     {english_learning}")
    console.print(f"音频调速：     {audio_speed}x")
    if description:
        console.print(f"描述：         {description}")
    
    if not Confirm.ask("\n确认创建？"):
        console.print("[yellow]已取消[/yellow]")
        return
    
    # 创建 Group
    try:
        config = load_config()
        from database.models import init_db, Group
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group_id = f"group-{len(db.get_all_groups()) + 1}"
        new_group = Group(
            id=group_id,
            name=group_name,
            description=description,
            rss_sources=selected_sources,
            podcast_structure=podcast_structure,
            english_learning_mode=english_learning,
            audio_speed=audio_speed,
            trigger_type=trigger_type,
            trigger_config={"cron": cron_expr, "threshold": count_threshold}
        )
        
        db.add_group(new_group)
        db.close()
        
        console.print(f"\n[green]✅ Group 创建成功![/green]")
        console.print(f"   ID: {group_id}")
        console.print(f"\n使用 [bold]rss2pod group show {group_id}[/bold] 查看详情")
        
    except Exception as e:
        console.print(f"[red]❌ 创建失败：{e}[/red]")
        sys.exit(1)


@group_app.command()
def edit(group_id: str = typer.Argument(..., help="Group ID")):
    """编辑 Group"""
    console.print(f"[bold]编辑 Group: {group_id}[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        console.print(f"当前配置:")
        console.print(f"  名称：     {group.name}")
        console.print(f"  描述：     {group.description or '-'}")
        console.print(f"  RSS 源：    {len(group.rss_sources)} 个")
        console.print(f"  触发类型： {group.trigger_type}")
        cron = group.trigger_config.get('cron', '-') if group.trigger_config else '-'
        console.print(f"  Cron:      {cron}")
        console.print(f"  播客结构： {group.podcast_structure}")
        console.print(f"  英语学习： {group.english_learning_mode}")
        console.print(f"  音频调速： {group.audio_speed}x")
        console.print()
        
        # 交互式修改
        if Confirm.ask("修改名称？", default=False):
            group.name = Prompt.ask("新名称", default=group.name)
        
        if Confirm.ask("修改描述？", default=False):
            group.description = Prompt.ask("新描述", default=group.description or "")
        
        if Confirm.ask("修改 RSS 源？", default=False):
            console.print("当前 RSS 源:")
            for i, source in enumerate(group.rss_sources, 1):
                console.print(f"  {i}. {source}")
            
            console.print("\n输入要删除的源编号（逗号分隔），或从本地订阅源中添加")
            action = Prompt.ask("操作（delete/add/skip）", choices=["delete", "add", "skip"], default="skip")
            
            if action == "delete":
                indices = Prompt.ask("要删除的编号")
                try:
                    to_remove = [int(x.strip()) - 1 for x in indices.split(',')]
                    group.rss_sources = [s for i, s in enumerate(group.rss_sources) if i not in to_remove]
                except:
                    pass
            elif action == "add":
                # 加载本地订阅源
                sources_file = os.path.join(os.path.dirname(__file__), 'sources.json')
                if not os.path.exists(sources_file):
                    console.print("[yellow]本地没有已保存的订阅源[/yellow]")
                    console.print("请先运行：[bold]rss2pod source sync[/bold]")
                else:
                    with open(sources_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    sources = data.get('sources', [])
                    
                    if not sources:
                        console.print("[yellow]本地没有可用的订阅源[/yellow]")
                    else:
                        # 显示可用订阅源
                        console.print("\n可用订阅源列表:")
                        for i, source in enumerate(sources, 1):
                            title = source['title'][:50] + '...' if len(source['title']) > 50 else source['title']
                            console.print(f"  {i}. {title}")
                        
                        console.print()
                        selection = Prompt.ask("输入要添加的订阅源编号（空行结束）", default="")
                        
                        if selection:
                            try:
                                idx = int(selection) - 1
                                if 0 <= idx < len(sources):
                                    url = sources[idx]['url']
                                    if url not in group.rss_sources:
                                        group.rss_sources.append(url)
                                        console.print(f"[green]✅ 已添加：{sources[idx]['title']}[/green]")
                                    else:
                                        console.print("[yellow]⚠️ 该源已存在[/yellow]")
                                else:
                                    console.print("[red]❌ 无效编号[/red]")
                            except ValueError:
                                console.print("[red]❌ 请输入数字编号[/red]")
        
        if Confirm.ask("修改触发类型？", default=False):
            group.trigger_type = Prompt.ask(
                "新触发类型",
                choices=["time", "count", "llm", "combined"],
                default=group.trigger_type
            )
        
        if Confirm.ask("修改 Cron 表达式？", default=False):
            if not group.trigger_config:
                group.trigger_config = {}
            group.trigger_config['cron'] = Prompt.ask("新 Cron 表达式", default=group.trigger_config.get('cron', '0 9 * * *'))
        
        if Confirm.ask("修改播客结构？", default=False):
            group.podcast_structure = Prompt.ask(
                "新播客结构",
                choices=["single", "dual"],
                default=group.podcast_structure
            )
        
        if Confirm.ask("修改英语学习？", default=False):
            group.english_learning_mode = Prompt.ask(
                "新英语学习设置",
                choices=["off", "vocab", "translation"],
                default=group.english_learning_mode
            )
        
        if Confirm.ask("修改音频调速？", default=False):
            from rich.prompt import FloatPrompt
            audio_speed = FloatPrompt.ask(
                "音频调速 (0.5-2.0，1.0为正常速度)",
                default=group.audio_speed
            )
            # 验证并规范化范围
            audio_speed = max(0.5, min(2.0, audio_speed))
            group.audio_speed = audio_speed
        
        # 保存
        if Confirm.ask("\n保存修改？", default=True):
            db.update_group(group)
            console.print("[green]✅ 已保存[/green]")
        else:
            console.print("[yellow]已取消修改[/yellow]")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def delete(group_id: str = typer.Argument(..., help="Group ID"), 
           force: bool = typer.Option(False, "--force", "-f", help="强制删除，不确认")):
    """删除 Group"""
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        if not force:
            console.print(f"[bold]确认删除 Group: {group.name}?[/bold]")
            console.print(f"  ID: {group_id}")
            console.print(f"  RSS 源：{len(group.rss_sources)} 个")
            if not Confirm.ask("\n此操作不可逆，确认删除？"):
                console.print("[yellow]已取消[/yellow]")
                return
        
        db.delete_group(group_id)
        console.print(f"[green]✅ Group 已删除[/green]")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def enable(group_id: str = typer.Argument(..., help="Group ID")):
    """启用 Group"""
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        group.enabled = True
        db.update_group(group)
        console.print(f"[green]✅ Group '{group.name}' 已启用[/green]")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def disable(group_id: str = typer.Argument(..., help="Group ID")):
    """禁用 Group"""
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        group.enabled = False
        db.update_group(group)
        console.print(f"[green]✅ Group '{group.name}' 已禁用[/green]")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


def get_fever_client():
    """获取 Fever API 客户端（使用 FeverService）"""
    from rss2pod.services import FeverService
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    db_path = os.path.join(os.path.dirname(__file__), 'rss2pod.db')
    service = FeverService(config_path=config_path, db_path=db_path)
    return service._get_client(with_cache=True)


# ============== fever 命令组 ==============
fever_app = typer.Typer(help="Fever API 同步")
app.add_typer(fever_app, name="fever")


@fever_app.command()
def test():
    """测试 Fever API 连接"""
    console.print("[bold]测试 Fever API 连接...[/bold]")

    try:
        client = get_fever_client()

        if client.test_auth():
            info = client._make_request({})
            console.print(f"[green]✅ 连接成功![/green]")
            console.print(f"   最后刷新：{info.get('last_refreshed_on_time', 'unknown')}")

            if get_verbose():
                feeds = client.get_feeds()
                console.print(f"   订阅源：{len(feeds)} 个")
        else:
            console.print(f"[red]❌ 认证失败[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


def _sync_feeds():
    """同步订阅源列表"""
    console.print("[bold]正在从 Fever API 同步订阅源...[/bold]\n")

    try:
        client = get_fever_client()
        feeds = client.get_feeds()
        
        # 保存订阅源到本地
        sources_file = os.path.join(os.path.dirname(__file__), 'sources.json')
        sources_data = {
            "synced_at": __import__('time').time(),
            "sources": [
                {
                    "id": str(feed.get('id', '')),
                    "title": feed.get('title', 'Unknown'),
                    "url": feed.get('url', '')
                }
                for feed in feeds
            ]
        }
        
        with open(sources_file, 'w', encoding='utf-8') as f:
            json.dump(sources_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]✅ 已同步 {len(feeds)} 个订阅源[/green]")
        console.print(f"   保存位置：{sources_file}")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


def _sync_articles(limit: int = 1500):
    """同步文章到缓存"""
    console.print(f"[bold]同步 Fever API 文章到本地缓存 (限制：{limit})...[/bold]\n")
    
    config = load_config()
    
    try:
        from services.pipeline.group_processor import sync_fever_cache
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        result = sync_fever_cache(db_path=db_path, limit=limit)
        
        if result.success:
            console.print(f"[green]✅ 同步成功![/green]")
            console.print(f"   同步文章：{result.items_synced} 篇")
            console.print(f"   新增：{result.new_items} 篇")
            console.print(f"   更新：{result.updated_items} 篇")
        else:
            console.print(f"[red]❌ 同步失败：{result.error_message}[/red]")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="sync-feeds")
def sync_feeds():
    """同步订阅源列表到本地"""
    _sync_feeds()


@fever_app.command(name="sync-articles")
def sync_articles(
    limit: int = typer.Option(1500, "--limit", "-l", help="最大同步文章数量")
):
    """同步文章到本地缓存"""
    _sync_articles(limit)


@fever_app.command(name="sync-all")
def sync_all(
    limit: int = typer.Option(1500, "--limit", "-l", help="最大同步文章数量")
):
    """同步订阅源和文章到本地缓存"""
    console.print("[bold]同步订阅源和文章...[/bold]\n")
    _sync_feeds()
    console.print()
    _sync_articles(limit)


@fever_app.command(name="cache-stats")
def cache_stats():
    """显示 Fever 缓存统计信息"""
    console.print(Panel("[bold blue]Fever 缓存统计[/bold blue]", box=box.DOUBLE))
    
    config = load_config()
    
    try:
        from services.pipeline.group_processor import get_fever_cache_stats
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        stats = get_fever_cache_stats(db_path)
        
        if 'error' in stats:
            console.print(f"[red]❌ 错误：{stats['error']}[/red]")
            return
        
        console.print(f"\n[bold]📊 缓存统计[/bold]")
        console.print(f"   文章总数：{stats.get('total_items', 0)}")
        console.print(f"   未读文章：{stats.get('unread_count', 0)}")
        console.print(f"   已收藏：{stats.get('saved_count', 0)}")
        console.print(f"   订阅源数：{stats.get('feed_count', 0)}")
        
        last_sync = stats.get('last_sync_time')
        if last_sync:
            from datetime import datetime
            try:
                sync_time = datetime.fromisoformat(last_sync).strftime('%Y-%m-%d %H:%M:%S')
                console.print(f"   最后同步：{sync_time}")
            except:
                console.print(f"   最后同步：{last_sync}")
        else:
            console.print(f"   最后同步：[yellow]尚未同步[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="cache-articles")
def cache_articles(
    limit: int = typer.Option(20, "--limit", "-l", help="显示文章数量"),
    unread: bool = typer.Option(True, "--unread/--all", help="只显示未读文章")
):
    """从缓存获取文章列表"""
    status_text = "未读" if unread else "所有"
    console.print(f"[bold]从缓存获取{status_text}文章 (限制：{limit})...[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import DatabaseManager
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = DatabaseManager(db_path)
        
        if unread:
            items = db.get_fever_cache_unread_items(limit=limit)
        else:
            items = db.get_fever_cache_items(limit=limit)
        
        if not items:
            all_items = db.get_fever_cache_items(limit=1)
            if not all_items:
                console.print("[yellow]缓存中没有文章，请先运行：rss2pod fever sync-all[/yellow]")
            else:
                console.print(f"[yellow]缓存中有文章，但没有{status_text}文章[/yellow]")
            db.close()
            return
        
        table = Table(
            title=f"文章列表 (共 {len(items)} 篇)",
            box=box.ROUNDED,
            show_lines=True
        )
        table.add_column("ID", style="cyan", width=8)
        table.add_column("标题", style="green")
        table.add_column("作者", style="yellow")
        table.add_column("状态", style="magenta")
        
        for item in items:
            title = item.title[:60] if len(item.title) > 60 else item.title
            
            read_icon = "✓" if item.is_read else "○"
            saved_icon = "★" if item.is_saved else " "
            status = f"{read_icon}{saved_icon}"
            
            table.add_row(
                str(item.id),
                title,
                item.author[:20] if item.author else '-',
                status
            )
        
        console.print(table)
        console.print("\n[dim]状态说明：✓ 已读 ○ 未读 | ★ 已收藏[/dim]")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="cache-feeds")
def cache_feeds():
    """从缓存获取订阅源列表"""
    console.print("[bold]从缓存获取订阅源列表...[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import DatabaseManager
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = DatabaseManager(db_path)
        
        # 从 fever_cache 表获取唯一的 feed_id
        cursor = db.conn.cursor()
        cursor.execute('SELECT DISTINCT feed_id FROM fever_cache ORDER BY feed_id')
        feed_ids = [row[0] for row in cursor.fetchall()]
        
        # 尝试从 sources.json 获取订阅源名称
        sources_file = os.path.join(os.path.dirname(__file__), 'sources.json')
        sources_map = {}
        if os.path.exists(sources_file):
            with open(sources_file, 'r', encoding='utf-8') as f:
                sources_data = json.load(f)
                for source in sources_data.get('sources', []):
                    sources_map[str(source.get('id', ''))] = source.get('title', 'Unknown')
        
        table = Table(
            title=f"订阅源缓存列表 (共 {len(feed_ids)} 个有文章的订阅源)",
            box=box.ROUNDED
        )
        table.add_column("Feed ID", style="cyan")
        table.add_column("名称", style="green")
        
        for feed_id in feed_ids:
            name = sources_map.get(str(feed_id), '(未知)')
            table.add_row(str(feed_id), name)
        
        console.print(table)
        console.print(f"\n共 {len(feed_ids)} 个订阅源有缓存文章")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="mark-read")
def mark_read(
    item_ids: str = typer.Argument(..., help="文章 ID 列表，逗号分隔，如：123,456,789")
):
    """标记文章为已读"""
    console.print(f"[bold]标记文章为已读：{item_ids}[/bold]\n")
    
    try:
        config = load_config()
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        
        from fetcher.fever_client import FeverClient, FeverCredentials
        
        api_key = hashlib.md5(
            f"{config['fever']['username']}:{config['fever']['password']}".encode()
        ).hexdigest()
        
        credentials = FeverCredentials(
            api_url=config['fever']['url'],
            api_key=api_key
        )
        client = FeverClient(credentials, db_path=db_path)
        
        ids = [int(x.strip()) for x in item_ids.split(',')]
        result = client.mark_as_read(ids)
        
        if result:
            console.print(f"[green]✅ 已标记 {len(ids)} 篇文章为已读[/green]")
        else:
            console.print("[red]❌ 操作失败[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="mark-saved")
def mark_saved(
    item_id: int = typer.Argument(..., help="文章 ID")
):
    """收藏文章"""
    console.print(f"[bold]收藏文章：{item_id}[/bold]\n")
    
    try:
        config = load_config()
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        
        from fetcher.fever_client import FeverClient, FeverCredentials
        
        api_key = hashlib.md5(
            f"{config['fever']['username']}:{config['fever']['password']}".encode()
        ).hexdigest()
        
        credentials = FeverCredentials(
            api_url=config['fever']['url'],
            api_key=api_key
        )
        client = FeverClient(credentials, db_path=db_path)
        
        result = client.save_item(item_id)
        
        if result:
            console.print(f"[green]✅ 已收藏文章 {item_id}[/green]")
        else:
            console.print("[red]❌ 操作失败[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="mark-unread")
def mark_unread(
    item_ids: str = typer.Argument(..., help="文章 ID 列表，逗号分隔")
):
    """标记文章为未读"""
    console.print(f"[bold]标记文章为未读：{item_ids}[/bold]\n")
    
    # 注意：Fever API 不直接支持标记为未读
    # 这里只更新本地缓存
    try:
        config = load_config()
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        
        from database.models import DatabaseManager
        db = DatabaseManager(db_path)
        
        ids = [int(x.strip()) for x in item_ids.split(',')]
        
        # 只更新本地缓存
        cursor = db.conn.cursor()
        placeholders = ','.join('?' * len(ids))
        cursor.execute(f'UPDATE fever_cache SET is_read = 0 WHERE id IN ({placeholders})', ids)
        db.conn.commit()
        
        console.print(f"[green]✅ 已标记 {len(ids)} 篇文章为未读（仅本地缓存）[/green]")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== prompt 命令组 ==============
prompt_app = typer.Typer(help="提示词管理")
app.add_typer(prompt_app, name="prompt")


@prompt_app.command("list")
def prompt_list():
    """列出所有可用的 prompts"""
    console.print(Panel("[bold blue]可用 Prompts 列表[/bold blue]", box=box.DOUBLE))
    
    try:
        # Add parent directory to path for imports
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        from llm.prompt_manager import get_prompt_manager
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        manager = get_prompt_manager(config_path)
        
        prompts = manager.list_prompts()
        
        table = Table(box=box.ROUNDED)
        table.add_column("Prompt 名称", style="cyan")
        table.add_column("描述", style="green")
        table.add_column("变量", style="yellow")
        
        for prompt in prompts:
            variables = ", ".join(prompt.variables) if prompt.variables else "-"
            table.add_row(
                prompt.name,
                prompt.description,
                variables
            )
        
        console.print(table)
        console.print(f"\n共 {len(prompts)} 个 prompts")
        console.print("\n[dim]提示：使用 `rss2pod prompt show <prompt_name>` 查看详细内容[/dim]")
        console.print("[dim]      使用 `rss2pod prompt edit <prompt_name>` 编辑 prompt[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@prompt_app.command("show")
def prompt_show(
    name: str = typer.Argument(..., help="prompt 名称"),
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="指定 Group ID 查看覆盖配置")
):
    """查看 prompt 详情"""
    console.print(f"[bold]查看 Prompt: {name}[/bold]\n")
    
    try:
        from llm.prompt_manager import get_prompt_manager
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        manager = get_prompt_manager(config_path)
        
        # 获取组别覆盖（如果指定）
        group_overrides = None
        if group_id:
            from database.models import init_db
            db_path = os.path.join(os.path.dirname(__file__), config_path)
            db = init_db(db_path.replace('config.json', 'rss2pod.db'))
            group = db.get_group(group_id)
            if group:
                group_overrides = {'prompt_overrides': group.prompt_overrides}
                db.close()
        
        prompt = manager.get_prompt(name, group_id=group_id, group_overrides=group_overrides)
        
        console.print(f"[bold]名称:[/bold] {prompt.name}")
        console.print(f"[bold]描述:[/bold] {prompt.description}")
        console.print(f"[bold]可用变量:[/bold] {', '.join(prompt.variables) if prompt.variables else '无'}\n")
        
        console.print(Panel("[bold]System Message[/bold]", box=box.ROUNDED))
        console.print(prompt.system or "(无)")
        
        console.print(Panel("[bold]Template[/bold]", box=box.ROUNDED))
        console.print(prompt.template or "(无)")
        
        if group_id:
            console.print(f"\n[dim]显示的是 Group '{group_id}' 的配置（可能包含覆盖）[/dim]")
        else:
            console.print(f"\n[dim]显示的是全局默认配置[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@prompt_app.command("edit")
def prompt_edit(
    name: str = typer.Argument(..., help="prompt 名称")
):
    """编辑 prompt（使用编辑器）"""
    console.print(f"[bold]编辑 Prompt: {name}[/bold]\n")
    
    try:
        from llm.prompt_manager import get_prompt_manager, PromptConfig
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        manager = get_prompt_manager(config_path)
        
        prompt = manager.get_prompt(name)
        
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
            f.write(f"# 编辑 Prompt: {name}\n")
            f.write(f"# 描述：{prompt.description}\n")
            f.write(f"# 可用变量：{', '.join(prompt.variables) if prompt.variables else '无'}\n")
            f.write(f"#\n")
            f.write(f"# === SYSTEM MESSAGE ===\n")
            f.write(prompt.system + "\n")
            f.write(f"\n")
            f.write(f"# === TEMPLATE ===\n")
            f.write(prompt.template)
        
        # 尝试使用常见编辑器
        editors = ['nano', 'vim', 'vi', 'code', 'notepad']
        editor = os.environ.get('EDITOR', None)
        
        if editor:
            editors.insert(0, editor)
        
        for ed in editors:
            try:
                subprocess.run([ed, temp_path])
                
                # 读取编辑后的内容
                with open(temp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析内容
                lines = content.split('\n')
                system_lines = []
                template_lines = []
                in_template = False
                
                for line in lines:
                    if line.startswith('# === SYSTEM MESSAGE ==='):
                        in_template = False
                        continue
                    elif line.startswith('# === TEMPLATE ==='):
                        in_template = True
                        continue
                    elif line.startswith('#'):
                        continue
                    
                    if in_template:
                        template_lines.append(line)
                    else:
                        system_lines.append(line)
                
                system_text = '\n'.join(system_lines).strip()
                template_text = '\n'.join(template_lines).strip()
                
                # 更新 prompt
                new_prompt = PromptConfig(
                    name=name,
                    description=prompt.description,
                    system=system_text,
                    template=template_text,
                    variables=prompt.variables
                )
                manager.set_global_prompt(name, new_prompt)
                
                # 保存配置
                if manager.save_to_config(config_path):
                    console.print("[green]✅ Prompt 已保存[/green]")
                else:
                    console.print("[red]❌ 保存失败[/red]")
                
                os.unlink(temp_path)
                return
                
            except FileNotFoundError:
                continue
        
        console.print("[red]❌ 未找到可用的编辑器[/red]")
        os.unlink(temp_path)
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@prompt_app.command("set")
def prompt_set(
    name: str = typer.Argument(..., help="prompt 名称"),
    group_id: str = typer.Option(..., "--group", "-g", help="指定 Group ID"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="prompt 内容（template）"),
    system: Optional[str] = typer.Option(None, "--system", "-s", help="system message")
):
    """为指定 Group 设置 prompt 覆盖"""
    console.print(f"[bold]为 Group '{group_id}' 设置 Prompt 覆盖：{name}[/bold]\n")
    
    try:
        from llm.prompt_manager import get_prompt_manager, PromptConfig
        from database.models import init_db
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        db_path = os.path.join(os.path.dirname(__file__), 'rss2pod.db')
        
        db = init_db(db_path)
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            db.close()
            return
        
        # 获取当前 prompt
        manager = get_prompt_manager(config_path)
        current_prompt = manager.get_prompt(name)
        
        # 创建新的覆盖配置
        new_prompt = PromptConfig(
            name=name,
            description=current_prompt.description,
            system=system if system is not None else current_prompt.system,
            template=content if content is not None else current_prompt.template,
            variables=current_prompt.variables
        )
        
        # 更新组别覆盖
        if 'prompt_overrides' not in group.prompt_overrides:
            group.prompt_overrides['prompt_overrides'] = {}
        
        group.prompt_overrides['prompt_overrides'][name] = new_prompt.to_dict()
        
        # 保存
        db.update_group(group)
        db.close()
        
        console.print("[green]✅ Prompt 覆盖已保存[/green]")
        console.print(f"   Group: {group_id}")
        console.print(f"   Prompt: {name}")
        if system:
            console.print(f"   System: {system[:50]}...")
        if content:
            console.print(f"   Template: {content[:50]}...")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@prompt_app.command("reset")
def prompt_reset(
    name: str = typer.Argument(..., help="prompt 名称"),
    group_id: str = typer.Option(..., "--group", "-g", help="指定 Group ID")
):
    """重置 Group 的 prompt 覆盖（恢复默认）"""
    console.print(f"[bold]重置 Group '{group_id}' 的 Prompt: {name}[/bold]\n")
    
    try:
        from database.models import init_db
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        db_path = os.path.join(os.path.dirname(__file__), 'rss2pod.db')
        
        db = init_db(db_path)
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            db.close()
            return
        
        # 移除覆盖配置
        if 'prompt_overrides' in group.prompt_overrides.get('prompt_overrides', {}):
            if name in group.prompt_overrides['prompt_overrides']:
                del group.prompt_overrides['prompt_overrides'][name]
        
        # 保存
        db.update_group(group)
        db.close()
        
        console.print("[green]✅ Prompt 已重置为默认值[/green]")
        console.print(f"   Group: {group_id}")
        console.print(f"   Prompt: {name}")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@prompt_app.command("export")
def prompt_export(
    filepath: str = typer.Argument(..., help="导出文件路径")
):
    """导出 prompts 到文件"""
    console.print(f"[bold]导出 Prompts 到：{filepath}[/bold]\n")
    
    try:
        from llm.prompt_manager import get_prompt_manager
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        manager = get_prompt_manager(config_path)
        
        if manager.export_prompts(filepath):
            console.print("[green]✅ Prompts 已导出[/green]")
            console.print(f"   文件：{filepath}")
        else:
            console.print("[red]❌ 导出失败[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@prompt_app.command("import")
def prompt_import(
    filepath: str = typer.Argument(..., help="导入文件路径"),
    merge: bool = typer.Option(True, "--merge/--replace", help="合并或替换现有配置")
):
    """从文件导入 prompts"""
    console.print(f"[bold]从文件导入 Prompts: {filepath}[/bold]\n")
    
    try:
        from llm.prompt_manager import get_prompt_manager
        
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        manager = get_prompt_manager(config_path)
        
        if manager.import_prompts(filepath, merge=merge):
            if manager.save_to_config(config_path):
                console.print("[green]✅ Prompts 已导入并保存[/green]")
            else:
                console.print("[yellow]⚠️ Prompts 已导入但保存失败[/yellow]")
        else:
            console.print("[red]❌ 导入失败[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== llm 命令组 ==============
llm_app = typer.Typer(help="大语言模型")
app.add_typer(llm_app, name="llm")


@llm_app.command()
def test():
    """测试 LLM 连接"""
    console.print("[bold]测试 LLM 连接...[/bold]")
    
    config = load_config()
    
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {config['llm']['api_key']}",
            "Content-Type": "application/json"
        }
        data = {
            "model": config['llm']['model'],
            "messages": [
                {"role": "system", "content": "你是一个助手。"},
                {"role": "user", "content": "你好，请用一句话介绍你自己"}
            ]
        }
        
        resp = requests.post(
            f"{config['llm']['base_url']}/chat/completions",
            headers=headers, json=data, timeout=30
        )
        
        if resp.status_code == 200:
            result = resp.json()
            content = result['choices'][0]['message']['content']
            console.print(f"[green]✅ 连接成功![/green]")
            console.print(f"\n[bold]回复:[/bold] {content}")
        else:
            console.print(f"[red]❌ API 错误：{resp.status_code}[/red]")
            console.print(f"响应：{resp.text[:200]}")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@llm_app.command()
def chat(message: str = typer.Argument(..., help="要发送的消息")):
    """与 LLM 对话"""
    console.print(f"[bold]发送：{message}[/bold]\n")
    
    config = load_config()
    
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {config['llm']['api_key']}",
            "Content-Type": "application/json"
        }
        data = {
            "model": config['llm']['model'],
            "messages": [{"role": "user", "content": message}]
        }
        
        resp = requests.post(
            f"{config['llm']['base_url']}/chat/completions",
            headers=headers, json=data, timeout=60
        )
        
        if resp.status_code == 200:
            result = resp.json()
            content = result['choices'][0]['message']['content']
            console.print(f"[green][bold]回复:[/bold] {content}[/green]")
        else:
            console.print(f"[red]❌ API 错误：{resp.status_code}[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== tts 命令组 ==============
tts_app = typer.Typer(help="文字转语音")
app.add_typer(tts_app, name="tts")


@tts_app.command()
def test():
    """测试 TTS 连接"""
    console.print("[bold]测试 TTS 连接...[/bold]")
    
    config = load_config()
    
    # 获取 TTS 配置（支持新的 providers 结构）
    tts_config = config.get('tts', {})
    active_provider = tts_config.get('active_provider', 'siliconflow')
    active_adapter = tts_config.get('active_adapter', 'moss')
    providers = tts_config.get('providers', {})
    
    if active_provider == 'siliconflow':
        provider_config = providers.get('siliconflow', {})
        adapter_config = provider_config.get('adapters', {}).get(active_adapter, {})
        api_key = provider_config.get('api_key')
        
        if api_key:
            console.print(f"[green]✅ SiliconFlow 已配置[/green]")
            console.print(f"   适配器：{active_adapter}")
            console.print(f"   模型：{adapter_config.get('model', 'N/A')}")
            console.print(f"   音色：{adapter_config.get('voice_host' if active_adapter == 'moss' else 'voice', 'N/A')}")
        else:
            console.print(f"[yellow]⚠️ SiliconFlow API Key 未配置[/yellow]")
    else:
        console.print(f"[yellow]⚠️ TTS 提供商：{active_provider}[/yellow]")


@tts_app.command("list-voices")
def list_voices():
    """列出可用音色"""
    console.print("[bold]SiliconFlow 可用音色[/bold]\n")
    
    config = load_config()
    tts_config = config.get('tts', {})
    model = tts_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
    
    # 根据模型确定音色前缀
    from tts.siliconflow_provider import SiliconFlowClient
    voices = SiliconFlowClient.get_available_voices(model)
    
    console.print(f"[dim]当前配置模型：{model}[/dim]\n")
    
    table = Table(box=box.ROUNDED)
    table.add_column("音色 ID", style="cyan")
    table.add_column("描述", style="green")
    
    for voice in voices:
        table.add_row(voice['id'], voice['name'])
    
    console.print(table)
    
    # 显示两个模型的音色说明
    console.print("\n[yellow]注意：MOSS 模型和 CosyVoice 模型使用各自独立的音色系统[/yellow]")
    console.print("  - MOSS 模型 (fnlp/MOSS-TTSD-v0.5): 使用 fnlp/MOSS-TTSD-v0.5:xxx 格式")
    console.print("  - CosyVoice 模型 (FunAudioLLM/CosyVoice2-0.5B): 使用 FunAudioLLM/CosyVoice2-0.5B:xxx 格式")


@tts_app.command()
def listen(
    text: str = typer.Argument(..., help="要转换为音频的文本"),
    voice: Optional[str] = typer.Option(
        None, "--voice", "-v", 
        help="音色（不指定则使用配置文件中的默认音色）"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", 
        help="输出音频文件路径（不指定则自动生成）"
    )
):
    """
    将文本转换为音频并保存到本地
    
    示例:
        rss2pod tts listen "你好，欢迎收听"
        rss2pod tts listen "你好" --voice FunAudioLLM/CosyVoice2-0.5B:alex
        rss2pod tts listen "你好" -o ./output.mp3
    """
    console.print(f"[bold]TTS 转换[/bold]")
    console.print(f"输入文本：{text[:50]}{'...' if len(text) > 50 else ''}\n")
    
    config = load_config()
    
    # 获取 TTS 配置（支持新的 providers 结构）
    tts_config = config.get('tts', {})
    active_provider = tts_config.get('active_provider', 'siliconflow')
    active_adapter = tts_config.get('active_adapter', 'moss')
    providers = tts_config.get('providers', {})
    
    # 获取当前 provider 和 adapter 的配置
    provider_config = providers.get(active_provider, {})
    adapter_config = provider_config.get('adapters', {}).get(active_adapter, {})
    
    provider = active_provider
    api_key = provider_config.get('api_key')
    base_url = provider_config.get('base_url', 'https://api.siliconflow.cn/v1')
    model = adapter_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
    
    # 根据 adapter 类型确定默认音色
    if active_adapter == 'cosyvoice':
        default_voice = adapter_config.get('voice', 'claire')
    else:
        default_voice = f"fnlp/MOSS-TTSD-v0.5:{adapter_config.get('voice_host', 'alex')}"
    
    # 使用命令行参数覆盖或默认值
    selected_voice = voice or default_voice
    
    if provider != 'siliconflow':
        console.print(f"[yellow]⚠️ 当前配置的 TTS 提供商是 {provider}，但 listen 命令仅支持 siliconflow[/yellow]")
    
    if not api_key:
        console.print("[red]❌ TTS API Key 未配置[/red]")
        console.print("请运行：[bold]rss2pod config set tts.providers.siliconflow.api_key <your_api_key>[/bold]")
        return
    
    console.print(f"使用适配器：{active_adapter}")
    console.print(f"使用模型：{model}")
    console.print(f"使用音色：{selected_voice}")
    
    # 生成输出文件路径
    if not output:
        import hashlib
        import time
        timestamp = int(time.time())
        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        output = f"./output_{text_hash}_{timestamp}.mp3"
    
    # 调用 SiliconFlow 客户端
    try:
        from tts.siliconflow_provider import SiliconFlowClient
        
        async def synthesize():
            client = SiliconFlowClient(
                api_key=api_key,
                base_url=base_url,
                model=model
            )
            
            try:
                # 检测是否使用 CosyVoice 模型（单人）还是 MOSS 模型（双人/单人）
                if 'CosyVoice' in model:
                    # CosyVoice 单人模式
                    # 使用完整的音色格式（格式：FunAudioLLM/CosyVoice2-0.5B:claire）
                    # 如果 selected_voice 不包含模型前缀，则自动添加
                    if ':' not in selected_voice:
                        # 只提供了音色名称，需要添加模型前缀
                        voice_full = f"{model}:{selected_voice}"
                    else:
                        # 已提供完整格式
                        voice_full = selected_voice
                    audio_data = await client.synthesize(text, voice=voice_full)
                else:
                    # MOSS 模型：支持单人 voice 模式或双人 references 模式
                    # 如果 selected_voice 包含当前模型前缀，使用 voice 模式
                    if selected_voice and selected_voice.startswith('fnlp/MOSS-TTSD-v0.5:'):
                        # MOSS 单人 voice 模式
                        audio_data = await client.synthesize(text, voice=selected_voice)
                    else:
                        # MOSS 双人 references 模式（向后兼容）
                        voice_host = tts_config.get('voice_host', 'alex')
                        voice_co_host = tts_config.get('voice_co_host', 'claire')
                        references = client.build_references(
                            host_voice=voice_host,
                            co_host_voice=voice_co_host
                        )
                        audio_data = await client.synthesize(text, references=references)
                
                # 保存文件
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(audio_data)
                
                return str(output_path.resolve()), audio_data
                
            finally:
                await client.close()
        
        import asyncio
        from pathlib import Path
        
        audio_path, audio_data = asyncio.run(synthesize())
        
        # 显示结果
        file_size = len(audio_data)
        duration_estimate = file_size / 16000  # 粗略估算（假设 16kbps）
        
        console.print(f"\n[green]✅ 转换成功![/green]")
        console.print(f"   音频路径：{audio_path}")
        console.print(f"   文件大小：{file_size} 字节 ({file_size / 1024:.2f} KB)")
        console.print(f"   预计时长：{duration_estimate:.1f} 秒")
        
    except ImportError as e:
        console.print(f"[red]❌ 导入错误：{e}[/red]")
        console.print("请确保已安装依赖：pip install aiohttp")
    except Exception as e:
        console.print(f"[red]❌ 转换失败：{e}[/red]")
        sys.exit(1)


# ============== db 命令组 ==============
db_app = typer.Typer(help="数据库管理")
app.add_typer(db_app, name="db")


@db_app.command()
def stats():
    """显示数据库统计"""
    console.print(Panel("[bold blue]数据库统计[/bold blue]", box=box.DOUBLE))
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        stats = db.get_stats()
        
        console.print(f"\n[bold]📊 统计信息[/bold]")
        console.print(f"   文章总数：{stats.get('total_articles', 0)}")
        console.print(f"   启用 Group: {stats.get('enabled_groups', 0)}")
        console.print(f"   期数总数：{stats.get('total_episodes', 0)}")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@db_app.command("list-articles")
def db_list_articles(
    limit: int = typer.Option(20, "--limit", "-l"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="文章状态：pending, processed, all"),
    all_articles: bool = typer.Option(False, "--all", "-a", help="显示所有文章")
):
    """列出文章
    
    默认显示所有文章。使用 --status pending 只显示待处理的文章。
    """
    config = load_config()
    
    # 确定查询状态
    query_status = "all"
    if status:
        if status not in ["pending", "processed"]:
            console.print(f"[red]❌ 无效状态：{status} (请使用 pending, processed 或 all)[/red]")
            return
        query_status = status
    elif all_articles:
        query_status = "all"
    
    status_text = {"pending": "待处理", "processed": "已处理", "all": "所有"}.get(query_status, query_status)
    console.print(f"[bold]文章列表 ({status_text}, 限制：{limit})[/bold]\n")
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        # 根据状态查询
        if query_status == "all":
            cursor = db.conn.cursor()
            cursor.execute('SELECT * FROM articles LIMIT ?', (limit,))
            rows = cursor.fetchall()
            articles = [db._row_to_article(row) for row in rows]
        else:
            articles = db.get_articles_by_status(query_status, limit)
        
        if not articles:
            console.print(f"[yellow]没有找到 {status_text} 状态的文章[/yellow]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("标题", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("Source", style="blue")
        
        for article in articles:
            table.add_row(
                article.id[:12] + '...' if len(article.id) > 12 else article.id,
                article.title[:50] + '...' if len(article.title) > 50 else article.title,
                article.status,
                article.source[:20] + '...' if len(article.source) > 20 else article.source
            )
        
        console.print(table)
        console.print(f"\n共 {len(articles)} 篇文章")
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@db_app.command("list-groups")
def db_list_groups():
    """列出 Group"""
    console.print("[bold]Group 列表[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        groups = db.get_all_groups()
        
        if not groups:
            console.print("[yellow]没有找到 Group[/yellow]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("RSS 源", style="blue")
        
        for group in groups:
            table.add_row(
                group.id,
                group.name,
                "✅" if group.enabled else "❌",
                f"{len(group.rss_sources)} 个"
            )
        
        console.print(table)
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== 入口 ==============

# ============== generate 命令 ==============
generate_app = typer.Typer(help="播客生成")
app.add_typer(generate_app, name="generate")


@generate_app.command()
def run(
    group_id: str = typer.Argument(None, help="Group ID（不填则触发所有启用的组）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="模拟运行，不实际生成"),
    all_groups: bool = typer.Option(False, "--all", help="触发所有启用的组"),
    force: bool = typer.Option(False, "--force", help="强制使用最新三篇文章，忽略文章更新检查"),
    export_articles: bool = typer.Option(False, "--export-articles", help="将抓取到的文章列表导出到 JSON 文件"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细输出（DEBUG 日志级别）")
):
    """手动触发生成播客期数
    
    全局选项 --verbose/-v 放在命令前使用，例如：
        rss2pod --verbose generate run
        rss2pod -v generate run group-1
    """
    
    config = load_config()
    
    # 根据 --verbose 设置日志级别
    log_level = "DEBUG" if get_verbose() else "INFO"
    
    try:
        from database.models import init_db
        from services.pipeline.group_processor import process_group_sync
        from orchestrator.logging_config import setup_logging
        
        # 设置日志级别
        setup_logging(level=log_level)
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        if all_groups or group_id is None:
            groups = db.get_all_groups(enabled_only=True)
            if not groups:
                console.print("[yellow]没有启用的 Group[/yellow]")
                return
            console.print(f"[bold]将触发 {len(groups)} 个启用的 Group[/bold]\n")
        else:
            group = db.get_group(group_id)
            if not group:
                console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
                return
            groups = [group]
        
        success_count = 0
        fail_count = 0
        
        for group in groups:
            console.print(Panel(f"[bold]处理 Group: {group.name}[/bold]", box=box.ROUNDED))
            console.print(f"  ID: {group.id}")
            console.print(f"  触发类型：{group.trigger_type}")
            console.print(f"  RSS 源：{len(group.rss_sources)} 个")
            
            if force:
                console.print("  [yellow]⚠️ 强制模式 - 将使用最新三篇文章[/yellow]")
            
            if export_articles:
                console.print("  [cyan]📄 文章导出模式 - 将导出抓取的文章到 JSON 文件[/cyan]")
            
            if dry_run:
                console.print("  [yellow]⚠️ 模拟运行模式 - 不会实际生成[/yellow]")
                console.print("  [dim]（模拟：检查未读文章 -> 摘要 -> 生成脚本 -> TTS）[/dim]\n")
            else:
                try:
                    result = process_group_sync(group.id, db_path, force=force, export_articles=export_articles)
                    
                    if result.success:
                        console.print(f"[green]✓ 成功[/green]")
                        console.print(f"  Episode: {result.episode_id}")
                        console.print(f"  完成阶段：{', '.join(result.stages_completed)}")
                        console.print(f"  获取文章：{result.articles_fetched}")
                        success_count += 1
                    else:
                        console.print(f"[red]✗ 失败[/red]")
                        console.print(f"  失败阶段：{result.failed_stage}")
                        console.print(f"  错误：{result.error_message}")
                        fail_count += 1
                except Exception as e:
                    console.print(f"[red]✗ 异常：{e}[/red]")
                    fail_count += 1
            
            console.print()
        
        db.close()
        
        if dry_run:
            console.print("[bold]模拟运行完成[/bold]")
        else:
            console.print(f"\n[bold]处理完成：{success_count} 成功，{fail_count} 失败[/bold]")
        
    except ImportError as e:
        console.print(f"[red]❌ 导入错误：{e}[/red]")
        console.print("请确保已安装依赖：pip install croniter aiohttp")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@generate_app.command()
def history(
    group_id: Optional[str] = typer.Option(None, "--group", "-g", help="指定 Group ID"),
    limit: int = typer.Option(10, "--limit", "-l", help="显示数量")
):
    """查看生成历史"""
    console.print(f"[bold]生成历史 (限制：{limit})[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        if group_id:
            episodes = db.get_episodes_by_group(group_id, limit)
        else:
            cursor = db.conn.cursor()
            cursor.execute('SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?', (limit,))
            episodes = [db._row_to_episode(row) for row in cursor.fetchall()]
        
        if not episodes:
            console.print("[yellow]没有找到期数[/yellow]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Group", style="green")
        table.add_column("标题", style="blue")
        table.add_column("期数", style="yellow")
        table.add_column("音频", style="magenta")
        
        for ep in episodes:
            table.add_row(
                ep.id[:8] + '...',
                ep.group_id,
                ep.title[:40] + '...' if len(ep.title) > 40 else ep.title,
                f"#{ep.episode_number}",
                "✅" if ep.audio_path else "❌"
            )
        
        console.print(table)
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== trigger 命令组 ==============
trigger_app = typer.Typer(help="触发器管理")
app.add_typer(trigger_app, name="trigger")


@trigger_app.command()
def status(group_id: str = typer.Argument(..., help="Group ID")):
    """查看触发器状态"""
    console.print(f"[bold]触发器状态：{group_id}[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        console.print(f"Group: {group.name}")
        console.print(f"状态：{'✅ 启用' if group.enabled else '❌ 禁用'}")
        console.print(f"触发类型：{group.trigger_type}")
        console.print(f"触发配置：{json.dumps(group.trigger_config, indent=2)}")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@trigger_app.command()
def set(
    group_id: str = typer.Argument(..., help="Group ID"),
    trigger_type: str = typer.Option("time", "--type", "-t", help="触发类型"),
    cron: str = typer.Option("0 9 * * *", "--cron", "-c", help="Cron 表达式"),
    threshold: int = typer.Option(10, "--threshold", "-n", help="数量阈值")
):
    """设置触发器"""
    console.print(f"[bold]设置触发器：{group_id}[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        group.trigger_type = trigger_type
        group.trigger_config = {
            "cron": cron,
            "threshold": threshold
        }
        
        db.update_group(group)
        console.print("[green]✅ 触发器已更新[/green]")
        console.print(f"  类型：{trigger_type}")
        console.print(f"  Cron: {cron}")
        console.print(f"  阈值：{threshold}")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@trigger_app.command()
def disable(group_id: str = typer.Argument(..., help="Group ID")):
    """禁用触发器（禁用 Group）"""
    console.print(f"[bold]禁用触发器：{group_id}[/bold]")
    
    config = load_config()
    
    try:
        from database.models import init_db
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        group = db.get_group(group_id)
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        group.enabled = False
        db.update_group(group)
        console.print("[green]✅ Group 已禁用，触发器停止工作[/green]")
        
        db.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== scheduler 命令组 ==============
scheduler_app = typer.Typer(help="调度器管理")
app.add_typer(scheduler_app, name="scheduler")


@scheduler_app.command()
def start():
    """启动调度器（守护进程）"""
    console.print(Panel("[bold blue]启动 RSS2Pod 调度器[/bold blue]", box=box.DOUBLE))
    
    config = load_config()
    
    try:
        from orchestrator import Scheduler
        
        orchestrator_config = config.get('orchestrator', {})
        log_config = config.get('logging', {})
        orchestrator_config['logging'] = log_config
        
        scheduler = Scheduler(orchestrator_config, db_path=config.get('db_path', 'rss2pod.db'))
        
        console.print("[green]✓[/green] 调度器已启动")
        console.print(f"  检查间隔：{orchestrator_config.get('check_interval_seconds', 60)}秒")
        console.print(f"  最大并发：{orchestrator_config.get('max_concurrent_groups', 3)}个 Group")
        console.print("\n[dim]按 Ctrl+C 停止调度器[/dim]\n")
        
        scheduler.start()
        
    except ImportError as e:
        console.print(f"[red]❌ 导入错误：{e}[/red]")
        console.print("请确保已安装依赖：pip install croniter aiohttp")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]调度器已停止[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@scheduler_app.command()
def status():
    """查看调度器状态"""
    console.print("[bold]调度器状态[/bold]\n")
    
    config = load_config()
    
    try:
        from database.models import init_db
        from orchestrator.state_manager import StateManager
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        state_manager = StateManager(db)
        
        # 获取状态统计
        stats = state_manager.get_stats()
        
        console.print(f"[bold]处理状态统计:[/bold]")
        for status, count in stats.get('states_by_status', {}).items():
            status_icon = {"idle": "⏸️", "running": "▶️", "error": "❌", "disabled": "🚫"}.get(status, "•")
            console.print(f"  {status_icon} {status}: {count}")
        
        console.print(f"\n[bold]运行中管道：[/bold]{stats.get('running_pipelines', 0)}")
        console.print(f"[bold]今日运行：[/bold]{stats.get('runs_today', 0)}")
        
        # 显示启用的 Group
        groups = db.get_all_groups(enabled_only=True)
        console.print(f"\n[bold]启用的 Group: [/bold]{len(groups)}")
        for group in groups[:5]:
            trigger_config = group.trigger_config or {}
            cron = trigger_config.get('cron', 'N/A')
            console.print(f"  • {group.name} (Cron: {cron})")
        
        if len(groups) > 5:
            console.print(f"  ... 还有 {len(groups) - 5} 个")
        
        db.close()
        
    except ImportError as e:
        console.print(f"[red]❌ 导入错误：{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@scheduler_app.command()
def stop():
    """停止调度器"""
    console.print("[yellow]⚠️  注意：调度器需要在运行它的进程中停止[/yellow]")
    console.print("\n如果调度器在后台运行，请使用以下方法停止:")
    console.print("  1. 找到进程：ps aux | grep 'rss2pod scheduler'")
    console.print("  2. 发送信号：kill <PID>")
    console.print("\n或者直接在运行调度器的终端按 Ctrl+C")


@scheduler_app.command()
def run(group_id: str = typer.Argument(None, help="Group ID（不填则触发所有启用的组）")):
    """手动触发一次调度
    
    全局选项 --verbose/-v 放在命令前使用，例如：
        rss2pod --verbose scheduler run group-1
    """
    console.print("[bold]手动触发调度[/bold]\n")
    
    config = load_config()
    
    # 根据 --verbose 设置日志级别
    log_level = "DEBUG" if get_verbose() else "INFO"
    
    try:
        from database.models import init_db
        from services.pipeline.group_processor import process_group_sync
        from orchestrator.logging_config import setup_logging
        
        # 设置日志级别
        setup_logging(level=log_level)
        
        db_path = os.path.join(os.path.dirname(__file__), config.get('db_path', 'rss2pod.db'))
        db = init_db(db_path)
        
        if group_id:
            groups = [db.get_group(group_id)] if db.get_group(group_id) else []
            if not groups:
                console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
                return
        else:
            groups = db.get_all_groups(enabled_only=True)
        
        if not groups:
            console.print("[yellow]没有需要处理的 Group[/yellow]")
            return
        
        console.print(f"将处理 {len(groups)} 个 Group\n")
        
        for group in groups:
            console.print(Panel(f"[bold]处理：{group.name}[/bold]", box=box.ROUNDED))
            
            try:
                result = process_group_sync(group.id, db_path)
                
                if result.success:
                    console.print(f"[green]✓ 成功[/green]")
                    console.print(f"  Episode: {result.episode_id}")
                    console.print(f"  完成阶段：{', '.join(result.stages_completed)}")
                    console.print(f"  获取文章：{result.articles_fetched}")
                else:
                    console.print(f"[red]✗ 失败[/red]")
                    console.print(f"  失败阶段：{result.failed_stage}")
                    console.print(f"  错误：{result.error_message}")
                
            except Exception as e:
                console.print(f"[red]✗ 异常：{e}[/red]")
            
            console.print()
        
        db.close()
        
    except ImportError as e:
        console.print(f"[red]❌ 导入错误：{e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@scheduler_app.command()
def test_trigger(group_id: str = typer.Argument(..., help="Group ID")):
    """测试触发条件（不实际执行 pipeline）
    
    用于诊断触发器是否会触发，以及原因。
    """
    console.print("[bold]测试触发条件[/bold]\n")
    
    config = load_config()
    
    try:
        from rss2pod.services import SchedulerService
        
        scheduler_service = get_service(SchedulerService)
        result = scheduler_service.test_trigger(group_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            scheduler_service.close()
            return
        
        data = result.data
        
        # 显示基本信息
        console.print(Panel(f"[bold]{data['group_name']}[/bold]", box=box.DOUBLE))
        console.print(f"ID:    {data['group_id']}")
        console.print(f"状态:  {'✅ 启用' if data['enabled'] else '❌ 禁用'}")
        console.print(f"类型:  {data['trigger_type']}")
        
        # Cron 触发信息
        if 'cron' in data:
            cron = data['cron']
            console.print(f"\n[bold]⏰ Cron 触发[/bold]")
            console.print(f"  表达式: {cron.get('expression') or '未配置'}")
            
            if cron.get('expression'):
                next_run = cron.get('next_run')
                if next_run:
                    console.print(f"  下次运行: {next_run}")
                
                if cron.get('will_trigger'):
                    console.print(f"  状态: [green]✅ 会触发[/green]")
                else:
                    remaining = cron.get('remaining', 'N/A')
                    console.print(f"  状态: [red]❌ 不会触发 (还差 {remaining})[/red]")
        
        # 数量触发信息
        if 'count' in data:
            count = data['count']
            console.print(f"\n[bold]📊 数量触发[/bold]")
            console.print(f"  阈值: {count.get('threshold', 0)} 篇")
            console.print(f"  当前: {count.get('current', 0)} 篇")
            
            if count.get('will_trigger'):
                console.print(f"  状态: [green]✅ 会触发[/green]")
            else:
                remaining = count.get('remaining', 0)
                console.print(f"  状态: [red]❌ 不会触发 (还差 {remaining} 篇)[/red]")
        
        # 结论
        console.print()
        if data.get('will_trigger'):
            console.print(Panel("[green]✅ 会触发[/green]", box=box.ROUNDED))
        else:
            console.print(Panel("[red]❌ 不会触发[/red]", box=box.ROUNDED))
        
        # 原因
        reasons = data.get('reasons', [])
        if reasons:
            console.print("\n[bold]原因:[/bold]")
            for reason in reasons:
                console.print(f"  • {reason}")
        
        scheduler_service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        import traceback
        if get_verbose():
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


# ============== assets 命令组 ==============
assets_app = typer.Typer(help="资源文件管理")
app.add_typer(assets_app, name="assets")


@assets_app.command("list")
def assets_list(
    group_id: str = typer.Argument(..., help="Group ID")
):
    """列出 Group 下所有 Episode 的资源"""
    console.print(f"[bold]Episode 资源列表：{group_id}[/bold]\n")
    
    try:
        from services.asset_service import list_episode_assets
        
        episodes = list_episode_assets(group_id)
        
        if not episodes:
            console.print("[yellow]没有找到任何 Episode 资源[/yellow]")
            return
        
        for episode in episodes:
            timestamp = episode.get('episode_timestamp', 'unknown')
            # 获取 assets 字典
            assets = episode.get('assets', {})
            
            console.print(Panel(f"[bold]Episode {timestamp}[/bold]", box=box.ROUNDED))
            console.print(f"资源目录：{assets.get('assets_dir', 'N/A')}")
            
            # 文稿文件
            source_summaries = assets.get('source_summaries')
            group_summary = assets.get('group_summary')
            podcast_script = assets.get('podcast_script')
            
            has_files = source_summaries or group_summary or podcast_script
            if has_files:
                console.print(f"\n[bold]文稿文件:[/bold]")
                if source_summaries:
                    console.print(f"  • source_summaries.json")
                if group_summary:
                    console.print(f"  • group_summary.json")
                if podcast_script:
                    console.print(f"  • podcast_script.json")
            
            # 分段音频 - audio_segments 是文件路径列表
            audio_segments = assets.get('audio_segments', [])
            if audio_segments:
                console.print(f"\n[bold]分段音频:[/bold]")
                for seg_path in audio_segments:
                    import os
                    filename = os.path.basename(seg_path)
                    file_size = os.path.getsize(seg_path) if os.path.exists(seg_path) else 0
                    size_kb = file_size / 1024
                    console.print(f"  • {filename} ({size_kb:.1f} KB)")
            else:
                console.print(f"\n[yellow]⚠️  无分段音频（可能已清理）[/yellow]")
            
            console.print()
        
        console.print(f"共 {len(episodes)} 个 Episode")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        import traceback
        if get_verbose():
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@assets_app.command("show")
def assets_show(
    group_id: str = typer.Argument(..., help="Group ID"),
    timestamp: str = typer.Argument(..., help="Episode 时间戳")
):
    """查看指定 Episode 的资源详情"""
    console.print(f"[bold]Episode 资源详情：{group_id} / {timestamp}[/bold]\n")
    
    try:
        from services.asset_service import get_episode_assets
        
        assets = get_episode_assets(group_id, timestamp)
        
        if not assets:
            console.print("[yellow]未找到该 Episode 资源[/yellow]")
            return
        
        console.print(f"资源目录：{assets.get('assets_dir')}")
        
        # 文稿文件
        source_summaries = assets.get('source_summaries')
        group_summary = assets.get('group_summary')
        podcast_script = assets.get('podcast_script')
        
        has_files = source_summaries or group_summary or podcast_script
        if has_files:
            console.print(f"\n[bold]文稿文件:[/bold]")
            if source_summaries:
                console.print(f"  • source_summaries.json")
            if group_summary:
                console.print(f"  • group_summary.json")
            if podcast_script:
                console.print(f"  • podcast_script.json")
        
        # 分段音频 - audio_segments 是文件路径列表
        audio_segments = assets.get('audio_segments', [])
        if audio_segments:
            console.print(f"\n[bold]分段音频:[/bold]")
            for seg_path in audio_segments:
                import os
                filename = os.path.basename(seg_path)
                file_size = os.path.getsize(seg_path) if os.path.exists(seg_path) else 0
                size_kb = file_size / 1024
                console.print(f"  • {filename} ({size_kb:.1f} KB)")
        else:
            console.print(f"\n[yellow]⚠️  无分段音频[/yellow]")
        
        console.print()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@assets_app.command("cleanup")
def assets_cleanup(
    group_id: str = typer.Argument(..., help="Group ID"),
    timestamp: str = typer.Argument(None, help="Episode 时间戳（不填则清理所有）"),
    force: bool = typer.Option(False, "--force", "-f", help="强制删除，不确认")
):
    """清理 Episode 中间文件（保留最终音频）"""
    if timestamp:
        console.print(f"[bold]清理 Episode 中间文件：{group_id} / {timestamp}[/bold]")
    else:
        console.print(f"[bold]清理 Group 所有 Episode 中间文件：{group_id}[/bold]")
    
    try:
        from services.asset_service import cleanup_episode_assets, list_episode_assets
        
        if timestamp:
            # 清理指定 Episode
            if not force:
                if not Confirm.ask("\n此操作将删除中间文件（分段音频、文稿），但保留最终音频。确认删除？"):
                    console.print("[yellow]已取消[/yellow]")
                    return
            
            cleanup_episode_assets(group_id, timestamp)
            console.print(f"[green]✅ 已清理 Episode {timestamp} 的中间文件[/green]")
        else:
            # 清理所有 Episode
            episodes = list_episode_assets(group_id)
            if not episodes:
                console.print("[yellow]没有找到任何 Episode 资源[/yellow]")
                return
            
            console.print(f"\n找到 {len(episodes)} 个 Episode:")
            for ep in episodes:
                ts = ep.get('episode_timestamp', 'unknown')
                console.print(f"  • {ts}")
            
            if not force:
                if not Confirm.ask("\n此操作将删除所有中间文件（分段音频、文稿），但保留最终音频。确认删除？"):
                    console.print("[yellow]已取消[/yellow]")
                    return
            
            for ep in episodes:
                ts = ep.get('episode_timestamp', 'unknown')
                cleanup_episode_assets(group_id, ts)
                console.print(f"  [green]✓ 已清理 {ts}[/green]")
            
            console.print(f"\n[green]✅ 已清理 {len(episodes)} 个 Episode 的中间文件[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== web 命令组 ==============
web_app = typer.Typer(help="Web 服务管理")
app.add_typer(web_app, name="web")


@web_app.command()
def start(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="监听地址"),
    port: int = typer.Option(8080, "--port", "-p", help="监听端口")
):
    """启动 Web 服务器"""
    console.print(Panel("[bold blue]启动 RSS2Pod Web 服务器[/bold blue]", box=box.DOUBLE))
    
    try:
        from rss2pod.web import start_server
        start_server(host=host, port=port)
    except ImportError as e:
        console.print(f"[red]❌ 导入错误：{e}[/red]")
        console.print("请确保已安装依赖：pip install fastapi uvicorn")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== 入口 ==============
if __name__ == "__main__":
    app()
