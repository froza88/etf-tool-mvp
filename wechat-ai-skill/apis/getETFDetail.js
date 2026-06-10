/**
 * ETF 详情 — 查看单只 ETF 完整信息
 */
const API_BASE = 'https://your-api-domain.com'

async function getETFDetail({ code }) {
  const res = await wx.request({
    url: `${API_BASE}/api/etf/detail`,
    method: 'POST',
    data: { code },
    header: { 'Content-Type': 'application/json' }
  })

  if (res.statusCode !== 200 || !res.data.code) {
    return {
      isError: true,
      content: [{ type: 'text', text: `未找到代码 ${code} 对应的 ETF，请检查代码是否正确。` }]
    }
  }

  const e = res.data
  const lines = [
    `📊 **${e.code} ${e.name}**`,
    ``,
    `管理人：${e.issuer || '-'}`,
    `分类：${e.category || '-'}`,
    `跟踪指数：${e.track_index || '-'}`,
    `成立日期：${e.listing_date || '-'}`,
    ``,
    `**规模与费率**`,
    `规模：${(e.scale_yi||0).toFixed(1)} 亿元`,
    `管理费：${(e.fee_mgmt||0).toFixed(2)}% | 托管费：${(e.fee_custody||0).toFixed(2)}% | 总费率：${(e.fee_total||0).toFixed(2)}%`,
    ``,
    `**收益表现**`,
    `近1年：${e.year_1_return ? (e.year_1_return>0?'+':'')+e.year_1_return.toFixed(2)+'%' : '-'}`,
    `近3年：${e.year_3_return ? (e.year_3_return>0?'+':'')+e.year_3_return.toFixed(2)+'%' : '-'}`,
    ``,
    `**风险指标**`,
    `夏普比率：${e.sharpe_ratio ? e.sharpe_ratio.toFixed(2) : '-'}`,
    `年化波动：${e.annual_vol ? e.annual_vol.toFixed(2)+'%' : '-'}`,
    `最大回撤：${e.max_drawdown != null ? e.max_drawdown.toFixed(1)+'%' : '-'}`,
    `跟踪误差：${e.tracking_error ? e.tracking_error.toFixed(2)+'%' : '-'}`,
    ``,
    `**前5大持仓**`,
    `${e.holdings_str || '-'}`,
    ``,
    `⚠️ 数据仅供参考，不构成投资建议。`
  ]

  return {
    content: [{ type: 'text', text: lines.join('\n') }],
    structuredContent: e
  }
}

module.exports = getETFDetail
