"""Plotly visualization helpers for CFD/FEM-style results."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from .simple_solver import SimpleCFDResult


FIELD_LABELS = {
    "velocity": "速度 |u| m/s",
    "pressure": "压力 Pa",
    "temperature": "温度 °C",
    "ethylene": "乙烯浓度 mol/m3",
    "propylene": "丙烯浓度 mol/m3",
    "ENB": "ENB浓度 mol/m3",
    "hydrogen": "氢气浓度 mol/m3",
    "r_E": "r_E mol/m3/s",
    "r_P": "r_P mol/m3/s",
    "r_ENB": "r_ENB mol/m3/s",
    "r_total": "总聚合速率 mol/m3/s",
    "solids": "聚合物固含 wt%",
    "viscosity": "黏度 Pa.s",
    "fouling": "挂胶风险指数",
    "wall_shear": "壁面剪切应力 Pa",
    "dead_zone_mask": "死区mask",
    "high_fouling_mask": "高挂胶mask",
}


def mesh_plot(result: SimpleCFDResult) -> go.Figure:
    """Return a structured mesh plot."""
    mesh = result.mesh
    fig = go.Figure()
    step_x = max(len(mesh.x) // 20, 1)
    step_y = max(len(mesh.y) // 12, 1)
    for i in range(0, mesh.X.shape[0], step_y):
        fig.add_trace(go.Scatter(x=mesh.X[i, mesh.mask[i, :]], y=mesh.Y[i, mesh.mask[i, :]], mode="lines", line=dict(color="#cbd5e1", width=1), showlegend=False))
    for j in range(0, mesh.X.shape[1], step_x):
        fig.add_trace(go.Scatter(x=mesh.X[mesh.mask[:, j], j], y=mesh.Y[mesh.mask[:, j], j], mode="lines", line=dict(color="#cbd5e1", width=1), showlegend=False))
    fig.update_layout(height=330, title="CFD网格 mesh", xaxis_title="x / m", yaxis_title="y / m", margin=dict(l=10, r=10, t=45, b=10))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def contour_plot(result: SimpleCFDResult, field_name: str) -> go.Figure:
    """Return a contour plot for a named CFD field."""
    mesh = result.mesh
    z = result.fields.field(field_name)
    fig = go.Figure(
        data=[
            go.Contour(
                x=mesh.x,
                y=mesh.y,
                z=z,
                colorscale="Turbo",
                contours=dict(showlabels=False),
                colorbar=dict(title=FIELD_LABELS.get(field_name, field_name)),
            )
        ]
    )
    fig.update_layout(height=360, title=FIELD_LABELS.get(field_name, field_name), xaxis_title="x / m", yaxis_title="y / m", margin=dict(l=10, r=10, t=45, b=10))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def velocity_vector_plot(result: SimpleCFDResult) -> go.Figure:
    """Return a 2D velocity vector/quiver style plot."""
    mesh = result.mesh
    u = result.fields.u
    v = result.fields.v
    speed = result.fields.field("velocity")
    step_x = max(mesh.X.shape[1] // 18, 1)
    step_y = max(mesh.X.shape[0] // 12, 1)
    fig = go.Figure()
    fig.add_trace(
        go.Contour(
            x=mesh.x,
            y=mesh.y,
            z=speed,
            colorscale="Blues",
            showscale=True,
            colorbar=dict(title="|u| m/s"),
            opacity=0.75,
        )
    )
    scale = 0.35 * max(mesh.dx, mesh.dy) / max(float(np.nanmax(speed)), 1.0e-9)
    xs: list[float] = []
    ys: list[float] = []
    for iy in range(0, mesh.X.shape[0], step_y):
        for ix in range(0, mesh.X.shape[1], step_x):
            if not mesh.mask[iy, ix]:
                continue
            x0 = float(mesh.X[iy, ix])
            y0 = float(mesh.Y[iy, ix])
            x1 = x0 + float(u[iy, ix]) * scale
            y1 = y0 + float(v[iy, ix]) * scale
            xs.extend([x0, x1, None])
            ys.extend([y0, y1, None])
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#0f172a", width=1), name="velocity vectors"))
    fig.update_layout(height=360, title="速度矢量 velocity vectors", xaxis_title="x / m", yaxis_title="y / m", margin=dict(l=10, r=10, t=45, b=10))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def streamline_plot(result: SimpleCFDResult) -> go.Figure:
    """Return a finite-element style streamline visualization."""
    mesh = result.mesh
    speed = result.fields.field("velocity")
    fig = go.Figure()
    fig.add_trace(go.Contour(x=mesh.x, y=mesh.y, z=speed, colorscale="Viridis", showscale=True, colorbar=dict(title="|u| m/s")))
    if mesh.geometry_type == "Pipe 2D":
        for frac in np.linspace(0.15, 0.85, 7):
            y = np.full_like(mesh.x, mesh.y[0] + frac * (mesh.y[-1] - mesh.y[0]))
            fig.add_trace(go.Scatter(x=mesh.x, y=y, mode="lines", line=dict(color="white", width=1), showlegend=False))
    else:
        rmax = mesh.length_scale_m * 0.85
        for r in np.linspace(rmax * 0.25, rmax, 5):
            theta = np.linspace(0.0, 2.0 * np.pi, 120)
            fig.add_trace(go.Scatter(x=r * np.cos(theta), y=r * np.sin(theta), mode="lines", line=dict(color="white", width=1), showlegend=False))
    fig.update_layout(height=360, title="流线 streamlines", xaxis_title="x / m", yaxis_title="y / m", margin=dict(l=10, r=10, t=45, b=10))
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def surface_plot(result: SimpleCFDResult, field_name: str) -> go.Figure:
    """Return a quasi-3D surface plot for a named field."""
    mesh = result.mesh
    z = result.fields.field(field_name)
    fig = go.Figure(data=[go.Surface(x=mesh.X, y=mesh.Y, z=z, colorscale="Turbo", colorbar=dict(title=FIELD_LABELS.get(field_name, field_name)))])
    fig.update_layout(height=420, title=f"准三维表面：{FIELD_LABELS.get(field_name, field_name)}", margin=dict(l=10, r=10, t=45, b=10))
    return fig


def reactor_cfd_3d_view(result: SimpleCFDResult, field_name: str = "temperature") -> go.Figure:
    """Return an enhanced 3D stirred-tank view with an internal CFD slice."""
    mesh = result.mesh
    field = result.fields.field(field_name)
    theta = np.linspace(0, 2 * np.pi, 80)
    z = np.linspace(0.0, 2.4, 16)
    theta_grid, z_grid = np.meshgrid(theta, z)
    radius = max(result.input.geometry.reactor_diameter_m / 2.0, 0.25)
    shell_x = radius * np.cos(theta_grid)
    shell_y = radius * np.sin(theta_grid)
    shell_z = z_grid
    fig = go.Figure()
    fig.add_trace(
        go.Surface(
            x=shell_x,
            y=shell_y,
            z=shell_z,
            opacity=0.18,
            colorscale=[[0, "#0f172a"], [1, "#38bdf8"]],
            showscale=False,
            name="透明釜体/夹套",
        )
    )
    z_slice = np.full_like(mesh.X, 1.15)
    fig.add_trace(
        go.Surface(
            x=mesh.X,
            y=mesh.Y,
            z=z_slice,
            surfacecolor=field,
            colorscale="Turbo",
            colorbar=dict(title=FIELD_LABELS.get(field_name, field_name)),
            opacity=0.88,
            name="CFD切片",
        )
    )
    speed = result.fields.field("velocity")
    step_x = max(mesh.X.shape[1] // 12, 1)
    step_y = max(mesh.X.shape[0] // 8, 1)
    fig.add_trace(
        go.Cone(
            x=mesh.X[::step_y, ::step_x].ravel(),
            y=mesh.Y[::step_y, ::step_x].ravel(),
            z=np.full_like(mesh.X[::step_y, ::step_x], 1.38).ravel(),
            u=result.fields.u[::step_y, ::step_x].ravel(),
            v=result.fields.v[::step_y, ::step_x].ravel(),
            w=np.zeros_like(result.fields.u[::step_y, ::step_x]).ravel(),
            sizemode="absolute",
            sizeref=0.08,
            colorscale="Blues",
            showscale=False,
            name="内部速度矢量",
        )
    )
    wall_risk = result.fields.fouling_index
    high = np.where((wall_risk > 3.0) & mesh.mask)
    if high[0].size:
        take = slice(None, None, max(high[0].size // 160, 1))
        fig.add_trace(
            go.Scatter3d(
                x=mesh.X[high][take],
                y=mesh.Y[high][take],
                z=np.full_like(mesh.X[high][take], 1.55),
                mode="markers",
                marker=dict(size=4, color="#ef4444", opacity=0.85),
                name="高挂胶风险斑块",
            )
        )
    fig.add_trace(go.Scatter3d(x=[0, 0], y=[0, 0], z=[0.2, 2.7], mode="lines", line=dict(color="#e5e7eb", width=8), name="搅拌轴"))
    for level in [0.85, 1.25]:
        fig.add_trace(go.Scatter3d(x=[-0.45, 0.45, None, 0, 0], y=[0, 0, None, -0.45, 0.45], z=[level, level, None, level, level], mode="lines", line=dict(color="#e5e7eb", width=8), name="搅拌桨", showlegend=False))
    for angle in np.linspace(0, 2 * np.pi, 4, endpoint=False):
        x = [0.92 * radius * np.cos(angle), 0.92 * radius * np.cos(angle)]
        y = [0.92 * radius * np.sin(angle), 0.92 * radius * np.sin(angle)]
        fig.add_trace(go.Scatter3d(x=x, y=y, z=[0.25, 2.2], mode="lines", line=dict(color="#f8fafc", width=5), name="挡板", showlegend=False))
    fig.update_layout(
        title=f"反应釜3D增强CFD视图：{FIELD_LABELS.get(field_name, field_name)}",
        height=520,
        margin=dict(l=0, r=0, t=42, b=0),
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="data",
            camera=dict(eye=dict(x=1.8, y=-1.9, z=1.25)),
        ),
    )
    return fig


def export_legacy_vtk(result: SimpleCFDResult) -> bytes:
    """Export CFD fields as an ASCII legacy VTK structured grid file."""
    mesh = result.mesh
    ny, nx = mesh.X.shape
    lines = [
        "# vtk DataFile Version 3.0",
        "EPDM lightweight CFD fields",
        "ASCII",
        "DATASET STRUCTURED_GRID",
        f"DIMENSIONS {nx} {ny} 1",
        f"POINTS {nx * ny} float",
    ]
    for iy in range(ny):
        for ix in range(nx):
            lines.append(f"{mesh.X[iy, ix]:.8e} {mesh.Y[iy, ix]:.8e} 0.0")
    lines.append(f"POINT_DATA {nx * ny}")
    lines.append("VECTORS velocity float")
    for iy in range(ny):
        for ix in range(nx):
            u = result.fields.u[iy, ix]
            v = result.fields.v[iy, ix]
            if not np.isfinite(u):
                u, v = 0.0, 0.0
            lines.append(f"{u:.8e} {v:.8e} 0.0")
    for name in ["temperature", "ethylene", "propylene", "ENB", "hydrogen", "r_total", "solids", "viscosity", "fouling", "wall_shear", "dead_zone_mask", "high_fouling_mask", "pressure"]:
        field = result.fields.field(name)
        lines.append(f"SCALARS {name} float 1")
        lines.append("LOOKUP_TABLE default")
        for iy in range(ny):
            for ix in range(nx):
                value = field[iy, ix]
                lines.append(f"{value if np.isfinite(value) else 0.0:.8e}")
    return ("\n".join(lines) + "\n").encode("utf-8")
