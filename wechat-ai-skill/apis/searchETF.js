/**
 * 搜索 ETF — 按名称/代码/分类搜索
 * 后端 API: etf_mcp_server.py 的 etf_search 工具
 */
const API_BASE = 'https://your-api-domain.com' // 替换为生产域名

async function searchETF({ keyword, category }) {
  const res = await wx.request({
    url: `${API_BASE}/api/etf/search`,
    method: 'POST',
    data: { keyword, category },
    header: { 'Content-Type': 'application/json' }
  })

  if (res.statusCode !== 200) {
    return {
      isError: true,
      content: [{ type: 'text', text: `搜索 ETF 失败：${res.errMsg || '请稍后重试'}` }]
    }
  }

  const items = res.data.items || []
  if (!items.length) {
    return {
      content: [{ type: 'text', text: `未找到与「${keyword}」相关的 ETF，请尝试更换搜索词或输入 6 位代码。` }],
      structuredContent: { items: [], total: 0 }
    }
  }

  // 构建返回内容：搜索结果列表
  const textLines = items.map((e, i) => {
    const scale = e.scale_yi > 100 ? `${(e.scale_yi/100).toFixed(1)}百亿` : `${e.scale_yi.toFixed(1)}亿`
    const ret = e.year_1_return ? ` | 近1年${e.year_1_return > 0 ? '+' : ''}${e.year_1_return.toFixed(1)}%` : ''
    return `${i+1}. ${e.code} ${e.name} — ${e.issuer} · ${scale}${ret}`
  }).join('\n')

  return {
    content: [
      { type: 'text', text: `搜索「${keyword}」找到 ${items.length} 只 ETF：\n\n${textLines}\n\n点击任意代码可查看详情，输入「对比 + 代码列表」可开始对比。\n\n⚠️ 数据仅供参考，不构成投资建议。投资有风险，决策需谨慎。` }
    ],
    structuredContent: { items, total: items.length }
  }
}

module.exports = searchETF
