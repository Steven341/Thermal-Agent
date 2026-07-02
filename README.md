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
