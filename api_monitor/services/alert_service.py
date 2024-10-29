# api_monitor/services/alert_service.py
from typing import Dict, Optional
from datetime import datetime, timedelta
from api_monitor.models.api import APIConfig, APIResponse
from api_monitor.models.statistics import APIStatistics
from api_monitor.notifications.base import BaseNotifier
from api_monitor.utils.logger import setup_logger

logger = setup_logger('alert_service')

class AlertType:
    """告警类型定义"""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    RECOVERY = 'recovery'

class AlertService:
    """告警服务"""
    def __init__(self, notifier: BaseNotifier, cooldown_minutes: int = 5):
        self.notifier = notifier
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.last_alert_times: Dict[str, datetime] = {}

    def should_alert(self, alert_key: str) -> bool:
        """检查是否应该发送告警"""
        if alert_key not in self.last_alert_times:
            return True
        
        time_since_last = datetime.now() - self.last_alert_times[alert_key]
        return time_since_last >= self.cooldown

    def _update_alert_time(self, alert_key: str):
        """更新告警时间"""
        self.last_alert_times[alert_key] = datetime.now()

    def process_response(self, api_config: APIConfig, response: APIResponse, 
                        stats: APIStatistics) -> None:
        """处理API响应并决定是否需要告警"""
        self._check_status(api_config, response, stats)
        self._check_response_time(api_config, response, stats)
        self._check_availability(api_config, stats)

    def _check_status(self, api_config: APIConfig, response: APIResponse, 
                     stats: APIStatistics):
        """检查状态码"""
        if not response.success:
            alert_key = f"{api_config.name}_status"
            if self.should_alert(alert_key):
                self.notifier.send_alert(
                    title=f"API Status Alert: {api_config.name}",
                    content=f"API returned non-200 status code: {response.status_code}\n"
                           f"Error: {response.error if response.error else 'Unknown'}",
                    alert_type=AlertType.ERROR
                )
                self._update_alert_time(alert_key)

    def _check_response_time(self, api_config: APIConfig, response: APIResponse, 
                           stats: APIStatistics):
        """检查响应时间"""
        if response.response_time > api_config.critical_response_time:
            alert_key = f"{api_config.name}_response_time_critical"
            if self.should_alert(alert_key):
                self.notifier.send_alert(
                    title=f"Critical Response Time: {api_config.name}",
                    content=f"Response time ({response.response_time:.2f}s) exceeds "
                           f"critical threshold ({api_config.critical_response_time}s)",
                    alert_type=AlertType.ERROR
                )
                self._update_alert_time(alert_key)
        elif response.response_time > api_config.warning_response_time:
            alert_key = f"{api_config.name}_response_time_warning"
            if self.should_alert(alert_key):
                self.notifier.send_alert(
                    title=f"Slow Response Time: {api_config.name}",
                    content=f"Response time ({response.response_time:.2f}s) exceeds "
                           f"warning threshold ({api_config.warning_response_time}s)",
                    alert_type=AlertType.WARNING
                )
                self._update_alert_time(alert_key)

    def _check_availability(self, api_config: APIConfig, stats: APIStatistics):
        """检查可用性"""
        availability = stats.get_availability_rate()
        if availability < api_config.availability_threshold:
            alert_key = f"{api_config.name}_availability"
            if self.should_alert(alert_key):
                self.notifier.send_alert(
                    title=f"Low Availability: {api_config.name}",
                    content=f"Availability ({availability:.1f}%) is below threshold "
                           f"({api_config.availability_threshold}%)",
                    alert_type=AlertType.WARNING
                )
                self._update_alert_time(alert_key)

    def send_recovery(self, api_config: APIConfig, alert_type: str, 
                     message: str) -> None:
        """发送恢复通知"""
        alert_key = f"{api_config.name}_recovery_{alert_type}"
        if self.should_alert(alert_key):
            self.notifier.send_recovery(
                title=f"Service Recovery: {api_config.name}",
                content=message
            )
            self._update_alert_time(alert_key)