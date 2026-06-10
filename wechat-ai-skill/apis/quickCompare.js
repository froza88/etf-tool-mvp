/**
 * 快捷对比 — 复用 compareETF
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
      content: [{
        type: 'text',
        text: `预设组「${group}」不存在，当前可用的快捷对比组：${available}。请告知用户目前不支持的场景，并引导用户通过 searchETF 手动搜索后再调用 compareETF。不要用无效的组名重试。`
      }]
    }
  }

  return await compareETF({ codes })
}

module.exports = quickCompare
