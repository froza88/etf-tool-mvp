# 归档清单 — 消费ETF vs 消费电子ETF

## 文章
- `消费ETFvs消费电子ETF.html` — HTML源文件
- `消费ETFvs消费电子ETF_自包含.html` — 自包含HTML（base64内嵌所有图）
- `article.md` — 公众号发布用Markdown

## 图表
- `charts/section_01_scale_donut.png` — 规模环形图
- `charts/section_02_return_lollipop.png` — 1年收益棒棒糖图
- `charts/section_03_risk_hbar.png` — 风险指标横向柱状图
- `charts/section_04_holdings_pie.png` — 持仓结构饼图
- `cover.png` — 封面图（1200×920）

## 生成脚本
- `generate_charts.py`
- `generate_cover.py`

## 真实照片（用户提供）
- `img_consumer_maotai.jpeg` — 茅台（消费-白酒）
- `img_consumer_milk.jpeg` — 牛奶（消费-乳业）
- `img_consumer_electronics_robot.jpeg` — 机器人（消费电子-AI）
- `img_consumer_electronics_gears.jpeg` — 齿轮（消费电子-精密制造）

## 数据
- `data.json` — 全量ETF列表 + 代表ETF详细数据

## 关键结论
- 消费ETF 34只合计约237亿，消费电子ETF 7只约109亿
- 近1年收益：消费-14%~+6%，消费电子+91%~+108%
- 持仓零重叠：消费=白酒乳业畜牧业，消费电子=半导体连接器面板
- 代表：消费→159928（汇添富110亿），消费电子→562950（易方达费率0.2%+108%）
- 费率差异大：消费类全线0.6%，消费电子最低0.20%（易方达562950）

## 修订记录
- 2026-06-07：猪肉→畜牧业全量替换；封面移到副标题下方；饼图改为环形图+图例；数据来源去"本地"和"快照"；matplotlib保存改用bbox_inches='tight'+pad_inches
- 2026-06-06：融入4张用户真实照片；561100费率从0%修正为0.60%；ETF名称规范化加管理人
- 2026-06-07 09:35：归档完成，上传腾讯文档
