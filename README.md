# Thermal Agent FDE V4 Qwen Self-Optimizing

这是一个“AI 辅助热仿真流程编排”原型仓库：用 Qwen 解析客户热仿真需求、生成优化建议，用 Python 工具链管理案例状态、几何清理计划、仿真配置、求解结果、报告与经验库。

> 当前默认是 **demo/mock 模式**：没有 Qwen Key、没有 Ansys 也可以跑通流程骨架。真实部署时需要替换 CAD/Ansys 执行层，见本文“真实部署需要修改哪些部分”。

## 一、整体工作流

```text
客户需求 + STEP 图纸
→ 创建 case / 初始化状态
→ Qwen 解析热仿真需求
→ 检查几何摘要
→ 生成几何清理计划：小零件、GB 标准件、小孔、圆角
→ 工程师审批
→ 执行几何清理
→ 几何健康检查
→ 构建仿真配置：边界条件、材料、求解参数、网格规则
→ 求解器：mock 或真实 Ansys
→ 后处理并评估结果
→ 不达标则 Qwen 生成优化方案
→ 应用优化方案并进入下一轮求解
→ 达标后生成报告并写入知识库
```

对应主编排代码是 `workflow/thermal_pipeline.py`。

## 二、目录和模块作用

### 1. 顶层入口

| 路径 | 作用 |
| --- | --- |
| `run_pipeline.py` | 命令行 demo 入口，默认运行 `demo_001`。适合本地 smoke test。 |
| `app.py` | FastAPI 服务入口，提供 case 创建、流水线运行、状态查询、反馈记录、规则挖掘、回归测试等 API。 |
| `requirements.txt` | Python 依赖。 |
| `README.md` | 项目说明、模块职责、部署替换点。 |

### 2. `workflow/`

| 路径 | 作用 |
| --- | --- |
| `workflow/thermal_pipeline.py` | 端到端主流程编排：创建 case、需求解析、几何清理、健康检查、配置生成、求解、后处理、评估、优化、报告。真实部署时通常不改这里，只替换下游工具模块。 |

### 3. `agent/`

| 路径 | 作用 |
| --- | --- |
| `agent/qwen_client.py` | Qwen API 客户端。负责读取 `QWEN_API_KEY`、`QWEN_BASE_URL`、`QWEN_MODEL`，发送 chat/completions 请求，提取 JSON，支持 timeout/retry。 |
| `agent/prompts.py` | Qwen 的系统 prompt、需求解析 prompt、优化规划 prompt。要提升模型稳定性、约束输出格式、修改提示词时主要改这里。 |
| `agent/schemas.py` | FastAPI 请求体 schema，例如 `PipelineRequest`、`FeedbackRequest`。 |

### 4. `tools/`：核心工具模块

| 模块 | 作用 | 真实部署关注点 |
| --- | --- | --- |
| `tools/case_manager.py` | 创建 case 目录、默认需求文件和默认 STEP。 | 真实系统可改为接收客户上传文件，而不是生成默认文件。 |
| `tools/case_state.py` | 管理 `case_state.json`，记录当前阶段、迭代轮次、上一步/下一步工具、审批记录。 | 通常不用改。 |
| `tools/decision_logger.py` | 写 `decision_log.jsonl` 和全局日志，记录 AI、Python、solver、工程师审批事件。 | 生产可接数据库/审计系统。 |
| `tools/io_utils.py` | JSON/JSONL 读写、case 路径和目录创建。 | 通常不用改。 |
| `tools/requirement_parser.py` | 调用 Qwen 解析客户需求，归一成下游字段：环境温度、功耗、风速、目标温度、材料、收敛标准等。 | 真实部署需强化 prompt 和字段校验，可接客户需求模板。 |
| `tools/geometry_inspector.py` | 生成几何摘要，如零件、孔、圆角、Named Selections 等。 | 真实部署应接 CAD/SpaceClaim/PyAnsys Geometry，读取真实 STEP 特征。 |
| `tools/geometry_cleanup_planner.py` | 根据几何摘要生成清理计划：删除小于 `2×2×2mm` 的零件、删除名字带 `GB` 的零件、填小孔、简化圆角。 | 规则可继续扩展；如果希望由 Qwen 参与清理决策，可在这里接 Qwen，但必须保留硬规则约束。 |
| `tools/geometry_cleanup_executor.py` | 执行几何清理。当前是 mock：复制 STEP 并记录删除/填孔/去圆角数量。 | **真实部署必须重点替换**：接 SpaceClaim/DesignModeler/PyAnsys Geometry，真正删除零件、填孔、简化圆角并导出 clean STEP。 |
| `tools/geometry_health_checker.py` | 清理后健康检查，失败时可中止流程。 | 真实部署应加入 CAD 修复、实体有效性、流体域封闭性、Named Selections 完整性检查。 |
| `tools/simulation_config_builder.py` | 生成仿真配置：边界条件、材料属性、求解参数、网格参数；包含“散热鳍片横截面至少 2 个网格”的规则。 | 真实部署时将这里的 JSON 映射到 Ansys 脚本。 |
| `tools/solver_worker.py` | 求解器统一入口。根据 `MOCK_ANSYS` 选择 mock 或真实 Ansys 后端。 | 部署时保持不变，通过环境变量切换后端。 |
| `tools/solver_worker_mock.py` | mock 求解器：生成假的网格、残差、温度、压降结果。 | 仅用于本地 demo，不用于真实交付。 |
| `tools/solver_worker_ansys.py` | 真实 Ansys 适配器：调用 `ANSYS_SOLVER_COMMAND` 指向的外部自动化脚本，要求输出与 mock 相同结构的结果 JSON。 | **接入 Ansys 的主要替换点**。 |
| `tools/postprocess.py` | 从 solver 输出生成 `result_summary.json`、温度图、残差图。 | 真实部署可改为读取 Fluent/Icepak/Mechanical 导出的场数据和图片。 |
| `tools/result_evaluator.py` | 判断结果是否通过：求解失败、网格失败、不收敛、温度超标、达标。 | 真实部署可加入压降、噪声、器件温升、可靠性等判据。 |
| `tools/optimization_context_builder.py` | 汇总需求、几何、配置、结果、规则、历史迭代、相似案例，形成 Qwen 优化上下文。 | 可加入更多工程特征和约束。 |
| `tools/optimization_planner.py` | 调用 Qwen 生成优化方案，并做规则过滤、范围钳制、审批约束、兜底策略。 | 真实部署需持续调 prompt 和规则，避免越权修改。 |
| `tools/config_modifier.py` | 应用优化方案到下一轮仿真配置。 | 若要真正改几何参数，需要接 CAD 参数化脚本，而不仅是改 JSON。 |
| `tools/report_generator.py` | 生成 Word 报告，并写入知识库。 | 真实部署可换成企业模板。 |
| `tools/knowledge_db.py` | 相似案例、经验库、工程师反馈。 | 可接数据库/向量库。 |
| `tools/rule_miner.py` | 从工程师反馈中挖掘候选规则。 | 候选规则仍需人工审查。 |
| `tools/regression_runner.py` | 回归测试入口，验证规则变化后 demo case 是否仍能通过。 | 真实部署需扩充标准案例集。 |

### 5. `rules/`

| 路径 | 作用 |
| --- | --- |
| `rules/optimization_rules.json` | Qwen 能修改哪些设计杠杆、范围、步长、审批权限、风险等级。 |
| `rules/geometry_rules.json` | 几何清理基础规则。 |
| `rules/geometry_health_rules.json` | 清理后几何健康检查规则。 |
| `rules/mesh_rules.json` | 网格规则。 |
| `rules/solver_rules.json` | 求解器规则。 |
| `rules/material_database.json` | 材料数据库。 |
| `rules/approval_policy.json` | 审批策略。 |
| `rules/regression_policy.json` | 回归策略。 |
| `rules/boundary_templates.json` | 边界条件模板。 |

### 6. `schemas/`

JSON Schema 草案，用于描述 case state、decision log、optimization context、optimization plan 等结构。后续如果要严格校验 Qwen 输出，建议在这里扩展完整 schema，并在工具模块中强制校验。

### 7. `cases/`

案例目录。每个 case 通常包含：

```text
cases/<case_id>/input/          # 客户需求和原始模型
cases/<case_id>/work/           # 中间文件：清理计划、仿真配置、最新评估、最新优化方案
cases/<case_id>/iterations/     # 每轮迭代快照
cases/<case_id>/mesh/           # 网格信息
cases/<case_id>/results/        # 求解结果、后处理图片、summary
cases/<case_id>/report/         # Word 报告
cases/<case_id>/state/          # case_state.json、decision_log.jsonl
```

### 8. `data/knowledge_db/` 和 `logs/`

| 路径 | 作用 |
| --- | --- |
| `data/knowledge_db/` | 相似案例、工程师反馈、经验模式、候选规则。 |
| `logs/global_decision_log.jsonl` | 全局决策日志。 |

## 三、当前代码对目标流程的满足情况

| 目标步骤 | 当前状态 | 说明 |
| --- | --- | --- |
| 删除小于 `2×2×2mm` 的零件 | 部分满足 | `geometry_cleanup_planner.py` 能生成计划；`geometry_cleanup_executor.py` 仍是 mock。 |
| 删除名字带 `GB` 的标准件 | 部分满足 | 已在清理计划中实现；真实删除需要接 CAD 执行器。 |
| 填直径小于 `5mm` 的孔 | 部分满足 | 已生成计划；真实填孔需要替换执行器。 |
| 圆角简化成直角 | 部分满足 | 已生成计划；真实几何操作未实现。 |
| 清理后健康检查 | 初步满足 | 有健康检查模块，但真实 CAD 有效性检查需增强。 |
| AI 设置边界条件、材料、求解参数 | 初步满足 | Qwen 解析需求 + `simulation_config_builder.py` 生成配置。 |
| 鳍片横截面至少 2 个网格 | 满足配置层 | 已写入 `mesh_settings.fin_cross_section_min_cells=2`。 |
| AI 调用仿真软件计算 | 部分满足 | 已有 Ansys 适配入口；还需要实际 Ansys 自动化脚本。 |
| 不达标后 AI 提建议并循环优化 | 初步满足 | `optimization_planner.py` + `config_modifier.py` + pipeline 循环已存在；真实几何修改还需接 CAD 参数化。 |

## 四、真实部署需要修改哪些部分

### 必改 1：接入真实 CAD/SpaceClaim 几何清理

当前 `tools/geometry_cleanup_executor.py` 只是 mock。真实部署需要把它改成真正调用 CAD 工具：

1. 读取 `cases/<case_id>/work/cleanup_plan.json`。
2. 打开 `cases/<case_id>/input/model.step`。
3. 执行：
   - 删除 `parts_to_remove`。
   - 填 `holes_to_fill`。
   - 简化 `fillets_to_simplify`。
4. 导出 `cases/<case_id>/work/clean_model.step`。
5. 返回清理结果 JSON。

推荐实现方式：

- Ansys SpaceClaim Python 脚本；或
- Ansys Discovery/Geometry 脚本；或
- PyAnsys Geometry；或
- 企业已有 CAD 自动化服务。

### 必改 2：接入真实 Ansys 网格和求解

当前真实 Ansys 的适配入口已经放在 `tools/solver_worker_ansys.py`。部署时一般不需要改 pipeline，只需要：

1. `.env` 设置：

```env
MOCK_ANSYS=false
ANSYS_SOLVER_COMMAND=/path/to/run_ansys_solver.py
ANSYS_SOLVER_TIMEOUT_SECONDS=7200
```

2. 实现 `run_ansys_solver.py`，支持以下参数：

```text
--project-root <repo>
--case-id <case_id>
--iteration-index <i>
--config <cases/<case_id>/work/simulation_config_iterXXX.json>
--output <cases/<case_id>/results/solver_result_iterXXX.json>
```

3. 脚本内部完成：

```text
读取 simulation_config
→ 导入 clean_model.step
→ 创建/检查 Named Selections
→ 设置材料
→ 设置 inlet/outlet/wall/heat source
→ 按 mesh_settings 生成网格
→ 运行 Fluent/Icepak/Mechanical 求解
→ 导出 solver_result_iterXXX.json
```

4. 输出 JSON 需要保持类似结构：

```json
{
  "status": "converged",
  "iteration_index": 0,
  "mesh_info": {
    "quality_metrics": {
      "min_orthogonal_quality": 0.35,
      "max_skewness": 0.72
    }
  },
  "final_residuals": {
    "continuity": 1e-6,
    "energy": 1e-7
  },
  "monitors": {
    "max_temperature_c": 87.5,
    "avg_temperature_c": 62.3,
    "pressure_drop_pa": 125.4
  },
  "convergence_achieved": true,
  "warnings": []
}
```

这样后面的 `postprocess.py`、`result_evaluator.py`、`optimization_planner.py` 可以继续复用。

### 必改 3：真实结果后处理

`tools/postprocess.py` 当前会生成 mock 风格温度图和残差图。真实部署建议改为：

- 读取 Ansys 导出的温度云图、残差曲线、monitor CSV。
- 抽取最大温度、平均温度、压降、质量流量。
- 保持输出 `result_summary.json` 字段稳定。

### 必改 4：真实几何优化/参数化修改

如果 Qwen 建议改鳍片高度、间距、底板厚度等几何参数，仅改 JSON 不够。需要扩展：

- `tools/config_modifier.py`：继续负责解析优化方案；
- 新增或扩展 CAD 参数化执行器：根据优化方案修改 CAD 参数并重新导出 STEP；
- 修改后再进入 `simulation_config_builder.py` 和 Ansys 求解。

### 建议改 5：Qwen 输出强校验

当前已经做了基础归一、过滤、范围钳制和审批控制。生产环境建议继续加强：

- 用 `schemas/optimization_plan.schema.json` 做严格 JSON Schema 校验。
- 把所有自动应用动作限定在 `rules/optimization_rules.json`。
- 几何/材料修改默认 `requires_review=true`。
- 所有 Qwen 输出保留到 decision log，便于审计。

### 建议改 6：数据和权限

生产环境建议改：

- `logs/` 写数据库或日志平台。
- `data/knowledge_db/` 接数据库/向量库。
- API 增加鉴权、文件上传、case 隔离和权限管理。
- 大文件和结果文件放对象存储或共享文件系统。

## 五、运行

```bash
cd thermal_agent_fde_v4_qwen_self_optimizing
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py
```

默认：

```env
DEMO_MODE=true
MOCK_ANSYS=true
```

所以没有 Qwen Key、没有 Ansys 也能跑通 demo 闭环。

codex-kvew13
## 六、使用 Qwen API
=====
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
main

编辑 `.env`：

```env
DEMO_MODE=false
QWEN_API_KEY=你的Qwen_API_Key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max
QWEN_TEMPERATURE=0.1
QWEN_TIMEOUT_SECONDS=60
QWEN_MAX_RETRIES=2
```

## 七、启动 API

```bash
uvicorn app:app --reload --port 8000
```

打开：

```text
http://127.0.0.1:8000/docs
```

主要接口：

- `GET /llm/test_qwen`
- `POST /cases/create`
- `POST /pipeline/run_self_optimizing`
- `GET /cases/{case_id}/state`
- `GET /cases/{case_id}/decision_log`
- `POST /feedback/engineer`
- `POST /rules/mine_feedback`
- `POST /regression/run`

## 八、自我优化闭环

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
