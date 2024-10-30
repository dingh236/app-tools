# dashboard/app.py

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging
import json
import asyncio
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class DashboardApp:
    def __init__(self):
        self.app = FastAPI()
        self.setup_routes()
        self.clients: List[WebSocket] = []
        self.metrics_store: Dict = {
            "system": {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_usage": 0,
                "timestamp": datetime.now().isoformat()
            },
            "services": {}
        }

    def setup_routes(self):
        # 挂载静态文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        static_dir = os.path.join(current_dir, "static")
        self.app.mount("/static", StaticFiles(directory=static_dir), name="static")

        # 设置路由
        self.app.get("/")(self.get_dashboard)
        self.app.get("/health")(self.health_check)
        self.app.get("/api/metrics")(self.get_metrics)
        self.app.websocket("/ws")(self.websocket_endpoint)

    async def get_dashboard(self):
        """返回仪表盘页面"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        static_dir = os.path.join(current_dir, "static")
        with open(os.path.join(static_dir, "index.html")) as f:
            return HTMLResponse(content=f.read())

    async def health_check(self):
        """健康检查端点"""
        return {"status": "ok"}

    async def get_metrics(self):
        """获取当前指标数据"""
        return self.metrics_store

    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket连接处理"""
        await websocket.accept()
        self.clients.append(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("type") == "get_metrics":
                    await self.send_metrics_update(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if websocket in self.clients:
                self.clients.remove(websocket)

    async def broadcast_metrics(self, metrics: Dict):
        """广播指标更新"""
        self.metrics_store.update(metrics)
        dead_clients = []

        for client in self.clients:
            try:
                await client.send_json({
                    "type": "metrics_update",
                    "data": self.metrics_store
                })
            except Exception as e:
                logger.error(f"Failed to send metrics to client: {e}")
                dead_clients.append(client)

        # 清理断开的连接
        for client in dead_clients:
            if client in self.clients:
                self.clients.remove(client)

    async def send_metrics_update(self, websocket: WebSocket):
        """发送指标更新到单个客户端"""
        try:
            await websocket.send_json({
                "type": "metrics_update",
                "data": self.metrics_store
            })
        except Exception as e:
            logger.error(f"Failed to send metrics update: {e}")
            if websocket in self.clients:
                self.clients.remove(websocket)

app = DashboardApp().app