/**
 * 搜索 ETF — "事实 + 动作" 两段式返回
 */
const API_BASE = 'https://your-api-domain.com'

async function searchETF({ keyword, category }) {
  const res = await wx.request({
    url: `${API_BASE}/api/etf/search`,
    method: 'POST',
    data: { keyword, category },
    header: { 'Content-Type': 'application/json' }
  })

  if (res.statusCode !== 200) {
    // 失败分支：事实 + 出口 + 禁令
    return {
      isError: true,
      content: [{
        type: 'text',
        text: [
          '搜索服务暂时不可用，可能是网络波动导致。',
          '接下来请向用户说明服务暂不可用，并建议稍后重试或直接输入 6 位 ETF 代码跳过搜索。',
          '不要再以相同关键词重复调用本接口。'
        ].join('\n')
      }]
    }
  }

  const items = res.data.items || []

  if (!items.length) {
    return {
      isError: true,
      content: [{
        type: 'text',
        text: [
          `未在 1685 只 ETF 中匹配到与「${keyword}」相关的结果。`,
          '接下来请告知用户未找到结果，建议更换更简短的关键词重试（如从「华夏沪深300ETF联接」改为「沪深300」），或输入准确的 6 位代码。',
          '不要用相同关键词再次调用本接口。'
        ].join('\n')
      }],
      structuredContent: { items: [], total: 0 }
    }
  }

  // 成功分支：事实 + 动作
  const list = items.map((e, i) => {
    const scale = e.scale_yi > 100 ? `${(e.scale_yi/100).toFixed(1)}百亿` : `${e.scale_yi.toFixed(1)}亿`
    const ret = e.year_1_return != null ? ` | 近1年${e.year_1_return > 0 ? '+' : ''}${e.year_1_return.toFixed(1)}%` : ''
    return `${i+1}. ${e.code} ${e.name} — ${e.issuer} · ${scale}${ret}`
  }).join('\n')

  const hint = items.length > 5
    ? '请引导用户缩小范围或直接输入代码开始对比。'
    : '用户可点击代码查看详情，或输入「对比 + 代码列表」开始多维对比。'

  return {
    content: [{
      type: 'text',
      text: [
        `已找到 ${items.length} 只与「${keyword}」匹配的 ETF（共 ${res.data.total} 只）：`,
        '',
        list,
        '',
        hint
      ].join('\n')
    }],
    structuredContent: { items, total: res.data.total || items.length }
  }
}

module.exports = searchETF
