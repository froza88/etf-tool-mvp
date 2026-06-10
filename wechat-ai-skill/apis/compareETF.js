/**
 * 对比 ETF — 2-5 只 ETF 全维度对比
 * 后端 API: etf_mcp_server.py 的 etf_compare 工具
 */
const API_BASE = 'https://your-api-domain.com'

async function compareETF({ codes }) {
  if (codes.length < 2) {
    return {
      isError: true,
      content: [{ type: 'text', text: '对比至少需要 2 只 ETF，请添加更多代码。' }]
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

  if (res.statusCode !== 200) {
    return {
      isError: true,
      content: [{ type: 'text', text: `对比查询失败：${res.errMsg || '请稍后重试'}` }]
    }
  }

  const etfs = res.data.etfs || []
  if (etfs.length < 2) {
    return {
      content: [{ type: 'text', text: `部分代码未找到有效数据，请检查代码是否正确（上海ETF以5/6开头，深圳以1开头）。` }]
    }
  }

  // 构建对比表格文本
  const header = '| 指标 | ' + etfs.map(e => e.code).join(' | ') + ' |'
  const sep    = '|------|' + etfs.map(() => '------|').join('')
  
  const fields = [
    ['名称', 'name'], ['管理人', 'issuer'], ['分类', 'category'],
    ['规模(亿)', 'scale_yi'], ['总费率(%)', 'fee_total'],
    ['近1年收益(%)', 'year_1_return'], ['近3年收益(%)', 'year_3_return'],
    ['夏普比率', 'sharpe_ratio'], ['年化波动(%)', 'annual_vol'],
    ['最大回撤(%)', 'max_drawdown'], ['跟踪误差(%)', 'tracking_error'],
    ['跟踪指数', 'track_index'], ['前5持仓', 'holdings_str']
  ]

  const rows = fields.map(([label, key]) => {
    return '| ' + label + ' | ' + etfs.map(e => {
      const v = e[key]
      if (v == null) return '-'
      if (typeof v === 'number') return v.toFixed(2)
      return v.toString().replace(/\|/g, '\\|')
    }).join(' | ') + ' |'
  })

  const tableText = header + '\n' + sep + '\n' + rows.join('\n')

  return {
    content: [
      {
        type: 'text',
        text: `以下为 ${etfs.map(e => e.code+' '+e.name).join(' vs ')} 全维度对比：\n\n${tableText}\n\n⚠️ 数据仅供参考，不构成投资建议。投资有风险，决策需谨慎。`
      }
    ],
    structuredContent: { etfs }
  }
}

module.exports = compareETF
