# V4.3 全项目深度审计

## 1. 当前项目结构

主项目目录为 `D:\codex\metallocene-epdm-digital-twin`。核心结构包括：

- `app.py`：Streamlit薄入口，负责会话初始化、导航、主题、全局快速输入和性能诊断。
- `data/`：组件物性、默认工艺、实验数据、参数集、模型注册表、工程规则和反应模板。
- `epdm_sim/`：过程模拟、热力学、反应器、热量衡算、流体性质、CFD、参数估计、报告、治理层模块。
- `epdm_sim/pages/`：页面渲染层。
- `epdm_sim/services/`：任务状态、缓存和仿真服务。
- `tests/`：单元测试、趋势测试、报告/应用 smoke 测试。
- `docs/`：合并说明、版本技术说明和本审计文件。

## 2. 主项目与 legacy_archive 关系

`metallocene-epdm-process-simulator` 已物理合并到：

`D:\codex\metallocene-epdm-digital-twin\legacy_archive\metallocene-epdm-process-simulator`

当前唯一运行入口是 `metallocene-epdm-digital-twin/app.py`。legacy archive 只作为基线源码和历史追溯，不再作为独立运行项目维护。

## 3. 核心模型清单

- 流程模拟：`flowsheet.py`
- 稳态/动态反应器：`reactor.py`, `dynamic_reactor.py`, `recipe.py`
- 动力学：`kinetics.py`
- 热力学/闪蒸：`thermo.py`, `eos.py`, `solubility.py`, `flash.py`
- 热量衡算：`heat_balance.py`
- 流体性质/流变/压降：`fluid_props.py`
- 产品性能：`polymer_props.py`
- 回收循环：`recycle_solver.py`
- 安全：`safety.py`
- CFD/OpenFOAM：`epdm_sim/cfd/*`
- 参数估计/校准：`calibration.py`, `parameter_estimation.py`
- 实验数据/数据库/案例：`experiment_data.py`, `db.py`, `case_manager.py`
- 优化/不确定性：`optimizer.py`, `pareto.py`, `uncertainty.py`
- V4.3治理层：`conservation.py`, `engineering_rules.py`, `io_schema.py`, `numerics.py`, `ui_workflow.py`, `ui_audit.py`, `model_confidence.py`, `reaction_templates.py`

## 4. 每个模型的数理假设

- 所有物料流量为非负有限数。
- 所有分率、转化率和气相分率有界在物理范围内。
- 聚合放热输出为正的移热需求，反应热参数按负值输入。
- Rachford-Rice 闪蒸求解结果必须给出 `0 <= V <= 1`。
- ODE、优化器和CFD失败时必须返回警告或 fallback，而不是让 UI 崩溃。
- V4.3 新增 `numerics.py` 用于统一 finite、bounded、safe log/exp/power 和 KPI 有限性检查。

## 5. 每个模型的化工假设

- 单体消耗质量应闭合到聚合物段质量。
- 乙烯/丙烯/ENB生成 E/P/D 聚合段。
- 聚合物伪组分在闪蒸中保持液相/产品相，不进入气相。
- 氢气作为链转移剂，增加时 Mw 和门尼不应升高。
- 低压约 0.7 MPa 有利于 ENB 结合，高压 2 MPa 不应异常提高 ENB 引入。
- 固含量、Mw 升高提高黏度；温度升高降低黏度。
- 管径减小或流量增加提高压降。

## 6. 输入/输出/单位

V4.3 新增 `io_schema.py`，为 active model registry 模块声明：

- 输入名称、单位、类型、范围、必填性；
- 输出名称、单位、物理边界；
- 可导出为 Excel `io_schema` sheet。

典型单位包括 `kg/h`, `mol/h`, `mol/L`, `Pa`, `MPa`, `K`, `degC`, `kJ/h`, `kW`, `wt%`, `fraction`。

## 7. 当前守恒检查覆盖情况

新增 `conservation.py` 覆盖：

- 总物料衡算；
- 乙烯/丙烯/ENB/H2/溶剂组分闭合；
- 单体消耗质量与聚合物生成质量；
- E/P/D 聚合段质量和；
- Flash-1/Flash-2 单元质量闭合；
- 聚合放热与单体消耗量；
- 产品 C2+C3+ENB 组成闭合；
- 回收循环闭合。

## 8. 当前趋势检查覆盖情况

新增 `engineering_rules.py` 与 `data/engineering_rules.json`，默认规则包括：

1. H2增加 -> Mw下降；
2. H2增加 -> Mooney下降；
3. 固含增加 -> 黏度增加；
4. 温度升高 -> 黏度下降；
5. Mw增加 -> 黏度增加；
6. 管径减小 -> 压降增加；
7. 流量增加 -> 压降增加；
8. 单体消耗增加 -> Q_rxn增加；
9. 闪蒸压力降低 -> vapor fraction增加；
10. polymer pseudo-component 不进入气相；
11. 高压不异常提高 ENB 引入；
12. ENB进料增加 -> 产品ENB wt%上升；
13. Al/Ti过低 -> 产率下降；
14. BHT不能导致负活性；
15. 产品组成和为100 wt%。

## 9. UI点击触发路径

新增 `ui_workflow.py`，注册所有关键动作：

- 快速流程模拟：`auto_cached`
- ODE、CFD、优化、Pareto、参数估计、不确定性、工程规则：`button_manual`
- Excel/Word/OpenFOAM导出：`export`
- 案例加载/保存：`data_import` 或 `button_manual`

UI 诊断面板显示 action registry 摘要，避免页面切换触发重任务。

## 10. 重计算路径

重任务统一通过 `TaskService` 记录：

- task_id
- input_hash / dependency_hash
- status
- runtime
- cache_hit
- stale_reason
- last_error

V4.3 在 task graph 中新增 `engineering_rules` 和 `conservation`。

## 11. 存在的硬编码点

- EPDM 默认 E/P/D segment map 仍主要在 `reactor.py` 内使用。
- 默认聚合热、ENB压力修正和门尼经验模型仍为 EPDM 特化参数。
- CFD 反应釜几何和流场仍为二维/准三维工程可视化模型。
- V4.3 新增 `reaction_templates.py` 作为逐步去硬编码接口，尚未全量重构动力学内核。

## 12. 仍需实验校准的数据

- 催化剂族特异的 kE/kP/kENB、Ea、kd；
- 低压/高压 ENB 引入与转化率；
- H2 液相浓度与 Mw/PDI/门尼；
- 聚合热和绝热温升中试数据；
- 不同固含/Mw/温度下胶液流变；
- Flash 残留 ENB/溶剂实测；
- 搅拌功率、kLa、U 值和挂胶位置数据；
- CFD真实几何、桨型、挡板和壁面剪切验证数据。

## 13. 下一轮开发优先级

1. 将 `reaction_templates.py` 与 `kinetics.py/reactor.py/heat_balance.py` 做更深的模板化耦合；
2. 用真实实验数据校准 Henry、EOS kij、黏度和动力学参数；
3. 将 engineering rules 扩展为按催化剂族和溶剂族分组；
4. 将动态 ODE 与实验时间序列自动对齐；
5. 增强 CFD 网格和OpenFOAM reactor case可运行性；
6. 引入更严格的质量/能量闭合误差分级和校正建议。
