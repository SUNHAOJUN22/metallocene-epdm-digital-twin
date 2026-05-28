# Metallocene EPDM Digital Twin - 功能与技术报告

## 1. 软件定位与核心目标
`metallocene-epdm-digital-twin` 是一款本地可运行的研发级茂金属 EPM/EPDM 溶液聚合工艺仿真与数字孪生平台。
主要应用于：
- 乙烯/丙烯/ENB 在烷烃/芳烃溶剂中的茂金属催化溶液聚合研发
- 趋势判断、实验设计 (DOE)、参数校准、牌号反推
- 工艺窗口筛选、热安全筛查、CFD 可视化与报告归档

## 2. 核心架构与功能模块
系统采用分层架构，底层由严谨的数理内核驱动，上层提供 Streamlit 的交互式 Web UI。核心模块包括：

### 2.1 反应与动态仿真 (Reactor & Dynamic Core)
- **动态反应器 (Dynamic Reactor)**: 支持批次 (Batch)、半连续 (Semi-batch)、CSTR 及 CSTR 串联模式的动态聚合过程模拟。
- **自适应积分与事件检测**: 包含 DAE (微分代数方程) 约束处理、基于残差的步长接受策略 (residual-based step acceptance) 和异常事件定位。

### 2.2 流程与热力学 (Flowsheet & Fluid Core)
- **相平衡与物性**: 支持闪蒸分离 (Flash)、流变学计算 (Rheology)、以及 VLE 相平衡计算。包含校准后的亨利常数 (Henry)、黏度和蒸发焓模型。
- **守恒与平衡 (Conservation)**: 实现严谨的质量、能量守恒闭合，包含回流求解器 (Recycle Solver) 和热量平衡。

### 2.3 求解器与数理内核 (Solver & Math Core)
- **方程导向求解 (Equation-Oriented Solver)**: 使用基于雅可比矩阵和有界牛顿步长的小残差闭合技术，提供守恒方程的可审计闭环。
- **残差感知决策引擎**: 优化器 (Optimizer)、参数估计 (Parameter Estimation)、贝叶斯 DOE (Bayesian DOE) 和后验过滤 (Posterior Filter) 直接与残差系统耦合，拒收高物理误差（如物料不守恒）的求解点。
- **量纲安全 (Dimensioned)**: 强类型的单位转换（如 MPa/Pa, °C/K），在传入计算内核前确保物理量的量纲一致性。

### 2.4 数据同化与可信度 (Data & Governance)
- **工业数据包与校准**: 引入真实工厂、实验与文献的数据同化，具有完整的溯源图 (Data Lineage Graph)。
- **模型可信度证书 (Confidence Certificate)**: 为每次求解生成多维度打分的证书，验证方程、残差、工业证据和校准物性的置信度。

### 2.5 用户界面与可视化 (UI & CFD)
- **Streamlit 可视化仪表盘**: 包含数字孪生总览、聚合工艺时序、反应器动力学、分离脱挥、敏感性分析等多个交互子页面。
- **CFD 场分布与 3D 设备**: 基于 PyVista 或 Plotly 的 3D 反应器布局展示与简化 CFD 场分布可视化。
- **导出与自动化报告**: 支持 Excel 快照与 Markdown 测试总结导出。

## 3. 技术栈
- **语言**: Python 3
- **前端/UI**: Streamlit
- **数值与科学计算**: NumPy, SciPy, Pandas
- **3D 与可视化**: Plotly
- **文档生成**: python-docx, Pytest
- **测试与质量保证**: 包含了基于 AST 的函数引用扫描 (function_inventory_audit) 和自动功能审查 (auto_functional_audit)。

## 4. 总结
Metallocene EPDM Digital Twin 不仅仅是一个简单的流程模拟器，而是一个内建“严谨数学边界”、“实验数据闭环”与“工业审计追溯”的现代研发工具。它通过引入严格的残差门禁和自动适应算法，确保了数字孪生模拟结果不仅在数值上收敛，同时在物理与工程意义上高度真实与安全。