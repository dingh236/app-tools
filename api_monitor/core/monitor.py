# api_monitor/core/monitor.py
from typing import List, Dict, Optional
import time
import requests
from datetime import datetime

from api_monitor.models.api import APIConfig
from api_monitor.models.statistics import APIStatistics
from api_monitor.notifications.base import BaseNotifier
from api_monitor.utils.logger import setup_logger

logger = setup_logger('monitor')

class AlertType:
    """告警类型常量"""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    RECOVERY = 'recovery'

class APIMonitor:
    """API监控核心类"""
    def __init__(self, apis: List[Dict], notifier: BaseNotifier):
        self.apis = apis
        self.notifier = notifier
        self.api_stats = {}
        self.initialize_statistics()

    def initialize_statistics(self):
        """初始化统计数据"""
        for api in self.apis:
            self.api_stats[api['url']] = APIStatistics(
                window_size=api.get('statistics_window', 60)
            )

    def calculate_statistics(self, api_url: str) -> Dict:
        """计算API的统计指标"""
        stats = self.api_stats[api_url]
        stats.update_window_stats()
        
        if not stats.response_times:
            return {}

        response_times = list(stats.response_times)
        window_duration = len(response_times) * 30 / 60  # 转换为分钟
        
        return {
            'avg_response_time': sum(response_times) / len(response_times),
            'max_response_time': max(response_times),
            'min_response_time': min(response_times),
            'success_rate': (stats.window_successful_requests / 
                           stats.window_total_requests * 100 if 
                           stats.window_total_requests > 0 else 0),
            'availability': (stats.window_available_requests / 
                           stats.window_total_requests * 100 if 
                           stats.window_total_requests > 0 else 0),
            'request_count': stats.window_total_requests,
            'window_duration_minutes': window_duration
        }

    def can_send_alert(self, api_url: str, alert_type: str) -> bool:
        """检查是否可以发送告警（基于冷却时间）"""
        stats = self.api_stats[api_url]
        current_time = time.time()
        cooldown_seconds = 5 * 60  # 5分钟冷却时间
        
        if current_time - stats.last_alert_time[alert_type] >= cooldown_seconds:
            stats.last_alert_time[alert_type] = current_time
            return True
        return False

    def send_alert(self, api_config: dict, alert_type: str, content: str,
                response_time: Optional[float] = None,
                status_code: Optional[int] = None,
                stats: Optional[dict] = None):
        """发送告警"""
        try:
            if not self.can_send_alert(api_config['url'], alert_type):
                logger.info(f"Alert suppressed for {api_config['name']} due to cooldown")
                return

            self.notifier.send_alert(
                title=f"API Monitor Alert: {api_config['name']}",
                content=content,
                alert_type=alert_type,
                response_time=response_time,
                status_code=status_code,
                stats=stats,
                url=api_config['url']  # 添加 URL
            )

        except Exception as e:
            logger.error(f"Error sending alert for {api_config['name']}: {str(e)}")

    def send_recovery_alert(self, api_config: dict, recovery_type: str, content: str):
        """发送恢复通知"""
        try:
            if not self.can_send_alert(api_config['url'], f"recovery_{recovery_type}"):
                return

            self.notifier.send_recovery(
                title=f"API Recovery: {api_config['name']}",
                content=content
            )

        except Exception as e:
            logger.error(f"Error sending recovery alert for {api_config['name']}: {str(e)}")

    def _check_status_code(self, api_config: dict, response: requests.Response,
                          response_time: float, stats: APIStatistics):
        """检查状态码"""
        current_stats = self.calculate_statistics(api_config['url'])
        
        if response.status_code != 200:
            stats.error_counts['status_code'] += 1
            if stats.error_counts['status_code'] >= 10:  # 连续10次触发告警
                self.send_alert(
                    api_config,
                    AlertType.ERROR if response.status_code >= 500 else AlertType.WARNING,
                    f"API returned non-200 status code ({response.status_code}) for 10 consecutive checks",
                    response_time=response_time,
                    status_code=response.status_code,
                    stats=current_stats
                )
        else:
            if stats.error_counts['status_code'] >= 10:
                self.send_recovery_alert(
                    api_config,
                    'status_code',
                    "API status code has returned to 200"
                )
            stats.error_counts['status_code'] = 0
            stats.successful_requests += 1

    def _check_response_time(self, api_config: dict, response_time: float,
                           stats: APIStatistics):
        """检查响应时间"""
        current_stats = self.calculate_statistics(api_config['url'])
        
        if response_time > api_config['critical_response_time']:
            stats.error_counts['response_time'] += 1
            if stats.error_counts['response_time'] >= 10:
                self.send_alert(
                    api_config,
                    AlertType.ERROR,
                    f"Response time ({response_time:.3f}s) exceeded critical threshold "
                    f"({api_config['critical_response_time']}s) for 10 consecutive checks",
                    response_time=response_time,
                    stats=current_stats
                )
        elif response_time > api_config['warning_response_time']:
            stats.error_counts['response_time'] += 1
            if stats.error_counts['response_time'] >= 10:
                self.send_alert(
                    api_config,
                    AlertType.WARNING,
                    f"Response time ({response_time:.3f}s) exceeded warning threshold "
                    f"({api_config['warning_response_time']}s) for 10 consecutive checks",
                    response_time=response_time,
                    stats=current_stats
                )
        else:
            if stats.error_counts['response_time'] >= 10:
                self.send_recovery_alert(
                    api_config,
                    'response_time',
                    f"Response time has returned to normal: {response_time:.3f}s"
                )
            stats.error_counts['response_time'] = 0

    def check_api(self, api_config: dict):
        """检查单个API状态"""
        logger.info(f"Checking API: {api_config['name']} - {api_config['url']}")
        start_time = time.time()
        stats = self.api_stats[api_config['url']]

        try:
            response = requests.request(
                method=api_config['method'],
                url=api_config['url'],
                headers=api_config['headers'],
                timeout=api_config['timeout']
            )
            
            response_time = time.time() - start_time
            stats.add_response(response_time, response.status_code)

            self._check_status_code(api_config, response, response_time, stats)
            self._check_response_time(api_config, response_time, stats)

            # 记录检查结果
            current_stats = self.calculate_statistics(api_config['url'])
            logger.info(
                f"API check completed for {api_config['name']} - "
                f"Status: {response.status_code}, "
                f"Response Time: {response_time:.3f}s, "
                f"Avg Response Time: {current_stats.get('avg_response_time', 0):.3f}s, "
                f"Success Rate: {current_stats.get('success_rate', 0):.1f}%, "
                f"Availability: {current_stats.get('availability', 0):.1f}%"
            )

        except requests.Timeout:
            self._handle_timeout_error(api_config, start_time, stats)
        except requests.RequestException as e:
            self._handle_request_error(api_config, e, start_time, stats)
        except Exception as e:
            self._handle_unexpected_error(api_config, e, start_time, stats)

    def _handle_timeout_error(self, api_config: dict, start_time: float, stats: APIStatistics):
        """处理超时错误"""
        error_time = time.time() - start_time
        stats.add_response(error_time, None)
        
        current_stats = self.calculate_statistics(api_config['url'])
        self.send_alert(
            api_config,
            AlertType.ERROR,
            f"API request timed out after {api_config['timeout']}s",
            response_time=error_time,
            stats=current_stats
        )

    def _handle_request_error(self, api_config: dict, error: requests.RequestException,
                            start_time: float, stats: APIStatistics):
        """处理请求错误"""
        error_time = time.time() - start_time
        stats.add_response(error_time, None)
        
        current_stats = self.calculate_statistics(api_config['url'])
        self.send_alert(
            api_config,
            AlertType.ERROR,
            f"API request failed: {str(error)}",
            response_time=error_time,
            stats=current_stats
        )

    def _handle_unexpected_error(self, api_config: dict, error: Exception,
                                start_time: float, stats: APIStatistics):
        """处理意外错误"""
        error_time = time.time() - start_time
        stats.add_response(error_time, None)
        
        current_stats = self.calculate_statistics(api_config['url'])
        self.send_alert(
            api_config,
            AlertType.ERROR,
            f"Unexpected error: {str(error)}",
            response_time=error_time,
            stats=current_stats
        )
    

    def check_all_apis(self):
        """检查所有配置的API"""
        logger.info("=== Starting API check cycle ===")
        for api_config in self.apis:
            try:
                self.check_api(api_config)
            except Exception as e:
                logger.error(f"Failed to check API {api_config['name']}: {str(e)}", 
                           exc_info=True)
        logger.info("=== API check cycle completed ===")