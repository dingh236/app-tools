# monitoring_system/api_monitor/api.py

from fastapi import FastAPI
from datetime import datetime

app = FastAPI()

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """获取监控指标"""
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "ok"
    }