from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime

class BaseNotifier(ABC):
    """通知服务基类"""
    @abstractmethod
    def send_alert(self, title: str, content: str, alert_type: str, **kwargs) -> bool:
        """发送告警"""
        pass

    @abstractmethod
    def send_recovery(self, title: str, content: str, **kwargs) -> bool:
        """发送恢复通知"""
        pass