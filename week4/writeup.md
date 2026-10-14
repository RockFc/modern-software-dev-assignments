# Week 4 Write-up
Tip: To preview this markdown file
- On Mac, press `Command (⌘) + Shift + V`
- On Windows/Linux, press `Ctrl + Shift + V`

## INSTRUCTIONS

Fill out all of the `TODO`s in this file.

## SUBMISSION DETAILS

Name: **TODO** \
SUNet ID: **TODO** \
Citations:
- Claude Code best practices: https://www.anthropic.com/engineering/claude-code-best-practices
- SubAgents overview: https://docs.anthropic.com/en/docs/claude-code/sub-agents
- CS146S Week4 assignment.md / docs/TASKS.md

This assignment took me about **TODO** hours to do.

## YOUR RESPONSES

### Automation #1 — Cursor 项目规则（AGENTS.md）

a. Design inspiration  
> 参考 Agent Manager 课上的「行为文件」思路，以及 Claude Code best practices 里用持久上下文约束工具使用与工作流的做法。用 Cursor 的 `AGENTS.md` / Project Rules 承担与 `CLAUDE.md` 相同角色。

b. Design  
> **目标**：让 Agent 一进仓库就知道 week4 环境、命令、目录与先测后写流程。  
> **输入**：仓库结构、`docs/TASKS.md`、conda `cs146s`。  
> **输出**：稳定的 Agent 行为（只改 week4、用 make/pytest、对照 TASKS）。  
> **步骤**：用提示生成草稿 → 人工补上 cs146s、容器内验证、路由顺序与安全边界。

c. How to run / safety  
> Cursor 打开本仓库即可自动加载规则。回滚：删除或还原 `AGENTS.md`。安全：禁止改其他 week、禁止删 `data/app.db`。

d. Before vs after  
> **之前**：每次对话都要重复说明环境与目录。  
> **之后**：规则长期生效，提示词只需描述具体任务。

e. How you used it to enhance the starter  
> 做 TASK 2（笔记搜索）时，按规则要求：先补测试 → 再改 `search_notes` 与前端 → 在容器 `cs146s-dev` 的 `cs146s` 环境中跑测，避免在宿主机误跑。

### Automation #2 — Cursor Custom Command `week4-tests`

a. Design inspiration  
> 对应作业示例中的 test-runner slash command；并结合 best practices 中可复用、可重复的命令式工作流。

b. Design  
> **目标**：一键在正确环境下跑 pytest，并用中文总结失败与下一步。  
> **输入**：可选测试路径 / `-k`；默认 `backend/tests --maxfail=1 -x`。  
> **输出**：通过/失败数量、失败用例、对照 `TASKS.md` 的一条建议。  
> **步骤**：检查 conda=`cs146s` 与 `week4/` → 跑 pytest → 只依据真实输出汇总。

c. How to run / safety  
> 在 Cursor 中调用 `/week4-tests`（可带参数）。默认只诊断不改代码；回滚即停用该 command。须在 Docker 容器内、`cs146s` 环境下验证。

d. Before vs after  
> **之前**：手动 activate、cd、记 pytest 参数、自己读日志。  
> **之后**：一条命令完成检查与中文摘要，失败时指向 TASKS。

e. How you used it to enhance the starter  
> 用该命令验收 TASK 2：新增大小写不敏感搜索测试、`ilike` 实现、前端搜索框对接 `/notes/search/?q=`；最终容器内 `make test` / pytest **5 passed**。

### 增强 starter 摘要（TASK 2）

- `notes.py`：`ilike` 实现 case-insensitive 搜索  
- `test_notes.py`：补 case-insensitive 与空查询用例  
- `index.html` + `app.js`：搜索 UI，请求 `/notes/search/?q=`  
- 验证：容器内测试全绿；浏览器用 hello/HELLO 搜索一致