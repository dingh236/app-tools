import time
import requests
from datetime import datetime
from typing import Tuple, Optional
from api_monitor.models.api import APIConfig, APIResponse
from api_monitor.models.statistics import APIStatistics
from api_monitor.utils.logger import setup_logger

logger = setup_logger('check_service')

class APICheckService:
    """API检查服务"""
    def __init__(self, api_config: APIConfig, statistics: APIStatistics):
        self.api_config = api_config
        self.statistics = statistics

    def check(self) -> APIResponse:
        """执行API检查"""
        start_time = time.time()
        try:
            response = self._make_request()
            response_time = time.time() - start_time
            return self._create_response(
                status_code=response.status_code,
                response_time=response_time,
                success=response.status_code == 200
            )
        except requests.Timeout:
            return self._create_response(
                response_time=time.time() - start_time,
                error="Request timed out"
            )
        except requests.RequestException as e:
            return self._create_response(
                response_time=time.time() - start_time,
                error=str(e)
            )
        except Exception as e:
            return self._create_response(
                response_time=time.time() - start_time,
                error=f"Unexpected error: {str(e)}"
            )

    def _make_request(self) -> requests.Response:
        """发送HTTP请求"""
        return requests.request(
            method=self.api_config.method,
            url=self.api_config.url,
            headers=self.api_config.headers,
            timeout=self.api_config.timeout
        )

    def _create_response(self, response_time: float, status_code: Optional[int] = None,
                        success: bool = False, error: Optional[str] = None) -> APIResponse:
        """创建API响应对象"""
        return APIResponse(
            status_code=status_code,
            response_time=response_time,
            timestamp=datetime.now(),
            error=error,
            success=success
        )
