# alerts/rules.py
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class AlertRule:
    """告警规则数据类"""
    name: str
    type: str
    metric: str
    operator: str
    threshold: float
    duration: int
    severity: str
    description: str

class AlertRulesManager:
    """告警规则管理器"""
    def __init__(self, rules_file: str):
        self.rules_file = rules_file
        self.rules = self._load_rules()

    def _load_rules(self) -> List[AlertRule]:
        """加载告警规则"""
        try:
            with open(self.rules_file, 'r') as f:
                rules_data = json.load(f)
            
            rules = []
            for rule in rules_data.get('rules', []):
                rules.append(AlertRule(
                    name=rule['name'],
                    type=rule['type'],
                    metric=rule['metric'],
                    operator=rule['operator'],
                    threshold=float(rule['threshold']),
                    duration=int(rule['duration']),
                    severity=rule['severity'],
                    description=rule['description']
                ))
            
            logger.info(f"Successfully loaded {len(rules)} alert rules")
            return rules
        except FileNotFoundError:
            logger.error(f"Rules file not found: {self.rules_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in rules file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            raise

    def check_rule(self, metric_type: str, metrics: Dict[str, float]) -> List[AlertRule]:
        """检查是否触发告警规则"""
        triggered_rules = []
        
        for rule in self.rules:
            if rule.type == metric_type and rule.metric in metrics:
                if self._evaluate_condition(rule, metrics[rule.metric]):
                    triggered_rules.append(rule)
        
        return triggered_rules

    def _evaluate_condition(self, rule: AlertRule, value: float) -> bool:
        """评估条件"""
        operators = {
            '>': lambda x, y: x > y,
            '<': lambda x, y: x < y,
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '>=': lambda x, y: x >= y,
            '<=': lambda x, y: x <= y
        }
        
        operator_func = operators.get(rule.operator)
        if not operator_func:
            logger.warning(f"Unsupported operator: {rule.operator}")
            return False
            
        return operator_func(value, rule.threshold)