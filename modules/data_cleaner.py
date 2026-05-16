"""
数据清洗模块 - 去重、标准化、合并
"""
import json


def dedup_by_code(items, code_key='code'):
    """按代码去重，保留每个代码第一条记录"""
    seen = set()
    result = []
    for item in items:
        c = str(item.get(code_key, ''))
        if c and c not in seen:
            seen.add(c)
            result.append(item)
    return result


def sort_by_scale(items, scale_key='scale', reverse=True):
    """按规模/市值排序"""
    return sorted(items, key=lambda x: x.get(scale_key, 0) or 0, reverse=reverse)


def standardize_holdings(raw_holdings, max_count=5):
    """统一 top_holdings 格式为 [{'name':xx, 'weight':xx}, ...]"""
    result = []
    for h in raw_holdings[:max_count]:
        if isinstance(h, dict) and 'name' in h:
            result.append({'name': h['name'], 'weight': h.get('weight', '')})
        elif isinstance(h, str):
            parts = h.split(' ', 1)
            result.append({'name': parts[0], 'weight': parts[1] if len(parts) > 1 else ''})
    return result


def make_data_loader(cache=None):
    """创建数据加载器（带缓存）"""
    if cache is None:
        cache = {}

    def load_json(filepath):
        if filepath in cache:
            return cache[filepath]
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cache[filepath] = data
        return data

    return load_json
