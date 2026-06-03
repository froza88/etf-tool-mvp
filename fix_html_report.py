#!/usr/bin/env python3
"""独立生成ETF完整度HTML报告（含分页选页功能）"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DATA_FILE = PROJECT_ROOT / "etf_standard_data.json"

# 25个目标字段
TARGET_FIELDS = [
    'code', 'name', 'issuer', 'issuer_full', 'issuer_short',
    'scale', 'shares', 'issue_date', 'custodian', 'fund_manager',
    'change_pct', 'close', 'prev_close', 'change_rate',
    'volume', 'year_1_return', 'year_3_return',
    'max_drawdown', 'sharpe_ratio', 'annual_vol', 'category',
    'wind_基金管理人', 'wind_基金托管人', 'wind_基金成立日', 'wind_业绩比较基准'
]

def is_field_missing(value, field=''):
    if value is None or value == '':
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    if field == 'volume' and value == 0:
        return True
    return False

def load_etf_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else data['etfs']

def main():
    etfs = load_etf_data()
    print(f"加载 {len(etfs)} 只ETF")
    
    # 检查完整度
    etf_rows = []
    for etf in etfs:
        missing_fields = [f for f in TARGET_FIELDS if is_field_missing(etf.get(f), f)]
        completenss = round((len(TARGET_FIELDS) - len(missing_fields)) / len(TARGET_FIELDS) * 100, 1)
        etf_rows.append({
            'code': etf.get('code', ''),
            'name': etf.get('name', ''),
            'completeness': completenss,
            'missing_count': len(missing_fields),
            'missing_fields': missing_fields,
        })
    
    # 字段统计
    field_stats = {}
    for field in TARGET_FIELDS:
        missing_cnt = sum(1 for e in etfs if is_field_missing(e.get(field), field))
        field_stats[field] = {
            'missing': missing_cnt,
            'ok': len(etfs) - missing_cnt,
            'missing_ratio': round(missing_cnt / len(etfs) * 100, 1)
        }
    
    # 完整度分布
    bins = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 95), (95, 101)]
    bin_labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-95%', '95-100%']
    bin_counts = {label: 0 for label in bin_labels}
    for r in etf_rows:
        pct = r['completeness']
        for (lo, hi), label in zip(bins, bin_labels):
            if lo <= pct < hi:
                bin_counts[label] += 1
                break
    
    # 生成HTML
    etf_json = json.dumps(etf_rows, ensure_ascii=False)
    field_stats_json = json.dumps(field_stats, ensure_ascii=False)
    bin_data = json.dumps([bin_counts[l] for l in bin_labels], ensure_ascii=False)
    bin_labels_json = json.dumps(bin_labels, ensure_ascii=False)
    
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ETF数据完整度报告</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, 'Segoe UI', sans-serif; background:#f5f7fa; color:#333; }
.header { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color:white; padding:24px 32px; }
.header h1 { font-size:24px; margin-bottom:4px; }
.header p { font-size:14px; opacity:0.85; }
.nav { display:flex; gap:8px; padding:12px 32px; background:white; border-bottom:1px solid #e5e7eb; }
.nav-btn { padding:8px 18px; border:1px solid #d1d5db; background:white; border-radius:6px; cursor:pointer; font-size:13px; }
.nav-btn.active { background:#3b82f6; color:white; border-color:#3b82f6; }
.section { padding:24px 32px; }
.card { background:white; border-radius:12px; padding:20px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }
.card h2 { font-size:16px; margin-bottom:16px; color:#1e3a8a; }
.stats-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px,1fr)); gap:12px; }
.stat-box { background:#f0f9ff; border-radius:8px; padding:14px; text-align:center; }
.stat-box .num { font-size:28px; font-weight:700; color:#1e3a8a; }
.stat-box .label { font-size:12px; color:#6b7280; margin-top:4px; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { background:#f3f4f6; padding:8px 10px; text-align:left; font-weight:600; border-bottom:2px solid #e5e7eb; position:sticky; top:0; cursor:pointer; }
td { padding:8px 10px; border-bottom:1px solid #f3f4f6; }
tr:hover { background:#f9fafb; }
.missing { color:#ef4444; font-weight:600; }
.ok { color:#10b981; }
.filter-bar { display:flex; gap:10px; margin-bottom:16px; flex-wrap:wrap; align-items:center; }
.filter-bar input, .filter-bar select { padding:7px 12px; border:1px solid #d1d5db; border-radius:6px; font-size:13px; }
.filter-bar label { font-size:13px; color:#6b7280; }
.badge-miss { background:#fef2f2; color:#ef4444; padding:2px 8px; border-radius:10px; font-size:11px; }
.badge-ok { background:#f0fdf4; color:#10b981; padding:2px 8px; border-radius:10px; font-size:11px; }
.chart-container { display:flex; gap:20px; flex-wrap:wrap; }
.chart-box { flex:1; min-width:300px; }
.chart-bar { display:flex; align-items:center; margin-bottom:6px; }
.chart-bar .label { width:80px; font-size:12px; text-align:right; padding-right:8px; }
.chart-bar .bar { height:18px; background:#3b82f6; border-radius:3px; min-width:2px; }
.chart-bar .num { font-size:11px; margin-left:6px; color:#6b7280; }
.pagination { display:flex; gap:6px; align-items:center; margin-top:12px; flex-wrap:wrap; }
.pagination button { padding:5px 10px; border:1px solid #d1d5db; background:white; border-radius:4px; cursor:pointer; font-size:12px; }
.pagination button:disabled { opacity:0.5; cursor:default; }
.pagination button.active-page { background:#3b82f6; color:white; border-color:#3b82f6; }
</style>
</head>
<body>
<div class="header">
  <h1>📊 ETF数据完整度报告</h1>
  <p>共 <strong id="totalCount">0</strong> 只ETF | <strong id="avgCompleteness">0</strong>% 平均完整度 | 生成时间：<span id="genTime"></span></p>
</div>
<div class="nav">
  <button class="nav-btn active" onclick="showTab('overview')">总览</button>
  <button class="nav-btn" onclick="showTab('fields')">字段分析</button>
  <button class="nav-btn" onclick="showTab('etflist')">ETF列表</button>
</div>

<!-- Tab: 总览 -->
<div id="tab-overview" class="section">
  <div class="stats-grid" id="statsGrid"></div>
  <div class="card" style="margin-top:20px;">
    <h2>完整度分布</h2>
    <div class="chart-container">
      <div class="chart-box"><div id="distChart"></div></div>
      <div class="chart-box"><div id="fieldChart"></div></div>
    </div>
  </div>
</div>

<!-- Tab: 字段分析 -->
<div id="tab-fields" class="section" style="display:none;">
  <div class="card">
    <h2>各字段缺失统计（点击表头排序）</h2>
    <table>
      <thead><tr>
        <th onclick="sortFieldTable('field')">字段名 ↕</th>
        <th onclick="sortFieldTable('missing')">缺失数量 ↕</th>
        <th onclick="sortFieldTable('missingRatio')">缺失比例 ↕</th>
        <th onclick="sortFieldTable('ok')">有数据 ↕</th>
        <th>缺失比例条</th>
      </tr></thead>
      <tbody id="fieldTableBody"></tbody>
    </table>
  </div>
</div>

<!-- Tab: ETF列表 -->
<div id="tab-etflist" class="section" style="display:none;">
  <div class="filter-bar">
    <label>筛选：</label>
    <select id="filterCompleteness" onchange="renderETFList()">
      <option value="all">全部完整度</option>
      <option value="0-20">0-20%</option>
      <option value="20-40">20-40%</option>
      <option value="40-60">40-60%</option>
      <option value="60-80">60-80%</option>
      <option value="80-95">80-95%</option>
      <option value="95-100">95-100%</option>
    </select>
    <input type="text" id="filterCode" placeholder="搜ETF代码/名称" oninput="renderETFList()" style="width:160px;">
    <label>每页：</label>
    <select id="pageSize" onchange="renderETFList()">
      <option value="20">20</option>
      <option value="50">50</option>
      <option value="100">100</option>
    </select>
  </div>
  <div class="card">
    <table>
      <thead><tr>
        <th>代码</th><th>名称</th><th onclick="sortETFList('completeness')">完整度% ↕</th>
        <th>缺失数</th><th>缺失字段</th>
      </tr></thead>
      <tbody id="etfTableBody"></tbody>
    </table>
    <div class="pagination" id="pagination"></div>
  </div>
</div>

<script>
var ETF_DATA = """ + etf_json + """;
var FIELD_STATS = """ + field_stats_json + """;
var BIN_LABELS = """ + bin_labels_json + """;
var BIN_DATA = """ + bin_data + """;
var currentTab = 'overview';
var fieldSortKey = 'missing';
var fieldSortDir = -1;
var etfSortKey = 'completeness';
var etfSortDir = -1;
var etfPage = 1;

document.getElementById('genTime').textContent = new Date().toLocaleString('zh-CN');

function showTab(tab) {
  currentTab = tab;
  var btns = document.querySelectorAll('.nav-btn');
  for (var i=0; i<btns.length; i++) btns[i].classList.remove('active');
  event.target.classList.add('active');
  document.getElementById('tab-overview').style.display = tab=='overview'?'block':'none';
  document.getElementById('tab-fields').style.display = tab=='fields'?'block':'none';
  document.getElementById('tab-etflist').style.display = tab=='etflist'?'block':'none';
  if (tab=='overview' && !window._overviewRendered) { renderOverview(); window._overviewRendered=true; }
  if (tab=='fields' && !window._fieldsRendered) { renderFieldTable(); window._fieldsRendered=true; }
  if (tab=='etflist' && !window._etfRendered) { renderETFList(); window._etfRendered=true; }
}

function renderOverview() {
  var total = ETF_DATA.length;
  var avg = (ETF_DATA.reduce(function(s,e){return s+e.completeness},0)/total).toFixed(1);
  document.getElementById('totalCount').textContent = total;
  document.getElementById('avgCompleteness').textContent = avg;
  
  // 统计卡片
  var statsGrid = document.getElementById('statsGrid');
  var complete100 = ETF_DATA.filter(function(e){return e.completeness>=100}).length;
  var complete80 = ETF_DATA.filter(function(e){return e.completeness>=80}).length;
  statsGrid.innerHTML = ''
    + '<div class="stat-box"><div class="num">' + total + '</div><div class="label">ETF总数</div></div>'
    + '<div class="stat-box"><div class="num">' + avg + '%</div><div class="label">平均完整度</div></div>'
    + '<div class="stat-box"><div class="num">' + complete80 + '</div><div class="label">≥80%完整</div></div>'
    + '<div class="stat-box"><div class="num">' + (total-complete80) + '</div><div class="label"><80%完整</div></div>';
  
  // 完整度分布图
  var distChart = document.getElementById('distChart');
  var maxCount = Math.max.apply(null, BIN_DATA);
  distChart.innerHTML = '';
  for (var i=0; i<BIN_DATA.length; i++) {
    var w = maxCount>0 ? Math.round(BIN_DATA[i]/maxCount*200) : 0;
    distChart.innerHTML += '<div class="chart-bar"><div class="label">' + BIN_LABELS[i] + '</div><div class="bar" style="width:' + w + 'px;"></div><div class="num">' + BIN_DATA[i] + '只</div></div>';
  }
  
  // 缺失最多字段图
  var fieldChart = document.getElementById('fieldChart');
  var topFields = Object.keys(FIELD_STATS).sort(function(a,b){return FIELD_STATS[b].missing-FIELD_STATS[a].missing}).slice(0,10);
  var maxM = FIELD_STATS[topFields[0]].missing;
  fieldChart.innerHTML = '';
  for (var j=0; j<topFields.length; j++) {
    var f = topFields[j];
    var w = Math.round(FIELD_STATS[f].missing/maxM*200);
    fieldChart.innerHTML += '<div class="chart-bar"><div class="label">' + f + '</div><div class="bar" style="width:' + w + 'px;"></div><div class="num">' + FIELD_STATS[f].missing + '只</div></div>';
  }
}

function renderFieldTable() {
  var tbody = document.getElementById('fieldTableBody');
  var fields = Object.keys(FIELD_STATS).sort(function(a,b){
    var va = FIELD_STATS[a][fieldSortKey], vb = FIELD_STATS[b][fieldSortKey];
    return fieldSortDir * (va>vb?1:va<vb?-1:0);
  });
  tbody.innerHTML = fields.map(function(f){
    var s = FIELD_STATS[f];
    var barW = Math.round(s.missing_ratio/100*200);
    return '<tr><td><code>' + f + '</code></td><td>' + s.missing + '</td><td>' + s.missing_ratio + '%</td><td>' + s.ok + '</td>'
      + '<td><div style="background:#fee2e2;height:18px;width:' + barW + 'px;"></div></td></tr>';
  }).join('');
}

function sortFieldTable(key) {
  if (fieldSortKey===key) fieldSortDir *= -1; else { fieldSortKey=key; fieldSortDir=-1; }
  renderFieldTable();
}

function renderETFList() {
  var filterRange = document.getElementById('filterCompleteness').value;
  var filterText = document.getElementById('filterCode').value.toLowerCase();
  var pageSize = parseInt(document.getElementById('pageSize').value);
  
  var filtered = ETF_DATA.filter(function(e){
    if (filterRange!='all') {
      var parts = filterRange.split('-'); var lo=parseInt(parts[0]); var hi=parseInt(parts[1]);
      if (e.completeness < lo || e.completeness >= hi) return false;
    }
    if (filterText && !(e.code.toLowerCase().indexOf(filterText)>=0 || e.name.toLowerCase().indexOf(filterText)>=0)) return false;
    return true;
  });
  
  filtered.sort(function(a,b){
    var vA = a[etfSortKey], vB = b[etfSortKey];
    return etfSortDir * (vA>vB?1:vA<vB?-1:0);
  });
  
  var totalPages = Math.ceil(filtered.length / pageSize);
  etfPage = Math.min(etfPage, totalPages || 1);
  var start = (etfPage-1)*pageSize;
  var pageData = filtered.slice(start, start+pageSize);
  
  var tbody = document.getElementById('etfTableBody');
  tbody.innerHTML = pageData.map(function(e){
    return '<tr><td><strong>'+e.code+'</strong></td><td>'+e.name+'</td>'
      + '<td class="'+(e.completeness>=80?'ok':'missing')+'">'+e.completeness+'%</td>'
      + '<td><span class="badge-miss">'+e.missing_count+'</span></td>'
      + '<td style="font-size:11px;color:#6b7280;">'+(e.missing_fields.length>0?e.missing_fields.join(', '):'<span class="ok">完整</span>')+'</td></tr>';
  }).join('');
  
  // 分页导航（含页码列表 + 跳转）
  var pag = document.getElementById('pagination');
  pag.innerHTML = '';
  // 首页 + 上一页
  if (etfPage > 1) pag.innerHTML += '<button onclick="etfPage=1;renderETFList()">首页</button>';
  if (etfPage > 1) pag.innerHTML += '<button onclick="etfPage--;renderETFList()">上一页</button>';
  // 页码列表（当前页前后2页）
  var ps = Math.max(1, etfPage-2), pe = Math.min(totalPages, etfPage+2);
  for (var p=ps; p<=pe; p++) {
    if (p===etfPage) pag.innerHTML += '<button disabled class="active-page">' + p + '</button>';
    else pag.innerHTML += '<button onclick="etfPage=' + p + ';renderETFList()">' + p + '</button>';
  }
  // 下一页 + 末页
  if (etfPage < totalPages) pag.innerHTML += '<button onclick="etfPage++;renderETFList()">下一页</button>';
  if (etfPage < totalPages) pag.innerHTML += '<button onclick="etfPage=' + totalPages + ';renderETFList()">末页</button>';
  // 跳转输入
  pag.innerHTML += ' 跳至<input type="number" id="jumpPage" style="width:54px;padding:3px 4px;border:1px solid #d1d5db;border-radius:4px;font-size:12px;" min="1" max="' + totalPages + '">页<button onclick="var p=parseInt(document.getElementById(\\'jumpPage\\').value);if(p>=1&&p<=' + totalPages + '){etfPage=p;renderETFList();}" style="margin-left:4px;padding:3px 10px;border:1px solid #d1d5db;background:white;border-radius:4px;cursor:pointer;font-size:12px;">跳转</button>';
  // 统计信息
  pag.innerHTML += '<span style="margin-left:12px;font-size:12px;color:#6b7280;">第' + etfPage + '/' + totalPages + '页，共' + filtered.length + '只</span>';
}

function sortETFList(key) {
  if (etfSortKey===key) etfSortDir *= -1; else { etfSortKey=key; etfSortDir=-1; }
  etfPage=1;
  renderETFList();
}

// 初始化
renderOverview();
window._overviewRendered = true;
</script>
</body>
</html>"""
    
    output_file = PROJECT_ROOT / f"etf_completeness_report_fixed_{PROJECT_ROOT.name}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML报告已保存: {output_file}")
    print(f"   用浏览器打开此文件查看")

if __name__ == "__main__":
    main()
