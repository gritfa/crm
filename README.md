# CRM 系统

一个面向小型服务团队的轻量 CRM 系统。项目采用独立历史和全新实现，
不包含任何生产数据、数据库备份或客户附件。

## 功能

- 登录与会话认证
- 管理员创建、启用和停用用户
- 客户资料、联系人和负责人
- 销售线索、跟进日期及一键转客户
- 合同金额、状态和周期
- 按合同登记收款、计算已收与待收
- 首页展示客户、线索、合同、本月收款和近期跟进
- 手机端适配：底部标签栏导航、列表自动转卡片，可加到手机主屏

为了保持小而可维护，本项目不包含复杂审批、会计账簿、税务申报、RPA、电子签、
审计引擎、佣金、生产备份和批量数据导入。

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy 2
- SQLite
- Jinja2 + HTMX + Bootstrap
- pytest

前后端由一个 Python 服务提供，不需要 Node.js、Redis 或独立前端构建流程。
手机端同样走这一套模板，没有第二套代码。

## 手机端

电脑和手机是同一套页面、同一批路由，靠 CSS 断点切换呈现方式，因此没有独立的
App、小程序或 `/m` 路由需要单独维护。

- **导航**：窄屏底部固定标签栏（首页 / 客户 / 线索 / 合同 / 收款），当前板块高亮；
  「用户管理」和「退出」收在右上角折叠菜单里。宽屏保持原来的顶部导航。
- **列表**：客户、线索、合同、收款等宽表格在窄屏自动转成卡片，首列作卡片标题，
  其余字段按「字段名 : 值」竖排，操作按钮撑成整行，不再左右横拉。
- **表单**：电话、金额字段会唤起对应的手机键盘；输入框字号固定 16px，
  避免 iOS 聚焦时自动放大页面；按钮和可点区域不小于 44px。
- **刘海屏**：`viewport-fit=cover` 配合 `safe-area-inset`，底栏不会被 home 横条压住。

### 加到手机主屏

用手机浏览器打开站点，选择「添加到主屏幕」，即可像 App 一样全屏打开
（`display: standalone`）。图标和名称由 `app/static/manifest.webmanifest` 定义。

Service Worker（`app/static/sw.js`）**只缓存样式和图标这类静态资源**，
客户、合同、收款等业务页面一律实时请求服务器，不落本地缓存——避免手机丢失
或被他人拿到后泄露数据，也不会读到过期内容。断网时打开会显示离线提示页。

浏览器要求 PWA 运行在 HTTPS（`localhost` 除外），所以正式部署需配好证书。

图标由脚本生成，改动配色后重新执行并提交结果即可：

```bash
python scripts/generate_icons.py
```

## 本地运行

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m uvicorn app.main:app --reload
```

浏览器打开 <http://127.0.0.1:8000>。

开发环境首次启动会根据 `.env` 创建管理员。示例配置是：

- 手机号：`13800000000`
- 密码：`ChangeMe123!`

部署前必须更换 `SECRET_KEY` 和管理员密码，并把 `SESSION_HTTPS_ONLY` 设为 `true`。

## 虚构演示数据

如需体验完整流程，可执行：

```powershell
python scripts/seed_demo.py
```

脚本只创建带有“示例”标识的虚构客户、线索、合同和收款记录，且仅在 SQLite
数据库上运行。

## 测试

```powershell
python -m pytest
```

测试使用独立的临时 SQLite 数据库，不读取本地业务数据库。

## 项目结构

```text
app/
  routes/       # 登录、用户、客户、线索、合同、收款和首页
  templates/    # 服务端 HTML 页面
  static/       # 样式、PWA 清单、Service Worker、图标
  models.py     # 6 个核心业务模型
  main.py       # FastAPI 入口
scripts/
  seed_demo.py       # 虚构演示数据
  generate_icons.py  # 生成 PWA 图标
tests/          # 关键业务流程测试 + 手机端适配回归
```

## 数据边界

- SQLite 数据库、`.env`、上传目录均被 `.gitignore` 排除。
- 仓库不应提交真实客户姓名、手机号、合同、账号密码或数据库备份。
- 本项目不兼容原版 59 张表的生产数据库；它是独立的小型产品，不是原系统的替换部署包。
