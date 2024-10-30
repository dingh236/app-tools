from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import psutil
import platform
import os

@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    disk_io: Dict
    network_io: Dict

@dataclass
class ServiceMetrics:
    """服务指标"""
    timestamp: datetime
    service_name: str
    process_id: Optional[int]
    port: int
    status: str
    response_time: float
    error_count: int
    request_count: int

class MetricsCollector:
    """指标收集器"""
    def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=psutil.cpu_percent(interval=1),
            memory_percent=psutil.virtual_memory().percent,
            disk_usage=psutil.disk_usage('/').percent,
            disk_io=psutil.disk_io_counters()._asdict(),
            network_io=psutil.net_io_counters()._asdict()
        )
    
    def collect_service_metrics(self, service_config: Dict) -> ServiceMetrics:
        """收集服务指标"""
        # 检查服务状态
        process_id = self._get_service_pid(service_config['process_name'])
        status = self._check_service_status(process_id, service_config['port'])
        
        # 检查服务响应时间
        response_time = self._check_service_response(
            service_config['health_check_url']
        )
        
        return ServiceMetrics(
            timestamp=datetime.now(),
            service_name=service_config['name'],
            process_id=process_id,
            port=service_config['port'],
            status=status,
            response_time=response_time,
            error_count=0,  # 需要从日志或错误追踪系统获取
            request_count=0  # 需要从服务统计获取
        )

    def _get_service_pid(self, process_name: str) -> Optional[int]:
        """获取服务进程ID"""
        for proc in psutil.process_iter(['pid', 'name']):
            if process_name in proc.info['name']:
                return proc.info['pid']
        return None

    def _check_service_status(self, pid: Optional[int], port: int) -> str:
        """检查服务状态"""
        if pid is None:
            return 'DOWN'
        
        # 检查端口是否在监听
        connections = psutil.net_connections()
        for conn in connections:
            if conn.laddr.port == port:
                return 'RUNNING'
        
        return 'UNKNOWN'

    def _check_service_response(self, url: str) -> float:
        """检查服务响应时间"""
        try:
            import requests
            start_time = datetime.now()
            response = requests.get(url, timeout=5)
            response_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                return response_time
            return -1
        except Exception:
            return -1