/**
 * ETF 排名
 */
const API_BASE = 'https://your-api-domain.com'

const LABELS = {
  year_1_return: '近1年收益', scale_yi: '规模',
  fee_total: '总费率（从低到高）', sharpe_ratio: '夏普比率',
  max_drawdown: '最大回撤', annual_vol: '年化波动率'
}

async function rankETF({ field, limit = 10, category }) {
  const res = await wx.request({
    url: `${API_BASE}/api/etf/rank`,
    method: 'POST',
    data: { field, limit: Math.min(limit, 20), category },
    header: { 'Content-Type': 'application/json' }
  })

  if (res.statusCode !== 200) {
    return {
      isError: true,
      content: [{ type: 'text', text: '排名服务暂不可用。请告知用户稍后重试，不要再以相同参数重复调用。' }]
    }
  }

  const items = res.data.items || []
  if (!items.length) {
    return {
      content: [{ type: 'text', text: '当前条件下无排名数据，部分 ETF 的该指标暂未收录。请告知用户可尝试更换排序维度。' }],
      structuredContent: { field, items: [] }
    }
  }

  const label = LABELS[field] || field
  const list = items.map((e, i) => {
    const val = field === 'scale_yi' ? `${e.value.toFixed(1)}亿` : `${e.value > 0 ? '+' : ''}${e.value.toFixed(2)}%`
    return `${i+1}. ${e.code} ${e.name} — ${e.issuer} · ${val}`
  }).join('\n')

  return {
    content: [{
      type: 'text',
      text: [
        `已为您按${label}排序，TOP ${items.length}：`,
        '',
        list,
        '',
        '请向用户展示结果，可简要说明头部 ETF 的特征。'
      ].join('\n')
    }],
    structuredContent: { field, items }
  }
}

module.exports = rankETF
