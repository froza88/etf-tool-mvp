# 归档清单 — 黄金ETF vs 黄金股ETF

## 文章
- **标题**：黄金ETF vs 黄金股ETF：名字差一字，买的是两回事
- **系列**：易混淆ETF系列 #1
- **日期**：2026-06-02
- **公众号**：卡比兽比卡
- **导语**：用数字，辨真相

## 文章结构
封面 → 全市场13只全量对比（7黄金ETF + 6黄金股ETF）→ 深挖之前先定主角 → 基本信息 → 资产结构+持仓对比 → 规模 → 回报 → 风险 → 什么时候用哪个

## 文件清单
| 文件 | 说明 |
|------|------|
| 黄金ETFvs黄金股ETF.html | HTML源文件 |
| 黄金ETFvs黄金股ETF_自包含.html | 自包含HTML（base64内嵌5图） |
| article.md | 公众号发布用Markdown |
| cover.png | 封面图（实物金条 vs 金矿石照片） |
| generate_cover.py | 封面生成脚本 |
| generate_charts.py | 4张图表生成脚本 |
| data.json | 全13只ETF数据+计算指标 |
| gold_bar.jpg / gold_ore.jpg | 封面素材照（CC授权） |

## 图表（4张，4种类型）
| 文件 | 类型 | 内容 |
|------|------|------|
| section_holdings.png | 环形图 | 100%实物金条 vs 45只股票4分类 |
| section_aum.png | 横向柱状图 | 1,045亿 vs 110亿（9倍） |
| section_returns.png | 棒棒糖图 | 27.2% vs 48.5%（1.8倍） |
| section_risk.png | 双组柱状图 | 波动+回撤双指标对比 |

## 数据
- 全市场13只：7只黄金ETF + 6只黄金股ETF
- 数据源：本地DB（回报/波动/回撤/夏普）+ FTShare API（行情/成交额/成立日）+ 天天基金（费率）
- 代表产品：518880 华安（规模/流动性/历史三项断层）vs 517520 永赢（唯一有足够风险回报对比数据）

## 发布记录
| 平台 | 链接 | 状态 |
|------|------|------|
| 腾讯文档 | https://docs.qq.com/page/DV3JxUFVDWUxEWm1y?_fid=WrqPUCYLDZmr | ✅ 已发布 |
| 微信公众号 | 草稿箱 Media ID: mlSCTjUQn0RtlX7Zjux0aHxcT7XLqqBoI_y5x_-t1q_T8pSJ-qqwRe9_kZG_xaHm | ✅ 已发布 |

## 关键结论
- 黄金ETF = 实物金条（商品），黄金股ETF = 金矿公司股权（股票）——一个"金"字的差别
- 回报差距：黄金股ETF 48.5% > 黄金ETF 27.2%（经营杠杆放大）
- 风险差距：黄金股ETF波动42.8% > 黄金ETF 28.1%，回撤36.2% > 24.9%
- 同类之间：同品种ETF持仓几乎相同，选规模大+流动性好的即可
