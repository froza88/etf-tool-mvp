// 卡比兽比卡 ETF 对比 Skill — 接口注册
const skill = wx.modelContext.createSkill('path/to/pkg/etf-skill')

// 中间件：统一处理 ETag 缓存和日志
skill.use(async (ctx, next) => {
  const start = Date.now()
  try {
    await next()
  } catch (err) {
    console.error(`[ETF Skill] ${ctx.name} 执行失败:`, err)
    return {
      isError: true,
      content: [{ type: 'text', text: '数据查询暂时不可用，请稍后重试。' }]
    }
  }
})

// 引入并注册 5 个原子接口
const searchETF    = require('./apis/searchETF')
const compareETF   = require('./apis/compareETF')
const rankETF      = require('./apis/rankETF')
const getETFDetail = require('./apis/getETFDetail')
const quickCompare = require('./apis/quickCompare')

skill.registerAPI('searchETF',    searchETF)
skill.registerAPI('compareETF',   compareETF)
skill.registerAPI('rankETF',      rankETF)
skill.registerAPI('getETFDetail', getETFDetail)
skill.registerAPI('quickCompare', quickCompare)
