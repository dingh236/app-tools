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
        create_api_config('线上API', 'https://api.fitnexa.com/ys/device/user/info'),
        create_api_config('测试API', 'https://aitest.fitnexa.com/ys/device/user/info'),
        create_api_config('线上API-IP', 'http://40.90.222.230/ys/device/user/info'),
        create_api_config('httpbin', 'https://httpbin.org/status/500'),
        create_api_config('CDN-API', 'https://fitnexa01-dcgyf3g8gygcg6eg.z01.azurefd.net/ys/device/user/info'),
        create_api_config('测试API-IP', 'http://20.157.110.98/ys/device/user/info')
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
        'webhook': 'https://open.feishu.cn/open-apis/bot/v2/hook/8b4a5064-422b-44a2-935b-2575e7db9a5b',
        'user_ids': ["c2df4aaa"]
    }

    # 日志配置
    LOG_CONFIG = {
        'log_dir': '/root/logs',
        'log_level': 'INFO',
        'log_format': '%(asctime)s - %(levelname)s - %(message)s',
        'backup_count': 30,
    }