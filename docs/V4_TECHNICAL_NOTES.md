# V4 技术说明：实验可验证、参数可追溯、模型可信度可量化、结果可复现

## 架构

V4 保持 V3 的瘦身架构：`app.py` 只负责入口、导航、主题和 session 初始化；页面位于 `epdm_sim/pages/`；重计算服务位于 `epdm_sim/services/`；核心模型位于 `epdm_sim/` 和 `epdm_sim/cfd/`。

新增服务和数据层：

- `services/task_service.py`：按钮触发长任务的状态、耗时、缓存、错误记录。
- `db.py`：SQLite 本地数据仓库，保存实验、参数集、案例、模型运行、报告和CFD运行。
- `case_manager.py`：案例zip包新增 `manifest.json`。

## 真实模型拟合

`parameter_estimation.py` 的 `estimate_parameters()` 支持：

- `empirical_proxy`
- `flowsheet_real`
- `dynamic_ode_real`
- `hybrid`

`flowsheet_real` 使用 `run_flowsheet(config, kinetic_params_override=...)`；`dynamic_ode_real` 使用 `simulate_dynamic_semibatch_ode(config, params=...)`。失败样本不会中断拟合，会转为 `run_failures` 和惩罚残差。

## 热力学和溶解度

`eos.py` 新增 PR/SRK root、phi、K 输出：

- `cubic_z_roots()`
- `fugacity_coefficient()`
- `cubic_eos_details()`
- `k_value_comparison()`

`solubility.py` 从 `data/solubility_parameters.json` 读取 Henry 参数，并支持催化剂族修正和实验校准入口。

## Recipe动态釜式模型

`recipe.py` 定义 `RecipeStep` 和 `Recipe`，提供：

- 默认半连续recipe；
- DataFrame编辑；
- JSON导入/导出；
- event log；
- recipe到ODE配置映射。

`reactor.simulate_dynamic_semibatch_ode()` 输出气液组成、压力、jacket duty、controller output、C2/C3/ENB组成和event log，并支持quench事件快速终止催化剂活性。

## 不确定性和模型可信度

`uncertainty.py` 实现轻量 Monte Carlo / Latin Hypercube：

- 扰动 kinetic、deltaH、Henry/VLE proxy、viscosity、flash K；
- 输出 P05/P50/P95；
- 输出 tornado proxy；
- 输出冷却不足、挂胶、压降风险概率；
- 生成 model confidence card。

## CFD/OpenFOAM

新增：

- `cfd/boundary.py`
- `CFDFields.dead_zone_mask`
- `CFDFields.high_fouling_mask`
- `run_pipe_fvm_solver()`
- VTK导出 masks；
- OpenFOAM `0/C` 和 `system/controlDict.scalarTransportFoam`。

## 验收

V4 当前验收：

```text
python -m py_compile app.py epdm_sim/**/*.py -> passed
python -m pytest -> 69 passed
```

## 局限

V4 强化了可验证和可追溯框架，但真实工程设计仍需：

- 真实VLE/溶解度实验；
- 反应量热；
- H2链转移DOE；
- 在线热流/温度/压力/投料时间序列；
- 聚合物胶液流变；
- 真实反应釜/桨叶几何；
- OpenFOAM/Fluent 3D验证。
