# api_monitor/notifications/feishu.py
import requests
from datetime import datetime
from typing import Dict, Optional
from .base import BaseNotifier
from api_monitor.config.settings import APIMonitorSettings
from api_monitor.utils.logger import setup_logger

logger = setup_logger('feishu_notifier')

class AlertType:
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'
    RECOVERY = 'recovery'

class AlertTemplate:
    ERROR = 'red'
    WARNING = 'orange'
    INFO = 'blue'
    RECOVERY = 'green'

class FeishuNotifier(BaseNotifier):
    """飞书通知实现"""
    def __init__(self, webhook_url: str, user_ids: list):
        self.webhook_url = webhook_url
        self.user_ids = user_ids

    def _build_message(self, title: str, content: str, alert_type: str, 
                    response_time: Optional[float] = None,
                    status_code: Optional[int] = None,
                    stats: Optional[Dict] = None,
                    url: Optional[str] = None) -> Dict:
        """构建飞书消息"""
        color = {
            AlertType.ERROR: AlertTemplate.ERROR,
            AlertType.WARNING: AlertTemplate.WARNING,
            AlertType.INFO: AlertTemplate.INFO,
            AlertType.RECOVERY: AlertTemplate.RECOVERY
        }.get(alert_type, AlertTemplate.INFO)

        # 构建消息内容
        content_lines = [
            f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Service**: {title}",
        ]
        
        # 添加 URL 信息
        if url:
            content_lines.append(f"**URL**: {url}")

        content_lines.extend([
            "",  # 空行作为分隔
            f"**Alert Type**: {alert_type.upper()}"
        ])

        if status_code is not None:
            content_lines.append(f"**Status Code**: {status_code}")
        
        if response_time is not None:
            content_lines.append(f"**Response Time**: {response_time:.3f}s")

        if stats:
            content_lines.extend([
                f"**Average Response Time**: {stats.get('avg_response_time', 0):.3f}s",
                f"**Success Rate**: {stats.get('success_rate', 0):.1f}%",
                f"**Availability**: {stats.get('availability', 0):.1f}%",
                f"**Total Requests**: {stats.get('request_count', 0)}"
            ])

        content_lines.extend([
            "",  # 空行作为分隔
            f"**Details**: {content}"
        ])

        message = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": color
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "\n".join(content_lines)
                        }
                    }
                ]
            }
        }

        # 添加用户@提醒
        if self.user_ids:
            message["card"]["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "".join([f"<at id={uid}>@user</at>" for uid in self.user_ids]) + " 请注意！"
                }
            })

        return message

    def send_alert(self, title: str, content: str, alert_type: str, **kwargs) -> bool:
        """发送告警消息"""
        try:
            message = self._build_message(title, content, alert_type, **kwargs)
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'}
            )
            success = response.status_code == 200
            if success:
                logger.info(f"Successfully sent {alert_type} alert: {title}")
            else:
                logger.error(f"Failed to send alert: {response.text}")
            return success
        except Exception as e:
            logger.error(f"Error sending alert: {str(e)}")
            return False

    def send_recovery(self, title: str, content: str, **kwargs) -> bool:
        """发送恢复通知"""
        return self.send_alert(title, content, AlertType.RECOVERY, **kwargs)