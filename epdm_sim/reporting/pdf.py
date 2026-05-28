"""PDF report export module."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from ..conservation import run_conservation_checks
from ..engineering_checks import run_engineering_checks
from ..model_confidence import build_model_confidence_card
from ..posterior import PosteriorResult
from ..cfd.grid_convergence import CFDGridConvergenceResult
from .render_helpers import _append_pdf_figures, _table


def export_pdf_report(
    result,
    sensitivity_df: pd.DataFrame | None = None,
    optimization: Any | None = None,
    calibration: Any | None = None,
    doe_df: pd.DataFrame | None = None,
    scaleup_df: pd.DataFrame | None = None,
    figures: dict[str, Any] | None = None,
    parameter_estimation: Any | None = None,
    dynamic_semibatch_df: pd.DataFrame | None = None,
    case_comparison: pd.DataFrame | None = None,
    recycle_solver: Any | None = None,
    safety: Any | None = None,
    pareto_df: pd.DataFrame | None = None,
    uncertainty: Any | None = None,
    model_confidence: dict[str, Any] | pd.DataFrame | None = None,
    recipe_df: pd.DataFrame | None = None,
    task_log: pd.DataFrame | None = None,
    manifest: dict[str, Any] | None = None,
    calibration_loop_result: Any | None = None,
    model_audit: Any | None = None,
    posterior: PosteriorResult | None = None,
    constrained_windows: pd.DataFrame | None = None,
    audit_records: Any | None = None,
    workflow_df: pd.DataFrame | None = None,
    cfd_grid_convergence: CFDGridConvergenceResult | pd.DataFrame | None = None,
) -> bytes:
    """Build a compact PDF report with assumptions, inputs and key results."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase import pdfmetrics
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    base = ParagraphStyle("cn", parent=styles["BodyText"], fontName="STSong-Light", fontSize=9, leading=13)
    title = ParagraphStyle("title", parent=styles["Title"], fontName="STSong-Light", fontSize=16)
    story = [Paragraph("茂金属乙丙橡胶 EPDM/EPM 溶液聚合工艺仿真报告", title), Spacer(1, 0.3 * cm)]
    cfg = result.config
    story.append(Paragraph("输入条件", base))
    inputs = [
        ["反应温度/°C", f"{cfg.temperature_C:.1f}", "反应压力/MPa", f"{cfg.pressure_MPa:.2f}"],
        ["乙烯 kg/h", f"{cfg.ethylene_kg_h:.2f}", "丙烯 kg/h", f"{cfg.propylene_kg_h:.2f}"],
        ["ENB kg/h", f"{cfg.enb_kg_h:.2f}", "氢气 g/h", f"{cfg.hydrogen_g_h:.2f}"],
        ["溶剂", cfg.solvent, "停留时间/min", f"{cfg.residence_time_min:.1f}"],
    ]
    story.append(_table(inputs))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("关键结果", base))
    k = result.kpis
    outputs = [
        ["聚合物 kg/h", f"{k['polymer_kg_h']:.3f}", "固含 wt%", f"{k['solids_wt']:.2f}"],
        ["C2 wt%", f"{k['C2_wt']:.2f}", "ENB wt%", f"{k['ENB_wt']:.2f}"],
        ["Mw", f"{k['Mw']:.0f}", "PDI", f"{k['PDI']:.2f}"],
        ["门尼 ML(1+4)", f"{k['Mooney']:.1f}", "Tg/°C", f"{k['Tg_C']:.1f}"],
        ["反应热负荷/kW", f"{k['heat_duty_kW']:.2f}", "绝热温升/K", f"{k['deltaT_ad_K']:.1f}"],
        ["预热/脱挥负荷 kW", f"{k['preheat_kW']:.2f} / {k['devol_duty_kW']:.2f}", "总冷却负荷/kW", f"{k['total_cooling_load_kW']:.2f}"],
        ["黏度/Pa.s", f"{k['dynamic_viscosity_Pa_s']:.4g}", "挂胶风险", str(k["fouling_risk"])],
        ["压降/kPa", f"{k['pipe_pressure_drop_kPa']:.2f}", "泵功率/kW", f"{k['pump_power_kW']:.3f}"],
        ["ENB残留/ppm", f"{k['ENB_residue_ppm']:.0f}", "最佳牌号", f"{k['best_grade']} ({k['best_grade_score']:.1f})"],
    ]
    story.append(_table(outputs))
    story.append(Spacer(1, 0.25 * cm))
    story.append(Paragraph("工艺优化建议", base))
    for rec in k["recommendations"]:
        story.append(Paragraph(f"- {rec}", base))
    story.append(Paragraph("3D装置与CFD：交互式报告页面包含3D装置总览、聚合釜、闪蒸/脱挥系统、产品罐和CFD剖面云图；静态PDF保留关键诊断摘要。", base))
    story.append(Paragraph(f"美孚/内部目标牌号对标：最佳匹配为 {k['best_grade']}，匹配分数 {k['best_grade_score']:.1f}。", base))
    engineering_checks = run_engineering_checks(result)
    failed_checks = [check for check in engineering_checks if not check.passed]
    story.append(Paragraph(f"工程逻辑检查：{len(engineering_checks) - len(failed_checks)}/{len(engineering_checks)} 项通过。", base))
    conservation_checks = run_conservation_checks(result)
    conservation_failed = [check for check in conservation_checks if not check.passed]
    confidence_card = build_model_confidence_card(result, engineering_checks=engineering_checks, conservation_results=conservation_checks)
    story.append(Paragraph(f"守恒闭合：{len(conservation_checks) - len(conservation_failed)}/{len(conservation_checks)} 项通过。", base))
    story.append(Paragraph(f"模型可信度综合评分：{confidence_card.overall_score:.1f}/100。", base))
    story.append(Paragraph("模板化动力学和产品性能模型：Excel报告记录 reaction template、kinetics_template 与 property_model；PDF保留摘要。", base))
    story.append(Paragraph("参数估计-不确定性-DOE闭环：若未手动运行，报告标记为未运行，不主动触发ODE/CFD/优化。", base))
    story.append(Paragraph("流变模型与Flash诊断：Excel报告记录rheology模型、flash_diagnostics和模型审计表。", base))
    if sensitivity_df is not None and not sensitivity_df.empty:
        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph(f"敏感性分析已导出 {len(sensitivity_df)} 条计算结果。", base))
    if optimization is not None:
        story.append(Paragraph(f"优化目标牌号 {optimization.grade_id}，匹配分数 {optimization.score:.1f}。", base))
    if calibration is not None:
        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph("模型校准摘要", base))
        story.append(_table([["target", "R2", "MAE"]] + calibration.metrics_dataframe().round(4).astype(str).values.tolist()))
    if doe_df is not None and not doe_df.empty:
        story.append(Paragraph(f"DOE推荐已导出 {len(doe_df)} 条实验建议，覆盖温度、压力、ENB、E/P、Al/Ti、BHT、H2和rpm。", base))
    if scaleup_df is not None and not scaleup_df.empty:
        story.append(Paragraph("2L/5L放大相似结果已导出，重点关注P/V、kLa、U、Mw/PDI偏移和挂胶风险。", base))
    if parameter_estimation is not None:
        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph("非线性参数估计", base))
        story.append(_table([["target", "R2", "MAE"]] + parameter_estimation.metrics_dataframe().round(4).astype(str).values.tolist()))
    if dynamic_semibatch_df is not None and not dynamic_semibatch_df.empty:
        story.append(Paragraph(f"动态釜式ODE模拟已导出 {len(dynamic_semibatch_df)} 个时间点。", base))
    if case_comparison is not None and not case_comparison.empty:
        story.append(Paragraph(f"案例对比已导出 {len(case_comparison)} 条差异记录。", base))
    recycle = recycle_solver or getattr(result, "recycle_solver", None)
    if recycle is not None:
        story.append(Paragraph(f"回收循环收敛：{recycle.convergence_iterations} 次迭代，闭合误差 {recycle.closure_error:.3g} kg/h。", base))
    if safety is not None:
        story.append(Paragraph(f"热安全筛查：风险 {safety.runaway_risk_level}，MTSR-like {safety.MTSR_like_C:.1f} °C。", base))
    if pareto_df is not None and not pareto_df.empty:
        story.append(Paragraph(f"多目标Pareto工艺窗口：已筛选 {len(pareto_df)} 个可行窗口，详见Excel或交互页面。", base))
    if uncertainty is not None:
        story.append(Spacer(1, 0.25 * cm))
        story.append(Paragraph("模型可信度与不确定性", base))
        story.append(_table([["risk", "probability"]] + [[k, f"{v:.3f}"] for k, v in uncertainty.risk_probabilities.items()]))
    elif model_confidence is not None:
        story.append(Paragraph("模型可信度摘要已导出到Excel。", base))
    if manifest is not None:
        story.append(Paragraph(f"案例Manifest：app_version={manifest.get('app_version')}，config_hash={manifest.get('config_hash')}。", base))
    figure_notes = _append_pdf_figures(story, figures or {}, Image, base)
    for note in figure_notes:
        story.append(Paragraph(note, base))
    story.append(Spacer(1, 0.25 * cm))
    story.append(
        Paragraph(
            "模型假设与局限性：本软件是研发级表观模型，不是工业设计包；动力学参数需要更多实验数据校准；"
            "热力学模型对聚合物溶液、ENB活度和高压气液平衡做了简化；流体物性默认值为工程估算，"
            "黏度、导热和密度需要实测数据补充校准；结果用于研发趋势判断、实验设计和工艺窗口筛选。",
            base,
        )
    )
    doc.build(story)
    return buffer.getvalue()
