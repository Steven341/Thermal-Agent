# thermal_agent_fde_v4_qwen_self_optimizing

基于 Qwen LLM 的电子设备热设计智能优化 Agent，支持自我迭代优化的完整闭环流程。

## 核心特性

### 1. Case 状态机 (`case_state.json`)
- 追踪当前阶段（pipeline stage）
- 记录迭代轮次（iteration index）
- 指导下一步工具调用
- 状态持久化到 `cases/<case_id>/state/`

### 2. 决策日志 (`decision_log.jsonl`)
- AI 决策留痕（Qwen 推理过程）
- Python 工具执行记录
- 工程师审批记录
- 规则更新审计轨迹

### 3. 优化规则体系 (`optimization_rules.json`)
- 定义 AI 可修改的设计杠杆
- 参数调整范围与权限控制
- 风险等级评估（低/中/高）
- 自动应用策略配置

### 4. 几何健康检查
- `geometry_health_rules.json`: 清理规则定义
- `geometry_health_checker.py`: 清理后验证
- 失败回滚机制
- 支持 CAD/SpaceClaim 集成

### 5. 知识库系统 (`data/knowledge_db/`)
- `case_index.jsonl`: 相似案例检索
- `experience_patterns.json`: 经验模式库
- `engineer_feedback.jsonl`: 工程师反馈收集
- `rule_change_log.jsonl`: 规则变更历史

### 6. 自我优化闭环
- **内层循环**: 单 case 多迭代优化
- **外层循环**: 跨 case 规则挖掘与回归测试
- `rule_miner.py`: 从反馈中挖掘规则候选
- `regression_runner.py`: 规则变更前回归验证

---

## 项目结构

```
thermal_agent_fde_v4_qwen_self_optimizing/
├── agent/                      # LLM 交互层
│   ├── qwen_client.py         # Qwen API 客户端
│   ├── prompts.py             # Prompt 模板
│   └── schemas.py             # Pydantic 数据模型
├── tools/                      # 工具函数库
│   ├── case_manager.py        # Case 创建与管理
│   ├── case_state.py          # 状态机操作
│   ├── decision_logger.py     # 决策日志记录
│   ├── geometry_*.py          # 几何检查/清理系列工具
│   ├── simulation_config_builder.py  # 仿真配置生成
│   ├── solver_worker*.py      # 求解器接口（Mock/Ansys）
│   ├── optimization_*.py      # 优化计划生成与验证
│   ├── config_modifier.py     # 配置文件修改器
│   ├── result_evaluator.py    # 结果评估
│   ├── report_generator.py    # Word 报告生成
│   ├── rule_miner.py          # 规则挖掘
│   └── regression_runner.py   # 回归测试
├── workflow/                   # 工作流编排
│   └── thermal_pipeline.py    # 主流程编排
├── rules/                      # 规则配置文件
│   ├── optimization_rules.json       # 优化规则
│   ├── geometry_rules.json           # 几何规则
│   ├── geometry_health_rules.json    # 几何健康检查规则
│   ├── mesh_rules.json               # 网格规则
│   ├── solver_rules.json             # 求解器规则
│   ├── material_database.json        # 材料数据库
│   ├── boundary_templates.json       # 边界条件模板
│   ├── approval_policy.json          # 审批策略
│   └── regression_policy.json        # 回归测试策略
├── schemas/                    # JSON Schema 定义
│   ├── case_state.schema.json
│   ├── decision_log.schema.json
│   ├── optimization_context.schema.json
│   └── optimization_plan.schema.json
├── data/knowledge_db/          # 知识库
├── cases/                      # 案例目录
│   └── demo_001/              # 示例案例
│       ├── input/             # 输入几何/需求
│       ├── work/              # 工作目录（配置文件）
│       ├── mesh/              # 网格文件
│       ├── results/           # 求解结果
│       ├── iterations/        # 迭代历史
│       ├── report/            # 生成报告
│       └── state/             # 状态与日志
├── app.py                      # FastAPI 服务入口
├── run_pipeline.py             # 命令行运行脚本
├── requirements.txt            # Python 依赖
└── README.md                   # 本文档
```

---

## 快速开始

### 环境准备

```bash
cd thermal_agent_fde_v4_qwen_self_optimizing
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 配置文件

创建 `.env` 文件（参考下方配置项）：

```bash
# Windows
echo DEMO_MODE=true > .env
echo MOCK_ANSYS=true >> .env

# Linux/Mac
cat > .env << EOF
DEMO_MODE=true
MOCK_ANSYS=true
EOF
```

### 运行 Demo

```bash
python run_pipeline.py
```

默认配置说明：
- `DEMO_MODE=true`: 使用内置示例数据，无需外部输入
- `MOCK_ANSYS=true`: 使用 Mock 求解器，无需安装 Ansys

---

## 配置选项

### 基础配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEMO_MODE` | `true` | 演示模式，使用示例数据 |
| `MOCK_ANSYS` | `true` | Mock 求解器模式 |
| `AUTO_APPLY_LOW_RISK_OPTIMIZATION` | `true` | 自动应用低风险优化 |

### Qwen API 配置

编辑 `.env` 启用真实 LLM：

```env
DEMO_MODE=false
QWEN_API_KEY=your_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-max
```

获取 API Key: https://dashscope.console.aliyun.com/

### Ansys 求解器配置

切换到真实 Ansys 求解器：

```env
MOCK_ANSYS=false
ANSYS_SOLVER_COMMAND=/path/to/run_ansys_solver.py
ANSYS_SOLVER_TIMEOUT_SECONDS=7200
```

`ANSYS_SOLVER_COMMAND` 指向的脚本需接收以下参数：

```bash
--project-root <repo_root>
--case-id <case_id>
--iteration-index <i>
--config <cases/<case_id>/work/simulation_config_iterXXX.json>
--output <cases/<case_id>/results/solver_result_iterXXX.json>
```

输出格式需与 `tools/solver_worker_mock.py` 保持一致。

> **注意**: 
> - 几何清理目前通过 `tools/geometry_cleanup_executor.py` 实现（Mock 模式为复制 STEP 文件）
> - 真实 CAD 清理需替换该模块（如集成 SpaceClaim）
> - Ansys 网格/求解替换点为 `tools/solver_worker_ansys.py`

---


### Ansys 真实接入后的准确性边界

本项目可以校验真实 Ansys 自动化脚本是否按约定返回了可用结果，但**不能仅凭 Agent 流程保证物理仿真绝对准确**。真实准确性仍取决于几何清理是否保留关键流道/热接触、材料与边界条件是否来自工程输入、网格无关性是否通过、湍流/辐射/接触热阻等物理模型是否匹配场景，以及是否与实验、历史案例或手算基准完成相关性验证。

当前代码新增了求解器结果质量门禁：后处理会检查必要监控量、收敛标志、最终残差、网格质量阈值以及可选的能量/质量不平衡指标。若真实 Ansys 输出缺少关键字段或数值不满足规则，Agent 会把该结果标记为不可直接采信，而不是继续当作准确结果优化。

建议真实 Ansys 自动化脚本在 `solver_result_iterXXX.json` 中额外输出：

```json
{
  "convergence_achieved": true,
  "final_residuals": {"continuity": 1e-6, "energy": 1e-7},
  "mesh_info": {"quality_metrics": {"min_orthogonal_quality": 0.35, "max_skewness": 0.72, "aspect_ratio_max": 15.3}},
  "monitors": {"max_temperature_c": 87.5, "avg_temperature_c": 62.3, "pressure_drop_pa": 125.4, "energy_imbalance_percent": 1.2, "mass_imbalance_percent": 0.4}
}
```

---

## API 服务

### 启动服务

```bash
uvicorn app:app --reload --port 8000
```

### API 文档

访问：http://127.0.0.1:8000/docs

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 服务信息 |
| `GET` | `/llm/test_qwen` | 测试 Qwen 连接 |
| `POST` | `/cases/create` | 创建新案例 |
| `GET` | `/cases/{case_id}/state` | 获取案例状态 |
| `GET` | `/cases/{case_id}/decision_log` | 获取决策日志 |
| `POST` | `/pipeline/run_self_optimizing` | 运行自优化流程 |
| `POST` | `/feedback/engineer` | 提交工程师反馈 |
| `POST` | `/rules/mine_feedback` | 从反馈挖掘规则 |
| `POST` | `/regression/run` | 执行回归测试 |

### 使用示例

```bash
# 创建案例
curl -X POST http://localhost:8000/cases/create \
  -H "Content-Type: application/json" \
  -d '{"case_id": "my_project_001"}'

# 运行优化流程
curl -X POST http://localhost:8000/pipeline/run_self_optimizing \
  -H "Content-Type: application/json" \
  -d '{"case_id": "demo_001", "approved": true, "max_iterations": 5}'

# 查看状态
curl http://localhost:8000/cases/demo_001/state
```

---

## 自我优化闭环详解

### 内层循环（单 Case 迭代优化）

```
┌─────────────────────────────────────────────────────────────┐
│  Iteration Loop (max_iterations)                            │
│                                                             │
│  result_summary.json                                        │
│    ↓                                                        │
│  evaluate_result → 评估当前设计性能                         │
│    ↓                                                        │
│  optimization_context.json → 构建优化上下文                 │
│    ↓                                                        │
│  Qwen LLM → optimization_plan.json → 生成优化计划           │
│    ↓                                                        │
│  validate against optimization_rules.json → 规则校验        │
│    ↓                                                        │
│  config_modifier.py → 修改仿真配置                          │
│    ↓                                                        │
│  build_simulation_config_iterXXX.json                       │
│    ↓                                                        │
│  run_solver → 执行仿真                                      │
│    ↓                                                        │
│  extract_results → 提取结果                                 │
│    └─────────────────────────────────────────────────────────┘
```

### 外层循环（跨 Case 规则进化）

```
┌─────────────────────────────────────────────────────────────┐
│  Rule Evolution Loop                                        │
│                                                             │
│  engineer_feedback.jsonl                                    │
│    ↓                                                        │
│  rule_miner.py → candidate_rule_updates.json → 挖掘候选规则 │
│    ↓                                                        │
│  人工审查批准                                              │
│    ↓                                                        │
│  修改 rules/*.json → 规则上线                               │
│    ↓                                                        │
│  regression_runner.py → 回归测试验证                        │
│    ↓                                                        │
│  确认无退化 → 规则固化                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 规则体系说明

### 优化规则 (`optimization_rules.json`)

定义 AI 可执行的操作权限：

```json
{
  "design_levers": [
    {
      "name": "fan_speed",
      "type": "continuous",
      "min": 0.5,
      "max": 1.5,
      "risk_level": "low",
      "auto_apply": true
    },
    {
      "name": "heatsink_fin_count",
      "type": "integer",
      "min": 10,
      "max": 50,
      "risk_level": "medium",
      "auto_apply": false
    }
  ]
}
```

### 几何规则 (`geometry_rules.json`)

定义几何处理约束：

- 最小特征尺寸
- 允许简化类型
- 保留区域定义

### 健康检查规则 (`geometry_health_rules.json`)

清理后验证标准：

- 体积变化阈值
- 关键特征完整性
- 水密性检查

---


## 真实部署 Corner Cases 清单

面向真实 AI Agent 自动化仿真流水线，除 Demo 闭环外建议重点处理以下场景：

| 类别 | 需要防护的情况 | 当前防护/建议 |
|------|----------------|---------------|
| Case 输入 | API、队列或批处理传入 `../`、空字符串、超长 ID、跨平台非法文件名 | `case_id` 仅允许字母、数字、点、下划线、短横线，且必须以字母或数字开头 |
| 文件状态 | JSON 文件为空、损坏或不是对象；JSONL 日志中夹杂坏行 | JSON 读取会给出明确错误；JSONL 读取会保留坏行诊断，不阻断 API 查看日志 |
| 求解器集成 | 外部 Ansys 脚本超时、返回非零、未写结果、stdout 不是 JSON | 真实求解器适配层会持久化失败结果、更新状态并写决策日志 |
| 结果后处理 | 求解器缺失温度、网格质量或监控字段；数值字段为字符串/空值 | 后处理和评估会降级为 `failed`、`invalid_result` 或 `missing_result`，避免 KeyError 中断流水线 |
| 审批与风险 | 中高风险优化、真实 CAD 清理、真实求解资源消耗 | 保持审批门禁；生产环境建议接入 RBAC、配额和任务取消机制 |
| 并发运行 | 同一 case 被多个请求同时运行 | 当前目录结构可持久化状态；生产建议增加 case 级锁或任务队列避免并发写冲突 |
| 可观测性 | LLM 决策、工具输出、规则变更不可追溯 | `decision_log.jsonl` 和 `logs/global_decision_log.jsonl` 持续记录关键事件 |

## 输出产物

运行完成后，在 `cases/<case_id>/` 目录下生成：

| 目录/文件 | 说明 |
|-----------|------|
| `state/case_state.json` | 最终状态快照 |
| `state/decision_log.jsonl` | 完整决策日志 |
| `report/report.docx` | Word 格式报告 |
| `results/` | 各迭代结果文件 |
| `iterations/iter_XXX/` | 详细迭代数据 |
| `work/simulation_config_iterXXX.json` | 仿真配置历史 |

---

## 依赖说明

```txt
fastapi>=0.110.0        # Web 框架
uvicorn>=0.27.0         # ASGI 服务器
pydantic>=2.6.0         # 数据验证
python-dotenv>=1.0.1    # 环境变量管理
requests>=2.31.0        # HTTP 客户端
python-docx>=1.1.0      # Word 报告生成
matplotlib>=3.8.0       # 图表绘制
numpy>=1.26.0           # 数值计算
```

---

## 扩展开发

### 添加新工具

1. 在 `tools/` 目录创建新模块
2. 实现统一接口：`func(project_root: Path, case_id: str, **kwargs) -> Dict`
3. 在 `workflow/thermal_pipeline.py` 中集成

### 自定义规则

1. 参考 `rules/` 下现有规则格式
2. 在 `optimization_rules.json` 中添加新 design lever
3. 运行回归测试验证兼容性

### 集成真实求解器

1. 实现 `ANSYS_SOLVER_COMMAND` 指定脚本
2. 确保输入输出格式与 Mock 版本一致
3. 设置 `MOCK_ANSYS=false` 切换

---

## 版本历史

- **V4**: 自我优化闭环、规则挖掘、回归测试
- **V3**: 决策日志、状态机、规则校验
- **V2**: 几何健康检查、知识库
- **V1**: 基础流程框架

---

## License

MIT
