#!/bin/bash
# /root/app-tools/monitoring_system/run.sh

# 激活虚拟环境
source /root/app-tools/work/venv/bin/activate

# 设置 Python 路径
export PYTHONPATH="/root/app-tools/monitoring_system:$PYTHONPATH"

# 运行监控系统
python /root/app-tools/monitoring_system/start.py