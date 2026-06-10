/**
 * 快捷对比 — 加载预设 ETF 对比组合
 */
const compareETF = require('./compareETF')

const QUICK_GROUPS = {
  '黄金vs黄金股': ['518880', '517520'],
  '消费vs消费电子': ['159928', '159732'],
  '医药vs医疗': ['512010', '512170'],
  '沪深300三巨头': ['510300', '510310', '510330'],
  '科创50': ['588000', '588080', '588050', '588060', '588090'],
  '半导体设备': ['159516', '159558', '560780', '561980', '562590'],
  'AI ETF': ['159819', '515070', '515980'],
  '黄金ETF': ['518880', '159937', '159934', '518800', '518850'],
  '创业板vs科创50': ['159915', '588000'],
  '红利vs红利低波': ['510880', '512890'],
  '中证500vs1000': ['510500', '512100'],
  '通信ETF': ['515880', '515050', '159994']
}

async function quickCompare({ group = '' }) {
  const codes = QUICK_GROUPS[group]
  if (!codes) {
    const available = Object.keys(QUICK_GROUPS).join('、')
    return {
      isError: true,
      content: [{ type: 'text', text: `未找到预设组「${group}」。当前可用：${available}` }]
    }
  }

  // 直接复用 compareETF
  return await compareETF({ codes })
}

module.exports = quickCompare
