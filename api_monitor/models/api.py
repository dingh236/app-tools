from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

@dataclass
class APIResponse:
    """API响应数据模型"""
    status_code: Optional[int]
    response_time: float
    timestamp: datetime
    error: Optional[str] = None
    success: bool = False

@dataclass
class APIConfig:
    """API配置数据模型"""
    name: str
    url: str
    method: str
    timeout: int
    warning_response_time: float
    critical_response_time: float
    headers: Dict[str, str]
    success_rate_threshold: float
    availability_threshold: float

    @classmethod
    def from_dict(cls, data: Dict) -> 'APIConfig':
        return cls(**data)