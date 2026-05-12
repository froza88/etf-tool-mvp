# 🚀 ETF筛选器 MVP

> 智能ETF筛选与对比工具 - 帮助你快速找到最适合的ETF投资标的

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-lightgrey.svg)](https://flask.palletsprojects.com/)

## 📖 项目简介

ETF筛选器是一个轻量级的Web应用，旨在帮助投资者快速筛选、对比和分析ETF（交易所交易基金）产品。无论你是新手投资者还是资深交易者，这个工具都能帮你：

- 🔍 **快速筛选**：根据多维度条件筛选ETF
- 📊 **详细对比**：并排对比多个ETF的关键指标
- 📈 **数据分析**：查看历史表现、费率、持仓等详细信息
- 💡 **智能推荐**：基于你的偏好推荐合适的ETF

## ✨ 核心功能

### 1. ETF筛选
- 按分类筛选（股票型、债券型、商品型、货币型、跨境型）
- 按主题筛选（科技、医疗、消费、新能源等）
- 按费率筛选（低费率优选）
- 按规模筛选（大型、中型、小型ETF）

### 2. ETF对比
- 支持多个ETF并排对比
- 关键指标可视化展示
- 费率、收益率、风险指标一目了然

### 3. ETF详情
- 基本信息（基金代码、名称、管理人、成立时间）
- 业绩表现（今年以来、近1年、近3年收益率）
- 持仓明细（前十大重仓股）
- 费率结构（管理费、托管费）

### 4. 数据导出
- 支持导出筛选结果为CSV/Excel
- 方便进一步分析

## 🎯 适用人群

- 📊 **个人投资者**：快速找到适合自己的ETF
- 💼 **理财顾问**：为客户提供专业的ETF建议
- 🎓 **投资新手**：学习ETF投资知识
- 📈 **资深玩家**：快速筛选和对比ETF

## 🛠️ 技术栈

- **后端**：Python 3.8+ / Flask 2.0+
- **前端**：HTML5 / CSS3 / JavaScript (Vanilla)
- **数据存储**：JSON（易于扩展至数据库）
- **部署**：支持Render、Heroku、Vercel等云平台

## 🚀 快速开始

### 本地运行

1. **克隆仓库**
```bash
git clone https://github.com/froza88/ETF-tool-MVP.git
cd ETF-tool-MVP
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **启动应用**
```bash
python app.py
```

4. **访问应用**
打开浏览器，访问：`http://localhost:5000`

### 云端部署

#### 一键部署到Render（推荐）

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**详细部署指南**：查看 [RENDER_DEPLOYMENT_GUIDE.md](RENDER_DEPLOYMENT_GUIDE.md)

#### 部署到Heroku

```bash
heroku create your-app-name
git push heroku main
```

## 📂 项目结构

```
etf-tool-mvp/
├── app.py                      # Flask应用主程序
├── etf_data.py                 # ETF数据处理模块
├── etf_data_generated.json     # ETF数据文件
├── requirements.txt            # Python依赖
├── Procfile                    # 云端部署配置
├── templates/                  # HTML模板
│   ├── index.html              # 首页
│   ├── screening-demo.html     # 筛选演示页
│   ├── compare.html            # 对比页
│   └── detail.html             # 详情页
├── static/                     # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
├── DEPLOYMENT_GUIDE.md         # 部署指南
├── RENDER_DEPLOYMENT_GUIDE.md  # Render部署指南
└── README.md                   # 本文件
```

## 🌟 功能路线图

- [x] **MVP核心功能** (当前版本)
  - [x] ETF筛选
  - [x] ETF对比
  - [x] ETF详情查看
  
- [ ] **V2.0 计划功能**
  - [ ] 用户账户系统
  - [ ] 自选ETF列表
  - [ ] 实时数据更新（对接API）
  - [ ] 高级筛选条件
  - [ ] ETF评分系统
  - [ ] 微信小程序版本
  
- [ ] **V3.0 高级功能**
  - [ ] AI智能推荐
  - [ ] 组合回测
  - [ ] 社区讨论
  - [ ] 付费高级功能

查看完整商业计划：[ETF筛选器创业方案V2.md](ETF筛选器创业方案V2.md)

## 💡 商业模式

本项目采用 **Freemium（免费增值）** 模式：

### 免费版
- 基础筛选功能
- 查看前50只ETF
- 有限对比次数（每天3次）

### 付费版（¥19.9/月 或 ¥199/年）
- 无限筛选和对比
- 全量ETF数据（130+只）
- 高级筛选条件
- 数据导出功能
- 优先客服支持

查看详细方案：[ETF筛选器 Freemium 订阅方案](https://docs.qq.com/doc/your-doc-id)

## 🤝 贡献指南

欢迎贡献代码、提出建议或报告问题！

1. Fork本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- ETF数据来源：公开市场数据
- 图标：Font Awesome / Heroicons
- 字体：系统默认字体栈

## 📧 联系方式

- GitHub Issues：[提交问题](https://github.com/froza88/ETF-tool-MVP/issues)
- Email：froza@163.com

---

⭐ 如果这个项目对你有帮助，请给它一个星标！

**Made with ❤️ by froza**
