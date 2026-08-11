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
  static/       # 少量样式
  models.py     # 6 个核心业务模型
  main.py       # FastAPI 入口
scripts/
  seed_demo.py  # 虚构演示数据
tests/          # 关键业务流程测试
```

## 数据边界

- SQLite 数据库、`.env`、上传目录均被 `.gitignore` 排除。
- 仓库不应提交真实客户姓名、手机号、合同、账号密码或数据库备份。
- 本项目不兼容原版 59 张表的生产数据库；它是独立的小型产品，不是原系统的替换部署包。
