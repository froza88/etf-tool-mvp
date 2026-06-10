/**
 * 排名 ETF — 按指定字段排序
 */
const API_BASE = 'https://your-api-domain.com'

async function rankETF({ field, limit = 10, category }) {
  const fieldLabels = {
    year_1_return: '近1年收益', scale_yi: '规模',
    fee_total: '总费率', sharpe_ratio: '夏普比率',
    max_drawdown: '最大回撤', annual_vol: '年化波动率'
  }

  const res = await wx.request({
    url: `${API_BASE}/api/etf/rank`,
    method: 'POST',
    data: { field, limit: Math.min(limit, 20), category },
    header: { 'Content-Type': 'application/json' }
  })

  if (res.statusCode !== 200) {
    return {
      isError: true,
      content: [{ type: 'text', text: `排名查询失败：${res.errMsg || '请稍后重试'}` }]
    }
  }

  const items = res.data.items || []
  const label = fieldLabels[field] || field
  const unit = field === 'scale_yi' ? '亿' : field === 'fee_total' ? '%' : '%'
  const isFee = field === 'fee_total'

  const textLines = items.map((e, i) => {
    const val = field === 'scale_yi' ? `${e.value.toFixed(1)}亿` : `${e.value > 0 ? '+' : ''}${e.value.toFixed(2)}%`
    return `${i+1}. ${e.code} ${e.name} — ${e.issuer} · ${val}`
  }).join('\n')

  return {
    content: [
      {
        type: 'text',
        text: `按${label}${isFee ? '从低到高' : '排名'} TOP ${items.length}：\n\n${textLines}\n\n⚠️ 数据仅供参考，不构成投资建议。投资有风险，决策需谨慎。`
      }
    ],
    structuredContent: { field, items }
  }
}

module.exports = rankETF
