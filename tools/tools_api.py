"""
ETF 工具类 API Blueprint
包含 AKShare / WeStock 代理接口和工具页面
从 app.py 抽取出来，减少主路由复杂度
"""
from flask import Blueprint, request, jsonify, send_from_directory
from datetime import datetime
import re
import os

tools_bp = Blueprint('tools', __name__, url_prefix='/tools')

# ========== AKShare ETF 对比 API ==========
# 内存缓存（5分钟TTL）
_akshare_cache = {"data": None, "timestamp": 0, "ttl": 300}

_AKSHARE_FIELD_ORDER = [
    "代码", "名称", "最新价", "IOPV实时估值", "基金折价率",
    "开盘价", "最高价", "最低价", "昨收",
    "涨跌幅", "涨跌额",
    "成交量", "成交额", "换手率", "量比",
    "主力净流入-净额", "主力净流入-净占比",
    "超大单净流入-净额", "超大单净流入-净占比",
    "大单净流入-净额", "大单净流入-净占比",
    "中单净流入-净额", "中单净流入-净占比",
    "小单净流入-净额", "小单净流入-净占比",
    "委比", "外盘", "内盘", "现手", "买一", "卖一",
    "最新份额", "流通市值", "总市值",
    "数据日期", "更新时间",
]

@tools_bp.route('/akshare-compare')
def akshare_compare_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__)),
        'akshare_etf_compare.html'
    )

@tools_bp.route('/westock-compare')
def westock_compare_page():
    return send_from_directory(
        os.path.join(os.path.dirname(__file__)),
        'westock_etf_compare.html'
    )


def register_tools_api(app):
    """注册 tools API（AKShare + WeStock 代理）到 Flask app"""
    import time
    from pathlib import Path

    # ========== AKShare ETF 对比 API 代理 ==========
    @app.route('/api/tools/akshare/etf-compare')
    def api_tools_akshare_etf_compare():
        codes = request.args.get('codes', '').split(',')
        codes = [c.strip() for c in codes if c.strip()]
        if not codes:
            return jsonify({'error': '请提供 ETF 代码', 'etfs': []}), 400

        try:
            import akshare as ak
            import pandas as pd

            now = time.time()
            cache = _akshare_cache

            if cache["data"] is not None and (now - cache["timestamp"]) < cache["ttl"]:
                df = cache["data"]
                cached = True
            else:
                df = ak.fund_etf_spot_em()
                if df is None or len(df) == 0:
                    return jsonify({'error': 'AKShare 数据为空', 'etfs': []}), 500
                cache["data"] = df
                cache["timestamp"] = now
                cached = False

            df['代码'] = df['代码'].astype(str).str.zfill(6)
            mask = df['代码'].isin([c.zfill(6) for c in codes])
            filtered = df[mask].copy()

            if len(filtered) == 0:
                return jsonify({'error': f'未找到代码 {codes} 的 ETF 数据', 'etfs': [], 'available_count': len(df)}), 404

            code_order = {c.zfill(6): i for i, c in enumerate(codes)}
            filtered['__sort'] = filtered['代码'].map(code_order)
            filtered = filtered.sort_values('__sort').drop(columns=['__sort'])

            actual_fields = list(filtered.columns)
            ordered_fields = [f for f in _AKSHARE_FIELD_ORDER if f in actual_fields]
            ordered_fields += [f for f in actual_fields if f not in ordered_fields and not f.startswith('__')]

            etfs = []
            for _, row in filtered.iterrows():
                etf = {}
                for col in ordered_fields:
                    val = row[col]
                    if pd.isna(val):
                        etf[col] = None
                    elif isinstance(val, (pd.Timestamp,)):
                        etf[col] = str(val)
                    else:
                        etf[col] = val
                etfs.append(etf)

            return jsonify({
                'etfs': etfs, 'count': len(etfs),
                'source': 'akshare_api', 'updated': datetime.now().isoformat(),
                'cached': cached, 'cache_age_sec': int(now - cache["timestamp"]) if cached else 0
            })
        except ImportError:
            return jsonify({'error': 'AKShare 未安装，请运行 pip install akshare', 'etfs': []}), 500
        except Exception as e:
            import traceback, sys
            print(f"[API] AKShare 调用失败: {e}\n{traceback.format_exc()}", file=sys.stderr)
            return jsonify({'error': str(e), 'etfs': []}), 500

    # ========== WeStock ETF 对比 API 代理 ==========
    ROOT = Path(__file__).parent.parent
    WESTOCK_SCRIPT = '/Users/apangduo/.workbuddy/plugins/marketplaces/cb_teams_marketplace/plugins/finance-data/skills/westock-data/scripts/index.js'

    @app.route('/api/tools/westock/etf-compare')
    def api_tools_westock_etf_compare():
        codes = request.args.get('codes', '').split(',')
        codes = [c.strip() for c in codes if c.strip()]
        if not codes:
            return jsonify({'error': '请提供 ETF 代码', 'etfs': []}), 400

        try:
            import subprocess

            def fmt_code(c):
                c = c.strip()
                if c.startswith(('sh', 'sz', 'bj')):
                    return c
                if c[0] in '50':
                    return 'sh' + c.zfill(6)
                elif c[0] in '031':
                    return 'sz' + c.zfill(6)
                else:
                    return 'sh' + c.zfill(6)

            formatted_codes = [fmt_code(c) for c in codes]
            cmd = ['node', WESTOCK_SCRIPT, 'etf', ','.join(formatted_codes)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return jsonify({'error': f'WeStock 脚本失败: {result.stderr[:300]}', 'etfs': []}), 500

            etfs = _parse_westock_markdown(result.stdout)
            if not etfs:
                return jsonify({'error': '未解析到数据', 'etfs': [], 'raw': result.stdout[:500]}), 404

            return jsonify({
                'etfs': etfs, 'count': len(etfs),
                'source': 'westock_api', 'updated': datetime.now().isoformat()
            })
        except subprocess.TimeoutExpired:
            return jsonify({'error': 'WeStock 脚本超时', 'etfs': []}), 504
        except Exception as e:
            import traceback, sys
            print(f"[API] WeStock 失败: {e}\n{traceback.format_exc()}", file=sys.stderr)
            return jsonify({'error': str(e), 'etfs': []}), 500

    # ========== WeStock Markdown 解析 ==========
    def _parse_westock_markdown(md_text):
        etfs = []
        sections = re.split(r'####\s+', md_text)
        for section in sections[1:]:
            lines = section.strip().split('\n')
            if not lines:
                continue
            code_line = lines[0].strip()
            if not re.match(r'(sh|sz|bj)\d+', code_line):
                continue
            table_start = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('|') and '---' not in line:
                    table_start = i
                    break
            if table_start == -1:
                continue
            header_line = lines[table_start].strip()
            headers = [h.strip() for h in header_line.split('|')[1:-1]]
            data_start = table_start + 2
            etf_data = {}
            for i in range(data_start, min(data_start + 1, len(lines))):
                data_line = lines[i].strip()
                if not data_line.startswith('|'):
                    break
                values = [v.strip() for v in data_line.split('|')[1:-1]]
                for j, h in enumerate(headers):
                    if j < len(values):
                        val = values[j]
                        try:
                            etf_data[h] = float(val) if '.' in val else int(val)
                        except (ValueError, IndexError):
                            etf_data[h] = val
            etfs.append(etf_data)
        return etfs

    # 注册 blueprint
    app.register_blueprint(tools_bp)
