from typing import Dict, Any
from api_monitor.models.api import APIConfig

class ConfigValidator:
    """配置验证器"""
    @staticmethod
    def validate_api_config(config: Dict[str, Any]) -> bool:
        """验证API配置的完整性"""
        required_fields = {
            'name', 'url', 'method', 'timeout',
            'warning_response_time', 'critical_response_time',
            'headers', 'success_rate_threshold', 'availability_threshold'
        }
        
        return all(field in config for field in required_fields)

    @staticmethod
    def validate_monitor_config(config: Dict[str, Any]) -> bool:
        """验证监控配置的完整性"""
        required_fields = {
            'check_interval', 'alert_check_count',
            'statistics_window', 'alert_cooldown'
        }
        
        return all(field in config for field in required_fields)