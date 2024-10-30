# services/monitor.py

import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
import psutil
import aiohttp
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class ServiceMonitor:
    """服务监控类"""
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.services_status = {}
        self.last_check_time = None
        self.metrics_history = {
            'system': [],
            'services': {}
        }

    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Successfully loaded config from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # 返回默认配置
            return {
                "services": [],
                "monitor": {
                    "check_interval": 30,
                    "system_metrics_interval": 60
                },
                "thresholds": {
                    "cpu_percent": 80,
                    "memory_percent": 85,
                    "disk_usage": 90,
                    "response_time": 5
                }
            }

    async def collect_metrics(self) -> Dict[str, Any]:
        """收集所有指标"""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "system": await self._collect_system_metrics(),
                "services": {}
            }

            # 收集服务指标
            for service in self.config['services']:
                service_metrics = await self._collect_service_metrics(service)
                metrics['services'][service['name']] = service_metrics

            self.last_check_time = datetime.now()
            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "system": {},
                "services": {},
                "error": str(e)
            }

    async def _collect_system_metrics(self) -> Dict[str, float]:
        """收集系统指标"""
        try:
            # CPU使用率（使用interval=1以获得更准确的读数）
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            # 网络IO
            net_io = psutil.net_io_counters()
            
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_usage": disk.percent,
                "disk_used": disk.used,
                "disk_total": disk.total,
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv,
                "timestamp": datetime.now().isoformat()
            }

            # 添加到历史记录
            self.metrics_history['system'].append(metrics)
            
            # 保持历史记录在合理范围内（例如保留最近24小时的数据）
            max_history = 24 * 60  # 24小时，每分钟一个数据点
            if len(self.metrics_history['system']) > max_history:
                self.metrics_history['system'] = self.metrics_history['system'][-max_history:]

            return metrics

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "disk_usage": 0,
                "error": str(e)
            }

    async def _collect_service_metrics(self, service_config: Dict) -> Dict[str, Any]:
        """收集服务指标"""
        try:
            start_time = datetime.now()
            service_metrics = {
                "name": service_config["name"],
                "status": "DOWN",
                "response_time": None,
                "last_check": start_time.isoformat()
            }

            # 检查进程
            if "process_name" in service_config:
                service_metrics["process_running"] = self._check_process(
                    service_config["process_name"]
                )

            # 检查端口
            if "port" in service_config:
                service_metrics["port_listening"] = self._check_port(
                    service_config["port"]
                )

            # 检查健康检查URL
            if "health_check_url" in service_config:
                response_time, status_code = await self._check_health_endpoint(
                    service_config["health_check_url"],
                    service_config.get("timeout", 5)
                )
                service_metrics.update({
                    "response_time": response_time,
                    "status_code": status_code,
                    "status": "UP" if status_code == 200 else "DOWN"
                })

            # 更新服务历史记录
            if service_config["name"] not in self.metrics_history['services']:
                self.metrics_history['services'][service_config["name"]] = []
            
            self.metrics_history['services'][service_config["name"]].append({
                "timestamp": start_time.isoformat(),
                **service_metrics
            })

            # 保持历史记录在合理范围内
            max_history = 24 * 60  # 24小时，每分钟一个数据点
            if len(self.metrics_history['services'][service_config["name"]]) > max_history:
                self.metrics_history['services'][service_config["name"]] = \
                    self.metrics_history['services'][service_config["name"]][-max_history:]

            return service_metrics

        except Exception as e:
            logger.error(f"Error collecting metrics for service {service_config['name']}: {e}")
            return {
                "name": service_config["name"],
                "status": "ERROR",
                "error": str(e),
                "last_check": datetime.now().isoformat()
            }

    def _check_process(self, process_name: str) -> bool:
        """检查进程是否运行"""
        try:
            for proc in psutil.process_iter(['name']):
                if process_name in proc.info['name']:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking process {process_name}: {e}")
            return False

    def _check_port(self, port: int) -> bool:
        """检查端口是否在监听"""
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return False

    async def _check_health_endpoint(self, url: str, timeout: int) -> tuple:
        """检查健康检查端点"""
        async with aiohttp.ClientSession() as session:
            try:
                start_time = datetime.now()
                async with session.get(url, timeout=timeout) as response:
                    response_time = (datetime.now() - start_time).total_seconds()
                    return response_time, response.status
            except Exception as e:
                logger.error(f"Error checking health endpoint {url}: {e}")
                return None, None

    async def start_monitoring(self):
        """启动监控"""
        logger.info("Starting service monitoring...")
        try:
            while True:
                metrics = await self.collect_metrics()
                
                # 这里可以添加将指标发送到仪表盘的代码
                if hasattr(self, 'dashboard') and self.dashboard:
                    await self.dashboard.broadcast_metrics(metrics)
                
                # 检查阈值并触发告警
                await self._check_thresholds(metrics)
                
                # 等待下一次检查
                await asyncio.sleep(self.config['monitor']['check_interval'])
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            raise

    async def _check_thresholds(self, metrics: Dict):
        """检查指标是否超过阈值"""
        thresholds = self.config['thresholds']
        
        # 检查系统指标
        if metrics['system'].get('cpu_percent', 0) > thresholds['cpu_percent']:
            logger.warning(f"CPU usage ({metrics['system']['cpu_percent']}%) exceeded threshold")
            
        if metrics['system'].get('memory_percent', 0) > thresholds['memory_percent']:
            logger.warning(f"Memory usage ({metrics['system']['memory_percent']}%) exceeded threshold")
            
        if metrics['system'].get('disk_usage', 0) > thresholds['disk_usage']:
            logger.warning(f"Disk usage ({metrics['system']['disk_usage']}%) exceeded threshold")

        # 检查服务指标
        for service_name, service_metrics in metrics['services'].items():
            if service_metrics.get('response_time') and \
               service_metrics['response_time'] > thresholds['response_time']:
                logger.warning(
                    f"Service {service_name} response time "
                    f"({service_metrics['response_time']}s) exceeded threshold"
                )

    def get_metrics_history(self) -> Dict:
        """获取历史指标数据"""
        return self.metrics_history