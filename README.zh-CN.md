# Metallocene EPDM Digital Twin

语言：[English](README.md) | **中文**

面向茂金属 EPM/EPDM 溶液聚合的工业研究软件，用于残差感知流程模拟、模型治理、报告生成和可复现实验验证。

当前正式版本：**V6.4 / 0.7.4**

V6.5 状态：**质量增强冲刺与数理严谨性审计记录，未作为正式版本升级**

仓库地址：[SUNHAOJUN22/metallocene-epdm-digital-twin](https://github.com/SUNHAOJUN22/metallocene-epdm-digital-twin)

---

## 1. 项目定位

本项目是一个基于 Streamlit 的数字孪生与科学软件工作台，面向茂金属 EPM/EPDM 及相关溶液聚合过程研究。

它用于支持：

- 带质量与能量残差检查的流程模拟；
- 反应器、闪蒸、热平衡、循环、物性和输运计算；
- 动态 ODE/DAE 诊断和稳定性检查；
- residual-aware 优化、DOE、posterior filtering 和不确定性评估；
- benchmark、data lineage、evidence chain 和 model confidence 治理；
- Excel、Word/PDF 方向报告以及复现实验包导出；
- 面向 Aspen Plus/HYSYS 的交换表、变量映射和结果对比辅助；
- 通过 UI 显式 action 触发重计算任务。

本项目不是黑盒生产 APC/DCS 控制器。它是研究与工程决策支持平台，强调审计轨迹、benchmark 边界和验证门禁。

---

## 2. 当前质量基线

V6.5 质量增强冲刺在 V6.4 / 0.7.4 正式基线上记录的最新结果为：

| 门禁 | 记录结果 |
| --- | --- |
| `pytest` | 361 passed |
| `auto_functional_audit` | 151/151 passed |
| `function_inventory_audit` | 1007/1007 public callable direct references |
| `release_gate` | passed |
| Streamlit | HTTP 200 |

详见：

- [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- [docs/QUALITY_BASELINE.md](docs/QUALITY_BASELINE.md)
- [docs/V6_5_MATH_RIGOR_AUDIT.md](docs/V6_5_MATH_RIGOR_AUDIT.md)
- [docs/V6_5_CHANGELOG.md](docs/V6_5_CHANGELOG.md)

---

## 3. 核心能力

### 流程与反应器建模

- EPDM/EPM 溶液聚合流程模拟
- 反应器动力学与聚合物物性预测
- 模板化 flowsheet 模拟
- 闪蒸、循环、溶解度、热平衡和输运计算
- CFD 方向辅助模块和可视化契约

### 数理内核

- 通过 dimensioned input 和 unit conversion trace 显式处理单位；
- finite、nonnegative、bounded 和 trend-aware 检查；
- 基于 ResidualSystem 的质量、组分、能量、flash、heat、recycle 和 dynamic residual 诊断；
- equation registry、equation binding、reverse check 和 equation-residual coupling；
- conservation correction、equation-oriented solver certificate 和 nonlinear residual loop audit。

### 动态与稳定性诊断

- dynamic template reactor；
- ODE/DAE state invariant 检查；
- adaptive step 和 event localization 诊断；
- quench、cooling failure、runaway risk 和 residual-triggered fallback 报告。

### 校准与证据治理

- experimental benchmark registry；
- benchmark source registry，置信等级为：
  `plant > experiment > literature > synthetic > regression_snapshot`
- data-lineage graph；
- evidence-chain score；
- model-confidence certificate；
- calibrated property model runtime 和 audit 层。

### 决策工作流

- residual-aware optimizer；
- residual-aware DOE；
- posterior residual filtering；
- uncertainty risk bounds；
- validation data gap recommendation。

### 报告与复现

- Excel 报告导出；
- Aspen 交换 sheets：stream import/export、variable mapping、unit context 和 reconciliation workflow；
- Word/PDF 方向报告辅助；
- reproducibility package manifest；
- report consistency check；
- residual、equation、benchmark、lineage、property model 和 governance certificate 快照。

---

## 4. 仓库结构

```text
.
├── app.py                         # Streamlit 应用入口
├── epdm_sim/                      # 运行时代码包
│   ├── math_core/                 # 方程、约束、残差抽象
│   ├── solver_core/               # 约束求解器、证书、残差迭代
│   ├── dynamic_core/              # ODE/DAE 策略、不变量、自适应诊断
│   ├── flowsheet_core/            # 物料/能量闭合与 flowsheet helper
│   ├── reactor_core/              # 反应器平衡、放热、聚合物矩
│   ├── fluid_core/                # 密度、热容、黏度、水力学
│   ├── mcp/                       # 受控 MCP-style tool 契约
│   ├── reporting/                 # Excel/PDF/Word 报告支持
│   └── pages/                     # Streamlit 页面模块
├── data/                          # registry、benchmark、模型与配置数据
├── docs/                          # 审计报告、质量记录、路线图
├── scripts/                       # 质量门禁、审计、测试和报告命令
├── tests/                         # 单元、集成、科学、UI 契约测试
└── requirements.txt               # 运行依赖
```

生成物、本地数据库、smoke artifacts、渲染图、日志和 Office 导出文件会被 Git 忽略。

---

## 5. 环境要求

- Python **3.11+**
- Windows、Linux 或 macOS
- 推荐使用独立虚拟环境

核心 Python 依赖见 [requirements.txt](requirements.txt) 和 [pyproject.toml](pyproject.toml)。

---

## 6. 安装

```powershell
git clone https://github.com/SUNHAOJUN22/metallocene-epdm-digital-twin.git
cd metallocene-epdm-digital-twin

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux/macOS：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 7. 运行应用

```powershell
python -m streamlit run app.py --server.headless true --server.port 8501
```

浏览器访问：

```text
http://127.0.0.1:8501/
```

UI 包含 dashboard、reactor、separation、heat/fluid、dynamic reactor、calibration、experiment data、sensitivity/optimization、model governance、report 和 workflow 页面。

重计算任务必须通过显式 UI action 和 TaskService mapping 启动。页面切换和报告导出不应自动触发 ODE、CFD、optimizer、posterior、DOE 或 uncertainty heavy task。

---

## 8. 质量门禁命令

运行环境检查：

```powershell
python scripts\dev_tasks.py check-env
```

运行完整测试：

```powershell
python -m pytest -q tests
```

运行功能与 inventory 审计：

```powershell
python scripts\auto_functional_audit.py
python scripts\function_inventory_audit.py
```

运行性能与 UI smoke 检查：

```powershell
python scripts\performance_profile.py
python scripts\ui_e2e_smoke.py
python scripts\ui_e2e_workflow.py
```

运行可执行的专业 skill 外围 QA：

```powershell
python scripts\dev_tasks.py professional-skill-qa
```

该命令检查适合由专业 workflow skill 接管的外围 artifact：Excel 报告结构、Word 报告内容、UI 契约 artifact 和 GitHub workflow readiness。它不会替代科学内核门禁。

MCP-style 集成契约也纳入同一个专业 skill QA：

```powershell
python scripts\dev_tasks.py professional-skill-qa
```

`epdm_sim/mcp/` 是面向未来科学 workflow / MCP / ChatGPT Apps 集成的 in-process、tool-only 边界。它默认 `dry_run=True`，要求显式 unit context，拒绝错误单位、NaN/inf、负绝对温度和 outside-validity 字段；heavy task 必须显式授权才允许执行。它不替代 ResidualSystem、flash/EOS、ODE/DAE、benchmark validation 或 release gate。

运行完整质量和发布门禁：

```powershell
python scripts\dev_tasks.py quality-gate
python scripts\dev_tasks.py generate-test-report
python scripts\dev_tasks.py continuous-improve
python scripts\release_gate.py
```

---

## 9. 科学验证契约

平台遵循以下工程契约：

- 所有核心输出必须 finite；
- 需要非负的物理量必须保持 nonnegative；
- pressure、temperature、density、viscosity、flow、risk probability 和 vapor fraction 必须 bounded；
- total mass、component mass、energy、flash、heat-balance、recycle 和 dynamic accumulation residual 必须 finite 并通过 acceptance；
- large residual 不能被 correction logic 掩盖；
- polymer vapor 被视为物理 critical，除非明确为零或有受控处理；
- optimizer、DOE、posterior 和 uncertainty 决策必须拒绝或强惩罚 residual-critical 和 outside-validity candidate；
- unit conversion 必须显式且可追踪。

数理运行时由仓库原生代码、benchmark、ResidualSystem、pytest、audit 和 release gate 验证。通用外部 skill 或视觉 QA 工具不能替代科学内核。

---

## 10. 数据与证据策略

Benchmark 和 calibration evidence 按来源置信度分级：

1. plant
2. experiment
3. literature
4. synthetic
5. regression_snapshot

关键 release evidence 应包含：

- `source_reference`
- `measurement_unit`
- `uncertainty`
- `validity_range`
- `data_hash`
- `confidence_level`
- `review_status`

超出适用范围或低置信 evidence 可用于回归和诊断，但不应提升为高置信 critical validation。

---

## 11. 报告与复现

报告和复现实验包应保留：

- residual snapshot；
- equation registry snapshot；
- model registry snapshot；
- benchmark source snapshot；
- data-lineage snapshot；
- calibrated property usage；
- unit conversion trace；
- solver certificate；
- governance 和 confidence artifact。

报告导出不得重新运行 heavy computation。缺失的 heavy-task 输出应写为 `not_run`，而不是静默重算。

---

## 12. 文档索引

主要文档：

- [docs/QUALITY_BASELINE.md](docs/QUALITY_BASELINE.md)
- [docs/TEST_REPORT.md](docs/TEST_REPORT.md)
- [docs/FUNCTION_MATRIX.md](docs/FUNCTION_MATRIX.md)
- [docs/UNIT_SYSTEM.md](docs/UNIT_SYSTEM.md)
- [docs/SCIENTIFIC_VALIDATION.md](docs/SCIENTIFIC_VALIDATION.md)
- [docs/QUALITY_GATES.md](docs/QUALITY_GATES.md)
- [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md)
- [docs/OPTIMIZATION_ROADMAP.md](docs/OPTIMIZATION_ROADMAP.md)
- [docs/CONTINUOUS_IMPROVEMENT_LOG.md](docs/CONTINUOUS_IMPROVEMENT_LOG.md)
- [docs/MCP_INTERFACE_DESIGN.md](docs/MCP_INTERFACE_DESIGN.md)
- [docs/MCP_TOOL_CONTRACT.md](docs/MCP_TOOL_CONTRACT.md)
- [docs/MCP_SAFETY_POLICY.md](docs/MCP_SAFETY_POLICY.md)
- [docs/ASPEN_INTEGRATION_GUIDE.md](docs/ASPEN_INTEGRATION_GUIDE.md)

详细生成/手册类文档：

- [README.md](README.md)
- [README_Manual_And_Tech.md](README_Manual_And_Tech.md)
- [README_Deep_Technical.md](README_Deep_Technical.md)
- [README_technical.md](README_technical.md)

---

## 13. 已知限制

- 部分 benchmark 仍属于 synthetic 或 regression-oriented 数据，进入高风险工程使用前应替换为 reviewed plant、experiment 或 literature evidence。
- 本项目是研究级数字孪生，不是认证过的工厂安全系统。
- 工业部署需要独立验证、网络安全审查、数据治理审查、HAZOP/LOPA 对齐和现场特定模型校准。
- 本地生成物和 SQLite 工作数据被有意排除在源码控制之外。
- 当前仓库尚未包含开源许可证文件。

---

## 14. 开发规则

贡献者应保持现有验证契约：

- 不通过删除测试来通过 gate；
- 不跳过失败检查；
- 没有记录清楚的工程理由，不放宽 residual severity 或 tolerance；
- 不掩盖 NaN、infinite、负物性或 critical residual；
- 不用通用工具替换运行时数学、物理或验证逻辑；
- 修改运行时行为或 release gate 时必须更新 changelog 和质量文档。
- 对适合专业 workflow skill 替换的 UI/report/GitHub artifact 检查，使用 `professional-skill-qa`。
- `epdm_sim.mcp` 只能作为受控外部 tool 边界；科学计算和 residual acceptance 仍保留在 repo-native gate 内。

推荐 pre-push 命令：

```powershell
python scripts\dev_tasks.py quality-gate
python scripts\release_gate.py
python scripts\dev_tasks.py professional-skill-qa
```

---

## 15. 路线图

近期优先级：

- 增加 reviewed plant/experiment/literature evidence 覆盖；
- 更真实的 plant/LIMS/ELN 数据接入；
- 继续对超大模块做 API 兼容拆分；
- 将 nonlinear residual loop 更深接入 recycle、flash 和 heat-balance solve path；
- 改善宽表审计报告的可读性；
- 为长时间科学 gate 增加可选 CI hardening。
- 围绕当前 in-process `epdm_sim.mcp` registry 增加生产级 MCP/ChatGPT Apps transport，包括 auth、schema discovery 和 hosted connector 审查。
- 增加基于现场批准 COM automation 和 reviewed plant data 的 Aspen Plus/HYSYS round-trip 示例。
