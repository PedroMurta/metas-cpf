"""Gráficos com eixos: linhas no tempo, barras, rankings, mapa de calor e dispersão.

Todos devolvem um dicionário de opções ECharts; desenhe com gt.grafico(chave, opcoes, altura).
Efeitos comuns: linha principal ciano com brilho e área em degradê, último ponto pulsando, barras arredondadas
com trilho e entrada em cascata.
"""
from __future__ import annotations

import json

from streamlit_echarts import JsCode

from .tema import (AZUL, BRL_JS, CIANO, CORAL, TEMA, base, br, cascata, degrade, destaque, eixo_categoria,
                        eixo_valor, finito, legenda, mistura, num_js, pulso, rgba, tooltip)

_SOMBRA_EIXO = {"type": "shadow", "shadowStyle": {"color": "rgba(0,184,230,.08)"}}
_LINHA_EIXO = {"type": "line", "lineStyle": {"color": CIANO, "opacity": .5}}


def _area(cor: str, alfa: float = .3) -> dict:
    return {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1, "colorStops": [
        {"offset": 0, "color": rgba(cor, alfa)}, {"offset": 1, "color": rgba(cor, 0)}]}}


def _linha_ref(valor, texto: str, cor: str, eixo: str = "yAxis") -> dict:
    return {eixo: valor, "label": {"formatter": texto, "color": cor, "fontSize": 11, "fontWeight": 600},
            "lineStyle": {"color": cor, "type": "dashed", "width": 1.5}}


# ---------------------------------------------------------------- linhas no tempo

def linha_meta(rotulos, realizado, meta, nome_real: str = "Realizado", nome_meta: str = "Meta",
               formato: str | None = None, suave: float = .3) -> dict:
    """Realizado em ciano com brilho e área; meta tracejada; último ponto pulsando.
    formato: função JS que recebe o valor (padrão: R$ abreviado)."""
    fmt = JsCode(formato or BRL_JS)
    real = list(realizado)
    return {**base(),
            "grid": {"left": 8, "right": 24, "top": 40, "bottom": 8, "containLabel": True},
            "legend": legenda(data=[nome_meta, nome_real]),
            "tooltip": tooltip(trigger="axis", valueFormatter=fmt, axisPointer=_LINHA_EIXO),
            "xAxis": eixo_categoria(rotulos, boundaryGap=False),
            "yAxis": eixo_valor(fmt),
            "series": [
                {"type": "line", "name": nome_meta, "data": list(meta), "symbol": "none", "smooth": .3,
                 "lineStyle": {"width": 2, "type": "dashed", "color": TEMA["meta"]}, "itemStyle": {"color": TEMA["meta"]}},
                {"type": "line", "name": nome_real, "data": real, "symbol": "none", "smooth": suave,
                 "lineStyle": {"width": 3.5, "color": CIANO, "shadowBlur": 14, "shadowColor": "rgba(0,184,230,.7)"},
                 "itemStyle": {"color": CIANO}, "areaStyle": _area(CIANO, .32)},
                *([pulso(len(real) - 1, real[-1], tamanho=10)] if real else []),
            ]}


def serie_temporal(rotulos, series: list[dict], *, faixas=None, referencia=None, y_min=None, y_max=None,
                   casas: int = 2, tendencia: dict | None = None, sufixo: str = "") -> dict:
    """Linhas no tempo. A série com destaque=True ganha brilho, área em degradê e o último ponto pulsando;
    as demais ficam finas (traco="solid"|"dashed"|"dotted").

    series: [{nome, valores, cor?, destaque?, area?, traco?, simbolo?}] (None = mês sem dado; a linha liga os vizinhos;
    area=False tira o degradê do destaque; simbolo="emptyCircle" mostra marcador vazado em todos os pontos, inclusive na série de destaque).
    sufixo: texto depois do número no eixo e no tooltip ("%").
    faixas: [(rótulo_início, rótulo_fim, texto, "atual"|"ref")] sombreadas no fundo.
    referencia: (valor, texto) → linha tracejada horizontal.
    tendencia: {ini, y_ini, fim, y_fim, cor} → seta do nível inicial ao final, com os dois valores.
    """
    rot = list(map(str, rotulos))
    saida = []
    for s in series:
        cor, principal, simbolo = s.get("cor") or CIANO, bool(s.get("destaque")), s.get("simbolo")
        vals = [finito(v) for v in s["valores"]]
        item = {"type": "line", "name": s["nome"], "data": vals, "smooth": .25, "connectNulls": True,
                "symbol": simbolo or "circle", "symbolSize": 7 if simbolo else 5,
                "showSymbol": bool(simbolo) or not principal, "z": 4 if principal else 3,
                "lineStyle": {"width": 3.5 if principal else 2.2, "color": cor, "type": s.get("traco", "solid"),
                              "shadowBlur": 14 if principal else 0, "shadowColor": rgba(cor, .6)},
                "itemStyle": {"color": cor}}
        if principal and s.get("area", True):
            item["areaStyle"] = _area(cor, .26)
        saida.append(item)
        if principal and vals and vals[-1] is not None:
            saida.append(pulso(len(rot) - 1, vals[-1], cor))
    if saida and faixas:
        areas = [[{"xAxis": ini, "name": texto, "itemStyle": {"color": rgba("#5b6b7d", .08) if tipo == "ref"
                                                               else rgba(AZUL, .09)}}, {"xAxis": fim}]
                 for ini, fim, texto, tipo in faixas if ini in rot and fim in rot]
        saida[0]["markArea"] = {"silent": True, "data": areas,
                                "label": {"position": "insideTop", "color": TEMA["fraco"], "fontSize": 11,
                                          "fontWeight": 600}}
    if saida and referencia is not None:
        saida[0]["markLine"] = {"silent": True, "symbol": "none", "animation": False,
                                "label": {"formatter": referencia[1], "position": "insideEndTop",
                                          "color": TEMA["fraco"], "fontSize": 11},
                                "lineStyle": {"color": TEMA["meta"], "type": "dashed", "width": 1.2},
                                "data": [{"yAxis": referencia[0]}]}
    if tendencia and tendencia["ini"] in rot and tendencia["fim"] in rot:
        cor = tendencia.get("cor") or CIANO
        saida.append({"type": "line", "name": "_tendencia", "silent": True, "z": 7, "symbol": ["circle", "arrow"],
                      "symbolSize": [9, 15], "tooltip": {"show": False},
                      "data": [{"value": [rot.index(tendencia["ini"]), tendencia["y_ini"]],
                                "label": {"color": TEMA["valor"]}},
                               {"value": [rot.index(tendencia["fim"]), tendencia["y_fim"]], "label": {"color": cor}}],
                      "lineStyle": {"color": TEMA["valor"], "width": 2.2},
                      "itemStyle": {"color": TEMA["valor"], "borderColor": "#fff", "borderWidth": 1.5},
                      "label": {"show": True, "position": "top", "distance": 10, "fontWeight": 800, "fontSize": 13,
                                "formatter": JsCode("function (p) { return Number(p.value[1]).toLocaleString("
                                                    f"'pt-BR', {{minimumFractionDigits: {casas}, "
                                                    f"maximumFractionDigits: {casas}}}); }}")}})
    nomes = [s["nome"] for s in series]
    return {**base(),
            "grid": {"left": 8, "right": 24, "top": 44 if len(nomes) > 1 else 28, "bottom": 8, "containLabel": True},
            "legend": legenda(show=len(nomes) > 1, data=nomes),
            "tooltip": tooltip(trigger="axis", valueFormatter=num_js(casas, sufixo), axisPointer=_LINHA_EIXO),
            "xAxis": eixo_categoria(rot, boundaryGap=False),
            "yAxis": eixo_valor(num_js(min(casas, 1), sufixo), min=y_min, max=y_max),
            "series": saida}


def faixa_linha(rotulos, valores, meta: float, minimo: float, maximo: float, nome: str = "Índice") -> dict:
    """Evolução de um índice com faixa aceitável (mín–máx) em verde translúcido, linhas de Mínimo/Meta/Máximo e
    o índice em ciano com brilho; último ponto pulsando."""
    _, medio, bom = TEMA["situacao"]
    vals = [round(float(v), 2) for v in valores]
    num = num_js(2)
    return {**base(),
            "grid": {"left": 8, "right": 78, "top": 20, "bottom": 8, "containLabel": True},
            "tooltip": tooltip(trigger="axis", valueFormatter=num, axisPointer=_LINHA_EIXO),
            "xAxis": eixo_categoria(rotulos, boundaryGap=False),
            "yAxis": eixo_valor(min=0, max=max(maximo + 1, max(vals, default=0) * 1.15)),
            "series": [
                {"type": "line", "name": nome, "data": vals, "symbol": "none", "smooth": .3,
                 "lineStyle": {"width": 3.5, "color": CIANO, "shadowBlur": 14, "shadowColor": "rgba(0,184,230,.7)"},
                 "itemStyle": {"color": CIANO}, "areaStyle": _area(CIANO, .22),
                 "markArea": {"silent": True, "itemStyle": {"color": rgba(bom, .08)},
                              "data": [[{"yAxis": minimo}, {"yAxis": maximo}]]},
                 "markLine": {"silent": True, "symbol": "none", "animation": False, "label": {"position": "end"},
                              "data": [_linha_ref(minimo, f"Mínimo ({minimo:g})", medio),
                                       _linha_ref(meta, f"Meta ({meta:g})", bom),
                                       _linha_ref(maximo, f"Máximo ({maximo:g})", medio)]}},
                *([pulso(len(vals) - 1, vals[-1])] if vals else []),
            ]}


# ---------------------------------------------------------------- barras verticais

def _barra_sinal(v: float, c: str, raio: int = 6) -> dict:
    """Barra vertical a partir do zero: degradê da cor cheia para clara, topo (ou base) arredondado."""
    return {"value": v, "itemStyle": {
        "color": {"type": "linear", "x": 0, "y": 0 if v >= 0 else 1, "x2": 0, "y2": 1 if v >= 0 else 0,
                  "colorStops": [{"offset": 0, "color": c}, {"offset": 1, "color": mistura(c, "#ffffff", .35)}]},
        "borderRadius": [raio, raio, 0, 0] if v >= 0 else [0, 0, raio, raio],
        "shadowBlur": 8, "shadowColor": rgba(c, .5)}}


def _zero(texto: str = "") -> dict:
    return {"silent": True, "symbol": "none", "animation": False,
            "label": {"formatter": texto, "position": "insideEndTop", "color": TEMA["fraco"], "fontSize": 11}
            if texto else {"show": False},
            "lineStyle": {"color": TEMA["meta"], "width": 1.5}, "data": [{"yAxis": 0}]}


def desvio(rotulos, valores) -> dict:
    """Desvio da meta (%) por mês, centrado em zero, menor é melhor: ≤0 verde, acima vermelho; último mês
    pulsando."""
    ruim, _, bom = TEMA["situacao"]
    cor = lambda v: bom if v <= 0 else ruim  # noqa: E731
    vals = [round(float(v), 1) for v in valores]
    pct = JsCode("function (v) { return (v > 0 ? '+' : '') + Number(v).toLocaleString('pt-BR', "
                 "{maximumFractionDigits: 1}) + '%'; }")
    return {**base(),
            "grid": {"left": 8, "right": 16, "top": 20, "bottom": 8, "containLabel": True},
            "tooltip": tooltip(trigger="axis", axisPointer=_SOMBRA_EIXO, valueFormatter=pct),
            "xAxis": eixo_categoria(rotulos), "yAxis": eixo_valor(pct),
            "series": [{"type": "bar", "name": "Desvio", "data": [_barra_sinal(v, cor(v)) for v in vals],
                        "barMaxWidth": 22, "animationDelay": cascata(60), "markLine": _zero("na meta")},
                       *([pulso(len(vals) - 1, vals[-1], cor(vals[-1]), 8)] if vals else [])]}


def saldo(rotulos, valores, modo: str = "barra") -> dict:
    """Saldo por mês com sinal: superávit verde, déficit vermelho.
    modo="barra": barras a partir do zero, último mês pulsando.
    modo="area": saldo acumulado em linha com área; linha e área ficam vermelhas abaixo de zero.
    (A cor por sinal usa um degradê com corte no zero: visualMap junto com markLine quebra o componente.)"""
    ruim, _, bom = TEMA["situacao"]
    rot, vals = list(map(str, rotulos)), [round(float(v), 2) for v in valores]
    fmt = JsCode(BRL_JS)
    opcoes = {**base(), "grid": {"left": 8, "right": 16, "top": 20, "bottom": 8, "containLabel": True},
              "xAxis": eixo_categoria(rot, boundaryGap=modo == "barra"), "yAxis": eixo_valor(fmt)}
    ult = vals[-1] if vals else 0
    if modo == "area":
        topo, fundo = max(vals + [0]), min(vals + [0])
        z = topo / (topo - fundo) if topo != fundo else (0 if topo <= 0 else 1)

        def corte(alfa: float) -> dict:
            cp, cn = (rgba(CIANO, alfa), rgba(ruim, alfa)) if alfa < 1 else (CIANO, ruim)
            return {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1, "colorStops": [
                {"offset": 0, "color": cp}, {"offset": z, "color": cp}, {"offset": z, "color": cn},
                {"offset": 1, "color": cn}]}
        cor_ult = CIANO if ult >= 0 else ruim
        return {**opcoes, "tooltip": tooltip(trigger="axis", valueFormatter=fmt, axisPointer=_LINHA_EIXO),
                "series": [{"type": "line", "name": "Saldo acumulado", "data": vals, "symbol": "none", "smooth": .3,
                            "itemStyle": {"color": cor_ult},
                            "lineStyle": {"width": 3.5, "color": corte(1), "shadowBlur": 12,
                                          "shadowColor": rgba(cor_ult, .5)},
                            "areaStyle": {"color": corte(.25), "origin": 0}, "markLine": _zero()},
                           *([pulso(len(rot) - 1, ult, cor_ult)] if vals else [])]}
    cor = lambda v: bom if v >= 0 else ruim  # noqa: E731
    return {**opcoes, "tooltip": tooltip(trigger="axis", valueFormatter=fmt, axisPointer=_SOMBRA_EIXO),
            "series": [{"type": "bar", "name": "Saldo", "data": [_barra_sinal(v, cor(v)) for v in vals],
                        "barMaxWidth": 22, "markLine": _zero(), "animationDelay": cascata(40)},
                       *([pulso(len(rot) - 1, ult, cor(ult), 8)] if vals else [])]}


def barras_agrupadas(rotulos, series: list[tuple[str, list, str]]) -> dict:
    """Barras agrupadas por mês (nome, valores, cor): topo arredondado, degradê vertical com brilho, legenda no
    topo, valores em R$ (mi/mil)."""
    fmt = JsCode(BRL_JS)
    return {**base(),
            "grid": {"left": 8, "right": 16, "top": 40, "bottom": 8, "containLabel": True},
            "legend": legenda(itemHeight=8),
            "tooltip": tooltip(trigger="axis", valueFormatter=fmt, axisPointer=_SOMBRA_EIXO),
            "xAxis": eixo_categoria(rotulos), "yAxis": eixo_valor(fmt),
            "series": [{"type": "bar", "name": nome, "data": [round(float(v), 2) for v in valores],
                        "barMaxWidth": 16, "barGap": "20%",
                        "itemStyle": {"borderRadius": [6, 6, 0, 0], "shadowBlur": 8, "shadowColor": rgba(cor, .5),
                                      "color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1, "colorStops": [
                                          {"offset": 0, "color": cor}, {"offset": 1, "color": rgba(cor, .45)}]}},
                        "animationDelay": cascata(40, k * 120)}
                       for k, (nome, valores, cor) in enumerate(series)]}


def empilhado(rotulos, series: list[tuple[str, list, str]], nome_y: str = "", casas: int = 0,
              sufixo: str = "") -> dict:
    """Colunas empilhadas (nome, valores, cor), topo arredondado; rótulos inclinados com muitas categorias.
    Legenda clicável liga/desliga categorias. sufixo="%" fixa o eixo em 0–100."""
    rot = list(map(str, rotulos))
    extra = {"max": 100} if sufixo == "%" else {"minInterval": 1}
    return {**base(),
            "grid": {"left": 8, "right": 16, "top": 44, "bottom": 8, "containLabel": True},
            "legend": legenda(itemWidth=12, itemHeight=10),
            "tooltip": tooltip(trigger="axis", axisPointer=_SOMBRA_EIXO, valueFormatter=num_js(casas, sufixo)),
            "xAxis": eixo_categoria(rot, axisLabel={"color": TEMA["fraco"], "fontSize": 10, "interval": 0,
                                                    "rotate": 40 if len(rot) > 8 else 0}),
            "yAxis": eixo_valor(num_js(0, sufixo), name=nome_y, nameTextStyle={"color": TEMA["fraco"], "fontSize": 11},
                                **extra),
            "series": [{"type": "bar", "name": nome, "stack": "total", "barMaxWidth": 46,
                        "data": [round(finito(v) or 0, casas) for v in valores], "emphasis": {"focus": "series"},
                        "itemStyle": {"color": cor, "borderColor": "rgba(255,255,255,.7)", "borderWidth": 1,
                                      "borderRadius": [5, 5, 0, 0] if k == len(series) - 1 else 0},
                        "animationDelay": cascata(25, k * 150)}
                       for k, (nome, valores, cor) in enumerate(series)]}


def colunas(rotulos, valores, cores, casas: int = 1, sufixo: str = "", *, textos=None, rico: dict | None = None,
            largura: int = 46) -> dict:
    """Colunas verticais com o valor no topo, uma cor por coluna (storytelling: contexto em cinza, achado na cor
    de destaque); topo arredondado e entrada em cascata. textos: rótulo próprio de cada coluna (aceita "\\n"),
    também usado no tooltip; rótulos do eixo com quebra de linha também valem ("2027\\nsem meta"). rico: estilos
    do rich text do ECharts para textos como "{pos|+12%}\\n{v|703 mil}" (o tooltip mostra o texto sem marcação)."""
    vals = [finito(v) for v in valores]
    cores = [cores] * len(vals) if isinstance(cores, str) else list(cores)
    linhas = max((str(t).count("\n") + 1 for t in textos), default=1) if textos else 1
    dados = [{"value": None if v is None else round(v, casas),
              "itemStyle": {"color": c, "borderRadius": [6, 6, 0, 0], "shadowBlur": 8, "shadowColor": rgba(c, .25)}}
             for v, c in zip(vals, cores)]
    if textos:
        for d, t in zip(dados, textos):
            d["txt"] = t
    rotulo = _rotulo_txt() if textos else JsCode(
        f"function (p) {{ return Number(p.value).toLocaleString('pt-BR', "
        f"{{minimumFractionDigits: {casas}, maximumFractionDigits: {casas}}}) + '{sufixo}'; }}")
    return {**base(),
            "grid": {"left": 8, "right": 8, "top": 14 + 14 * linhas, "bottom": 8, "containLabel": True},
            "tooltip": (tooltip(trigger="item", formatter=JsCode(
                            "function (p) { return '<b>' + " + _ESC_NOME + ".replace(/\\n/g, ' ') + '</b><br>' + "
                            "p.data.txt.replace(/\\{\\w+\\|([^}]*)\\}/g, '$1').replace(/\\n/g, '<br>'); }"))
                        if textos else
                        tooltip(trigger="axis", axisPointer=_SOMBRA_EIXO, valueFormatter=num_js(casas, sufixo))),
            "xAxis": eixo_categoria(rotulos, axisLabel={"color": TEMA["fraco"], "fontSize": 11, "interval": 0}),
            "yAxis": eixo_valor(show=False, min=0,
                                max=max([v for v in vals if v is not None] + [0]) * (1.1 + .07 * linhas) or 1),
            "series": [{"type": "bar", "barMaxWidth": largura, "animationDelay": cascata(80), "data": dados,
                        "label": {"show": True, "position": "top", "color": TEMA["valor"], "fontSize": 12,
                                  "fontWeight": 700, "lineHeight": 15, "formatter": rotulo,
                                  **({"rich": rico} if rico else {})}}]}


def barras_proporcao(rotulos, series: list[tuple[str, list, str]], casas: int = 2, rotulo: int | None = 0) -> dict:
    """Barras horizontais empilhadas em % (0–100), uma por rótulo (1º no topo): cada série (nome, valores em %, cor)
    é uma parte. rotulo: índice da série que mostra o valor dentro da barra (None = nenhuma). Legenda embaixo."""
    def serie(k, nome, valores, cor):
        return {"type": "bar", "name": nome, "stack": "p", "barWidth": 38,
                "data": [None if v is None else round(float(v), casas) for v in valores],
                "itemStyle": {"color": cor, "borderRadius": 0},
                "label": {"show": k == rotulo, "position": "insideRight", "color": TEMA["valor"] if k else "#fff",
                          "fontSize": 13, "fontWeight": 700, "formatter": JsCode(
                              f"function (p) {{ return Number(p.value).toLocaleString('pt-BR', {{minimumFractionDigits: "
                              f"{casas}, maximumFractionDigits: {casas}}}) + '%'; }}")},
                "animationDelay": cascata(80, k * 200)}

    return {**base(),
            "grid": {"left": 8, "right": 24, "top": 16, "bottom": 40, "containLabel": True},
            "legend": legenda(top=None, right=None, bottom=0, left="center", itemWidth=14, itemHeight=6),
            "tooltip": tooltip(trigger="axis", axisPointer=_SOMBRA_EIXO, valueFormatter=num_js(casas, "%")),
            "xAxis": eixo_valor(num_js(casas, "%"), min=0, max=100),
            "yAxis": eixo_categoria(rotulos, inverse=True, axisLabel={"color": TEMA["texto"], "fontSize": 12}),
            "series": [serie(k, n, v, c) for k, (n, v, c) in enumerate(series)]}


def piramide(rotulos, esquerda, direita, nomes: tuple[str, str], cores: tuple[str, str], casas: int = 1,
             sufixo: str = "%") -> dict:
    """Pirâmide (ex.: etária): `esquerda` cresce para a esquerda e `direita` para a direita, rótulo na ponta."""
    m = max([abs(float(v)) for v in [*esquerda, *direita]] + [1]) * 1.25

    def serie(nome, vals, cor, sinal):
        return {"type": "bar", "name": nome, "stack": "p", "barWidth": "62%",
                "data": [round(sinal * float(v), casas) for v in vals],
                "itemStyle": {"color": cor, "borderRadius": [6, 0, 0, 6] if sinal < 0 else [0, 6, 6, 0],
                              "shadowBlur": 6, "shadowColor": rgba(cor, .3)},
                "label": {"show": True, "position": "left" if sinal < 0 else "right", "color": TEMA["valor"],
                          "fontSize": 11, "fontWeight": 600, "formatter": JsCode(
                              f"function (p) {{ return Math.abs(p.value).toLocaleString('pt-BR', {{minimumFractionDigits: "
                              f"{casas}, maximumFractionDigits: {casas}}}) + '{sufixo}'; }}")},
                "emphasis": {"focus": "series"}, "animationDelay": cascata(40)}

    return {**base(),
            "grid": {"left": 8, "right": 8, "top": 34, "bottom": 8, "containLabel": True},
            "legend": legenda(left="center", right=None, itemWidth=12, itemHeight=10),
            "tooltip": tooltip(trigger="axis", axisPointer=_SOMBRA_EIXO, valueFormatter=JsCode(
                f"function (v) {{ return Math.abs(v).toLocaleString('pt-BR', {{minimumFractionDigits: {casas}, "
                f"maximumFractionDigits: {casas}}}) + '{sufixo}'; }}")),
            "xAxis": {"type": "value", "min": -m, "max": m, "show": False},
            "yAxis": eixo_categoria(rotulos, axisLine={"show": False}, axisLabel={"color": TEMA["texto"], "fontSize": 11}),
            "series": [serie(nomes[0], esquerda, cores[0], -1), serie(nomes[1], direita, cores[1], 1)]}


# ---------------------------------------------------------------- barras horizontais e rankings

# nome da categoria escapado no tooltip HTML: rótulos vêm de dados (ex.: nome de empresa digitado no cadastro)
_ESC_NOME = "String(p.name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')"


def _rotulo_txt() -> JsCode:
    return JsCode("function (p) { return p.data.txt; }")


def _tooltip_txt() -> dict:
    return tooltip(trigger="item", formatter=JsCode(
        "function (p) { return '<b>' + " + _ESC_NOME + " + '</b><br>' + p.data.txt; }"))


def barras_h(rotulos, valores, cores, *, textos=None, casas: int = 2, sufixo: str = "",
             referencia: float | None = None, ref_texto: str = "", maximo: float | None = None) -> dict:
    """Barras horizontais arredondadas (1º item no topo), uma cor por barra (ou uma só), rótulo à direita.
    Com valores negativos a barra cresce para a esquerda e o trilho some. referencia: linha tracejada verde."""
    vals = [float(v) for v in valores]
    cores = [cores] * len(vals) if isinstance(cores, str) else list(cores)
    textos = list(textos) if textos else [br(v, casas, sufixo=sufixo) for v in vals]
    positivos = all(v >= 0 for v in vals)
    dados = [{"value": round(v, 4), "txt": txt, "label": {"position": "right" if v >= 0 else "left"},
              "itemStyle": {"color": degrade(c, invertido=v < 0), "shadowBlur": 8, "shadowColor": rgba(c, .3),
                            "borderRadius": 8 if positivos else ([0, 8, 8, 0] if v >= 0 else [8, 0, 0, 8])}}
             for v, c, txt in zip(vals, cores, textos)]
    serie = {"type": "bar", "data": dados, "barWidth": 13, "showBackground": positivos,
             "backgroundStyle": {"color": TEMA["trilho"], "borderRadius": 8},
             "label": {"show": True, "color": TEMA["valor"], "fontWeight": 700, "fontSize": 11, "formatter": _rotulo_txt()},
             "animationDelay": cascata(40)}
    if referencia is not None:
        serie["markLine"] = {"silent": True, "symbol": "none", "animation": False,
                             "label": {"formatter": ref_texto, "color": TEMA["fraco"], "fontSize": 11},
                             "lineStyle": {"color": TEMA["situacao"][2], "type": "dashed", "width": 1.5},
                             "data": [{"xAxis": referencia}]}
    return {**base(),
            "grid": {"left": 8, "right": 56, "top": 22, "bottom": 8, "containLabel": True},
            "tooltip": _tooltip_txt(),
            "xAxis": {"type": "value", "show": False,
                      "max": maximo if maximo is not None else max(vals + [referencia or 0, 0]) * 1.18 or 1,
                      "min": 0 if positivos else min(vals) - .14 * (max(vals + [0]) - min(vals))},  # espaço p/ rótulo
            "yAxis": eixo_categoria(rotulos, inverse=True, axisLine={"show": False},
                                    axisLabel={"color": TEMA["texto"], "fontSize": 11, "width": 210,
                                               "overflow": "truncate"}),
            "series": [serie]}


def barras_divergentes(rotulos, valores, textos=None, nome_eixo: str = "") -> dict:
    """Barras horizontais a partir do zero: positivo verde à direita, negativo vermelho à esquerda; 1º item no
    topo. textos: rótulo de cada barra (padrão: valor com sinal)."""
    ruim, _, bom = TEMA["situacao"]
    vals = [float(v) for v in valores]
    textos = list(textos) if textos else [br(v, 3, sinal=True) for v in vals]
    dados = [{"value": round(v, 4), "txt": txt, "label": {"position": "right" if v >= 0 else "left"},
              "itemStyle": {"color": degrade(c := bom if v >= 0 else ruim, invertido=v < 0),
                            "borderRadius": [0, 6, 6, 0] if v >= 0 else [6, 0, 0, 6],
                            "shadowBlur": 8, "shadowColor": rgba(c, .35)}} for v, txt in zip(vals, textos)]
    m = max([abs(v) for v in vals] + [.02]) * 2.2
    return {**base(),
            "grid": {"left": 8, "right": 16, "top": 12, "bottom": 30 if nome_eixo else 8, "containLabel": True},
            "tooltip": _tooltip_txt(),
            "xAxis": eixo_valor(num_js(2), min=-m, max=m, name=nome_eixo, nameLocation="middle", nameGap=26,
                                nameTextStyle={"color": TEMA["fraco"], "fontSize": 11}),
            "yAxis": eixo_categoria(rotulos, inverse=True, axisLine={"show": False},
                                    axisLabel={"color": TEMA["texto"], "fontSize": 12, "fontWeight": 600}),
            "series": [{"type": "bar", "data": dados, "barWidth": 16, "animationDelay": cascata(90),
                        "label": {"show": True, "color": TEMA["valor"], "fontWeight": 700, "fontSize": 12,
                                  "formatter": _rotulo_txt()},
                        "markLine": {"silent": True, "symbol": "none", "animation": False, "label": {"show": False},
                                     "lineStyle": {"color": TEMA["meta"], "width": 1.5}, "data": [{"xAxis": 0}]}}]}


def ranking(rotulos, valores, referencia: float, tolerancia: float, sufixo: str = "%", melhor: str = "alvo",
            alerta: float | None = None) -> dict:
    """Barras arredondadas com trilho e meta tracejada (1º item no topo).
    melhor="alvo": dentro da tolerância em ciano, fora em coral.
    melhor="menor" (custo): até a referência verde, acima vermelho (tolerância ignorada).
    melhor="alvo_situacao": dentro da tolerância verde, fora vermelho; com alerta (> tolerancia), a faixa entre
    tolerancia e alerta fica âmbar."""
    ruim, medio, bom = TEMA["situacao"]

    def cor(v: float) -> dict:
        dentro = abs(v - referencia) <= tolerancia
        if melhor == "menor":
            return degrade(bom if v <= referencia else ruim, clareia=.25)
        if melhor == "alvo_situacao":
            perto = alerta is not None and abs(v - referencia) <= alerta
            return degrade(bom if dentro else medio if perto else ruim, clareia=.25)
        return {"type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 0, "colorStops":
                [{"offset": 0, "color": AZUL}, {"offset": 1, "color": CIANO}] if dentro else
                [{"offset": 0, "color": "#c94040"}, {"offset": 1, "color": CORAL}]}
    vals = [float(v) for v in valores]
    rotulo = JsCode("function (p) { return Number(p.value).toLocaleString('pt-BR', {maximumFractionDigits: 1}) + '"
                    + sufixo + "'; }")
    return {**base(),
            "grid": {"left": 8, "right": 56, "top": 26, "bottom": 8, "containLabel": True},
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                "function (p) { return '<b>' + p.name + '</b><br>' + Number(p.value).toLocaleString('pt-BR', "
                "{maximumFractionDigits: 1}) + '" + sufixo + "'; }")),
            "xAxis": {"type": "value", "show": False, "max": max([referencia * 1.15] + [v * 1.1 for v in vals])},
            "yAxis": eixo_categoria(rotulos, inverse=True, axisLine={"show": False},
                                    axisLabel={"color": TEMA["texto"], "fontSize": 11, "width": 190,
                                               "overflow": "truncate"}),
            "series": [{"type": "bar", "barWidth": 14, "showBackground": True,
                        "data": [{"value": round(v, 2), "itemStyle": {"color": cor(v)}} for v in vals],
                        "backgroundStyle": {"color": TEMA["trilho"], "borderRadius": 8},
                        "itemStyle": {"borderRadius": 8, "shadowBlur": 10, "shadowColor": "rgba(0,184,230,.3)"},
                        "label": {"show": True, "position": "right", "color": TEMA["valor"], "fontWeight": 700,
                                  "fontSize": 12, "formatter": rotulo},
                        "animationDelay": cascata(90),
                        "markLine": {"symbol": "none", "silent": True,
                                     "label": {"formatter": "meta", "color": TEMA["fraco"], "fontSize": 11},
                                     "lineStyle": {"color": TEMA["meta"], "type": "dashed", "width": 1.5},
                                     "data": [{"xAxis": referencia}]}}]}


def pontos_ranking(rotulos, valores, destacado: str | None, referencia: float, sufixo: str = "%",
                   melhor: str = "menor") -> dict:
    """Ranking em pirulito: haste da referência até o ponto, ponto verde (lado bom) ou vermelho, a unidade
    escolhida pulsando com etiqueta. melhor="menor" (custo) ou "maior" (receita)."""
    ruim, _, bom = TEMA["situacao"]
    rot, vals = list(map(str, rotulos)), [round(float(v), 1) for v in valores]
    cor = (lambda v: bom if v <= referencia else ruim) if melhor == "menor" else \
        (lambda v: bom if v >= referencia else ruim)  # noqa: E731
    rotulo = JsCode("function (p) { return Number(p.value[0]).toLocaleString('pt-BR', {maximumFractionDigits: 1}) + '"
                    + sufixo + "'; }")
    series = [  # haste: barra invisível até min(ref, v) + barra fina de |v − ref|
        {"type": "bar", "stack": "h", "data": [min(referencia, v) for v in vals], "barWidth": 3, "silent": True,
         "itemStyle": {"color": "transparent"}, "tooltip": {"show": False}},
        {"type": "bar", "stack": "h", "barWidth": 3, "silent": True, "tooltip": {"show": False},
         "data": [{"value": abs(v - referencia), "itemStyle": {"color": rgba(cor(v), .35)}} for v in vals],
         "animationDelay": cascata(25)},
        {"type": "scatter", "name": "Unidades", "symbolSize": 11, "z": 4,
         "data": [{"value": [v, r], "itemStyle": {"color": cor(v)}} for v, r in zip(vals, rot) if r != destacado],
         "itemStyle": {"borderColor": TEMA["borda_bolha"], "borderWidth": 1.5, "shadowBlur": 8,
                       "shadowColor": "rgba(0,0,0,.25)"},
         "label": {"show": True, "position": "right", "color": TEMA["fraco"], "fontSize": 11, "formatter": rotulo},
         "animationDelay": cascata(25, 300),
         "markLine": {"silent": True, "symbol": "none", "animation": False,
                      "label": {"formatter": f"Ref. {referencia:g}{sufixo}", "position": "start",
                                "color": TEMA["fraco"], "fontSize": 11},
                      "lineStyle": {"color": TEMA["meta"], "type": "dashed", "width": 1.5},
                      "data": [{"xAxis": referencia}]}},
    ]
    if destacado in rot:
        v = vals[rot.index(destacado)]
        series.append(destaque(destacado, v, destacado, 16, br(v, 1, sufixo=sufixo), posicao="right"))
    return {**base(),
            "grid": {"left": 8, "right": 70, "top": 24, "bottom": 8, "containLabel": True},
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                "function (p) { var v = p.value || []; return '<b>' + v[1] + '</b><br>' + "
                "Number(v[0]).toLocaleString('pt-BR', {maximumFractionDigits: 1}) + '" + sufixo + "'; }")),
            "xAxis": eixo_valor(JsCode("function (v) { return v.toLocaleString('pt-BR') + '" + sufixo + "'; }"),
                                scale=True, axisLine={"show": True, "lineStyle": {"color": TEMA["linha"]}}),
            "yAxis": eixo_categoria(rot, inverse=True, axisLine={"show": False},
                                    axisLabel={"color": TEMA["texto"], "fontSize": 11, "width": 230,
                                               "overflow": "truncate"}),
            "series": series}


def faixa_ranking(rotulos, valores, destacado: str | None, minimo: float, meta: float, maximo: float) -> dict:
    """Ranking com faixa aceitável: barras sobre trilho; o destacado em ciano com brilho, dentro do intervalo
    verde, fora vermelho; faixa mín–máx e linhas Mín/Meta/Máx. Rótulos "X - Nome" mostram só o Nome."""
    ruim, medio, bom = TEMA["situacao"]
    rot = list(map(str, rotulos))
    dados = []
    for r, v in zip(rot, map(float, valores)):
        if r == destacado:
            cor, sombra = {"type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 0, "colorStops": [
                {"offset": 0, "color": AZUL}, {"offset": 1, "color": CIANO}]}, CIANO
        else:
            c = bom if minimo <= v <= maximo else ruim
            cor, sombra = degrade(c, clareia=.25), rgba(c, .4)
        dados.append({"value": round(v, 2), "itemStyle": {"color": cor, "shadowBlur": 10, "shadowColor": sombra}})
    fmt = JsCode("function (p) { return Number(p.value).toLocaleString('pt-BR', {minimumFractionDigits: 2, "
                 "maximumFractionDigits: 2}); }")
    return {**base(),
            "grid": {"left": 8, "right": 48, "top": 30, "bottom": 8, "containLabel": True},
            "tooltip": tooltip(trigger="item", formatter=fmt),
            "xAxis": eixo_valor(min=0, max=max([float(v) for v in valores] + [maximo]) * 1.2),
            "yAxis": eixo_categoria([r.split(" - ")[-1] for r in rot], axisLine={"show": False},
                                    axisLabel={"color": TEMA["texto"], "fontSize": 11, "fontWeight": 600}),
            "series": [{"type": "bar", "data": dados, "barWidth": 14, "showBackground": True,
                        "backgroundStyle": {"color": TEMA["trilho"], "borderRadius": 8}, "itemStyle": {"borderRadius": 8},
                        "label": {"show": True, "position": "right", "color": TEMA["valor"], "fontWeight": 700,
                                  "fontSize": 12, "formatter": fmt},
                        "animationDelay": cascata(90),
                        "markArea": {"silent": True, "itemStyle": {"color": rgba(bom, .07)},
                                     "data": [[{"xAxis": minimo}, {"xAxis": maximo}]]},
                        "markLine": {"silent": True, "symbol": "none", "animation": False, "label": {"position": "end"},
                                     "data": [_linha_ref(minimo, f"Mín ({minimo:g})", medio, "xAxis"),
                                              _linha_ref(meta, f"Meta ({meta:g})", bom, "xAxis"),
                                              _linha_ref(maximo, f"Máx ({maximo:g})", medio, "xAxis")]}}]}


# ---------------------------------------------------------------- correlação

def mapa_calor(rotulos, matriz, *, linhas=None, escala=None, casas: int = 2, sufixo: str = "") -> dict:
    """Mapa de calor. Padrão: correlação (−1 a 1, `rotulos` nas duas dimensões), vermelho negativo, branco perto de
    zero, navy positivo; |r| ≥ 0,5 em negrito.
    Com `escala` (cores do menor ao maior valor): valores quaisquer, colunas = `rotulos`, linhas = `linhas`,
    legenda de cor embaixo; None = célula vazia; texto branco nas células escuras."""
    if escala is None:
        rot = list(map(str, rotulos))
        dados = [{"value": [j, i, round(v, 2)], "label": {"color": "#fff" if abs(v) >= .6 else TEMA["valor"],
                                                          "fontWeight": 800 if abs(v) >= .5 else 500}}
                 for i, linha in enumerate(matriz) for j, v in enumerate(map(finito, linha)) if v is not None]
        return {**base(),
                "grid": {"left": 8, "right": 70, "top": 10, "bottom": 8, "containLabel": True},
                "tooltip": tooltip(trigger="item", formatter=JsCode(
                    "function (p) { var c = " + json.dumps(rot, ensure_ascii=False) + "; var v = p.value; "
                    "return '<b>' + c[v[0]] + ' × ' + c[v[1]] + '</b><br>r = ' + "
                    "Number(v[2]).toLocaleString('pt-BR', {minimumFractionDigits: 2}); }")),
                "visualMap": {"min": -1, "max": 1, "calculable": False, "orient": "vertical", "right": 0, "top": "middle",
                              "itemHeight": 200, "itemWidth": 10, "text": ["+1", "−1"],
                              "textStyle": {"color": TEMA["fraco"], "fontSize": 11},
                              "inRange": {"color": ["#c94040", "#f2b8a6", "#f6f8fb", "#9cc7e4", "#0f2540"]}},
                "xAxis": eixo_categoria(rot, axisLine={"show": False},
                                        axisLabel={"color": TEMA["texto"], "fontSize": 11, "interval": 0, "rotate": 30}),
                "yAxis": eixo_categoria(rot, inverse=True, axisLine={"show": False},
                                        axisLabel={"color": TEMA["texto"], "fontSize": 11}),
                "series": [{"type": "heatmap", "data": dados,
                            "label": {"show": True, "fontSize": 12, "formatter": JsCode(
                                "function (p) { return Number(p.value[2]).toLocaleString('pt-BR', "
                                "{minimumFractionDigits: 2}); }")},
                            "itemStyle": {"borderColor": "rgba(255,255,255,.9)", "borderWidth": 3, "borderRadius": 6},
                            "emphasis": {"itemStyle": {"shadowBlur": 12, "shadowColor": "rgba(0,184,230,.5)"}}}]}
    col, lin = list(map(str, rotulos)), list(map(str, linhas or rotulos))
    vals = [finito(v) for linha in matriz for v in linha]
    vals = [v for v in vals if v is not None]
    lo, hi = (min(vals), max(vals)) if vals else (0, 1)
    hi = hi if hi > lo else lo + 1
    fmt = (f"Number(p.value[2]).toLocaleString('pt-BR', {{minimumFractionDigits: {casas}, "
           f"maximumFractionDigits: {casas}}})")
    dados = [{"value": [j, i, round(v, casas)],
              "label": {"color": "#fff" if (v - lo) / (hi - lo) >= .6 else TEMA["valor"]}}
             for i, linha in enumerate(matriz) for j, v in enumerate(map(finito, linha)) if v is not None]
    return {**base(),
            "grid": {"left": 8, "right": 8, "top": 8, "bottom": 48, "containLabel": True},
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                "function (p) { var c = " + json.dumps(col, ensure_ascii=False) + ", l = "
                + json.dumps(lin, ensure_ascii=False) + "; return '<b>' + l[p.value[1]] + ' · ' + c[p.value[0]] "
                f"+ '</b><br>' + {fmt} + '{sufixo}'; }}")),
            "visualMap": {"min": lo, "max": hi, "calculable": False, "orient": "horizontal", "left": "center",
                          "bottom": 0, "itemWidth": 10, "itemHeight": 160, "text": [br(hi, casas), br(lo, casas)],
                          "textStyle": {"color": TEMA["fraco"], "fontSize": 11}, "inRange": {"color": list(escala)}},
            "xAxis": eixo_categoria(col, axisLine={"show": False},
                                    axisLabel={"color": TEMA["texto"], "fontSize": 11, "interval": 0}),
            "yAxis": eixo_categoria(lin, inverse=True, axisLine={"show": False},
                                    axisLabel={"color": TEMA["texto"], "fontSize": 11}),
            "series": [{"type": "heatmap", "data": dados,
                        "label": {"show": True, "fontSize": 11, "fontWeight": 600,
                                  "formatter": JsCode(f"function (p) {{ return {fmt}; }}")},
                        "itemStyle": {"borderColor": "rgba(255,255,255,.9)", "borderWidth": 3, "borderRadius": 6},
                        "emphasis": {"itemStyle": {"shadowBlur": 12, "shadowColor": "rgba(0,184,230,.5)"}}}]}


def dispersao(x, y, nome_x: str, nome_y: str, casas: int = 2) -> dict:
    """Pontos ciano com brilho e a reta de tendência (mínimos quadrados) tracejada."""
    pts = [[a, b] for a, b in ((finito(a), finito(b)) for a, b in zip(x, y)) if a is not None and b is not None]
    series = [{"type": "scatter", "name": "Pontos", "data": pts, "symbolSize": 11, "animationDelay": cascata(40),
               "itemStyle": {"color": CIANO, "borderColor": "#fff", "borderWidth": 1.5, "shadowBlur": 10,
                             "shadowColor": rgba(CIANO, .6)}}]
    xs = [p[0] for p in pts]
    if len(pts) >= 3 and max(xs) > min(xs):
        n = len(pts)
        mx, my = sum(xs) / n, sum(p[1] for p in pts) / n
        inc = sum((p[0] - mx) * (p[1] - my) for p in pts) / sum((v - mx) ** 2 for v in xs)
        a, b = min(xs), max(xs)
        series.append({"type": "line", "name": "Tendência", "silent": True, "symbol": "none",
                       "data": [[a, round(my + inc * (a - mx), 4)], [b, round(my + inc * (b - mx), 4)]],
                       "lineStyle": {"color": TEMA["situacao"][0], "type": "dashed", "width": 2}})
    eixo = eixo_valor(num_js(1), scale=True, axisLine={"lineStyle": {"color": TEMA["linha"]}}, nameLocation="middle",
                      nameTextStyle={"color": TEMA["texto"], "fontSize": 12, "fontWeight": 600})
    f = (f"function (v) {{ return Number(v).toLocaleString('pt-BR', {{minimumFractionDigits: {casas}, "
         f"maximumFractionDigits: {casas}}}); }}")
    return {**base(),
            "grid": {"left": 40, "right": 24, "top": 30, "bottom": 40, "containLabel": True, "show": True,
                     "borderColor": TEMA["moldura"], "borderWidth": 1, "backgroundColor": "transparent"},
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                f"function (p) {{ var f = {f}; return {json.dumps(nome_x, ensure_ascii=False)} + ': <b>' + "
                f"f(p.value[0]) + '</b><br>' + {json.dumps(nome_y, ensure_ascii=False)} + ': <b>' + "
                "f(p.value[1]) + '</b>'; }")),
            "xAxis": {**eixo, "name": nome_x, "nameGap": 30}, "yAxis": {**eixo, "name": nome_y, "nameGap": 44},
            "series": series}


def pontos(grupos: list[dict], nome_x: str, nome_y: str, *, destacado: tuple | None = None,
           ref_y: float | None = None, ref_texto: str = "", casas: int = 1, sufixo_x: str = "",
           sufixo_y: str = "") -> dict:
    """Pontos rotulados por grupo de cor, com legenda e linha de referência horizontal opcional.

    grupos: [{"nome", "cor", "pontos": [(x, y, rótulo), ...]}]; o rótulo aparece no tooltip.
    destacado: (x, y, rótulo) pulsando em ciano com etiqueta (unidade escolhida)."""
    fx = (f"Number(v[0]).toLocaleString('pt-BR', {{minimumFractionDigits: {casas}, maximumFractionDigits: {casas}}})"
          f" + '{sufixo_x}'")
    fy = (f"Number(v[1]).toLocaleString('pt-BR', {{minimumFractionDigits: {casas}, maximumFractionDigits: {casas}}})"
          f" + '{sufixo_y}'")
    dica = JsCode(f"function (p) {{ var v = p.value; return '<b>' + v[2] + '</b><br>' + "
                  f"{json.dumps(nome_x, ensure_ascii=False)} + ': ' + {fx} + '<br>' + "
                  f"{json.dumps(nome_y, ensure_ascii=False)} + ': ' + {fy}; }}")
    series = []
    for i, g in enumerate(grupos):
        s = {"type": "scatter", "name": g["nome"], "symbolSize": 10, "animationDelay": cascata(8, 200 * i),
             "data": [[finito(x), finito(y), r] for x, y, r in g["pontos"] if finito(x) is not None
                      and finito(y) is not None],
             "itemStyle": {"color": rgba(g["cor"], .75), "borderColor": mistura(g["cor"], "#0f2540", .3),
                           "borderWidth": 1}}
        if i == 0 and ref_y is not None:
            s["markLine"] = {"silent": True, "symbol": "none", "animation": False,
                             "label": {"formatter": ref_texto, "position": "insideEndTop", "color": TEMA["fraco"],
                                       "fontSize": 11},
                             "lineStyle": {"color": TEMA["meta"], "type": "dashed", "width": 1.5},
                             "data": [{"yAxis": ref_y}]}
        series.append(s)
    if destacado:
        x, y, r = destacado
        series.append(destaque(r, finito(x), finito(y), 16, r, posicao="top"))
    eixo = lambda nome, gap, suf: eixo_valor(num_js(0, suf), scale=True, name=nome, nameLocation="middle",  # noqa: E731
                                             nameGap=gap, axisLine={"show": True, "lineStyle": {"color": TEMA["linha"]}},
                                             nameTextStyle={"color": TEMA["texto"], "fontSize": 12, "fontWeight": 600})
    return {**base(),
            "legend": legenda(data=[g["nome"] for g in grupos]),
            "grid": {"left": 16, "right": 24, "top": 40, "bottom": 36, "containLabel": True},
            "tooltip": tooltip(trigger="item", formatter=dica),
            "xAxis": eixo(nome_x, 28, sufixo_x), "yAxis": eixo(nome_y, 40, sufixo_y),
            "series": series}
