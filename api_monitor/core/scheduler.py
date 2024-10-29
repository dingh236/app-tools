from apscheduler.schedulers.blocking import BlockingScheduler
from api_monitor.core.monitor import APIMonitor
from api_monitor.utils.logger import setup_logger

logger = setup_logger('scheduler')

class MonitorScheduler:
    """监控调度器"""
    def __init__(self, monitor: APIMonitor, interval_seconds: int):
        self.monitor = monitor
        self.interval = interval_seconds
        self.scheduler = BlockingScheduler()

    def start(self):
        """启动调度器"""
        try:
            logger.info(f"Starting scheduler with {self.interval}s interval")
            self.scheduler.add_job(
                self.monitor.check_all_apis,
                'interval',
                seconds=self.interval
            )
            self.monitor.check_all_apis()  # 立即执行一次
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {str(e)}", exc_info=True)
            raise