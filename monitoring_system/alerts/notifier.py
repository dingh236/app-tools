# alerts/notifier.py
from typing import Dict, List, Any
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AlertNotifier:
    """告警通知器"""
    def __init__(self, config: Dict):
        self.config = config
        self.notification_channels = {
            'feishu': self._send_feishu_alert,
            'email': self._send_email_alert,
            'webhook': self._send_webhook_alert
        }

    def send_alert(self, rule: Dict, metrics: Any):
        """发送告警"""
        alert_data = self._prepare_alert_data(rule, metrics)
        
        for channel in self.config['channels']:
            try:
                self.notification_channels[channel['type']](
                    alert_data,
                    channel['config']
                )
            except Exception as e:
                logger.error(f"Failed to send alert via {channel['type']}: {e}")

    def send_service_down_alert(self, metrics: Any):
        """发送服务宕机告警"""
        alert_data = {
            'title': f'Service Down: {metrics.service_name}',
            'content': (f'Service {metrics.service_name} is down.\n'
                       f'Last check time: {metrics.timestamp}\n'
                       f'Process ID: {metrics.process_id}\n'
                       f'Port: {metrics.port}'),
            'level': 'critical',
            'timestamp': datetime.now()
        }
        
        self.send_alert(None, alert_data)

    def send_service_recovery_alert(self, metrics: Any):
        """发送服务恢复告警"""
        alert_data = {
            'title': f'Service Recovered: {metrics.service_name}',
            'content': (f'Service {metrics.service_name} has recovered.\n'
                       f'Recovery time: {metrics.timestamp}\n'
                       f'Process ID: {metrics.process_id}\n'
                       f'Port: {metrics.port}'),
            'level': 'info',
            'timestamp': datetime.now()
        }
        
        self.send_alert(None, alert_data)

    def _prepare_alert_data(self, rule: Dict, metrics: Any) -> Dict:
        """准备告警数据"""
        return {
            'title': rule['name'],
            'content': self._format_alert_content(rule, metrics),
            'level': rule['severity'],
            'timestamp': datetime.now(),
            'metrics': metrics
        }

    def _format_alert_content(self, rule: Dict, metrics: Any) -> str:
        """格式化告警内容"""
        return (
            f"Alert: {rule['description']}\n"
            f"Current Value: {metrics}\n"
            f"Threshold: {rule['threshold']}\n"
            f"Duration: {rule['duration']} seconds"
        )

    def _send_feishu_alert(self, alert_data: Dict, config: Dict):
        """发送飞书告警"""
        message = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": alert_data['title']},
                    "template": "red" if alert_data['level'] == 'critical' else "orange"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {"tag": "lark_md", "content": alert_data['content']}
                    }
                ]
            }
        }

        response = requests.post(
            config['webhook_url'],
            json=message,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to send Feishu alert: {response.text}")

    def _send_email_alert(self, alert_data: Dict, config: Dict):
        """发送邮件告警"""
        msg = MIMEText(alert_data['content'])
        msg['Subject'] = alert_data['title']
        msg['From'] = config['from_addr']
        msg['To'] = config['to_addr']

        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            if config.get('use_tls'):
                server.starttls()
            if config.get('username') and config.get('password'):
                server.login(config['username'], config['password'])
            server.send_message(msg)

    def _send_webhook_alert(self, alert_data: Dict, config: Dict):
        """发送Webhook告警"""
        response = requests.post(
            config['url'],
            json=alert_data,
            headers=config.get('headers', {})
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to send webhook alert: {response.text}")