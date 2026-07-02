# thermal_agent_fde_v4_qwen_self_optimizing

这一版补齐：

1. `case_state.json`：case 状态机，支持当前阶段、迭代轮次、下一步工具。
2. `decision_log.jsonl`：AI、Python、工程师审批、规则更新全部留痕。
3. `optimization_rules.json`：定义 AI 能改哪些设计杠杆、范围、权限、风险。
4. `geometry_health_rules.json` + `geometry_health_checker.py`：清理后健康检查，失败可回滚。
5. `data/knowledge_db/`：经验数据库、相似案例检索、工程师反馈。
6. `rule_miner.py` + `regression_runner.py`：外层自我迭代与规则回归测试骨架。

## 运行

```bash
cd thermal_agent_fde_v4_qwen_self_optimizing
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run_pipeline.py
```

默认：
- `DEMO_MODE=true`
- `MOCK_ANSYS=true`

所以没有 Qwen key、没有 Ansys 也能跑通闭环。

## 真实 Ansys 部署替换点

当前求解器通过 `tools/solver_worker.py` 统一入口选择后端：

- `MOCK_ANSYS=true`：调用 `tools/solver_worker_mock.py`，用于本地 smoke test。
- `MOCK_ANSYS=false`：调用 `tools/solver_worker_ansys.py`，把 `work/simulation_config_iterXXX.json` 交给真实 Ansys 自动化脚本。

真实环境需要在 `.env` 中配置：

```env
MOCK_ANSYS=false
ANSYS_SOLVER_COMMAND=/path/to/run_ansys_solver.py
ANSYS_SOLVER_TIMEOUT_SECONDS=7200
```

`ANSYS_SOLVER_COMMAND` 指向的脚本需要接收：

```text
--project-root <repo>
--case-id <case_id>
--iteration-index <i>
--config <cases/<case_id>/work/simulation_config_iterXXX.json>
--output <cases/<case_id>/results/solver_result_iterXXX.json>
```

并输出与 `tools/solver_worker_mock.py` 相同结构的 `solver_result_iterXXX.json`，后续 `postprocess.py`、`result_evaluator.py`、`optimization_planner.py` 就能继续复用。

注意：几何清理目前仍是受控规则计划 + mock 执行（复制 STEP），真实 CAD/SpaceClaim 清理应优先替换 `tools/geometry_cleanup_executor.py`；Ansys 网格/求解替换点是 `tools/solver_worker_ansys.py`。

## 使用 Qwen API

编辑 `.env`：

```env
DEMO_MODE=false
QWEN_API_KEY=你的Qwen_API_Key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max
```

## API

```bash
uvicorn app:app --reload --port 8000
```

打开：

```text
http://127.0.0.1:8000/docs
```

主要接口：

- `GET /llm/test_qwen`
- `POST /pipeline/run_self_optimizing`
- `GET /cases/{case_id}/state`
- `GET /cases/{case_id}/decision_log`
- `POST /feedback/engineer`
- `POST /rules/mine_feedback`
- `POST /regression/run`

## 自我优化闭环

内层循环：

```text
result_summary.json
→ evaluate_result
→ optimization_context.json
→ Qwen optimization_plan.json
→ validate against optimization_rules.json
→ config_modifier.py
→ next iteration
```

外层循环：

```text
engineer_feedback.jsonl
→ rule_miner.py
→ candidate_rule_updates.json
→ 人工审查
→ 修改 rules/*.json
→ regression_runner.py
→ 规则上线
```
