from typing import Dict, Any

class APIMonitorDefaults:
    """默认的API监控配置"""
    API_CONFIG = {
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

    MONITOR_CONFIG = {
        'check_interval': 30,
        'alert_check_count': 10,
        'statistics_window': 60,
        'alert_cooldown': 5
    }