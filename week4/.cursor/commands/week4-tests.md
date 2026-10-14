# week4-tests

在 CS146S week4 starter 中运行 pytest，并根据真实输出用中文总结结果。

用户在命令名后输入的内容就是**参数**（测试路径和/或 `-k` 表达式，例如 `backend/tests/test_notes.py -k search`）。没有输入任何内容则视为无参数。

## 步骤

### 1. 检查环境与目录

在同一个 shell 中执行：

```bash
cd "$(git rev-parse --show-toplevel)/week4"
echo "CONDA_DEFAULT_ENV=$CONDA_DEFAULT_ENV"; python --version; pwd
```

- 如果 `CONDA_DEFAULT_ENV` 不是 `cs146s`，先尝试激活：
  `source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate cs146s`
- 如果激活失败（例如环境不存在），**立即停止**，把报错原文告诉用户，并说明还没有运行测试。不要自行创建环境或安装依赖。
- 确认 `python --version` 是 3.12.x，且 `pwd` 以 `/week4` 结尾。

### 2. 运行测试

- 有参数：

  ```bash
  PYTHONPATH=. pytest -q <参数>
  ```

- 无参数：

  ```bash
  PYTHONPATH=. pytest -q backend/tests --maxfail=1 -x
  ```

参数原样传入，不要增删。完整保留输出，供下一步引用。

### 3. 用中文汇总（只依据真实输出）

按以下结构回复：

1. **结论**：一句话，例如“全部通过”或“有失败（因为 `-x` 在第一个失败处停止）”。
2. **数量**：引用 pytest 最后一行的汇总，包括 passed / failed / error / skipped 数和耗时。
3. **失败用例**（如果有）：每条一项，写明
   - 完整的用例名，例如 `backend/tests/test_notes.py::test_search`
   - 关键报错，即断言或异常的最后几行原文
   - 可能原因：先阅读对应的测试和被测代码（`backend/app/routers/`、`schemas.py`、`models.py`、`services/extract.py`），再下判断，不要凭空猜测
   - 如果是 `-x` 中断，说明“后续用例未执行，失败数量可能被低估”
4. **下一步**：阅读 `docs/TASKS.md`，给出**一条**具体建议：
   - 有失败：指出最可能对应的任务编号和需要修改的文件
   - 全绿：推荐 TASKS.md 中下一个尚未完成的任务（通过检查代码判断是否已实现），并写明先补哪个测试

warning 只在与失败相关时才提，否则一句带过。

### 4. 全绿时（可选）提示覆盖率

只给出建议，不要自动执行：

```bash
python -c "import pytest_cov" && PYTHONPATH=. pytest -q backend/tests --cov=backend/app --cov-report=term-missing
```

- 不要编造覆盖率数字。只有真正运行过并拿到输出时，才可以引用其中的数字。
- 如果 `pytest_cov` 无法导入，说明缺少 `pytest-cov`，由用户决定是否安装。

## 安全约束

- **默认只诊断，不修改任何文件。**
- 只有用户明确要求“修复失败的测试”时才改代码，并且：
  - 只修改 `week4/` 下的文件，不碰其他 week 目录和仓库根目录配置
  - 优先修实现；只有测试本身有误时才改测试，并说明理由
  - 修改后重新运行同一条测试命令，并汇报新结果
- 不要删除或重置 `data/app.db`，不要运行 `git reset`、`git checkout -- .` 等会丢弃改动的命令。
