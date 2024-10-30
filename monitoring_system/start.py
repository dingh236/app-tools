#!/usr/bin/env python3
# monitoring_system/start.py

import os
import sys
import asyncio
import logging
from pathlib import Path
from multiprocessing import Process

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('monitoring')

def start_dashboard():
    """启动仪表盘服务"""
    import uvicorn
    from dashboard.app import app
    uvicorn.run(app, host="0.0.0.0", port=8080)

def start_api_server():
    """启动API服务器"""
    import uvicorn
    from api_monitor.api import app
    uvicorn.run(app, host="localhost", port=8000)

async def run_service_monitor():
    """运行服务监控"""
    from services.monitor import ServiceMonitor
    config_path = os.path.join(current_dir, 'config', 'services.json')
    monitor = ServiceMonitor(config_path)
    await monitor.start_monitoring()

async def main():
    """主程序入口"""
    try:
        # 启动仪表盘进程
        dashboard_process = Process(target=start_dashboard)
        dashboard_process.start()
        logger.info("Dashboard started on http://localhost:8080")

        # 启动API服务器进程
        api_process = Process(target=start_api_server)
        api_process.start()
        logger.info("API server started on http://localhost:8000")

        # 运行服务监控
        await run_service_monitor()

    except KeyboardInterrupt:
        logger.info("Shutting down monitoring system...")
    except Exception as e:
        logger.error(f"Error starting monitoring system: {e}")
        raise
    finally:
        # 清理进程
        if 'dashboard_process' in locals():
            dashboard_process.terminate()
        if 'api_process' in locals():
            api_process.terminate()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System stopped by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)