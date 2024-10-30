# api_monitor/config/settings.py
from typing import List, Dict
from .default_config import APIMonitorDefaults

class APIMonitorSettings:
    """API监控系统配置"""
    @staticmethod
    def create_api_config(name: str, url: str) -> Dict:
        """创建API配置"""
        return {
            'name': name,
            'url': url,
            **APIMonitorDefaults.API_CONFIG
        }

    # API配置列表
    APIS = [
    create_api_config('httpbin', 'https://httpbin.org/status/500'),
    create_api_config('$API_name', '$API_URL')
    ]

    # 监控配置
    MONITOR_CONFIG = {
        'check_interval': 30,  # 检查间隔（秒）
        'alert_check_count': 10,  # 需要检查的次数才触发告警
        'statistics_window': 60,  # 统计窗口大小
        'alert_cooldown': 5  # 告警冷却时间（分钟）
    }

    # 飞书配置
    FEISHU_CONFIG = {
        'webhook': '飞书机器人Webhook地址',
        'user_ids': ["用户ID1"]
    }

    # 日志配置
    LOG_CONFIG = {
        'log_dir': '/root/logs',
        'log_level': 'INFO',
        'log_format': '%(asctime)s - %(levelname)s - %(message)s',
        'backup_count': 30,
    }
