/**
 * 对比 ETF — "事实 + 动作" 两段式返回
 */
const API_BASE = 'https://your-api-domain.com'

async function compareETF({ codes }) {
  if (codes.length < 2) {
    return {
      isError: true,
      content: [{ type: 'text', text: '代码不足 2 个，无法对比。请告知用户补充更多 ETF 代码，可调用 searchETF 帮助查找。' }]
    }
  }
  if (codes.length > 5) {
    codes = codes.slice(0, 5)
  }

  const res = await wx.request({
    url: `${API_BASE}/api/etf/compare`,
    method: 'POST',
    data: { codes },
    header: { 'Content-Type': 'application/json' }
  })

  if (res.statusCode !== 200 || !res.data.etfs) {
    return {
      isError: true,
      content: [{ type: 'text', text: 'ETF 数据查询服务暂不可用。请告知用户稍后重试，或提示用户可访问 froza88.github.io/etf-tool-mvp/ 网页版工具进行对比。不要再以相同代码列表重复调用。' }]
    }
  }

  const etfs = res.data.etfs
  const validCodes = etfs.map(e => e.code)

  if (etfs.length < 2) {
    return {
      isError: true,
      content: [{
        type: 'text',
        text: `以下代码未找到有效数据：${codes.filter(c => !validCodes.includes(c)).join('、')}。请告知用户这些代码无效。对有效代码（${validCodes.join('、')}），若数量不足请引导用户补充。`
      }]
    }
  }

  // 构建对比表格
  const header = '| 指标 | ' + etfs.map(e => e.code).join(' | ') + ' |'
  const sep    = '|------|' + etfs.map(() => '------|').join('')

  const fields = [
    ['简称', 'name'], ['管理人', 'issuer'], ['分类', 'category'],
    ['规模(亿)', 'scale_yi'], ['总费率(%)', 'fee_total'],
    ['近1年(%)', 'year_1_return'], ['近3年(%)', 'year_3_return'],
    ['夏普比率', 'sharpe_ratio'], ['年化波动(%)', 'annual_vol'],
    ['最大回撤(%)', 'max_drawdown'], ['跟踪误差(%)', 'tracking_error'],
    ['跟踪指数', 'track_index']
  ]

  const rows = fields.map(([label, key]) => {
    return '| ' + label + ' | ' + etfs.map(e => {
      const v = e[key]
      if (v == null || v === '') return '-'
      if (typeof v === 'number') return v.toFixed(2)
      return String(v).replace(/\|/g, '\\|')
    }).join(' | ') + ' |'
  })

  const table = header + '\n' + sep + '\n' + rows.join('\n')
  const names = etfs.map(e => e.code + ' ' + e.name).join(' vs ')

  return {
    content: [{
      type: 'text',
      text: [
        `已为您对比 ${names} 的核心指标：`,
        '',
        table,
        '',
        '请向用户展示上表，可标注最优值（红=越高越好，蓝=越低越好）。',
        '建议用一句话总结最显著的差异（如规模差距、费率差异、收益差异）。',
        '⚠️ 数据仅供参考，不构成投资建议。投资有风险，决策需谨慎。'
      ].join('\n')
    }],
    structuredContent: { etfs }
  }
}

module.exports = compareETF
