import logging
import os
from logging.handlers import TimedRotatingFileHandler
from api_monitor.config.settings import APIMonitorSettings

def setup_logger(name: str) -> logging.Logger:
    """设置日志记录器"""
    logger = logging.getLogger(name)
    
    # 如果已经设置过handler，直接返回
    if logger.handlers:
        return logger

    logger.setLevel(APIMonitorSettings.LOG_CONFIG['log_level'])

    # 确保日志目录存在
    os.makedirs(APIMonitorSettings.LOG_CONFIG['log_dir'], exist_ok=True)

    # 创建格式化器
    formatter = logging.Formatter(APIMonitorSettings.LOG_CONFIG['log_format'])

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 添加文件处理器
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(APIMonitorSettings.LOG_CONFIG['log_dir'], f'{name}.log'),
        when='midnight',
        interval=1,
        backupCount=APIMonitorSettings.LOG_CONFIG['backup_count'],
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
