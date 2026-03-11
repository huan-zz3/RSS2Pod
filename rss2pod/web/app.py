"""
FastAPI 应用主入口
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_app():
    """
    创建 FastAPI 应用
    
    Returns:
        FastAPI 应用实例
    """
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import RedirectResponse
    
    app = FastAPI(
        title="RSS2Pod",
        description="RSS to Podcast Service",
        version="1.0.0"
    )
    
    # 注册路由
    from . import api, rss
    
    app.include_router(api.router, prefix="/api", tags=["api"])
    app.include_router(rss.router, prefix="/feeds", tags=["rss"])
    
    # 静态文件服务
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # 媒体文件服务
    media_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'data', 'media'
    )
    if os.path.exists(media_dir):
        app.mount("/media", StaticFiles(directory=media_dir), name="media")
    
    # 首页重定向到静态页面
    @app.get("/")
    async def root():
        static_index = os.path.join(static_dir, 'index.html')
        if os.path.exists(static_index):
            from fastapi.responses import FileResponse
            return FileResponse(static_index)
        return {"message": "RSS2Pod API", "docs": "/docs"}
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return app


def start_server(host: str = "0.0.0.0", port: int = 8080):
    """
    启动 Web 服务器
    
    Args:
        host: 监听地址
        port: 监听端口
    """
    import uvicorn
    from services.config_service import load_config
    
    # 加载配置
    config = load_config()
    server_config = config.get('server', {})
    
    # 使用配置或默认值
    host = server_config.get('host', host)
    port = server_config.get('port', port)
    
    app = create_app()
    
    print(f"Starting RSS2Pod Web Server on http://{host}:{port}")
    print(f"  - API: http://{host}:{port}/api")
    print(f"  - RSS Feeds: http://{host}:{port}/feeds")
    print(f"  - Media: http://{host}:{port}/media")
    
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
