      
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import logging
from datetime import datetime
import os
from apscheduler.schedulers.blocking import BlockingScheduler
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Deque, Optional
import statistics
from logging.handlers import TimedRotatingFileHandler

# 确保日志目录存在
log_dir = '/root/logs'
os.makedirs(log_dir, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        TimedRotatingFileHandler(           # 按天切割日志
            os.path.join(log_dir, 'api_monitor.log'),
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('API_Monitor')

# 监控配置
DEFAULT_API_CONFIG = {
    'method': 'GET',
    'timeout': 20,
    'warning_response_time': 3,
    'critical_response_time': 5,
    'headers': {
        'User-Agent': 'API-Monitor/1.0'
    },
    'success_rate_threshold': 95,
    'availability_threshold': 98
}

def create_api_config(name, url):
    """
    创建API配置，使用默认值并只需要提供name和url
    """
    return {
        'name': name,
        'url': url,
        **DEFAULT_API_CONFIG
    }

MONITOR_CONFIG = {
    'apis': [
        # 只需要提供name和url，其他配置使用默认值
        create_api_config('线上API', 'https://api.fitnexa.com/ys/device/user/info'),
        create_api_config('测试API', 'https://apitest.fitnexa.com/ys/device/user/info'),
        create_api_config('线上API-IP', 'http://40.90.222.230/ys/device/user/info'),
        create_api_config('线上API-IP', 'https://httpbin.org/status/500'),
        create_api_config('测试API-IP', 'http://20.157.110.98/ys/device/user/info')
    ],
    'check_interval': 30,  # 检查间隔（秒）
    'alert_check_count': 10,  # 需要检查的次数才触发告警
    'statistics_window': 60,  # 统计窗口大小（存储60次采样点）
    'alert_cooldown': 5  # 告警冷却时间（分钟）
}

# 飞书配置
FEISHU_CONFIG = {
   'webhook': 'https://open.feishu.cn/open-apis/bot/v2/hook/1703bcca-9f9b-4829-a7cd-f0c65842af7e',
   'user_ids': ["c2df4aaa"]
}

class AlertType:
    """告警类型常量"""
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    RECOVERY = 'recovery'

class AlertTemplate:
    """告警模板常量"""
    ERROR = 'red'
    WARNING = 'orange'
    INFO = 'blue'
    RECOVERY = 'green'

# 状态码告警级别配置
STATUS_ALERT_LEVELS = {
    401: AlertType.WARNING,   # 未授权
    403: AlertType.WARNING,   # 禁止访问
    404: AlertType.WARNING,   # 未找到
    429: AlertType.WARNING,   # 请求过多
    500: AlertType.ERROR,     # 服务器错误
    502: AlertType.ERROR,     # 网关错误
    503: AlertType.ERROR,     # 服务不可用
    504: AlertType.ERROR,     # 网关超时
}

@dataclass
class APIStatistics:
    """API统计数据类"""
    response_times: Deque[float] = None
    status_codes: Deque[int] = None
    error_counts: Dict[str, int] = None
    last_alert_time: Dict[str, float] = None
    last_recovery_time: Dict[str, float] = None
    total_requests: int = 0
    successful_requests: int = 0
    available_requests: int = 0
    alert_states: Dict[str, bool] = None
    window_total_requests: int = 0
    window_successful_requests: int = 0
    window_available_requests: int = 0

    def __post_init__(self):
        self.response_times = deque(maxlen=MONITOR_CONFIG['statistics_window'])
        self.status_codes = deque(maxlen=MONITOR_CONFIG['statistics_window'])
        self.error_counts = defaultdict(int)
        self.last_alert_time = defaultdict(float)
        self.last_recovery_time = defaultdict(float)
        self.alert_states = defaultdict(bool)

    def update_window_stats(self):
        """更新滑动窗口统计数据"""
        self.window_total_requests = len(self.response_times)
        self.window_successful_requests = sum(1 for code in self.status_codes if code == 200)
        self.window_available_requests = sum(1 for code in self.status_codes if code is not None)

    def should_trigger_alert(self, error_type: str) -> bool:
        """检查是否应该触发告警"""
        return self.error_counts[error_type] >= MONITOR_CONFIG['alert_check_count']

    def reset_error_count(self, error_type: str):
        """重置错误计数并记录恢复时间"""
        self.error_counts[error_type] = 0
        self.last_recovery_time[error_type] = time.time()
        self.alert_states[error_type] = False

    def increment_error_count(self, error_type: str):
        """增加错误计数"""
        self.error_counts[error_type] += 1
        self.alert_states[error_type] = True

class AlertMessage:
    """告警消息构建类"""
    @staticmethod
    def build_alert_message(api_config: dict, alert_type: str, content: str,
                          response_time: Optional[float] = None,
                          status_code: Optional[int] = None,
                          stats: Optional[dict] = None) -> dict:
        """构建告警消息"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        color = {
            AlertType.ERROR: AlertTemplate.ERROR,
            AlertType.WARNING: AlertTemplate.WARNING,
            AlertType.INFO: AlertTemplate.INFO,
            AlertType.RECOVERY: AlertTemplate.RECOVERY
        }.get(alert_type, AlertTemplate.INFO)

        message = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"API Monitor Alert: {api_config['name']}"
                    },
                    "template": color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**Time**: {current_time}\n"
                                f"**Service**: {api_config['name']}\n"
                                f"**URL**: {api_config['url']}"
                            )
                        }
                    },
                    {
                        "tag": "hr"
                    }
                ]
            }
        }

        # 构建状态信息
        status_info = [
            f"**Alert Type**: {alert_type.upper()}",
            f"**Status Code**: {status_code if status_code is not None else 'N/A'}"
        ]
        
        if response_time is not None:
            status_info.append(f"**Response Time**: {response_time:.3f}s")
        
        if stats:
            status_info.extend([
                f"**Average Response Time**: {stats.get('avg_response_time', 0):.3f}s",
                f"**Success Rate**: {stats.get('success_rate', 0):.1f}%",
                f"**Availability**: {stats.get('availability', 0):.1f}%",
                f"**Total Requests**: {stats.get('request_count', 0)}"
            ])

        status_info.append(f"**Details**: {content}")

        message["card"]["elements"].append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": "\n".join(status_info)
            }
        })

        # 添加@提醒
        message["card"]["elements"].append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"\n{' '.join([f'<at id={user_id}>@user</at>' for user_id in FEISHU_CONFIG['user_ids']])} 请注意！"
            }
        })

        return message

class APIMonitor:
    """API监控类"""
    def __init__(self):
        self.api_stats = {}
        self.initialize_statistics()

    def initialize_statistics(self):
        """初始化统计数据"""
        for api in MONITOR_CONFIG['apis']:
            try:
                self.validate_api_config(api)
                self.api_stats[api['url']] = APIStatistics()
            except ValueError as e:
                logger.error(f"Invalid API configuration: {str(e)}")
                continue

    @staticmethod
    def validate_api_config(api_config: dict):
        """验证API配置的完整性"""
        required_fields = {
            'name', 'url', 'method', 'timeout', 
            'warning_response_time', 'critical_response_time',
            'success_rate_threshold', 'availability_threshold'
        }
        missing_fields = required_fields - set(api_config.keys())
        if missing_fields:
            raise ValueError(f"API {api_config['name']} missing required fields: {missing_fields}")

    def calculate_statistics(self, api_url: str) -> dict:
        """计算API的统计指标"""
        stats = self.api_stats[api_url]
        stats.update_window_stats()
        
        if not stats.response_times:
            return {}

        response_times = list(stats.response_times)
        window_duration = (MONITOR_CONFIG['statistics_window'] * 
                         MONITOR_CONFIG['check_interval']) / 60  # 转换为分钟
        
        return {
            'avg_response_time': statistics.mean(response_times),
            'max_response_time': max(response_times),
            'min_response_time': min(response_times),
            'success_rate': (stats.window_successful_requests / stats.window_total_requests * 100) 
                           if stats.window_total_requests > 0 else 0,
            'availability': (stats.window_available_requests / stats.window_total_requests * 100) 
                           if stats.window_total_requests > 0 else 0,
            'request_count': stats.window_total_requests,
            'window_duration_minutes': window_duration
        }

    def can_send_alert(self, api_url: str, alert_type: str) -> bool:
        """检查是否可以发送告警（基于冷却时间）"""
        stats = self.api_stats[api_url]
        current_time = time.time()
        cooldown_seconds = MONITOR_CONFIG['alert_cooldown'] * 60
        
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

            message = AlertMessage.build_alert_message(
                api_config, alert_type, content, response_time, status_code, stats
            )

            response = requests.post(
                FEISHU_CONFIG['webhook'],
                headers={'Content-Type': 'application/json'},
                json=message
            )

            if response.status_code == 200:
                logger.info(f"Alert sent successfully for {api_config['name']}: {alert_type}")
            else:
                logger.error(f"Failed to send alert for {api_config['name']}: {response.text}")

        except Exception as e:
            logger.error(f"Error sending alert for {api_config['name']}: {str(e)}")

    def send_recovery_alert(self, api_config: dict, alert_type: str, content: str):
        """发送恢复通知"""
        try:
            if not self.can_send_alert(api_config['url'], f"recovery_{alert_type}"):
                return

            recovery_message = AlertMessage.build_alert_message(
                api_config=api_config,
                alert_type=AlertType.RECOVERY,
                content=content
            )

            response = requests.post(
                FEISHU_CONFIG['webhook'],
                headers={'Content-Type': 'application/json'},
                json=recovery_message
            )

            if response.status_code == 200:
                logger.info(f"Recovery alert sent successfully for {api_config['name']}: {alert_type}")
            else:
                logger.error(f"Failed to send recovery alert for {api_config['name']}: {response.text}")

        except Exception as e:
            logger.error(f"Error sending recovery alert for {api_config['name']}: {str(e)}")

    def check_api(self, api_config: dict):
        """检查单个API状态"""
        start_time = time.time()
        stats = self.api_stats[api_config['url']]
        stats.total_requests += 1

        try:
            logger.info(f"Starting API check for {api_config['name']} - {api_config['url']}")
            self._perform_api_check(api_config, stats, start_time)
            logger.info(f"API check completed successfully for {api_config['name']}")
        except Exception as e:
            self._handle_check_exception(api_config, e, start_time, stats)

    def _perform_api_check(self, api_config: dict, stats: APIStatistics, start_time: float):
        """执行API检查"""
        response = requests.request(
            method=api_config['method'],
            url=api_config['url'],
            headers=api_config['headers'],
            timeout=api_config['timeout']
        )
        
        response_time = time.time() - start_time
        self._process_response(api_config, response, response_time, stats)

    def _process_response(self, api_config: dict, response: requests.Response, 
                        response_time: float, stats: APIStatistics):
        """处理API响应"""
        stats.response_times.append(response_time)
        stats.status_codes.append(response.status_code)
        stats.available_requests += 1

        # 添加日志记录 API 检查的详细结果
        current_stats = self.calculate_statistics(api_config['url'])
        logger.info(
            f"[{api_config['name']}] API check completed - Status: {response.status_code}, "
            f"Response Time: {response_time:.3f}s"
        )
        logger.info(
            f"[{api_config['name']}] Current Statistics - "
            f"Avg Response Time: {current_stats.get('avg_response_time', 0):.3f}s, "
            f"Success Rate: {current_stats.get('success_rate', 0):.1f}%, "
            f"Availability: {current_stats.get('availability', 0):.1f}%"
        )

        # 检查状态码
        self._check_status_code(api_config, response.status_code, response_time, stats)
        
        # 检查响应时间
        self._check_response_time(api_config, response_time, response.status_code, stats)
        
        # 检查成功率和可用性
        if stats.window_total_requests >= MONITOR_CONFIG['alert_check_count']:
            self._check_success_rate_and_availability(api_config, response_time, response.status_code, stats)


    def _check_status_code(self, api_config: dict, status_code: int, 
                          response_time: float, stats: APIStatistics):
        """检查状态码"""
        if status_code != 200:
            stats.increment_error_count('status_code')
            if stats.should_trigger_alert('status_code'):
                current_stats = self.calculate_statistics(api_config['url'])
                self.send_alert(
                    api_config,
                    STATUS_ALERT_LEVELS.get(status_code, AlertType.ERROR),
                    f"API returned non-200 status code for {MONITOR_CONFIG['alert_check_count']} consecutive checks\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes",
                    response_time=response_time,
                    status_code=status_code,
                    stats=current_stats
                )
        else:
            stats.successful_requests += 1
            if stats.error_counts['status_code'] >= MONITOR_CONFIG['alert_check_count']:
                current_stats = self.calculate_statistics(api_config['url'])
                self.send_recovery_alert(
                    api_config, 
                    'status_code', 
                    f"API status code has returned to 200\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes"
                )
            stats.reset_error_count('status_code')

    def _check_response_time(self, api_config: dict, response_time: float, 
                           status_code: int, stats: APIStatistics):
        """检查响应时间"""
        if response_time > api_config['critical_response_time']:
            stats.increment_error_count('critical_response_time')
            if stats.should_trigger_alert('critical_response_time'):
                current_stats = self.calculate_statistics(api_config['url'])
                self.send_alert(
                    api_config,
                    AlertType.ERROR,
                    f"Response time critically high for {MONITOR_CONFIG['alert_check_count']} consecutive checks\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes",
                    response_time=response_time,
                    status_code=status_code,
                    stats=current_stats
                )
        elif response_time > api_config['warning_response_time']:
            stats.increment_error_count('warning_response_time')
            if stats.should_trigger_alert('warning_response_time'):
                current_stats = self.calculate_statistics(api_config['url'])
                self.send_alert(
                    api_config,
                    AlertType.WARNING,
                    f"Response time exceeds warning threshold for {MONITOR_CONFIG['alert_check_count']} consecutive checks\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes",
                    response_time=response_time,
                    status_code=status_code,
                    stats=current_stats
                )
        else:
            if (stats.error_counts['critical_response_time'] >= MONITOR_CONFIG['alert_check_count'] or
                    stats.error_counts['warning_response_time'] >= MONITOR_CONFIG['alert_check_count']):
                current_stats = self.calculate_statistics(api_config['url'])
                self.send_recovery_alert(
                    api_config, 
                    'response_time', 
                    f"Response time has returned to normal: {response_time:.3f}s\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes"
                )
            stats.reset_error_count('critical_response_time')
            stats.reset_error_count('warning_response_time')

    def _check_success_rate_and_availability(self, api_config: dict, response_time: float, 
                                           status_code: int, stats: APIStatistics):
        """检查成功率和可用性"""
        current_stats = self.calculate_statistics(api_config['url'])
        
        # 检查成功率
        if current_stats['success_rate'] < api_config['success_rate_threshold']:
            stats.increment_error_count('success_rate')
            if stats.should_trigger_alert('success_rate'):
                self.send_alert(
                    api_config,
                    AlertType.WARNING,
                    f"Success rate below threshold for {MONITOR_CONFIG['alert_check_count']} consecutive checks\n"
                    f"Current rate: {current_stats['success_rate']:.1f}%\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes",
                    response_time=response_time,
                    status_code=status_code,
                    stats=current_stats
                )
        else:
            if stats.error_counts['success_rate'] >= MONITOR_CONFIG['alert_check_count']:
                self.send_recovery_alert(
                    api_config, 
                    'success_rate', 
                    f"Success rate has returned to normal: {current_stats['success_rate']:.1f}%\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes"
                )
            stats.reset_error_count('success_rate')

        # 检查可用性
        if current_stats['availability'] < api_config['availability_threshold']:
            stats.increment_error_count('availability')
            if stats.should_trigger_alert('availability'):
                self.send_alert(
                    api_config,
                    AlertType.WARNING,
                    f"Availability below threshold for {MONITOR_CONFIG['alert_check_count']} consecutive checks\n"
                    f"Current availability: {current_stats['availability']:.1f}%\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes",
                    response_time=response_time,
                    status_code=status_code,
                    stats=current_stats
                )
        else:
            if stats.error_counts['availability'] >= MONITOR_CONFIG['alert_check_count']:
                self.send_recovery_alert(
                    api_config, 
                    'availability', 
                    f"Availability has returned to normal: {current_stats['availability']:.1f}%\n"
                    f"Statistics based on last {current_stats['window_duration_minutes']:.1f} minutes"
                )
            stats.reset_error_count('availability')

    def _handle_check_exception(self, api_config: dict, e: Exception, 
                            start_time: float, stats: APIStatistics):
        """处理API检查过程中的异常"""
        error_time = time.time() - start_time
        stats.increment_error_count('exception')
        
        if isinstance(e, requests.exceptions.Timeout):
            error_message = f"API request timed out after {api_config['timeout']}s"
        elif isinstance(e, requests.exceptions.RequestException):
            error_message = f"API request failed: {str(e)}"
        else:
            error_message = f"Unexpected error: {str(e)}"
        
        current_stats = self.calculate_statistics(api_config['url'])
        logger.error(
            f"[{api_config['name']}] {error_message} - "
            f"Response Time: {error_time:.3f}s - "
            f"Avg Response Time: {current_stats.get('avg_response_time', 0):.3f}s, "
            f"Success Rate: {current_stats.get('success_rate', 0):.1f}%, "
            f"Availability: {current_stats.get('availability', 0):.1f}%"
        )
        
        if stats.should_trigger_alert('exception'):
            self.send_alert(
                api_config,
                AlertType.ERROR,
                f"{error_message} for {MONITOR_CONFIG['alert_check_count']} consecutive checks\n"
                f"Statistics based on last {current_stats.get('window_duration_minutes', 0):.1f} minutes",
                response_time=error_time,
                stats=current_stats
            )

    def check_all_apis(self):
        """检查所有配置的API"""
        logger.info("=== Starting API check cycle ===")
        for api_config in MONITOR_CONFIG['apis']:
            try:
                self.check_api(api_config)
            except Exception as e:
                logger.error(f"Failed to check API {api_config['name']}: {str(e)}", exc_info=True)
        logger.info("=== API check cycle completed ===")

def main():
    """主函数"""
    monitor = APIMonitor()
    scheduler = BlockingScheduler()
    
    scheduler.add_job(
        monitor.check_all_apis,
        'interval',
        seconds=MONITOR_CONFIG['check_interval']
    )

    logger.info("=== API Monitoring Service Started ===")
    logger.info("Monitoring following APIs:")
    for api in MONITOR_CONFIG['apis']:
        logger.info(f"- {api['name']}: {api['url']}")
    logger.info(f"Check interval: {MONITOR_CONFIG['check_interval']} seconds")
    logger.info(f"Alert trigger count: {MONITOR_CONFIG['alert_check_count']} consecutive checks")
    logger.info(f"Statistics window: {MONITOR_CONFIG['statistics_window']} samples")
    
    try:
        monitor.check_all_apis()  # 立即执行一次检查
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("=== Monitoring service stopped ===")
    except Exception as e:
        logger.error(f"Service error: {str(e)}", exc_info=True)

if __name__ == '__main__':
    main()