# AGENTS.md — CS146S Week4 Starter

FastAPI + SQLite + 静态前端的笔记 / 待办应用。本文件约束 Agent 在本目录下的行为。

## 1. 环境

- Conda 环境：`cs146s`（Python 3.12）
- 工作目录：始终在 `week4/` 下执行命令（`Makefile`、`frontend/`、`data/` 路径都相对于此目录）

```bash
conda activate cs146s
cd week4
```

依赖由仓库根目录的 `../pyproject.toml` 管理（fastapi、sqlalchemy、pydantic v2、pytest、httpx、black、ruff、pre-commit）。缺依赖时先报告，不要擅自修改 `pyproject.toml` / `poetry.lock`。

## 2. 常用命令

| 用途 | 有 make | 无 make |
| --- | --- | --- |
| 测试 | `make test` | `PYTHONPATH=. pytest -q backend/tests` |
| 运行 | `HOST=0.0.0.0 make run` | `PYTHONPATH=. uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000` |
| 格式化 | `make format` | `black . && ruff check . --fix` |
| Lint | `make lint` | `ruff check .` |
| 写入种子数据 | `make seed` | `PYTHONPATH=. python -c "from backend.app.db import apply_seed_if_needed; apply_seed_if_needed()"` |

- 端口可用 `PORT=xxxx` 覆盖，默认 8000
- 前端：`http://<host>:8000/`；OpenAPI：`/docs`、`/openapi.json`
- 单测单文件：`PYTHONPATH=. pytest -q backend/tests/test_notes.py -k search`
- pre-commit：`pre-commit install --config pre-commit-config.yaml`，`pre-commit run --all-files --config pre-commit-config.yaml`（配置文件名没有前导点）

## 3. 目录结构

```
week4/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口；挂载 /static，startup 时建表并写种子数据
│   │   ├── db.py              # engine、get_db 依赖、apply_seed_if_needed
│   │   ├── models.py          # SQLAlchemy 模型：Note、ActionItem
│   │   ├── schemas.py         # Pydantic 模型：NoteCreate/Read、ActionItemCreate/Read
│   │   ├── routers/
│   │   │   ├── notes.py       # /notes：GET /、POST /、GET /search/、GET /{note_id}
│   │   │   └── action_items.py# /action-items：GET /、POST /、PUT /{item_id}/complete
│   │   └── services/
│   │       └── extract.py     # extract_action_items(text) -> list[str]
│   └── tests/                 # conftest.py 提供 client fixture（临时 SQLite + 覆盖 get_db）
├── frontend/                  # index.html、app.js、styles.css（原生 JS，无构建步骤）
├── docs/TASKS.md              # 任务清单（优先依据）
├── data/                      # seed.sql、app.db（运行时数据库）
├── Makefile
└── pre-commit-config.yaml
```

## 4. 工作流

1. 从 `docs/TASKS.md` 选定任务，先阅读相关的 router、schema、model 和测试
2. 修改 API 时先写测试：在 `backend/tests/test_*.py` 里新增或修改用例，运行确认其**失败**
3. 实现：router → schema → model / service，保持改动最小
4. `make test` 全部通过
5. `make format && make lint` 无报错
6. 如果改了接口，同步更新 `frontend/app.js`（以及 `API.md`，若已存在）

约定：

- 测试统一使用 `client` fixture，不要直接连接 `data/app.db`
- DB 会话通过 `Depends(get_db)` 注入；`get_db` 会自动 commit / rollback，router 内一般无需手动 commit
- 静态路由必须注册在 `/{id}` 这类路径参数路由**之前**（例如 `/notes/search/` 要在 `/notes/{note_id}` 之前）
- 找不到资源返回 404，校验失败返回 400/422，并附带明确的 `detail`
- 风格：black + ruff，行宽 100；ruff 规则 `E,F,I,UP,B`；使用 Python 3.10+ 类型写法（`list[str]`、`X | None`）

## 5. 任务来源

- 优先依据 `docs/TASKS.md`；需求不明确时参考 `assignment.md`，仍不明确就向用户确认
- `writeup.md` 是作业报告，只在用户要求时修改

## 6. 安全边界

- 只修改 `week4/` 内的文件；**不要修改** `week1/`–`week3/`、`week5/`–`week8/` 及仓库根目录的配置
- **不要删除或覆盖** `data/app.db`、`data/seed.sql`；需要干净数据时，使用 `DATABASE_PATH=/tmp/xxx.db` 指向临时库
- 不要执行 `DROP TABLE`、`rm -rf data/`、`git reset --hard`、`git push --force` 等破坏性操作，确需执行时先征得用户同意
- 不要提交 `.env`、密钥或数据库文件
