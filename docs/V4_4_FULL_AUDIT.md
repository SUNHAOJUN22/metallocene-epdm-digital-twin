# V4.4 全项目审计

## 1. 模型模板化程度

V4.4 已将 `data/reaction_templates.json` 从纯元数据升级为默认模型执行参数来源：

- `reactor.py` 的默认 monomer 列表和 segment map 来自 `reaction_templates.py`。
- `heat_balance.py` 的默认 `deltaH_polymerization` 来自默认反应模板。
- `conservation.py` 的 segment balance 支持按模板读取 segment map。

当前默认模板仍为 `EPDM_EPM_metallocene_solution`，因此默认 EPDM/EPM 行为不变。通用模板 `generic_solution_copolymerization` 和 `generic_terpolymerization_apparent` 已可加载，但尚未声明为完整可运行工业模型。

## 2. 当前硬编码点

仍存在的 EPDM 特化点：

- `kinetics.py` 的速率对象仍以 `r_E/r_P/r_ENB` 为主；
- `reactor.py` 的产品组成输出仍使用 `ethylene_wt/propylene_wt/ENB_wt` 字段；
- `polymer_props.py` 的 Mooney/Tg/Tm 经验模型仍按 EPDM 组成定义；
- CFD 中的黏度、挂胶和反应热源仍按 EPDM 胶液经验模型解释。

V4.4 通过模板接口减少硬编码入口，但未把全部属性模型改为任意单体体系。

## 3. 前置/后置校验覆盖

前置校验：

- 新增 `preflight.py`。
- `simulation_service.py` 在快速 flowsheet 运行前调用 `run_preflight_for_flowsheet()`。
- `TaskService.run()` 支持可选 `preflight` 参数，失败时记录任务失败并阻止重任务执行。

后置校验：

- `conservation.py` 做质量、组分、反应器、Flash、热量、组成和回收闭合。
- `engineering_checks.py` 做流程级工程逻辑检查。
- `engineering_rules.py` 做趋势规则检查。
- `thermo_consistency.py` 做 EOS/Henry/Flash 逻辑检查。
- `dynamic_stability.py` 做 ODE profile 非负、温度边界、聚合物非下降和淬灭/失活检查。

## 4. 当前数理风险点

- 参数估计和辨识性仍使用工程 proxy，真实 Fisher 信息矩阵需要更多实验样本。
- PR/SRK EOS 已有 Z/phi/K 诊断，但仍不是严格多组分相平衡包。
- 动态 ODE 有非负保护和 fallback，但 pressure-control/headspace 仍为简化。
- 反应模板接口支持通用加载，但真实通用速率律执行仍需后续抽象。

## 5. 当前化工逻辑风险点

- 低压有利 ENB 引入、高压抑制 ENB 的规律来自现有实验/PDF规则，需要更大压力窗口数据验证。
- H2-Mw/门尼趋势可检查，但 H2液相浓度与真实链转移常数尚需实测校准。
- 胶液黏度、压降、挂胶风险仍基于经验模型，需高固含/高门尼流变数据。
- Flash 对 ENB活度、聚合物溶液非理想性和高压气液平衡仍简化。

## 6. UI点击路径风险

V4.4 保留 V4.3 的 UI action registry：

- `flowsheet_fast` 可缓存自动刷新；
- ODE、CFD、优化、Pareto、参数估计、不确定性、工程规则必须按钮触发；
- 导出动作读取已有结果，缺失重任务写“未运行”或表格摘要。

新增 `preflight` 后，明显非法输入会在模型运行前被拦截。`ui_audit.py` 继续扫描页面是否存在未受控重任务调用。

## 7. 参数可辨识性与DOE

新增：

- `identifiability.py`：有限差分敏感度、参数相关性、condition number、弱可辨识参数标记。
- `doe_optimal.py`：推荐下一批实验点，并过滤冷却裕度不足或挂胶风险过高的不可行点。

重点规则：

- `beta_P` 需要压力梯度；
- `beta_E` 需要 C_E/C_ENB 梯度；
- `ktr_H2` 需要 H2 梯度；
- `kd_h` 需要时间/停留时间梯度。

## 8. 下一步实验校准优先级

1. 0.7、1.0、2.0 MPa 压力梯度下 ENB 引入率和ENB残留；
2. H2 梯度下 Mw/PDI/门尼；
3. ENB 梯度和乙烯富集窗口下的 beta_E 竞争插入；
4. 不同 Al/Ti 与 BHT 条件下的活性和分子量；
5. 2L/5L 下 P/V、kLa、U、挂胶风险和门尼偏移；
6. Flash ENB/溶剂残留和溶剂回收率；
7. 高固含胶液流变曲线和壁面剪切/挂胶数据。
