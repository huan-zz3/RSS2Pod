#!/usr/bin/env python3
"""
RSS2Pod 命令行调试工具

仅包含 UI/显示逻辑，所有业务逻辑封装在 services/ 目录下的服务模块中。
"""

# 添加父目录到路径以便导入 rss2pod 模块
import sys
import hashlib
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import typer
import json
import subprocess
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt

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
# 这些函数保留用于向后兼容，推荐使用 ConfigService
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
            console.print("   [green]✅ 连接正常[/green]")
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
            console.print("   [green]✅ 数据库正常[/green]")
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
        console.print("   [yellow]⚠️  模块未导入[/yellow]")
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
    console.print("[green]✅ 配置已更新[/green]")
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
    
    console.print("[green]✅ 配置已重置[/green]")
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
    
    console.print("[bold]正在获取文章...[/bold]")
    console.print(f"订阅源 ID: [green]{identifier}[/green]\n")
    
    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        
        feed_id = int(identifier)
        
        result = service.get_cache_articles(limit=limit, unread=unread, feed_id=feed_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        items = result.data.get('items', [])
        
        if not items:
            status_text = "未读" if unread else "所有"
            console.print(f"[yellow]没有找到{status_text}文章[/yellow]")
            console.print("[dim]提示：请先运行 `rss2pod fever sync` 同步文章到本地缓存[/dim]")
            service.close()
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
            title = item.get('title', '')[:50]
            if len(item.get('title', '')) > 50:
                title += '...'
            
            created_time = item.get('created_on_time')
            if created_time:
                pub_time = datetime.fromtimestamp(int(created_time)).strftime('%Y-%m-%d %H:%M')
            else:
                pub_time = '-'
            
            table.add_row(
                str(item.get('id')),
                title,
                pub_time
            )
        
        console.print(table)
        console.print(f"\n共 {len(items)} 篇文章")
        
        service.close()
        
    except ValueError:
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
    
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        result = service.list_groups()
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        groups = result.data
        
        if not groups:
            console.print("[yellow]没有找到 Group[/yellow]")
            console.print("使用 [bold]rss2pod group create[/bold] 创建第一个 Group")
            service.close()
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("RSS 源", style="blue")
        table.add_column("触发", style="magenta")
        
        for group in groups:
            table.add_row(
                group['id'],
                group['name'],
                "✅" if group['enabled'] else "❌",
                f"{len(group['rss_sources'])} 个",
                group['trigger_type']
            )
        
        console.print(table)
        console.print(f"\n共 {len(groups)} 个 Group")
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def show(group_id: str = typer.Argument(..., help="Group ID")):
    """查看 Group 详情"""
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        result = service.get_group(group_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        group = result.data
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            service.close()
            return
        
        console.print(Panel(f"[bold]{group['name']}[/bold]", box=box.DOUBLE))
        console.print(f"ID:          {group['id']}")
        console.print(f"描述：       {group.get('description') or '-'}")
        console.print(f"状态：       {'✅ 启用' if group['enabled'] else '❌ 禁用'}")
        console.print(f"触发类型：   {group['trigger_type']}")
        cron = group.get('trigger_config', {}).get('cron', '-') if group.get('trigger_config') else '-'
        console.print(f"Cron:        {cron}")
        console.print(f"播客结构：   {group['podcast_structure']}")
        console.print(f"英语学习：   {group['english_learning_mode']}")
        console.print(f"音频调速：   {group['audio_speed']}x")
        console.print(f"\n[bold]RSS 源 ({len(group['rss_sources'])} 个):[/bold]")
        for i, source in enumerate(group['rss_sources'], 1):
            console.print(f"  {i}. {source}")
        
        service.close()
        
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
            from rss2pod.services import FeverService
            service = get_service(FeverService)
            result = service.sync_feeds()
            
            if result.success:
                console.print(f"[green]✅ 已同步 {result.data.get('feeds_count', 0)} 个订阅源[/green]\n")
            else:
                console.print(f"[red]❌ 同步失败：{result.error_message}[/red]")
                console.print("你可以稍后手动添加 RSS 源 URL\n")
                sources_file = None
            service.close()
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
            except (ValueError, IndexError):
                console.print("[yellow]无效选择，稍后手动添加[/yellow]\n")
    
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
    total_steps = 5  # 基础步骤
    if trigger_type in ["count", "combined"]:
        total_steps += 1  # 数量阈值
    if trigger_type in ["time", "combined"]:
        total_steps += 1  # Cron 表达式
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
    audio_speed = FloatPrompt.ask(
        "音频调速 (0.5-2.0，1.0 为正常速度)",
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
    
    # 创建 Group - 使用 GroupService
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        
        trigger_config = {"cron": cron_expr, "threshold": count_threshold}
        
        result = service.create_group({
            'name': group_name,
            'description': description,
            'rss_sources': selected_sources,
            'podcast_structure': podcast_structure,
            'english_learning_mode': english_learning,
            'audio_speed': audio_speed,
            'trigger_type': trigger_type,
            'trigger_config': trigger_config
        })
        
        if result.success:
            group_id = result.data.get('group', {}).get('id')
            console.print("\n[green]✅ Group 创建成功![/green]")
            console.print(f"   ID: {group_id}")
            console.print(f"\n使用 [bold]rss2pod group show {group_id}[/bold] 查看详情")
        else:
            console.print(f"[red]❌ 创建失败：{result.error_message}[/red]")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 创建失败：{e}[/red]")
        sys.exit(1)


@group_app.command()
def edit(group_id: str = typer.Argument(..., help="Group ID")):
    """编辑 Group"""
    console.print(f"[bold]编辑 Group: {group_id}[/bold]\n")
    
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        
        # 获取当前 Group
        result = service.get_group(group_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        group = result.data
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            service.close()
            return
        
        console.print("当前配置:")
        console.print(f"  名称：     {group['name']}")
        console.print(f"  描述：     {group.get('description') or '-'}")
        console.print(f"  RSS 源：    {len(group['rss_sources'])} 个")
        console.print(f"  触发类型： {group['trigger_type']}")
        cron = group.get('trigger_config', {}).get('cron', '-') if group.get('trigger_config') else '-'
        console.print(f"  Cron:      {cron}")
        console.print(f"  播客结构： {group['podcast_structure']}")
        console.print(f"  英语学习： {group['english_learning_mode']}")
        console.print(f"  音频调速： {group['audio_speed']}x")
        console.print()
        
        # 交互式修改
        update_data = {}
        
        if Confirm.ask("修改名称？", default=False):
            update_data['name'] = Prompt.ask("新名称", default=group['name'])
        
        if Confirm.ask("修改描述？", default=False):
            update_data['description'] = Prompt.ask("新描述", default=group.get('description') or "")
        
        if Confirm.ask("修改 RSS 源？", default=False):
            console.print("当前 RSS 源:")
            for i, source in enumerate(group['rss_sources'], 1):
                console.print(f"  {i}. {source}")
            
            console.print("\n输入要删除的源编号（逗号分隔），或从本地订阅源中添加")
            action = Prompt.ask("操作（delete/add/skip）", choices=["delete", "add", "skip"], default="skip")
            
            if action == "delete":
                indices = Prompt.ask("要删除的编号")
                try:
                    to_remove = [int(x.strip()) - 1 for x in indices.split(',')]
                    update_data['rss_sources'] = [s for i, s in enumerate(group['rss_sources']) if i not in to_remove]
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
                                    current_sources = update_data.get('rss_sources', group['rss_sources'])
                                    if url not in current_sources:
                                        current_sources.append(url)
                                        update_data['rss_sources'] = current_sources
                                        console.print(f"[green]✅ 已添加：{sources[idx]['title']}[/green]")
                                    else:
                                        console.print("[yellow]⚠️ 该源已存在[/yellow]")
                                else:
                                    console.print("[red]❌ 无效编号[/red]")
                            except ValueError:
                                console.print("[red]❌ 请输入数字编号[/red]")
        
        if Confirm.ask("修改触发类型？", default=False):
            update_data['trigger_type'] = Prompt.ask(
                "新触发类型",
                choices=["time", "count", "llm", "combined"],
                default=group['trigger_type']
            )
        
        if Confirm.ask("修改 Cron 表达式？", default=False):
            current_trigger_config = group.get('trigger_config', {})
            update_data['trigger_config'] = {
                **current_trigger_config,
                'cron': Prompt.ask("新 Cron 表达式", default=current_trigger_config.get('cron', '0 9 * * *'))
            }
        
        if Confirm.ask("修改播客结构？", default=False):
            update_data['podcast_structure'] = Prompt.ask(
                "新播客结构",
                choices=["single", "dual"],
                default=group['podcast_structure']
            )
        
        if Confirm.ask("修改英语学习？", default=False):
            update_data['english_learning_mode'] = Prompt.ask(
                "新英语学习设置",
                choices=["off", "vocab", "translation"],
                default=group['english_learning_mode']
            )
        
        if Confirm.ask("修改音频调速？", default=False):
            audio_speed = FloatPrompt.ask(
                "音频调速 (0.5-2.0，1.0 为正常速度)",
                default=group['audio_speed']
            )
            # 验证并规范化范围
            audio_speed = max(0.5, min(2.0, audio_speed))
            update_data['audio_speed'] = audio_speed
        
        # 保存
        if Confirm.ask("\n保存修改？", default=True):
            result = service.update_group(group_id, update_data)
            if result.success:
                console.print("[green]✅ 已保存[/green]")
            else:
                console.print(f"[red]❌ 保存失败：{result.error_message}[/red]")
        else:
            console.print("[yellow]已取消修改[/yellow]")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def delete(group_id: str = typer.Argument(..., help="Group ID"), 
           force: bool = typer.Option(False, "--force", "-f", help="强制删除，不确认")):
    """删除 Group"""
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        
        # 获取 Group 信息用于确认
        result = service.get_group(group_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        group = result.data
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            service.close()
            return
        
        if not force:
            console.print(f"[bold]确认删除 Group: {group['name']}?[/bold]")
            console.print(f"  ID: {group_id}")
            console.print(f"  RSS 源：{len(group['rss_sources'])} 个")
            if not Confirm.ask("\n此操作不可逆，确认删除？"):
                console.print("[yellow]已取消[/yellow]")
                service.close()
                return
        
        result = service.delete_group(group_id)
        
        if result.success:
            console.print("[green]✅ Group 已删除[/green]")
        else:
            console.print(f"[red]❌ 删除失败：{result.error_message}[/red]")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def enable(group_id: str = typer.Argument(..., help="Group ID")):
    """启用 Group"""
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        
        result = service.enable_group(group_id)
        
        if result.success:
            group = result.data
            console.print(f"[green]✅ Group '{group.get('name', group_id)}' 已启用[/green]")
        else:
            console.print(f"[red]❌ 启用失败：{result.error_message}[/red]")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@group_app.command()
def disable(group_id: str = typer.Argument(..., help="Group ID")):
    """禁用 Group"""
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        
        result = service.disable_group(group_id)
        
        if result.success:
            group = result.data
            console.print(f"[green]✅ Group '{group.get('name', group_id)}' 已禁用[/green]")
        else:
            console.print(f"[red]❌ 禁用失败：{result.error_message}[/red]")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


# ============== fever 命令组 ==============
fever_app = typer.Typer(help="Fever API 同步")
app.add_typer(fever_app, name="fever")


@fever_app.command()
def test():
    """测试 Fever API 连接"""
    console.print("[bold]测试 Fever API 连接...[/bold]")

    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        result = service.test_connection()
        
        if result.success:
            console.print("[green]✅ 连接成功![/green]")
            console.print(f"   最后刷新：{result.data.get('last_refreshed_on_time', 'unknown')}")
            console.print(f"   订阅源：{result.data.get('feeds_count', 0)} 个")
        else:
            console.print(f"[red]❌ 认证失败：{result.error_message}[/red]")
            service.close()
            sys.exit(1)
        
        service.close()

    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


def _sync_feeds():
    """同步订阅源列表"""
    console.print("[bold]正在从 Fever API 同步订阅源...[/bold]\n")

    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        result = service.sync_feeds()
        
        if result.success:
            console.print(f"[green]✅ 已同步 {result.data.get('feeds_count', 0)} 个订阅源[/green]")
            console.print(f"   保存位置：{os.path.join(os.path.dirname(__file__), 'sources.json')}")
        else:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            sys.exit(1)
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


def _sync_articles(limit: int = 1500):
    """同步文章到缓存"""
    console.print(f"[bold]同步 Fever API 文章到本地缓存 (限制：{limit})...[/bold]\n")
    
    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        result = service.sync_articles(limit=limit)
        
        if result.success:
            console.print("[green]✅ 同步成功![/green]")
            console.print(f"   同步文章：{result.metadata.get('items_synced', 0)} 篇")
            console.print(f"   新增：{result.metadata.get('new_items', 0)} 篇")
            console.print(f"   更新：{result.metadata.get('updated_items', 0)} 篇")
        else:
            console.print(f"[red]❌ 同步失败：{result.error_message}[/red]")
            sys.exit(1)
        
        service.close()
        
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
    
    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        result = service.get_cache_stats()
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        stats = result.data
        
        console.print("\n[bold]📊 缓存统计[/bold]")
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
            console.print("   最后同步：[yellow]尚未同步[/yellow]")
        
        service.close()
        
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
    
    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        
        result = service.get_cache_articles(limit=limit, unread=unread)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        items = result.data
        
        if not items:
            all_items_result = service.get_cache_articles(limit=1)
            if not all_items_result.success or not all_items_result.data:
                console.print("[yellow]缓存中没有文章，请先运行：rss2pod fever sync-all[/yellow]")
            else:
                console.print(f"[yellow]缓存中有文章，但没有{status_text}文章[/yellow]")
            service.close()
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
            title = item.get('title', '')[:60] if len(item.get('title', '')) > 60 else item.get('title', '')
            
            read_icon = "✓" if item.get('is_read', False) else "○"
            saved_icon = "★" if item.get('is_saved', False) else " "
            status = f"{read_icon}{saved_icon}"
            
            table.add_row(
                str(item.get('id', '')),
                title,
                item.get('author', '-')[:20] if item.get('author') else '-',
                status
            )
        
        console.print(table)
        console.print("\n[dim]状态说明：✓ 已读 ○ 未读 | ★ 已收藏[/dim]")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="cache-feeds")
def cache_feeds():
    """从缓存获取订阅源列表"""
    console.print("[bold]从缓存获取订阅源列表...[/bold]\n")

    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        result = service.get_cache_feeds()
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        feeds = result.data
        
        table = Table(
            title=f"订阅源缓存列表 (共 {len(feeds)} 个有文章的订阅源)",
            box=box.ROUNDED
        )
        table.add_column("Feed ID", style="cyan")
        table.add_column("名称", style="green")

        for feed in feeds:
            table.add_row(str(feed.get('feed_id', '')), feed.get('name', '(未知)'))

        console.print(table)
        console.print(f"\n共 {len(feeds)} 个订阅源有缓存文章")
        
        service.close()

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
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        
        ids = [int(x.strip()) for x in item_ids.split(',')]
        result = service.mark_as_read(ids)

        if result.success:
            console.print(f"[green]✅ 已标记 {len(ids)} 篇文章为已读[/green]")
        else:
            console.print(f"[red]❌ 操作失败：{result.error_message}[/red]")
        
        service.close()

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
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        
        result = service.mark_as_saved(item_id)

        if result.success:
            console.print(f"[green]✅ 已收藏文章 {item_id}[/green]")
        else:
            console.print(f"[red]❌ 操作失败：{result.error_message}[/red]")
        
        service.close()

    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@fever_app.command(name="mark-unread")
def mark_unread(
    item_ids: str = typer.Argument(..., help="文章 ID 列表，逗号分隔")
):
    """标记文章为未读"""
    console.print(f"[bold]标记文章为未读：{item_ids}[/bold]\n")
    
    try:
        from rss2pod.services import FeverService
        service = get_service(FeverService)
        
        ids = [int(x.strip()) for x in item_ids.split(',')]
        result = service.mark_as_unread(ids)

        if result.success:
            console.print(f"[green]✅ 已标记 {len(ids)} 篇文章为未读[/green]")
        else:
            console.print(f"[red]❌ 操作失败：{result.error_message}[/red]")
        
        service.close()

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
        from rss2pod.services import PromptService
        service = get_service(PromptService)
        result = service.list_prompts()
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        prompts = result.data.get('prompts', [])
        
        table = Table(box=box.ROUNDED)
        table.add_column("Prompt 名称", style="cyan")
        table.add_column("描述", style="green")
        table.add_column("变量", style="yellow")
        
        for prompt in prompts:
            variables = ", ".join(prompt.get('variables', [])) if prompt.get('variables') else "-"
            table.add_row(
                prompt.get('name', ''),
                prompt.get('description', ''),
                variables
            )
        
        console.print(table)
        console.print(f"\n共 {len(prompts)} 个 prompts")
        console.print("\n[dim]提示：使用 `rss2pod prompt show <prompt_name>` 查看详细内容[/dim]")
        console.print("[dim]      使用 `rss2pod prompt edit <prompt_name>` 编辑 prompt[/dim]")
        
        service.close()
        
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
        from rss2pod.services import PromptService
        service = get_service(PromptService)
        
        # 获取 prompt 配置
        result = service.get_prompt(name, group_id=group_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        prompt = result.data
        
        console.print(f"[bold]名称:[/bold] {prompt.get('name', name)}")
        console.print(f"[bold]描述:[/bold] {prompt.get('description', '')}")
        console.print(f"[bold]可用变量:[/bold] {', '.join(prompt.get('variables', [])) if prompt.get('variables') else '无'}\n")
        
        console.print(Panel("[bold]System Message[/bold]", box=box.ROUNDED))
        console.print(prompt.get('system', '') or "(无)")
        
        console.print(Panel("[bold]Template[/bold]", box=box.ROUNDED))
        console.print(prompt.get('template', '') or "(无)")
        
        if group_id:
            console.print(f"\n[dim]显示的是 Group '{group_id}' 的配置（可能包含覆盖）[/dim]")
        else:
            console.print("\n[dim]显示的是全局默认配置[/dim]")
        
        service.close()
        
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
        from rss2pod.services import PromptService
        service = get_service(PromptService)
        
        # 获取当前 prompt
        result = service.get_prompt(name)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        prompt = result.data
        
        # 创建临时文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
            f.write(f"# 编辑 Prompt: {name}\n")
            f.write(f"# 描述：{prompt.get('description', '')}\n")
            f.write(f"# 可用变量：{', '.join(prompt.get('variables', [])) if prompt.get('variables') else '无'}\n")
            f.write("#\n")
            f.write("# === SYSTEM MESSAGE ===\n")
            f.write(prompt.get('system', '') + "\n")
            f.write("\n")
            f.write("# === TEMPLATE ===\n")
            f.write(prompt.get('template', ''))
        
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
                new_prompt_config = {
                    'name': name,
                    'description': prompt.get('description', ''),
                    'system': system_text,
                    'template': template_text,
                    'variables': prompt.get('variables', [])
                }
                
                # 保存配置
                result = service.set_global_prompt(name, new_prompt_config)
                
                if result.success:
                    console.print("[green]✅ Prompt 已保存[/green]")
                else:
                    console.print(f"[red]❌ 保存失败：{result.error_message}[/red]")
                
                os.unlink(temp_path)
                service.close()
                return
                
            except FileNotFoundError:
                continue
        
        console.print("[red]❌ 未找到可用的编辑器[/red]")
        os.unlink(temp_path)
        service.close()
        
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
        from rss2pod.services import PromptService
        service = get_service(PromptService)
        
        # 获取当前 prompt
        result = service.get_prompt(name)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        current_prompt = result.data
        
        # 创建新的覆盖配置
        new_prompt_config = {
            'name': name,
            'description': current_prompt.get('description', ''),
            'system': system if system is not None else current_prompt.get('system', ''),
            'template': content if content is not None else current_prompt.get('template', ''),
            'variables': current_prompt.get('variables', [])
        }
        
        # 设置组别覆盖
        result = service.set_group_override(group_id, name, new_prompt_config)
        
        if result.success:
            console.print("[green]✅ Prompt 覆盖已保存[/green]")
            console.print(f"   Group: {group_id}")
            console.print(f"   Prompt: {name}")
            if system:
                console.print(f"   System: {system[:50]}...")
            if content:
                console.print(f"   Template: {content[:50]}...")
        else:
            console.print(f"[red]❌ 保存失败：{result.error_message}[/red]")
        
        service.close()
        
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
        from rss2pod.services import PromptService
        service = get_service(PromptService)
        
        result = service.reset_group_override(group_id, name)
        
        if result.success:
            console.print("[green]✅ Prompt 已重置为默认值[/green]")
            console.print(f"   Group: {group_id}")
            console.print(f"   Prompt: {name}")
        else:
            console.print(f"[red]❌ 重置失败：{result.error_message}[/red]")
        
        service.close()
        
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
        from rss2pod.services import PromptService
        service = get_service(PromptService)
        
        result = service.export_prompts(filepath)
        
        if result.success:
            console.print("[green]✅ Prompts 已导出[/green]")
            console.print(f"   文件：{filepath}")
        else:
            console.print(f"[red]❌ 导出失败：{result.error_message}[/red]")
        
        service.close()
        
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
        from rss2pod.services import PromptService
        service = get_service(PromptService)
        
        result = service.import_prompts(filepath, merge=merge)
        
        if result.success:
            console.print("[green]✅ Prompts 已导入[/green]")
        else:
            console.print(f"[red]❌ 导入失败：{result.error_message}[/red]")
        
        service.close()
        
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
    
    try:
        from rss2pod.services import LLMService
        service = get_service(LLMService)
        result = service.test_connection()
        
        if result.success:
            console.print("[green]✅ 连接成功![/green]")
            console.print(f"   提供商：{result.data.get('provider')}")
            console.print(f"   模型：{result.data.get('model')}")
        else:
            console.print(f"[red]❌ API 错误：{result.error_message}[/red]")
            service.close()
            sys.exit(1)
        
        service.close()

    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@llm_app.command()
def chat(message: str = typer.Argument(..., help="要发送的消息")):
    """与 LLM 对话"""
    console.print(f"[bold]发送：{message}[/bold]\n")
    
    try:
        from rss2pod.services import LLMService
        service = get_service(LLMService)
        result = service.chat(message)
        
        if result.success:
            console.print(f"[green][bold]回复:[/bold] {result.data.get('content', '')}[/green]")
        else:
            console.print(f"[red]❌ API 错误：{result.error_message}[/red]")
            service.close()
            sys.exit(1)
        
        service.close()
            
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
    
    try:
        from rss2pod.services import TTSService
        service = get_service(TTSService)
        result = service.test_connection()
        
        if result.success:
            console.print("[green]✅ TTS 已配置[/green]")
            console.print(f"   提供商：{result.data.get('provider')}")
            console.print(f"   适配器：{result.data.get('adapter')}")
            console.print(f"   模型：{result.data.get('model')}")
        else:
            console.print(f"[yellow]⚠️ TTS 未配置：{result.error_message}[/yellow]")
        
        service.close()

    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@tts_app.command("list-voices")
def list_voices():
    """列出可用音色"""
    console.print("[bold]SiliconFlow 可用音色[/bold]\n")
    
    try:
        from rss2pod.services import TTSService
        service = get_service(TTSService)
        
        # 获取当前配置的模型
        config = load_config()
        tts_config = config.get('tts', {})
        model = tts_config.get('model', 'fnlp/MOSS-TTSD-v0.5')
        
        result = service.list_voices(model=model)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        voices = result.data.get('voices', [])
        
        console.print(f"[dim]当前配置模型：{model}[/dim]\n")
        
        table = Table(box=box.ROUNDED)
        table.add_column("音色 ID", style="cyan")
        table.add_column("描述", style="green")
        
        for voice in voices:
            table.add_row(voice.get('id', ''), voice.get('name', ''))
        
        console.print(table)
        
        # 显示两个模型的音色说明
        console.print("\n[yellow]注意：MOSS 模型和 CosyVoice 模型使用各自独立的音色系统[/yellow]")
        console.print("  - MOSS 模型 (fnlp/MOSS-TTSD-v0.5): 使用 fnlp/MOSS-TTSD-v0.5:xxx 格式")
        console.print("  - CosyVoice 模型 (FunAudioLLM/CosyVoice2-0.5B): 使用 FunAudioLLM/CosyVoice2-0.5B:xxx 格式")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


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
    console.print("[bold]TTS 转换[/bold]")
    console.print(f"输入文本：{text[:50]}{'...' if len(text) > 50 else ''}\n")
    
    try:
        from rss2pod.services import TTSService
        service = get_service(TTSService)
        
        # 生成输出文件路径
        if not output:
            import time
            timestamp = int(time.time())
            text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
            output = f"./output_{text_hash}_{timestamp}.mp3"
        
        # 调用 TTS 服务
        result = service.synthesize(text=text, voice=voice, output_path=output)
        
        if result.success:
            data = result.data
            console.print("\n[green]✅ 转换成功![/green]")
            console.print(f"   音频路径：{data.get('audio_path')}")
            console.print(f"   文件大小：{data.get('file_size', 0)} 字节 ({data.get('file_size_kb', 0):.2f} KB)")
            console.print(f"   预计时长：{data.get('estimated_duration', 0):.1f} 秒")
        else:
            console.print(f"[red]❌ 转换失败：{result.error_message}[/red]")
            sys.exit(1)
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        import traceback
        if get_verbose():
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


# ============== db 命令组 ==============
db_app = typer.Typer(help="数据库管理")
app.add_typer(db_app, name="db")


@db_app.command()
def stats():
    """显示数据库统计"""
    console.print(Panel("[bold blue]数据库统计[/bold blue]", box=box.DOUBLE))
    
    try:
        from rss2pod.services import StatsService
        service = get_service(StatsService)
        result = service.get_database_stats()
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        stats = result.data
        console.print("\n[bold]📊 统计信息[/bold]")
        console.print(f"   文章总数：{stats.get('total_articles', 0)}")
        console.print(f"   启用 Group: {stats.get('enabled_groups', 0)}")
        console.print(f"   期数总数：{stats.get('total_episodes', 0)}")
        
        service.close()
        
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
        from rss2pod.services import DatabaseService
        service = get_service(DatabaseService)
        
        # 根据状态查询
        if query_status == "all":
            result = service.get_all_articles(limit=limit)
        else:
            result = service.get_articles_by_status(query_status, limit=limit)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        articles = result.data
        
        if not articles:
            console.print(f"[yellow]没有找到 {status_text} 状态的文章[/yellow]")
            return
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("标题", style="green")
        table.add_column("状态", style="yellow")
        table.add_column("Source", style="blue")
        
        for article in articles:
            # Article 是 dataclass 对象，使用属性访问
            article_id = article.id if hasattr(article, 'id') else article.get('id', '')
            title = article.title if hasattr(article, 'title') else article.get('title', '')
            status = article.status if hasattr(article, 'status') else article.get('status', '')
            source = article.source if hasattr(article, 'source') else article.get('source', '')
            
            table.add_row(
                article_id[:12] + '...' if len(article_id) > 12 else article_id,
                title[:50] + '...' if len(title) > 50 else title,
                status,
                source[:20] + '...' if len(source) > 20 else source
            )
        
        console.print(table)
        console.print(f"\n共 {len(articles)} 篇文章")
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@db_app.command("list-groups")
def db_list_groups():
    """列出 Group"""
    console.print("[bold]Group 列表[/bold]\n")
    
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        result = service.list_groups()
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        groups = result.data
        
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
                group.get('id', ''),
                group.get('name', ''),
                "✅" if group.get('enabled', False) else "❌",
                f"{len(group.get('rss_sources', []))} 个"
            )
        
        console.print(table)
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


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
    
    # 根据 --verbose 设置日志级别
    log_level = "DEBUG" if get_verbose() or verbose else "INFO"
    
    try:
        from rss2pod.services import SchedulerService, GroupService
        from rss2pod.services.logging_service import setup_logging
        
        # 设置日志级别
        setup_logging(level=log_level)
        
        scheduler_service = get_service(SchedulerService)
        group_service = get_service(GroupService)
        
        # 获取要处理的 Group 列表
        if all_groups or group_id is None:
            groups_result = scheduler_service.get_enabled_groups()
            if not groups_result.success:
                console.print(f"[red]❌ 错误：{groups_result.error_message}[/red]")
                scheduler_service.close()
                return
            
            groups = groups_result.data
            if not groups:
                console.print("[yellow]没有启用的 Group[/yellow]")
                return
            console.print(f"[bold]将触发 {len(groups)} 个启用的 Group[/bold]\n")
        else:
            group_result = group_service.get_group(group_id)
            if not group_result.success:
                console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
                group_service.close()
                scheduler_service.close()
                return
            groups = [group_result.data]
            if not groups[0]:
                console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
                group_service.close()
                scheduler_service.close()
                return
        
        success_count = 0
        fail_count = 0
        
        for group in groups:
            gid = group.get('id')
            console.print(Panel(f"[bold]处理 Group: {group.get('name')}[/bold]", box=box.ROUNDED))
            console.print(f"  ID: {gid}")
            console.print(f"  触发类型：{group.get('trigger_type')}")
            console.print(f"  RSS 源：{len(group.get('rss_sources', []))} 个")
            
            if force:
                console.print("  [yellow]⚠️ 强制模式 - 将使用最新三篇文章[/yellow]")
            
            if export_articles:
                console.print("  [cyan]📄 文章导出模式 - 将导出抓取的文章到 JSON 文件[/cyan]")
            
            if dry_run:
                console.print("  [yellow]⚠️ 模拟运行模式 - 不会实际生成[/yellow]")
                console.print("  [dim]（模拟：检查未读文章 -> 摘要 -> 生成脚本 -> TTS）[/dim]\n")
            else:
                try:
                    result = scheduler_service.trigger_generation(
                        gid,
                        force=force,
                        export_articles=export_articles
                    )
                    
                    if result.success:
                        console.print("[green]✓ 成功[/green]")
                        console.print(f"  Episode: {result.data.get('episode_id')}")
                        console.print(f"  完成阶段：{', '.join(result.data.get('stages_completed', []))}")
                        console.print(f"  获取文章：{result.data.get('articles_fetched')}")
                        success_count += 1
                    else:
                        console.print("[red]✗ 失败[/red]")
                        console.print(f"  失败阶段：{result.data.get('failed_stage')}")
                        console.print(f"  错误：{result.error_message}")
                        fail_count += 1
                except Exception as e:
                    console.print(f"[red]✗ 异常：{e}[/red]")
                    fail_count += 1
            
            console.print()
        
        scheduler_service.close()
        
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
    
    try:
        from rss2pod.services import SchedulerService
        service = get_service(SchedulerService)
        
        if group_id:
            result = service.get_generation_history(group_id=group_id, limit=limit)
        else:
            result = service.get_generation_history(limit=limit)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        episodes = result.data
        
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
                ep.get('id', '')[:8] + '...',
                ep.get('group_id', ''),
                ep.get('title', '')[:40] + '...' if len(ep.get('title', '')) > 40 else ep.get('title', ''),
                f"#{ep.get('episode_number', 0)}",
                "✅" if ep.get('audio_path') else "❌"
            )
        
        console.print(table)
        service.close()
        
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
    
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        result = service.get_group(group_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        group = result.data
        
        if not group:
            console.print(f"[red]❌ 未找到 Group: {group_id}[/red]")
            return
        
        console.print(f"Group: {group.get('name')}")
        console.print(f"状态：{'✅ 启用' if group.get('enabled') else '❌ 禁用'}")
        console.print(f"触发类型：{group.get('trigger_type')}")
        console.print(f"触发配置：{json.dumps(group.get('trigger_config', {}), indent=2)}")
        
        service.close()
        
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
    
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        
        update_data = {
            'trigger_type': trigger_type,
            'trigger_config': {
                'cron': cron,
                'threshold': threshold
            }
        }
        
        result = service.update_group(group_id, update_data)
        
        if result.success:
            console.print("[green]✅ 触发器已更新[/green]")
            console.print(f"  类型：{trigger_type}")
            console.print(f"  Cron: {cron}")
            console.print(f"  阈值：{threshold}")
        else:
            console.print(f"[red]❌ 更新失败：{result.error_message}[/red]")
        
        service.close()
        
    except Exception as e:
        console.print(f"[red]❌ 错误：{e}[/red]")
        sys.exit(1)


@trigger_app.command()
def disable(group_id: str = typer.Argument(..., help="Group ID")):
    """禁用触发器（禁用 Group）"""
    console.print(f"[bold]禁用触发器：{group_id}[/bold]")
    
    try:
        from rss2pod.services import GroupService
        service = get_service(GroupService)
        
        result = service.disable_group(group_id)
        
        if result.success:
            console.print("[green]✅ Group 已禁用，触发器停止工作[/green]")
        else:
            console.print(f"[red]❌ 禁用失败：{result.error_message}[/red]")
        
        service.close()
        
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
    
    try:
        from rss2pod.services import SchedulerService
        from rss2pod.services.logging_service import setup_logging
        
        # 设置日志
        log_level = "DEBUG" if get_verbose() else "INFO"
        setup_logging(level=log_level)
        
        scheduler_service = get_service(SchedulerService)
        
        # 获取配置
        config = load_config()
        orchestrator_config = config.get('orchestrator', {})
        
        console.print("[green]✓[/green] 调度器已启动")
        console.print(f"  检查间隔：{orchestrator_config.get('check_interval_seconds', 60)}秒")
        console.print(f"  最大并发：{orchestrator_config.get('max_concurrent_groups', 3)}个 Group")
        console.print("\n[dim]按 Ctrl+C 停止调度器[/dim]\n")
        
        # 启动调度器
        scheduler_service.start()
        
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
    
    try:
        from rss2pod.services import SchedulerService
        service = get_service(SchedulerService)
        result = service.get_status()
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        data = result.data
        
        # 显示状态统计
        states = data.get('states_by_status', {})
        console.print("[bold]处理状态统计:[/bold]")
        for status_name, count in states.items():
            status_icon = {"idle": "⏸️", "running": "▶️", "error": "❌", "disabled": "🚫"}.get(status_name, "•")
            console.print(f"  {status_icon} {status_name}: {count}")
        
        console.print(f"\n[bold]运行中管道：[/bold]{data.get('running_pipelines', 0)}")
        console.print(f"[bold]今日运行：[/bold]{data.get('runs_today', 0)}")
        
        # 显示启用的 Group
        enabled_groups = data.get('enabled_groups', [])
        console.print(f"\n[bold]启用的 Group: [/bold]{len(enabled_groups)}")
        for group_info in enabled_groups[:5]:
            console.print(f"  • {group_info.get('name', 'N/A')} (Cron: {group_info.get('cron', 'N/A')})")
        
        if len(enabled_groups) > 5:
            console.print(f"  ... 还有 {len(enabled_groups) - 5} 个")
        
        service.close()
        
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
    
    # 根据 --verbose 设置日志级别
    log_level = "DEBUG" if get_verbose() else "INFO"
    
    try:
        from rss2pod.services import SchedulerService
        from rss2pod.services.logging_service import setup_logging
        
        # 设置日志级别
        setup_logging(level=log_level)
        
        scheduler_service = get_service(SchedulerService)
        
        if group_id:
            # 触发指定 Group
            result = scheduler_service.run_once(group_id)
            
            if not result.success:
                console.print(f"[red]❌ 错误：{result.error_message}[/red]")
                scheduler_service.close()
                return
            
            console.print("[green]✅ 触发成功[/green]")
            console.print(f"  Group: {result.data.get('group_name')}")
            console.print(f"  Episode: {result.data.get('episode_id')}")
        else:
            # 触发所有启用的 Group
            result = scheduler_service.run_once()
            
            if not result.success:
                console.print(f"[red]❌ 错误：{result.error_message}[/red]")
                scheduler_service.close()
                return
            
            results = result.data
            console.print("[green]✅ 触发完成[/green]")
            console.print(f"  处理 Group 数：{len(results)}")
            for r in results:
                if r.get('success'):
                    console.print(f"  ✓ {r.get('group_name')}: {r.get('episode_id')}")
                else:
                    console.print(f"  ✗ {r.get('group_name')}: {r.get('error_message')}")
        
        scheduler_service.close()
        
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
        console.print(Panel(f"[bold]{data.get('group_name')}[/bold]", box=box.DOUBLE))
        console.print(f"ID:    {data.get('group_id')}")
        console.print(f"状态：  {'✅ 启用' if data.get('enabled') else '❌ 禁用'}")
        console.print(f"类型：  {data.get('trigger_type')}")
        
        # Cron 触发信息
        if 'cron' in data:
            cron = data.get('cron', {})
            console.print("\n[bold]⏰ Cron 触发[/bold]")
            console.print(f"  表达式：{cron.get('expression') or '未配置'}")
            
            if cron.get('expression'):
                next_run = cron.get('next_run')
                if next_run:
                    console.print(f"  下次运行：{next_run}")
                
                if cron.get('will_trigger'):
                    console.print("  状态：[green]✅ 会触发[/green]")
                else:
                    remaining = cron.get('remaining', 'N/A')
                    console.print(f"  状态：[red]❌ 不会触发 (还差 {remaining})[/red]")
        
        # 数量触发信息
        if 'count' in data:
            count = data.get('count', {})
            console.print("\n[bold]📊 数量触发[/bold]")
            console.print(f"  阈值：{count.get('threshold', 0)} 篇")
            console.print(f"  当前：{count.get('current', 0)} 篇")
            
            if count.get('will_trigger'):
                console.print("  状态：[green]✅ 会触发[/green]")
            else:
                remaining = count.get('remaining', 0)
                console.print(f"  状态：[red]❌ 不会触发 (还差 {remaining} 篇)[/red]")
        
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
        from rss2pod.services import AssetService
        service = get_service(AssetService)
        
        result = service.list_episode_assets(group_id)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        episodes = result.data
        
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
                console.print("\n[bold]文稿文件:[/bold]")
                if source_summaries:
                    console.print("  • source_summaries.json")
                if group_summary:
                    console.print("  • group_summary.json")
                if podcast_script:
                    console.print("  • podcast_script.json")
            
            # 分段音频 - audio_segments 是文件路径列表
            audio_segments = assets.get('audio_segments', [])
            if audio_segments:
                console.print("\n[bold]分段音频:[/bold]")
                for seg_path in audio_segments:
                    filename = os.path.basename(seg_path)
                    file_size = os.path.getsize(seg_path) if os.path.exists(seg_path) else 0
                    size_kb = file_size / 1024
                    console.print(f"  • {filename} ({size_kb:.1f} KB)")
            else:
                console.print("\n[yellow]⚠️  无分段音频（可能已清理）[/yellow]")
            
            console.print()
        
        console.print(f"共 {len(episodes)} 个 Episode")
        service.close()
        
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
        from rss2pod.services import AssetService
        service = get_service(AssetService)
        
        result = service.get_episode_assets(group_id, timestamp)
        
        if not result.success:
            console.print(f"[red]❌ 错误：{result.error_message}[/red]")
            service.close()
            return
        
        assets = result.data
        
        console.print(f"资源目录：{assets.get('assets_dir')}")
        
        # 文稿文件
        source_summaries = assets.get('source_summaries')
        group_summary = assets.get('group_summary')
        podcast_script = assets.get('podcast_script')
        
        has_files = source_summaries or group_summary or podcast_script
        if has_files:
            console.print("\n[bold]文稿文件:[/bold]")
            if source_summaries:
                console.print("  • source_summaries.json")
            if group_summary:
                console.print("  • group_summary.json")
            if podcast_script:
                console.print("  • podcast_script.json")
        
        # 分段音频 - audio_segments 是文件路径列表
        audio_segments = assets.get('audio_segments', [])
        if audio_segments:
            console.print("\n[bold]分段音频:[/bold]")
            for seg_path in audio_segments:
                filename = os.path.basename(seg_path)
                file_size = os.path.getsize(seg_path) if os.path.exists(seg_path) else 0
                size_kb = file_size / 1024
                console.print(f"  • {filename} ({size_kb:.1f} KB)")
        else:
            console.print("\n[yellow]⚠️  无分段音频[/yellow]")
        
        console.print()
        service.close()
        
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
        from rss2pod.services import AssetService
        service = get_service(AssetService)
        
        if timestamp:
            # 清理指定 Episode
            if not force:
                if not Confirm.ask("\n此操作将删除中间文件（分段音频、文稿），但保留最终音频。确认删除？"):
                    console.print("[yellow]已取消[/yellow]")
                    service.close()
                    return
            
            result = service.cleanup_episode_assets(group_id, timestamp)
            
            if result.success:
                console.print(f"[green]✅ 已清理 Episode {timestamp} 的中间文件[/green]")
            else:
                console.print(f"[red]❌ 清理失败：{result.error_message}[/red]")
        else:
            # 清理所有 Episode
            list_result = service.list_episode_assets(group_id)
            
            if not list_result.success:
                console.print(f"[red]❌ 错误：{list_result.error_message}[/red]")
                service.close()
                return
            
            episodes = list_result.data
            
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
                    service.close()
                    return
            
            for ep in episodes:
                ts = ep.get('episode_timestamp', 'unknown')
                result = service.cleanup_episode_assets(group_id, ts)
                if result.success:
                    console.print(f"  [green]✓ 已清理 {ts}[/green]")
                else:
                    console.print(f"  [red]✗ {ts}: {result.error_message}[/red]")
            
            console.print(f"\n[green]✅ 已清理 {len(episodes)} 个 Episode 的中间文件[/green]")
        
        service.close()
        
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