# API Monitor

## 简介
API Monitor是一个基于Python的API监控工具，用于监控多个API端点的可用性、响应时间和状态。

### 主要特性
- 支持多API端点同时监控
- 自动告警（通过飞书机器人）
- 统计数据收集和分析 
- 日志记录和轮转
- 可配置的告警阈值和检查间隔
- 自动恢复通知

## 目录结构
```
api_monitor/                 # 项目主目录
├── config/
│   ├── __init__.py
│   ├── default_config.py    # 默认配置
│   └── settings.py          # 用户配置
├── core/
│   ├── __init__.py
│   ├── monitor.py           # 核心监控类
│   └── scheduler.py         # 调度器
├── models/
│   ├── __init__.py
│   ├── api.py              # API相关数据模型
│   └── statistics.py       # 统计数据模型
├── services/
│   ├── __init__.py
│   ├── alert_service.py    # 告警服务
│   └── check_service.py    # 检查服务
├── utils/
│   ├── __init__.py
│   ├── logger.py           # 日志工具
│   └── validators.py       # 验证工具
├── notifications/
│   ├── __init__.py
│   ├── base.py            # 基础通知类
│   └── feishu.py          # 飞书通知实现
├── setup.py               # 入口文件
├── start.py              # 启动文件
└── requirements.txt      # 依赖管理
```

### 日志目录
```
/var/log/api_monitor        # 日志路径/按天切割/保留时间30天
├── alert_service.log
├── check_service.log
├── feishu_notifier.log
├── main.log
├── monitor.log
└── scheduler.log
```

## 配置说明

### API配置
在 `api_monitor/config/settings.py` 中修改API配置列表：
```python
# API配置列表
APIS = [
    create_api_config('httpbin', 'https://httpbin.org/status/500'),
    create_api_config('$API_name', '$API_URL')
]

# 飞书配置
FEISHU_CONFIG = {
    'webhook': '飞书机器人Webhook地址',
    'user_ids': ["用户ID1"]
}
```

### 监控参数配置
在 `api_monitor/config/default_config.py` 中通过 `MONITOR_CONFIG` 字典配置监控参数：

```python
class APIMonitorDefaults:
    """默认的API监控配置"""
    API_CONFIG = {
        'method': 'GET',
        'timeout': 20,                 # 超时时间（秒）
        'warning_response_time': 3,    # 警告响应时间阈值（秒）
        'critical_response_time': 5,   # 严重响应时间阈值（秒）
        'headers': {
            'User-Agent': 'API-Monitor/1.0'
        },
        'success_rate_threshold': 95,  # 成功率阈值（%）
        'availability_threshold': 98   # 可用性阈值（%）
    }
    
    MONITOR_CONFIG = {
        'check_interval': 30,          # 检查间隔（秒）
        'alert_check_count': 10,       # 触发告警的连续次数
        'statistics_window': 60,       # 统计窗口大小（次数）
        'alert_cooldown': 5            # 告警冷却时间（分钟）
    }
```

## 启动方式
```bash
source work/venv/bin/activate
python api_monitor/start.py
```

## 监控指标

### 响应时间
- 警告阈值：3秒
- 严重阈值：5秒

### 可用性指标
- 成功率阈值：95%
- 可用性阈值：98%

### 状态码监控
- 正常：200
- 警告级别：401, 403, 404, 429
- 严重级别：500, 502, 503, 504