/**
 * ETF 详情 — 单只完整档案
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
      content: [{
        type: 'text',
        text: `代码 ${code} 未找到对应 ETF。请告知用户该代码无效，建议调用 searchETF 搜索正确的代码。不要用相同的无效代码重试。`
      }]
    }
  }

  const e = res.data
  const text = [
    `已为您查到 **${e.code} ${e.name}** 的完整档案：`,
    '',
    `- 管理人：${e.issuer || '-'}`,
    `- 分类：${e.category || '-'}`,
    `- 跟踪指数：${e.track_index || '-'}`,
    `- 成立日期：${e.listing_date || '-'}`,
    '',
    `**规模与费率**`,
    `- 规模：${(e.scale_yi||0).toFixed(1)} 亿`,
    `- 管理费：${(e.fee_mgmt||0).toFixed(2)}% | 托管费：${(e.fee_custody||0).toFixed(2)}% | 总费率：${(e.fee_total||0).toFixed(2)}%`,
    '',
    `**收益表现**`,
    `- 近1年：${e.year_1_return != null ? (e.year_1_return>0?'+':'')+e.year_1_return.toFixed(2)+'%' : '-'}`,
    `- 近3年：${e.year_3_return != null ? (e.year_3_return>0?'+':'')+e.year_3_return.toFixed(2)+'%' : '-'}`,
    '',
    `**风险指标**`,
    `- 夏普：${e.sharpe_ratio != null ? e.sharpe_ratio.toFixed(2) : '-'}`,
    `- 波动：${e.annual_vol != null ? e.annual_vol.toFixed(2)+'%' : '-'}`,
    `- 回撤：${e.max_drawdown != null ? e.max_drawdown.toFixed(1)+'%' : '-'}`,
    `- 跟踪误差：${e.tracking_error != null ? e.tracking_error.toFixed(2)+'%' : '-'}`,
    '',
    `**前5大持仓**`,
    e.holdings_str || '-',
    '',
    '请向用户展示以上信息。如用户想对比，可引导输入另一 ETF 代码调用 compareETF。',
    '⚠️ 数据仅供参考，不构成投资建议。'
  ].join('\n')

  return {
    content: [{ type: 'text', text }],
    structuredContent: e
  }
}

module.exports = getETFDetail
