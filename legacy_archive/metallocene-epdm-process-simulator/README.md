# metallocene-epdm-process-simulator

> **合并状态：已合并到 `metallocene-epdm-digital-twin`。**
>
> 当前文件夹已物理迁入主项目，作为兼容入口和历史归档。主项目、主README、测试和后续开发均位于：
>
> ```text
> D:\codex\metallocene-epdm-digital-twin
> ```
>
> 原始早期 Streamlit 应用已保存在 `legacy_app.py`。当前 `app.py` 是兼容启动器，会转到统一的 digital twin 主应用。

本项目是一个本地可运行的“茂金属乙丙橡胶 EPDM/EPM 溶液聚合工艺仿真软件 MVP”。它用 Python + Streamlit 实现，用于模拟乙烯、丙烯、ENB 在溶剂中经茂金属催化剂进行溶液聚合的流程，并输出转化率、聚合热、胶液固含量、Mw/PDI/门尼估算、Tg/Tm、闪蒸回收、挂胶风险和优化建议。

## 安装方法

```bash
cd D:\codex\metallocene-epdm-digital-twin
pip install -r requirements.txt
```

## 运行方法

```bash
cd D:\codex\metallocene-epdm-digital-twin
streamlit run app.py
```

兼容方式：

```bash
cd D:\codex\metallocene-epdm-digital-twin\legacy_archive\metallocene-epdm-process-simulator
streamlit run app.py
```

上述兼容命令会自动启动 `metallocene-epdm-digital-twin` 的统一主应用。

如需查看早期MVP归档版本：

```bash
streamlit run legacy_app.py
```

## 模型范围

- 原料区：乙烯、丙烯、ENB、氢气、溶剂、催化剂、MAO、BHT。
- 单元操作：Mixer、Preheater、Batch/CSTR/串联 CSTR、Quench、两级 Flash、简化 Recycle/Purge。
- 结果：单体转化率、聚合物产率、产品组成、热负荷、固含量、Mw/Mn/PDI、门尼、Tg/Tm、ENB 残留、回收物流和挂胶风险。
- 热量与流体性质：反应热、预热/脱挥负荷、绝热温升、夹套移热裕度、混合物密度、Cp、黏度、导热系数、管路压降和泵功率。
- CFD/FEM风格可视化：二维/准三维速度场、流线、温度场、ENB浓度场、固含场、黏度场、挂胶风险场、压降和OpenFOAM case导出。
- 分析：单变量/双变量敏感性分析、目标牌号优化、Excel/PDF/Word 报告导出。

## 模型假设

- 聚合反应采用表观动力学：`r_i = k_i(T) * C_i * Cstar`。
- `Cstar` 由催化剂投料、Al/Ti、BHT 和失活项估算。
- ENB 插入受到压力和乙烯竞争插入的经验修正。
- 氢气作为链转移剂主要影响 Mw，不直接改变单体消耗。
- 闪蒸默认采用 Wilson K 值和 Rachford-Rice 方程。
- 流体物性来自 `data/components.json` 的默认工程估算值，可在 UI 中编辑；黏度模型可用 `data/fluid_property_calibration.csv` 的实测数据校准。
- 聚合物性能采用经验模型和内部实验数据回归，适合趋势判断。

## 如何添加新实验数据

把新的实验行追加到：

```text
data/internal_experiments.csv
```

字段保持为：

```text
run_id, ep_ratio, ethylene_g, propylene_g, enb_ml, polymer_g, activity_1e7_g_mol_h, mooney, Mw, PDI, C2_wt, C3_wt, ENB_wt, Tg_C, Tm_C
```

应用启动时会读取该文件并尝试回归门尼模型参数和 ENB feed-product 经验关系。缺失值可以留空。

## 如何校准动力学参数

动力学参数位于：

```text
epdm_sim/kinetics.py
```

重点校准：

- `k_E_ref`, `k_P_ref`, `k_ENB_ref`
- `Ea_E_J_mol`, `Ea_P_J_mol`, `Ea_ENB_J_mol`
- `kd_h`
- `beta_P`, `beta_E`
- `ktr_H2`, `Mw0`

建议以实验转化率、产品 C2/ENB wt%、聚合物产率和 Mw/门尼为目标，先固定热力学模型，再逐步回归动力学参数。

## 如何导出报告

在 Streamlit 的“报告导出”页面点击：

- “导出 Excel”：包含物流表、单元操作结果、反应器剖面、闪蒸分配、敏感性和优化结果。
- “导出 PDF 报告”：包含输入条件、关键结果、工艺建议和模型假设。
- “导出 Word 报告”：包含热量衡算、流体性质、压降泵送、模型假设和数据缺口。

## 热量衡算与流体性质

核心模块：

```text
epdm_sim/heat_balance.py
epdm_sim/fluid_props.py
```

默认聚合反应热：

```text
ethylene -95 kJ/mol
propylene -85 kJ/mol
ENB -80 kJ/mol
```

可在“热量衡算与流体性质”页面修改反应热、U、A、冷却介质温度和管路参数。页面同时给出温度/固含/Mw 对黏度的影响、反应温度对热负荷的影响、停留时间对固含的影响、Flash 压力对回收量的影响。

## CFD有限元流场仿真

核心模块：

```text
epdm_sim/cfd/
  mesh.py
  simple_solver.py
  fem_solver.py
  fields.py
  transport.py
  fouling.py
  visualization.py
  openfoam_export.py
```

第一版采用内置 Simple CFD 模式，不依赖大型外部求解器。FEniCSx/dolfinx 如果不可用会自动降级。页面可展示管道、反应釜截面和环隙的网格、速度矢量、流线、温度云图、ENB浓度云图、固含云图、黏度云图、挂胶风险云图和准三维表面图。

OpenFOAM 导出会生成 case skeleton，包括 `system/controlDict`、`system/fvSchemes`、`system/fvSolution`、`system/blockMeshDict`、`constant/transportProperties`、`constant/thermophysicalProperties`、`0/U`、`0/p`、`0/T` 和 `0/C_ENB`。导出的 case 是工业CFD起点，仍需用真实几何、流变、湍流模型和边界条件校准。

## 局限性

该软件是研发级模拟工具，不可直接替代 Aspen Plus、Polymer Plus 或工业设计包。当前模型对聚合物溶液热力学、ENB 活度、高压气液平衡、传热传质、搅拌、黏弹性、凝胶和真实回收循环均做了简化。结果应主要用于研发趋势判断、实验设计和工艺窗口筛选。
