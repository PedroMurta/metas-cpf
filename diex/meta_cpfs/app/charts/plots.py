"""Componentes Plotly do estudo — tema institucional de charts/theme.py (mesmo visual de ../meta_cpfs_unicos)."""
from __future__ import annotations
import plotly.graph_objects as go
from charts.theme import (apply_theme, get_formatter, fmt_number, COLORS, COR_NEUTRA, COR_POSITIVO, COR_NEGATIVO,
                          TEXT_COLOR)

CORES_NEGOCIO = {"SEST": COLORS["primary"], "SENAT": COLORS["secondary"], "Campanha": COLORS["purple"]}
LEGENDA_BAIXO = dict(orientation="h", x=0, xanchor="left", y=-0.1, yanchor="top", borderwidth=0)


def titulo(achado: str, detalhe: str = "") -> str:
    """Storytelling: achado em negrito + detalhe técnico em cinza."""
    sub = f"<br><span style='font-size:12px;color:{COR_NEUTRA}'>{detalhe}</span>" if detalhe else ""
    return f"<b>{achado}</b>{sub}"


def finalizar(fig: go.Figure, title: str, height: int | None) -> go.Figure:
    fig = apply_theme(fig, title, show_grid=True, height=height, legend=LEGENDA_BAIXO,
                      margin=dict(t=108 if title else 10, b=48))
    if title:
        fig.update_layout(title=dict(x=0, xanchor="left"))
    return fig


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def fig_evolucao(df, x, y, cor, title="", *, value_fmt="abbrev", height=400) -> go.Figure:
    """Barras por período + selo de variação entre períodos e conector entre os topos."""
    fmt, xs, ys = get_formatter(value_fmt), df[x].astype(str).tolist(), df[y].tolist()
    largura, topo = 0.55, max(ys) * 1.22
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=cor, width=largura, text=[fmt(v) for v in ys],
                           textposition="outside", textfont=dict(size=12, color=TEXT_COLOR),
                           hovertemplate="%{x}: %{text}<extra></extra>"))
    for i in range(1, len(ys)):
        var = 100 * (ys[i] / ys[i - 1] - 1)
        c, seta = (COR_POSITIVO, "▲") if var >= 0 else (COR_NEGATIVO, "▼")
        fig.add_shape(type="line", x0=i - 1 + largura / 2, x1=i - largura / 2, y0=ys[i - 1], y1=ys[i],
                      line=dict(color=c, width=1.5, dash="dot"))
        fig.add_annotation(x=i - 0.5, y=topo, showarrow=False, text=f"{seta} {fmt_number(abs(var), 1)}%",
                           font=dict(size=13, color=c), bgcolor=rgba(c, 0.10),
                           bordercolor=rgba(c, 0.35), borderwidth=1, borderpad=5)
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category")
    fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, max(ys) * 1.35])
    return fig


CINZA = rgba(COR_NEUTRA, 0.35)


def fig_linhas_destaque(g, x, y, grupo, title="", controle="Restante do Nacional", y_title="", sufixo="",
                        height=400) -> go.Figure:
    """Controle em cinza tracejado, destaque na cor SEST, rótulo direto no fim de cada linha (sem legenda)."""
    fig = go.Figure()
    for nome, d in g.sort_values(x).groupby(grupo):
        base = nome == controle
        cor = COR_NEUTRA if base else CORES_NEGOCIO["SEST"]
        fig.add_scatter(x=d[x], y=d[y], mode="lines+markers", name=nome,
                        line=dict(color=cor, width=2 if base else 3, dash="dash" if base else "solid"),
                        hovertemplate=f"{nome}<br>%{{x}}: %{{y:.1f}}{sufixo}<extra></extra>")
        fig.add_annotation(x=d[x].iloc[-1], y=d[y].iloc[-1], text=f"<b>{nome}</b>", xanchor="left", xshift=8,
                           showarrow=False, font=dict(size=12, color=cor))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False, margin=dict(r=200))
    fig.update_xaxes(dtick=1, showgrid=False)
    fig.update_yaxes(title=y_title, ticksuffix=sufixo, rangemode="tozero")
    return fig


# ---- Base de clientes ----------------------------------------------------------------------------------------
def fig_empilhado_v(df, x, series, title="", height=420) -> go.Figure:
    """Barras verticais empilhadas. series = [(coluna, nome, cor), ...]."""
    fig = go.Figure([go.Bar(x=df[x].astype(str), y=df[c], name=n, marker_color=cor,
                            hovertemplate=f"{n}<br>%{{x}}: %{{y:,.0f}}<extra></extra>") for c, n, cor in series])
    fig = finalizar(fig, title, height)
    fig.update_layout(barmode="stack", bargap=0.3, margin=dict(b=80))
    fig.update_xaxes(type="category", showgrid=False)
    return fig


def fig_cascata(rotulos, valores, medidas, title="", height=400, percentual: bool = False) -> go.Figure:
    """Cascata: medidas 'absolute' | 'relative' | 'total'. Queda em vermelho, entrada em verde, bases em cinza.

    percentual=True acrescenta, abaixo de cada valor, o % sobre a primeira barra (variação, no total final).
    """
    fmt = lambda v: f"{'+' if v > 0 else ''}{fmt_number(v, 0)}"
    textos = [fmt_number(v, 0) if m != "relative" else fmt(v) for v, m in zip(valores, medidas)]
    if percentual:
        inicio = valores[0]
        sinal = lambda f: f"{'+' if f > 0 else '−' if f < 0 else ''}{fmt_number(abs(100 * f), 2)}%"
        textos = [t if i == 0 else f"{t}\n({sinal(v / inicio if m == 'relative' else v / inicio - 1)})"
                  for i, (t, v, m) in enumerate(zip(textos, valores, medidas))]
    fig = go.Figure(go.Waterfall(x=rotulos, y=valores, measure=medidas, textposition="outside",
                                 text=textos,
                                 decreasing=dict(marker=dict(color=COR_NEGATIVO)),
                                 increasing=dict(marker=dict(color=COR_POSITIVO)),
                                 totals=dict(marker=dict(color=COR_NEUTRA)),
                                 connector=dict(line=dict(color=CINZA, width=1, dash="dot"))))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False)
    fig.update_yaxes(showticklabels=False, showgrid=False)
    return fig


def fig_barras_v(df, x, y, cores, title="", sufixo="", height=380, casas=1) -> go.Figure:
    """Barras verticais com valor no topo e cor por barra."""
    fig = go.Figure(go.Bar(x=df[x].astype(str), y=df[y], marker_color=cores, width=0.55,
                           text=[f"{fmt_number(v, casas)}{sufixo}" for v in df[y]], textposition="outside",
                           textfont=dict(size=12, color=TEXT_COLOR), hovertemplate="%{x}: %{text}<extra></extra>"))
    fig = finalizar(fig, title, height)
    fig.update_layout(showlegend=False)
    fig.update_xaxes(type="category", showgrid=False)
    fig.update_yaxes(showticklabels=False, showgrid=False, range=[0, df[y].max() * 1.25])
    return fig
