from api_monitor.core.monitor import APIMonitor
from api_monitor.core.scheduler import MonitorScheduler
from api_monitor.notifications.feishu import FeishuNotifier
from api_monitor.config.settings import APIMonitorSettings
from api_monitor.utils.logger import setup_logger

logger = setup_logger('main')

def main():
    """主程序入口"""
    try:
        # 初始化通知服务
        notifier = FeishuNotifier(
            webhook_url=APIMonitorSettings.FEISHU_CONFIG['webhook'],
            user_ids=APIMonitorSettings.FEISHU_CONFIG['user_ids']
        )

        # 初始化监控器
        monitor = APIMonitor(
            apis=APIMonitorSettings.APIS,
            notifier=notifier
        )

        # 初始化并启动调度器
        scheduler = MonitorScheduler(
            monitor=monitor,
            interval_seconds=APIMonitorSettings.MONITOR_CONFIG['check_interval']
        )

        logger.info("=== API Monitoring Service Starting ===")
        logger.info(f"Monitoring {len(APIMonitorSettings.APIS)} APIs")
        scheduler.start()

    except Exception as e:
        logger.error(f"Service error: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()