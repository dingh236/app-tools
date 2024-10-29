# api_monitor/models/statistics.py
from dataclasses import dataclass, field
from collections import deque, defaultdict
from typing import Dict, Deque, Optional
from datetime import datetime

@dataclass
class APIStatistics:
    """API统计数据模型"""
    window_size: int
    response_times: Deque[float] = field(default_factory=deque)
    status_codes: Deque[Optional[int]] = field(default_factory=deque)
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_alert_time: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    last_recovery_time: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    alert_states: Dict[str, bool] = field(default_factory=lambda: defaultdict(bool))
    total_requests: int = field(default=0)
    successful_requests: int = field(default=0)
    available_requests: int = field(default=0)
    window_total_requests: int = field(default=0)
    window_successful_requests: int = field(default=0)
    window_available_requests: int = field(default=0)

    def __post_init__(self):
        """初始化限制队列长度"""
        self.response_times = deque(maxlen=self.window_size)
        self.status_codes = deque(maxlen=self.window_size)

    def update_window_stats(self):
        """更新滑动窗口统计数据"""
        self.window_total_requests = len(self.response_times)
        self.window_successful_requests = sum(1 for code in self.status_codes if code == 200)
        self.window_available_requests = sum(1 for code in self.status_codes if code is not None)

    def add_response(self, response_time: float, status_code: Optional[int]):
        """添加新的响应记录"""
        self.response_times.append(response_time)
        self.status_codes.append(status_code)
        self.total_requests += 1
        
        if status_code == 200:
            self.successful_requests += 1
        if status_code is not None:
            self.available_requests += 1

    def increment_error_count(self, error_type: str):
        """增加错误计数"""
        self.error_counts[error_type] += 1
        self.alert_states[error_type] = True

    def reset_error_count(self, error_type: str):
        """重置错误计数"""
        self.error_counts[error_type] = 0
        self.alert_states[error_type] = False
        self.last_recovery_time[error_type] = datetime.now().timestamp()