#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF 数据补充脚本 — 从修复数据库、Wind、非凸等源补充标准数据缺失字段

用法：
  python supplement_data.py                    # 检查+补充（不部署）
  python supplement_data.py --deploy           # 补充 + git push 部署
  python supplement_data.py --check            # 仅检查，不修改
  python supplement_data.py --report           # 输出完整度报告 Markdown
  python supplement_data.py --report-html      # 生成自包含 HTML 报告

数据来源优先级：
  1. etf_db_repaired (本地修复数据库，187字段)
  2. etf_wind_data.json (Wind查询缓存)
  3. calculated_metrics (本地计算指标)
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
REPAIR_DB = ROOT / 'data/etf_db_repaired_20260603_231928.json'
STANDARD_FILE = ROOT / 'etf_standard_data.json'
GENERATED_FILE = ROOT / 'etf_data_generated.json'
WIND_FILE = ROOT / 'etf_wind_data.json'
CALC_FILE = ROOT / 'etf_calculated_metrics.json'

sys.path.insert(0, str(ROOT))
from modules.issuer_extract import get_full_name, get_short_name


def load_json(path):
    if not Path(path).exists():
        return None
    with open(path) as f:
        return json.load(f)


def is_valid(v):
    if v is None: return False
    if isinstance(v, str) and v.strip() == '': return False
    if isinstance(v, (int, float)) and v == 0: return False
    if isinstance(v, (list, dict)) and len(v) == 0: return False
    return True


def pick_first(d, *keys):
    for k in keys:
        v = d.get(k)
        if is_valid(v):
            return v
    return None


def check_completeness(etfs):
    """返回每个字段的完整度统计"""
    total = len(etfs)
    fields = {}
    for e in etfs:
        for k in e.keys():
            if k not in fields:
                fields[k] = {'valid': 0, 'total': 0}
            fields[k]['total'] += 1
            if is_valid(e.get(k)):
                fields[k]['valid'] += 1
    return {k: {'valid': v['valid'], 'total': v['total'],
                'coverage': v['valid']/total*100} for k, v in fields.items()}


def supplement_from_repair(standard_etfs, repair_data, calc_metrics=None):
    """
    从修复数据库补充标准数据缺失字段。
    只填充空值，不覆盖已有有效数据。
    """
    std_map = {e['code']: e for e in standard_etfs}
    repair_map = {e['code']: e for e in repair_data} if isinstance(repair_data, list) else repair_data
    
    calc_map = {}
    if calc_metrics:
        calc_map = calc_metrics
    
    filled = {}  # field -> count
    for code, etf in std_map.items():
        if code not in repair_map:
            continue
        r = repair_map[code]
        
        fillers = [
            # (目标字段, 源字段列表...)
            ('close', 'close'),
            ('prev_close', 'prev_close'),
            ('change_pct', 'change_pct'),
            ('change_rate', 'change_rate'),
            ('volume', 'volume'),
            ('scale', 'wind_最新规模', 'latest_scale', 'scale'),
            ('shares', 'wind_最新份额'),
            ('issue_date', 'issue_date', 'wind_基金成立日', 'establish_date'),
            ('listing_date', 'list_date', 'wind_上市日期'),
            ('custodian', 'custodian', 'wind_基金托管人'),
            ('benchmark', 'benchmark', 'wind_业绩比较基准'),
            ('wind_code', 'wind_code', 'wind_Wind代码'),
            ('short_name', 'wind_证券简称', 'wind_short_name'),
            ('invest_type', 'invest_type', 'wind_投资类型_二级分类'),
            ('fund_manager', 'fund_manager'),
            ('management_fee_rate', 'management_fee_history', 'wind_管理费率_支持历史'),
            ('custody_fee_rate', 'custodian_fee_history', 'wind_托管费率_支持历史'),
            ('nav', 'nav', 'wind_最新单位净值'),
            ('tracking_error', 'tracking_error_1y', 'tracking_error'),
            ('year_1_return', 'year_1_return'),
            ('year_3_return', 'year_3_return'),
            ('annual_3y', 'annual_3y'),
            ('max_drawdown', 'max_drawdown'),
            ('sharpe_ratio', 'sharpe_ratio'),
            ('annual_vol', 'annual_vol'),
            ('calmar_ratio', 'calmar_ratio'),
        ]
        
        for target, *sources in fillers:
            if is_valid(etf.get(target)):
                continue  # 已有有效值，不覆盖
            
            val = pick_first(r, *sources)
            if val is not None:
                etf[target] = val
                if target not in filled:
                    filled[target] = 0
                filled[target] += 1
        
        # 总费率派生
        if not is_valid(etf.get('fee_rate')):
            mgmt = etf.get('management_fee_rate', 0) or 0
            custody = etf.get('custody_fee_rate', 0) or 0
            if mgmt or custody:
                etf['fee_rate'] = round(float(mgmt) + float(custody), 4)
                if 'fee_rate' not in filled:
                    filled['fee_rate'] = 0
                filled['fee_rate'] += 1
        
        # 持仓
        if not is_valid(etf.get('top_holdings')):
            raw = r.get('top_holdings', [])
            if raw:
                holdings = []
                for h in raw[:5]:
                    if isinstance(h, dict) and 'name' in h:
                        holdings.append({"name": h['name'], "weight": h.get('weight', '')})
                if holdings:
                    etf['top_holdings'] = holdings
                    if 'top_holdings' not in filled:
                        filled['top_holdings'] = 0
                    filled['top_holdings'] += 1
        
        # 从 calc_metrics 补充
        if code in calc_map:
            cm = calc_map[code]
            for cm_field in ['year_1_return', 'year_3_return', 'sharpe_ratio', 
                             'annual_vol', 'max_drawdown']:
                if not is_valid(etf.get(cm_field)):
                    val = cm.get(cm_field)
                    if is_valid(val):
                        etf[cm_field] = val
                        if cm_field not in filled:
                            filled[cm_field] = 0
                        filled[cm_field] += 1
    
    return filled


def generate_report(etfs, title="ETF 数据完整度报告"):
    """生成 Markdown 报告"""
    total = len(etfs)
    cov = check_completeness(etfs)
    
    lines = [f"# {title}", f"\nETF总数：{total} | 字段数：{len(cov)} | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    
    # 分级
    excellent = [(k,v) for k,v in cov.items() if v['coverage']>=99]
    good = [(k,v) for k,v in cov.items() if 90<=v['coverage']<99]
    partial = [(k,v) for k,v in cov.items() if 50<=v['coverage']<90]
    poor = [(k,v) for k,v in cov.items() if v['coverage']<50]
    
    lines.append(f"| 等级 Grade | 数量 Count | 占比 Ratio |")
    lines.append(f"|------------|------------|-----------|")
    lines.append(f"| ✅ ≥99% | {len(excellent)} | {len(excellent)/len(cov)*100:.0f}% |")
    lines.append(f"| ⚠️ 90-99% | {len(good)} | {len(good)/len(cov)*100:.0f}% |")
    lines.append(f"| 🟡 50-90% | {len(partial)} | {len(partial)/len(cov)*100:.0f}% |")
    lines.append(f"| 🔴 <50% | {len(poor)} | {len(poor)/len(cov)*100:.0f}% |")
    
    for cat_name, items in [("🔴 缺失 Missing (<50%)", poor), 
                             ("🟡 部分 Partial (50-90%)", partial),
                             ("⚠️ 良好 Good (90-99%)", good)]:
        if not items:
            continue
        lines.append(f"\n## {cat_name}\n")
        lines.append(f"| 字段 Field | 有效 Valid | 覆盖率 Coverage |")
        lines.append(f"|------------|-----------|----------|")
        for k, v in sorted(items, key=lambda x: x[1]['coverage']):
            lines.append(f"| `{k}` | {v['valid']}/{total} | {v['coverage']:.1f}% |")
    
    return '\n'.join(lines)


def generate_html_report(etfs, output_path):
    """生成自包含 HTML 完整度报告（中英双语）
    
    读取 etf_completeness_report_template.html 模板，注入数据后写入 output_path。
    """
    total = len(etfs)
    cov = check_completeness(etfs)
    
    # 字段定义
    field_defs = [
        ("code","代码","标识"),("name","名称","标识"),("issuer","发行人","标识"),
        ("issuer_full","发行人全称","标识"),("issuer_short","发行人简称","标识"),
        ("wind_code","Wind代码","标识"),("short_name","证券简称","标识"),
        ("close","最新价","行情"),("prev_close","昨收","行情"),("change_pct","涨跌幅(%)","行情"),
        ("change_rate","涨跌额","行情"),("volume","成交量","行情"),
        ("scale","规模(亿元)","规模"),("shares","份额(亿份)","规模"),
        ("issue_date","成立日期","日期"),("listing_date","上市日期","日期"),
        ("category","分类","元数据"),("invest_type","投资类型","元数据"),
        ("custodian","托管人","元数据"),("benchmark","业绩基准","元数据"),
        ("fund_manager","基金经理","元数据"),
        ("management_fee_rate","管理费率(%)","费率"),("custody_fee_rate","托管费率(%)","费率"),
        ("fee_rate","总费率(%)","费率"),
        ("top_holdings","前5大持仓","持仓"),
        ("year_1_return","近1年收益(%)","收益"),("year_3_return","近3年收益(%)","收益"),
        ("annual_3y","年化3年(%)","收益"),
        ("sharpe_ratio","夏普比率","风险"),("annual_vol","年化波动(%)","风险"),
        ("max_drawdown","最大回撤(%)","风险"),("calmar_ratio","卡玛比率","风险"),
        ("tracking_error","跟踪误差(%)","风险"),
        ("nav","最新净值","净值"),
        ("track_index_code","跟踪指数代码","待补充"),("track_index_name","跟踪指数名称","待补充"),
        ("net_inflow_5d","近5日净流入","待补充"),("premium_discount","折溢价率","待补充"),
        ("valuation_percentile","估值分位","待补充"),
    ]
    
    fnames = [f[0] for f in field_defs]
    
    # ETF 完整度
    etf_data = []
    for e in etfs:
        missing = [f for f in fnames if not is_valid(e.get(f))]
        etf_data.append({
            "code": e.get("code", ""), "name": e.get("name", ""),
            "completeness": round((len(fnames) - len(missing)) / len(fnames) * 100, 1),
            "missing_count": len(missing), "missing_fields": missing[:10],
        })
    
    # 字段统计
    field_stats = {}
    for fname, cname, cat in field_defs:
        if fname in cov:
            field_stats[fname] = {
                "cn": cname, "cat": cat, "ok": cov[fname]["valid"],
                "missing": total - cov[fname]["valid"],
                "ratio": round(100 - cov[fname]["coverage"], 1)
            }
    
    # 分布
    bins = [("100%%",99.9,100),("95-99%%",95,99.9),("80-95%%",80,95),
            ("60-80%%",60,80),("40-60%%",40,60),("20-40%%",20,40),("<20%%",0,20)]
    bin_data = []
    for label, lo, hi in bins:
        cnt = sum(1 for x in etf_data if lo <= x["completeness"] < hi or (hi == 100 and x["completeness"] == 100))
        bin_data.append({"label": label, "count": cnt})
    
    # 分类汇总
    cat_totals = {}
    for fname, cname, cat in field_defs:
        if cat not in cat_totals:
            cat_totals[cat] = {"total": 0, "valid": 0}
        if fname in field_stats:
            cat_totals[cat]["total"] += total
            cat_totals[cat]["valid"] += field_stats[fname]["ok"]
    cat_vals = {k: round(v["valid"]/v["total"]*100,1) if v["total"] else 0 for k,v in cat_totals.items()}
    
    avg = sum(x["completeness"] for x in etf_data) / total
    
    import json as _json
    report_data = {
        "total": total, "avg": round(avg, 1),
        "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "field_defs": field_defs, "field_stats": field_stats,
        "etf_data": etf_data, "bin_data": bin_data, "cat_values": cat_vals,
    }
    
    # 读取模板，注入数据
    template_path = ROOT / "etf_completeness_report_template.html"
    if not template_path.exists():
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    with open(template_path) as f:
        template = f.read()
    html = template.replace("__REPORT_DATA__", _json.dumps(report_data, ensure_ascii=False))
    with open(output_path, "w") as f:
        f.write(html)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='ETF 数据补充工具')
    parser.add_argument('--deploy', action='store_true', help='补充后 git push 部署')
    parser.add_argument('--check', action='store_true', help='仅检查，不修改')
    parser.add_argument('--report', action='store_true', help='输出完整度报告 Markdown')
    parser.add_argument('--report-html', type=str, nargs='?', const='etf_completeness_report.html',
                        help='生成自包含 HTML 完整度报告（可选指定路径）')
    parser.add_argument('--dry-run', action='store_true', help='检查补充效果但不写入文件')
    args = parser.parse_args()
    
    # 加载数据
    standard_etfs = load_json(STANDARD_FILE)
    if not standard_etfs:
        print("❌ 未找到标准数据文件")
        sys.exit(1)
    
    repair_data = load_json(REPAIR_DB)
    calc_data = load_json(CALC_FILE) or {}
    
    before_cov = check_completeness(standard_etfs)
    total = len(standard_etfs)
    
    # 补充前状态
    before_ok = sum(1 for v in before_cov.values() if v['coverage'] >= 90)
    print(f"补充前：{total} ETF | {len(before_cov)} 字段 | ≥90% 覆盖: {before_ok}/{len(before_cov)}")
    
    # HTML 报告（可独立于 check 运行）
    if args.report_html:
        out = Path(args.report_html) if args.report_html != 'etf_completeness_report.html' else ROOT / args.report_html
        path = generate_html_report(standard_etfs, str(out))
        print(f"\n✅ HTML 报告: {path} ({Path(path).stat().st_size:,} bytes)")
        import webbrowser
        webbrowser.open(f'file://{path}')
    
    if args.check:
        if args.report:
            print(generate_report(standard_etfs))
        return
    
    # 执行补充
    if repair_data:
        filled = supplement_from_repair(standard_etfs, repair_data, calc_data)
        if filled:
            print(f"\n从修复数据库补充：")
            for field, count in sorted(filled.items(), key=lambda x: -x[1]):
                print(f"  +{field}: {count} 条")
        else:
            print("\n无需补充，所有字段均已完整")
    else:
        print(f"\n⚠️ 修复数据库不可用 ({REPAIR_DB})，跳过补充")
    
    after_cov = check_completeness(standard_etfs)
    after_ok = sum(1 for v in after_cov.values() if v['coverage'] >= 90)
    print(f"\n补充后：{total} ETF | {len(after_cov)} 字段 | ≥90% 覆盖: {after_ok}/{len(after_cov)}")
    
    if args.report:
        print("\n" + generate_report(standard_etfs, "补充后完整度报告"))
    
    if args.dry_run:
        print("\n[Dry Run] 未写入文件")
        return
    
    # 写入文件
    with open(STANDARD_FILE, 'w') as f:
        json.dump(standard_etfs, f, ensure_ascii=False)
    print(f"\n✅ 已写入: {STANDARD_FILE.name} ({Path(STANDARD_FILE).stat().st_size:,} bytes)")
    
    # 同步 generated
    gen_data = []
    gen_keys = ['code','close','prev_close','change_rate','issue_date','listing_date',
                'top_holdings','custodian','benchmark','wind_code','short_name',
                'invest_type','fund_manager','management_fee_rate','custody_fee_rate','nav']
    for e in standard_etfs:
        gen_data.append({k: e.get(k) for k in gen_keys})
    with open(GENERATED_FILE, 'w') as f:
        json.dump(gen_data, f, ensure_ascii=False)
    print(f"✅ 已写入: {GENERATED_FILE.name} ({Path(GENERATED_FILE).stat().st_size:,} bytes)")
    
    # 部署
    if args.deploy:
        import subprocess
        proj = ROOT
        subprocess.run([sys.executable, str(proj / 'pipeline.py'), 'deploy'], cwd=proj)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
