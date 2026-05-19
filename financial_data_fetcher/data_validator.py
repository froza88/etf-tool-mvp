#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DataValidator - 数据验证器

交叉验证、异常检测、字段完整性检查。
"""

import json
from pathlib import Path


class DataValidator:
    """数据验证器"""

    def __init__(self):
        self.rules = {}

    def validate(self, data, schema=None):
        """验证数据是否符合规范"""
        if not data:
            return False, ["数据为空"]

        errors = []
        
        # 基础检查：必要字段存在
        required = schema.get("required", []) if schema else []
        for field in required:
            if field not in data or data[field] is None:
                errors.append(f"缺失必要字段: {field}")

        # 类型检查
        types = schema.get("types", {}) if schema else {}
        for field, expected_type in types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(f"字段 {field} 类型错误: 期望 {expected_type}, 实际 {type(data[field])}")

        return len(errors) == 0, errors

    def cross_validate(self, data_from_source1, data_from_source2, fields=None):
        """交叉验证两个数据源的数据"""
        if not data_from_source1 or not data_from_source2:
            return False, ["数据源为空"]

        mismatches = []
        check_fields = fields or list(data_from_source1.keys())

        for field in check_fields:
            v1 = data_from_source1.get(field)
            v2 = data_from_source2.get(field)
            if v1 is None or v2 is None:
                continue
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                diff_pct = abs(v1 - v2) / max(abs(v1), abs(v2), 1) * 100
                if diff_pct > 5:  # 5% 差异阈值
                    mismatches.append(f"{field}: {v1} vs {v2} (差 {diff_pct:.1f}%)")
            elif v1 != v2:
                mismatches.append(f"{field}: {v1} vs {v2}")

        return len(mismatches) == 0, mismatches

    def detect_anomalies(self, data_list, field, threshold=3.0):
        """检测异常值（3sigma原则）"""
        values = [d.get(field) for d in data_list if d.get(field) is not None]
        if len(values) < 10:
            return []

        mean = sum(values) / len(values)
        std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5

        anomalies = []
        for i, v in enumerate(values):
            if abs(v - mean) > threshold * std:
                anomalies.append((i, v, mean + threshold * std))

        return anomalies
