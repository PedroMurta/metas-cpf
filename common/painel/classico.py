"""Gráficos SEST SENAT para Streamlit (ECharts via streamlit-echarts) e formatação pt-BR.

Padrão visual (referência: painel proposicao_meta, DIEX/GEPLANE):
- título fora do gráfico: achado em negrito + detalhe em cinza 12px (`titulo()`);
- tudo em cinza de contexto; só o achado na cor de destaque do assunto (`destacar()`);
- tooltip navy #0f2540, texto branco 13px; eixos #5a6a7e 12px; grade #e5e9ef; fonte Inter;
- números em pt-BR (1.234,56 · 12,34% · 1,5 mil / mi); percentuais sempre com duas casas;
- barras com barMaxWidth 46; legenda no topo; animação 900 ms cubicOut com 40 ms de atraso por item.

Opções são dicts nativos do ECharts montados em app/charts/*.py; as páginas só chamam `grafico()`.
"""
from __future__ import annotations

import json
import math
import re
from copy import deepcopy

import numpy as np
import pandas as pd
import streamlit as st
try:
    from streamlit_echarts import JsCode, st_echarts
except Exception:   # fora do runtime do Streamlit (notebooks) o componente não registra; formatos e Plotly seguem
    st_echarts = None

    class JsCode:   # mesmo marcador do streamlit_echarts
        def __init__(self, js_code: str):
            self.js_code = f"--x_x--0_0--{js_code}--x_x--0_0--"

        def __str__(self):
            return self.js_code

# ---- Paleta -------------------------------------------------------------------------------------------------------
ASSUNTOS = {  # cor de destaque por assunto (sestsenat-dados-design-web/core/assuntos.md)
    "institucional": "#0095cc",
    "sest": "#1f8f5f",
    "senat": "#e07b1a",
    "comunicacao": "#6b4fbb",
    "transporte": "#c99a12",
}
FORTE = "#0f2540"       # navy: linhas principais, rótulos de total, tooltip
CONTEXTO = "#c5ced8"    # cinza claro: categorias sem destaque
CONTEXTO2 = "#94a3b8"   # cinza médio: período de comparação, linhas de referência
TEXTO = "#5a6a7e"       # eixos, legendas, rótulos secundários
NEUTRA = "#6b7280"      # detalhe do título
GRADE = "#e5e9ef"
ALERTA = "#c94040"      # queda / fora da faixa
SUCESSO = "#1a9e6e"     # alta / dentro da meta
FONTE = "Inter, sans-serif"
MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def destaque(assunto: str = "institucional") -> str:
    return ASSUNTOS[assunto]


def destacar(categorias, alvos, assunto: str = "institucional") -> list[str]:
    """Cor por categoria: destaque nos alvos, cinza de contexto no resto."""
    alvos = {alvos} if isinstance(alvos, str) else set(alvos)
    return [destaque(assunto) if c in alvos else CONTEXTO for c in categorias]


def cores_periodo(categorias, atual, anterior=None, assunto: str = "institucional") -> list[str]:
    """Série temporal: período analisado no destaque, comparação em cinza médio, demais em cinza claro."""
    return [destaque(assunto) if str(c) == str(atual) else CONTEXTO2 if str(c) == str(anterior) else CONTEXTO
            for c in categorias]


def _mistura(a: str, b: str, t: float) -> str:
    ca, cb = ([int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in (a, b))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def sequencial(n: int, assunto: str = "institucional") -> list[str]:
    """Escala clara → destaque → navy (mapas de calor, pilhas ordenadas)."""
    a, b, c = "#f1f5f9", destaque(assunto), FORTE
    ts = [i / max(n - 1, 1) for i in range(n)]
    return [_mistura(a, b, t * 2) if t <= .5 else _mistura(b, c, (t - .5) * 2) for t in ts]


def tons(series: list[str], residuais=("Não informado", "Sem identificação", "Outros"),
         assunto: str = "institucional") -> dict[str, str]:
    """Pilhas e roscas: escala do destaque (1ª série mais escura); categorias residuais em cinza."""
    principais = [s for s in series if s not in residuais]
    escala = sequencial(len(principais) + 1, assunto)[1:][::-1]
    return {s: escala[principais.index(s)] if s in principais else CONTEXTO for s in series}


def divergente(assunto: str = "institucional") -> list[str]:
    """Negativo ← neutro → positivo. Fora do institucional o negativo é navy (evita verde × vermelho)."""
    return [ALERTA if assunto == "institucional" else FORTE, GRADE, destaque(assunto)]


# ---- Formatação pt-BR (Python) ------------------------------------------------------------------------------------
def fmt_numero(n, casas: int = 0) -> str:
    """1234.5 → '1.234,5'; nulo → '—'."""
    if n is None or pd.isna(n):
        return "—"
    return f"{float(n):,.{max(casas, 0)}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_int(n) -> str:
    return fmt_numero(n, 0)


def fmt_pct(n, casas: int = 2, sinal: bool = False) -> str:
    """12.345 → '12,35%'; com sinal: '+12,35%' / '−3,10%'."""
    texto = fmt_numero(abs(n) if sinal else n, casas)
    if texto == "—":
        return texto
    return (("+" if n >= 0 else "−") if sinal else "") + texto + "%"


def fmt_pp(n, casas: int = 2) -> str:
    """Diferença em pontos percentuais: '+1,20 p.p.'."""
    return "—" if fmt_numero(n) == "—" else f"{'+' if n >= 0 else '−'}{fmt_numero(abs(n), casas)} p.p."


def fmt_brl(n, casas: int = 2) -> str:
    return f"R$ {fmt_numero(n, casas)}"


def fmt_abrev(n, casas: int = 1) -> str:
    """1_500_000 → '1,5 mi'."""
    a = abs(float(n))
    for limite, sufixo in ((1e9, "bi"), (1e6, "mi"), (1e3, "mil")):
        if a >= limite:
            return f"{fmt_numero(n / limite, casas)} {sufixo}"
    return fmt_int(n)


def variacao(atual, anterior) -> float:
    """Variação % (nan se a base for nula ou zero)."""
    return float("nan") if anterior is None or pd.isna(anterior) or not anterior else 100 * (atual / anterior - 1)


def formatar_percentuais(texto):
    """Percentuais em texto livre no padrão pt-BR: '5.5%' → '5,50%'; inteiros ficam inteiros ('10%')."""
    if not isinstance(texto, str):
        return texto

    def formatar(m):
        bruto = m.group(1)
        sinal = bruto[0] if bruto[0] in "+-−" else ""
        corpo = bruto.lstrip("+-−")
        if "." in corpo and "," in corpo:
            decimal = max(".,", key=corpo.rfind)
        elif corpo.count(",") == 1 or corpo.count(".") == 1:
            decimal = "," if "," in corpo else "."
        else:
            decimal = None
        inteiro, _, fracao = corpo.rpartition(decimal) if decimal else (corpo, "", "")
        numero = float(re.sub(r"\D", "", inteiro) + "." + (fracao or "0"))
        prefixo = "+" if sinal == "+" else "−" if sinal in "-−" and sinal and numero else ""
        return f"{prefixo}{fmt_numero(numero, 2 if fracao else 0)}%"

    return re.sub(r"(?<![\w.,])([+\-−]?\d[\d.,]*\d|[+\-−]?\d)%", formatar, texto)


# ---- Formatação pt-BR (JavaScript, dentro do ECharts) ---------------------------------------------------------------
NUM_JS = ("(v, c) => (v == null || isNaN(v)) ? '—' : Number(v).toLocaleString('pt-BR', "
          "{minimumFractionDigits: c, maximumFractionDigits: c})")
EIXO_ABREV = JsCode("function (v) { const a = Math.abs(v); return a >= 1e6 ? (v / 1e6).toLocaleString('pt-BR', "
                    "{maximumFractionDigits: 1}) + ' mi' : a >= 1e3 ? (v / 1e3).toLocaleString('pt-BR', "
                    "{maximumFractionDigits: 1}) + ' mil' : Number(v).toLocaleString('pt-BR'); }")

EIXO_NUM = JsCode("function (v) { return Number(v).toLocaleString('pt-BR', {maximumFractionDigits: 2}); }")


def js_numero(casas: int = 0, sufixo: str = "") -> JsCode:
    """Formatter de eixo: valor → '1.234,56' + sufixo."""
    return JsCode(f"function (v) {{ const f = {NUM_JS}; return f(v, {casas}) + '{sufixo}'; }}")


def rotulo_numero(casas: int = 0, sufixo: str = "") -> JsCode:
    """Formatter de rótulo de série (p.value); vazio quando nulo."""
    return JsCode(f"function (p) {{ const f = {NUM_JS}; const v = Array.isArray(p.value) ? p.value[1] : p.value; "
                  f"return v == null ? '' : f(v, {casas}) + '{sufixo}'; }}")


# ---- Peças das opções ---------------------------------------------------------------------------------------------
def titulo(achado: str, detalhe: str = "") -> str:
    """Storytelling: achado em negrito + detalhe técnico em cinza (renderizado acima do gráfico)."""
    achado, detalhe = formatar_percentuais(achado), formatar_percentuais(detalhe)
    sub = f"<br><span style='font-size:12px;color:{NEUTRA}'>{detalhe}</span>" if detalhe else ""
    return f"<b>{achado}</b>{sub}"


def tooltip_eixo(casas: dict[str, int] | int = 0, sufixo: str = "", ponteiro: str = "shadow") -> dict:
    """Tooltip por categoria: título em negrito e uma linha por série. `casas` por série ou único."""
    padrao = casas if isinstance(casas, int) else 0
    mapa = json.dumps({} if isinstance(casas, int) else casas, ensure_ascii=False)
    return {"trigger": "axis", "axisPointer": {"type": ponteiro}, "formatter": JsCode(
        f"function (ps) {{ const f = {NUM_JS}; const cs = {mapa}; "
        "let s = '<b>' + ps[0].axisValueLabel + '</b>'; ps.forEach(p => { "
        "const v = Array.isArray(p.value) ? p.value[1] : p.value; if (v == null || p.seriesName === 'Total') return; "
        f"s += '<br>' + p.marker + p.seriesName + ': ' + f(v, cs[p.seriesName] ?? {padrao}) + '{sufixo}'; }}); "
        "return s; }")}


def eixo_categoria(dados, nome: str = "", **extra) -> dict:
    eixo = {"type": "category", "data": [str(d) for d in dados], "axisLabel": {"color": TEXTO}}
    if nome:
        eixo.update({"name": nome, "nameLocation": "middle", "nameGap": 30})
    return {**eixo, **extra}


def eixo_valor(nome: str = "", formatter=EIXO_ABREV, **extra) -> dict:
    return {"type": "value", "name": nome, "nameTextStyle": {"color": TEXTO, "align": "left"},
            "axisLabel": {"color": TEXTO, "formatter": formatter}, "splitLine": {"lineStyle": {"color": GRADE}},
            **extra}


def faixa(inicio, fim, rotulo: str) -> dict:
    """markArea cinza para sinalizar um choque (ex.: faixa('2020', '2021', 'Pandemia'))."""
    return {"silent": True, "itemStyle": {"color": "rgba(148,163,184,0.12)"},
            "label": {"show": True, "position": "insideTop", "color": TEXTO, "fontSize": 11, "formatter": rotulo},
            "data": [[{"xAxis": str(inicio)}, {"xAxis": str(fim)}]]}


def linha_referencia(valor, rotulo: str = "", eixo: str = "yAxis", cor: str = CONTEXTO2) -> dict:
    """markLine tracejada (meta, média, P25). Anexar em series[i]['markLine']."""
    return {"symbol": ["none", "none"], "silent": True,
            "lineStyle": {"color": cor, "type": "dashed", "width": 1.5},
            "label": {"show": bool(rotulo), "formatter": rotulo, "color": TEXTO, "fontSize": 11},
            "data": [{eixo: valor}]}


GRID = {"left": 8, "right": 8, "top": 30, "bottom": 8, "containLabel": True}
GRID_LEGENDA = {**GRID, "top": 48}


def _lista(serie) -> list:
    return [None if v is None or (isinstance(v, float) and math.isnan(v)) else v for v in _normalizar(list(serie))]


# ---- Construtores prontos -----------------------------------------------------------------------------------------
def barras(categorias, valores, achado: str, detalhe: str = "", *, cores=None, nome: str = "",
           casas: int = 0, sufixo: str = "", rotulos: bool = True, horizontal: bool = False,
           marcar: dict | None = None) -> dict:
    """Barras simples. `cores` = destacar(...) / cores_periodo(...); `marcar` = faixa(...) ou linha_referencia(...)."""
    categorias, valores = [str(c) for c in categorias], _lista(valores)
    cores = cores or [destaque()] * len(valores)
    serie = {"type": "bar", "name": nome or achado, "barMaxWidth": 46,
             "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(valores, cores)],
             "label": {"show": rotulos, "position": "right" if horizontal else "top", "color": TEXTO,
                       "fontSize": 11, "formatter": rotulo_numero(casas, sufixo)}}
    if marcar:
        serie["markArea" if "itemStyle" in marcar else "markLine"] = marcar
    cat = eixo_categoria(categorias, inverse=horizontal)
    val = eixo_valor(formatter=js_numero(0, sufixo) if sufixo else EIXO_NUM if casas else EIXO_ABREV)
    if horizontal:
        cat["axisLabel"].update({"width": 170, "overflow": "truncate", "ellipsis": "..."})
    return {"_titulo": titulo(achado, detalhe), "grid": {**GRID, "right": 56 if horizontal else 8},
            "tooltip": tooltip_eixo(casas, sufixo),
            "xAxis": val if horizontal else cat, "yAxis": cat if horizontal else val, "series": [serie]}


def barras_agrupadas(tab: pd.DataFrame, achado: str, detalhe: str = "", *, cores: dict[str, str] | None = None,
                     casas: int = 0, sufixo: str = "", nome_eixo: str = "") -> dict:
    """`tab`: categorias no índice, uma coluna por série (ex.: 2025 e 2026). Última coluna no destaque."""
    colunas = [str(c) for c in tab.columns]
    cores = cores or {c: destaque() if i == len(colunas) - 1 else CONTEXTO2 for i, c in enumerate(colunas)}
    series = [{"type": "bar", "name": c, "barMaxWidth": 40, "itemStyle": {"color": cores[c]}, "data": _lista(tab[o]),
               "label": {"show": True, "position": "top", "color": TEXTO, "fontSize": 11,
                         "formatter": rotulo_numero(casas, sufixo)}}
              for c, o in zip(colunas, tab.columns)]
    return {"_titulo": titulo(achado, detalhe), "legend": {"top": 0}, "grid": {**GRID_LEGENDA, "bottom": 28 if nome_eixo else 8},
            "tooltip": tooltip_eixo(casas, sufixo), "xAxis": eixo_categoria(tab.index, nome_eixo),
            "yAxis": eixo_valor(formatter=js_numero(0, sufixo) if sufixo else EIXO_ABREV), "series": series}


def barras_linha(categorias, barras_, linha, achado: str, detalhe: str = "", *, nome_barras: str = "Atendimentos",
                 nome_linha: str = "Pessoas atendidas", cores=None, marcar: dict | None = None) -> dict:
    """Duplo eixo: barras (esquerda, cores por período) + linha navy com rótulos (direita)."""
    categorias = [str(c) for c in categorias]
    cores = cores or [CONTEXTO2] * len(categorias)
    serie_barras = {"type": "bar", "name": nome_barras, "barMaxWidth": 46, "itemStyle": {"color": CONTEXTO2},
                    "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(_lista(barras_), cores)]}
    if marcar:
        serie_barras["markArea"] = marcar
    return {
        "_titulo": titulo(achado, detalhe),
        "legend": {"top": 0, "data": [nome_barras, nome_linha]},
        "grid": GRID_LEGENDA, "tooltip": tooltip_eixo(),
        "xAxis": eixo_categoria(categorias),
        "yAxis": [eixo_valor(nome_barras), eixo_valor(nome_linha, splitLine={"show": False})],
        "series": [serie_barras,
                   {"type": "line", "name": nome_linha, "yAxisIndex": 1, "data": _lista(linha), "symbolSize": 7,
                    "lineStyle": {"width": 3, "color": FORTE}, "itemStyle": {"color": FORTE},
                    "label": {"show": True, "position": "top", "color": FORTE, "fontSize": 11,
                              "formatter": rotulo_numero()}}],
    }


def empilhado(tab: pd.DataFrame, achado: str, detalhe: str = "", medida: str = "atendimentos",
              cores: dict[str, str] | None = None) -> dict:
    """Barras empilhadas por período com total no topo; tooltip traz valor e participação (%).

    `tab`: períodos no índice, uma coluna por série (a primeira fica na base da pilha, mais escura).
    """
    colunas = [str(c) for c in tab.columns]
    cores = cores or tons(colunas)
    series = [{"type": "bar", "name": c, "stack": "total", "barMaxWidth": 46,
               "itemStyle": {"color": cores[c], "borderColor": "#ffffff", "borderWidth": 1}, "data": _lista(tab[o])}
              for c, o in zip(colunas, tab.columns)]
    series.append({"type": "line", "name": "Total", "data": _lista(tab.sum(axis=1, min_count=1)), "symbol": "none",
                   "lineStyle": {"opacity": 0}, "tooltip": {"show": False},
                   "label": {"show": True, "position": "top", "color": FORTE, "fontSize": 11, "fontWeight": 600,
                             "formatter": rotulo_numero()}})
    return {
        "_titulo": titulo(achado, detalhe), "legend": {"top": 0, "data": colunas}, "grid": GRID_LEGENDA,
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}, "formatter": JsCode(
            f"function (ps) {{ const f = {NUM_JS}; const bs = ps.filter(p => p.seriesName !== 'Total' "
            "&& p.value != null); const t = bs.reduce((a, p) => a + p.value, 0); "
            f"let s = '<b>' + ps[0].axisValueLabel + '</b> · ' + f(t, 0) + ' {medida}'; "
            "bs.slice().reverse().forEach(p => { s += '<br>' + p.marker + p.seriesName + ': ' + f(p.value, 0) + "
            "' (' + f(100 * p.value / t, 2) + '%)'; }); return s; }")},
        "xAxis": eixo_categoria(tab.index), "yAxis": eixo_valor(), "series": series,
    }


def linhas(tab: pd.DataFrame, achado: str, detalhe: str = "", *, destaques=(), casas: int = 0, sufixo: str = "",
           categorias=None) -> dict:
    """Uma linha por coluna. Colunas em `destaques`: grossas (3px) e coloridas; demais finas em cinza de contexto.

    O 1º destaque usa a cor do assunto, o 2º o navy. Séries com nulo no fim (ano em curso) ficam tracejadas.
    """
    cats = [str(c) for c in (categorias if categorias is not None else tab.index)]
    destaques = [str(d) for d in destaques]
    series = []
    for coluna in tab.columns:
        nome = str(coluna)
        principal = nome in destaques
        cor = (destaque() if destaques.index(nome) == 0 else FORTE) if principal else CONTEXTO
        parcial = tab[coluna].isna().any()
        series.append({"type": "line", "name": nome, "data": _lista(tab[coluna]), "symbol": "circle",
                       "symbolSize": 6 if principal else 0, "z": 3 if principal else 1, "connectNulls": False,
                       "lineStyle": {"width": 3 if principal else 1.2, "color": cor,
                                     "type": "dashed" if parcial else "solid"},
                       "itemStyle": {"color": cor}})
    return {"_titulo": titulo(achado, detalhe), "legend": {"top": 0, "type": "scroll"}, "grid": GRID_LEGENDA,
            "tooltip": tooltip_eixo(casas, sufixo, ponteiro="line"),
            "xAxis": eixo_categoria(cats, boundaryGap=False),
            "yAxis": eixo_valor(formatter=js_numero(0, sufixo) if sufixo else EIXO_NUM if casas else EIXO_ABREV),
            "series": series}


def rosca(valores: dict[str, float], achado: str, detalhe: str = "", unidade: str = "pessoas",
          cores: dict[str, str] | None = None) -> dict:
    """Rosca com total no centro; ao passar o mouse, a fatia mostra nome e participação sobre fundo branco."""
    valores = {k: float(v) for k, v in valores.items() if v and not pd.isna(v)}
    cores = cores or tons(list(valores))
    estilo = {"t": {"fontSize": 22, "fontWeight": 700, "color": FORTE, "lineHeight": 28, "fontFamily": FONTE},
              "s": {"fontSize": 12, "color": TEXTO, "fontFamily": FONTE},
              "n": {"fontSize": 15, "fontWeight": 700, "color": FORTE, "lineHeight": 22, "fontFamily": FONTE},
              "v": {"fontSize": 13, "color": TEXTO, "fontFamily": FONTE}}
    total = JsCode(f"function (p) {{ return '{{t|' + Number(p.value).toLocaleString('pt-BR') + '}}\\n{{s|{unidade}}}'; }}")
    fatia = JsCode("function (p) { return '{n|' + p.name + '}\\n{v|' + p.percent.toLocaleString('pt-BR', "
                   "{minimumFractionDigits: 2, maximumFractionDigits: 2}) + '%}'; }")
    return {
        "_titulo": titulo(achado, detalhe), "legend": {"top": 0, "left": "center", "data": list(valores)},
        "tooltip": {"trigger": "item", "formatter": JsCode(
            f"function (p) {{ const f = {NUM_JS}; return p.marker + '<b>' + p.name + '</b><br>' + f(p.value, 0) + "
            f"' {unidade} (' + f(p.percent, 2) + '%)'; }}")},
        "series": [
            {"type": "pie", "name": "Total", "radius": [0, "42%"], "center": ["50%", "56%"], "z": 1, "silent": True,
             "tooltip": {"show": False}, "itemStyle": {"color": "rgba(0,0,0,0)"}, "labelLine": {"show": False},
             "label": {"show": True, "position": "center", "formatter": total, "rich": estilo},
             "data": [{"name": "Total", "value": sum(valores.values())}]},
            {"type": "pie", "name": achado, "radius": ["45%", "70%"], "center": ["50%", "56%"], "z": 2,
             "avoidLabelOverlap": False, "padAngle": 3, "itemStyle": {"borderRadius": 8},
             "label": {"show": False, "position": "center"}, "labelLine": {"show": False},
             "emphasis": {"scale": True, "scaleSize": 6, "label": {
                 "show": True, "position": "center", "backgroundColor": "#ffffff", "padding": [10, 14],
                 "formatter": fatia, "rich": estilo}},
             "data": [{"name": k, "value": v, "itemStyle": {"color": cores[k]}} for k, v in valores.items()]},
        ],
    }


def dispersao(x, y, nomes, achado: str, detalhe: str = "", *, nome_x: str = "", nome_y: str = "",
              cores=None, casas_x: int = 0, casas_y: int = 2) -> dict:
    """Pontos (ex.: unidades). `cores` = destacar(nomes, alvos); tooltip com o nome do ponto."""
    cores = cores or [destaque()] * len(nomes)
    dados = [{"name": str(n), "value": [a, b], "itemStyle": {"color": c}}
             for n, a, b, c in zip(nomes, _lista(x), _lista(y), cores)]
    return {"_titulo": titulo(achado, detalhe), "grid": {**GRID, "bottom": 28, "left": 16},
            "tooltip": {"trigger": "item", "formatter": JsCode(
                f"function (p) {{ const f = {NUM_JS}; return '<b>' + p.name + '</b><br>{nome_x}: ' + "
                f"f(p.value[0], {casas_x}) + '<br>{nome_y}: ' + f(p.value[1], {casas_y}); }}")},
            "xAxis": {**eixo_valor(nome_x, EIXO_NUM), "nameLocation": "middle", "nameGap": 26,
                      "nameTextStyle": {"color": TEXTO}, "scale": True, "boundaryGap": ["5%", "5%"]},
            "yAxis": {**eixo_valor(nome_y, EIXO_NUM), "scale": True, "boundaryGap": ["5%", "5%"]},
            "series": [{"type": "scatter", "symbolSize": 9, "data": dados,
                        "emphasis": {"itemStyle": {"borderColor": FORTE, "borderWidth": 2}}}]}


# ---- Renderização -------------------------------------------------------------------------------------------------
def tema_echarts(assunto: str = "institucional") -> dict:
    eixo = {"axisLine": {"lineStyle": {"color": GRADE}}, "axisTick": {"show": False},
            "axisLabel": {"color": TEXTO, "fontSize": 12}, "splitLine": {"lineStyle": {"color": GRADE}}}
    return {
        "color": [destaque(assunto), CONTEXTO2, CONTEXTO], "backgroundColor": "transparent",
        "textStyle": {"fontFamily": FONTE, "color": TEXTO},
        "legend": {"textStyle": {"color": TEXTO, "fontSize": 12}},
        "tooltip": {"backgroundColor": FORTE, "borderWidth": 0, "confine": True,
                    "textStyle": {"color": "#ffffff", "fontFamily": FONTE, "fontSize": 12}},
        "categoryAxis": deepcopy(eixo), "valueAxis": {**deepcopy(eixo), "axisLine": {"show": False}},
        "animationDuration": 900, "animationDurationUpdate": 800, "animationEasing": "cubicOut",
    }


def _normalizar(valor):
    """numpy / pandas / datas → tipos JSON (sem isso o st_echarts envia as opções como texto e quebra)."""
    if isinstance(valor, dict):
        return {k: _normalizar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_normalizar(v) for v in valor]
    if getattr(getattr(valor, "dtype", None), "kind", "") == "M":
        return [None if t == "NaT" else t for t in np.datetime_as_string(valor, unit="D").tolist()]
    if hasattr(valor, "isoformat") and hasattr(valor, "year"):
        return valor.isoformat()[:10]
    if hasattr(valor, "tolist"):
        return _normalizar(valor.tolist())
    if hasattr(valor, "item"):
        return _normalizar(valor.item())
    if valor is pd.NA or valor is pd.NaT or (isinstance(valor, float) and not math.isfinite(valor)):
        return None
    return valor


def grafico(opcoes: dict, chave: str, altura: int = 380, assunto: str = "institucional", container=None) -> None:
    """Renderiza opções ECharts com o tema; `_titulo` (de titulo()) vira o cabeçalho acima do gráfico."""
    opcoes = deepcopy(opcoes)
    cabeca = opcoes.pop("_titulo", "")
    base = {
        "color": [destaque(assunto), CONTEXTO2, CONTEXTO], "backgroundColor": "transparent",
        "textStyle": {"fontFamily": FONTE, "color": TEXTO, "fontSize": 12},
        "grid": dict(GRID),
        "tooltip": {"backgroundColor": FORTE, "borderWidth": 0, "confine": True,
                    "textStyle": {"color": "#ffffff", "fontFamily": FONTE, "fontSize": 13}},
        "animationDuration": 900, "animationDelay": JsCode("function (i) { return i * 40; }"),
        "animationDurationUpdate": 800, "animationEasing": "cubicOut",
    }
    tooltip = opcoes.pop("tooltip", {})
    base.update(_normalizar(opcoes))
    base["tooltip"] = {**base["tooltip"], **tooltip}
    for nome in ("xAxis", "yAxis"):  # sem linhas de grade (o radar mantém a teia)
        for eixo in base.get(nome) if isinstance(base.get(nome), list) else [base.get(nome)]:
            if isinstance(eixo, dict):
                eixo["splitLine"] = {**eixo.get("splitLine", {}), "show": False}
    with container if container is not None else st.container():
        if cabeca:
            st.markdown(cabeca, unsafe_allow_html=True)
        st_echarts(options=base, theme=tema_echarts(assunto), height=f"{altura}px", width="100%", key=chave)


def tema_plotly(assunto: str = "institucional") -> None:
    """Registra e ativa o template 'sestsenat' no Plotly (notebooks exploratórios). Chamar uma vez."""
    import plotly.graph_objects as go
    import plotly.io as pio
    eixo = dict(gridcolor=GRADE, linecolor=GRADE, zeroline=False, tickfont=dict(color=TEXTO, size=11))
    pio.templates["sestsenat"] = go.layout.Template(layout=dict(
        font=dict(family=FONTE, color=TEXTO, size=12), colorway=[destaque(assunto), CONTEXTO2, CONTEXTO],
        paper_bgcolor="white", plot_bgcolor="white", xaxis=eixo, yaxis=eixo, showlegend=False, separators=",.",
        title=dict(x=0, xanchor="left", font=dict(color=FORTE, size=16)), margin=dict(t=70, l=10, r=10, b=10)))
    pio.templates.default = "sestsenat"


def titulo_plotly(achado: str, detalhe: str = "") -> str:
    """Título = achado; subtítulo técnico em cinza."""
    return f'<b>{achado}</b><br><span style="font-size:12px;color:{NEUTRA}">{detalhe}</span>'


titulo_echarts = titulo   # nome usado no CLAUDE.md
