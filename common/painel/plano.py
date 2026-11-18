"""Planos 0–1 com quadrantes: matriz de bolhas por grupo, rastro de um item no tempo, cenário (atual → simulado)
e bolhas rotuladas.

quadrantes: {"Alto X, Alto Y": (nome, cor_do_fundo), "Baixo X, Alto Y": ..., "Alto X, Baixo Y": ...,
"Baixo X, Baixo Y": ...}; o corte é 0,5 nos dois eixos.
"""
from __future__ import annotations

import json

from streamlit_echarts import JsCode

from .tema import CIANO, TEMA, base, cascata, destaque, mistura, rgba, tooltip

_CAIXAS = {"Baixo X, Alto Y": [[0, .5], [.5, 1]], "Alto X, Alto Y": [[.5, .5], [1, 1]],
           "Baixo X, Baixo Y": [[0, 0], [.5, .5]], "Alto X, Baixo Y": [[.5, 0], [1, .5]]}

def _tooltip_ponto(rotulo_x: str, rotulo_y: str) -> JsCode:
    """Nome do ponto e as duas coordenadas em pt-BR."""
    rx, ry = json.dumps(rotulo_x, ensure_ascii=False), json.dumps(rotulo_y, ensure_ascii=False)
    return JsCode("function (p) { var v = p.value || (p.data && p.data.value) || []; "
                  "var f = function (x) { return Number(x).toLocaleString('pt-BR', {minimumFractionDigits: 2, "
                  "maximumFractionDigits: 2}); }; "
                  f"return '<b>' + String(p.name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</b><br>' + {rx} + ' <b>' + f(v[0]) + '</b> · ' + {ry} + ' <b>' + "
                  "f(v[1]) + '</b>'; }")


def _quadrantes(quadrantes: dict[str, tuple[str, str]]) -> dict:
    """Fundo dos quadrantes em tom leve + cortes em 0,5; nome e código do quadrante nos cantos."""
    areas = [[{"coord": c0, "name": f"{quadrantes[q][0]}\n{q}",
               "itemStyle": {"color": quadrantes[q][1], "opacity": TEMA["quad_opacidade"]},
               "label": {"position": "insideBottomLeft" if "Baixo Y" in q else "insideTopLeft"}},
              {"coord": c1}] for q, (c0, c1) in _CAIXAS.items() if q in quadrantes]
    return {"type": "scatter", "name": "_quadrantes", "data": [[0, 0]], "symbolSize": 0, "silent": True,
            "tooltip": {"show": False}, "animation": False,
            "markArea": {"silent": True, "data": areas, "label": {"color": TEMA["quad_rotulo"], "fontSize": 12,
                                                                   "fontWeight": 600, "lineHeight": 16}},
            "markLine": {"silent": True, "symbol": "none", "label": {"show": False}, "animation": False,
                         "lineStyle": {"color": TEMA["corte"], "type": "dashed"}, "data": [{"xAxis": .5}, {"yAxis": .5}]}}


def _eixos(nome_x: str, nome_y: str) -> dict:
    eixo = {"type": "value", "min": 0, "max": 1, "interval": .25, "splitLine": {"show": False},
            "axisLine": {"lineStyle": {"color": TEMA["linha"]}}, "axisTick": {"show": False},
            "axisLabel": {"color": TEMA["fraco"], "fontSize": 11,
                          "formatter": JsCode("function (v) { return v.toLocaleString('pt-BR'); }")},
            "nameTextStyle": {"color": TEMA["texto"], "fontSize": 12, "fontWeight": 600}}
    return {"xAxis": {**eixo, "name": nome_x, "nameLocation": "middle", "nameGap": 30},
            "yAxis": {**eixo, "name": nome_y, "nameLocation": "middle", "nameGap": 42}}


def _grade(**extra) -> dict:
    return {"left": 34, "right": 24, "top": 30, "bottom": 40, "containLabel": True, "show": True,
            "borderColor": TEMA["moldura"], "borderWidth": 1, "backgroundColor": "transparent", **extra}


def _tooltip_matriz(rotulo_x: str, rotulo_y: str) -> JsCode:
    """Nome, grupo, X e Y, um detalhe livre e cada indicador, coloridos pelas notas (< 0,5 / < 0,8 / ≥ 0,8)."""
    ruim, medio, bom = TEMA["notas"]
    return JsCode(
        "function (p) { var d = p.data || {}; if (!d.ind) return ''; "
        "var f = function (v) { return Number(v).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }; "
        f"var c = function (v) {{ return v < .5 ? '{ruim}' : v < .8 ? '{medio}' : '{bom}'; }}; "
        "var h = '<b>' + d.name + '</b><br><span style=\"opacity:.7\">' + (d.grupo || '') + '</span><br><br>' + "
        f"{json.dumps(rotulo_x, ensure_ascii=False)} + ': <b style=\"color:' + c(d.value[0]) + '\">' + f(d.value[0]) + '</b><br>' + "
        f"{json.dumps(rotulo_y, ensure_ascii=False)} + ': <b style=\"color:' + c(d.value[1]) + '\">' + f(d.value[1]) + '</b><br>' + "
        "(d.detalhe ? d.detalhe + '<br>' : '') + '<br>'; "
        "d.ind.forEach(function (i) { h += '<span style=\"opacity:.75\">' + i[0] + ':</span> "
        "<b style=\"color:' + c(i[1]) + '\">' + f(i[1]) + '</b><br>'; }); return h; }")


def matriz(pontos: list[dict], quadrantes: dict[str, tuple[str, str]], nome_x: str, nome_y: str,
           alvo: str | None = None, legenda_vertical: bool = False, rotulo_x: str = "X", rotulo_y: str = "Y",
           prefixo_grupo: str = "") -> dict:
    """Bolhas por grupo sobre os quadrantes; o ponto `alvo` pulsa sem parar com etiqueta.

    pontos: {nome, x, y, tamanho, tipo (grupo), cor, ind: [[indicador, nota]], detalhe? (HTML do tooltip)}.
    Legenda "A (7)" com a contagem; clicar num grupo esconde/mostra. rotulo_x/rotulo_y: nomes no tooltip.
    """
    tipos = sorted({p["tipo"] for p in pontos})
    nomes = {tp: f"{tp} ({sum(p['tipo'] == tp for p in pontos)})" for tp in tipos}
    series = [_quadrantes(quadrantes)]
    for tp in tipos:
        cor = next(p["cor"] for p in pontos if p["tipo"] == tp)
        series.append({"type": "scatter", "name": nomes[tp], "animationDelay": cascata(12),
                       "data": [{"name": p["nome"], "value": [p["x"], p["y"]], "symbolSize": p["tamanho"],
                                 "grupo": f"{prefixo_grupo}{tp}", "ind": p.get("ind", []), "detalhe": p.get("detalhe")}
                                for p in pontos if p["tipo"] == tp],
                       # aro na cor da bolha (escurecida), sem halo branco que "lava" a bolha
                       "itemStyle": {"color": cor, "opacity": .82, "borderColor": mistura(cor, "#0f2540", .35),
                                     "borderWidth": 1.2, "shadowBlur": 4, "shadowColor": rgba(cor, .35)},
                       "emphasis": {"scale": 1.3, "itemStyle": {"borderColor": CIANO, "borderWidth": 2}}})
    escolhido = next((p for p in pontos if p["nome"] == alvo), None)
    if escolhido:
        e = escolhido
        series.append(destaque(e["nome"], e["x"], e["y"], max(e["tamanho"], 14), e["nome"].split(" - ", 1)[-1],
                               {"grupo": f"{prefixo_grupo}{e['tipo']}", "ind": e.get("ind", []),
                                "detalhe": e.get("detalhe")}))
    legenda = {"orient": "vertical", "left": 0, "top": "middle"} if legenda_vertical else {"top": 0, "right": 0}
    return {**base(),
            "grid": _grade(left=120 if legenda_vertical else 34, top=30 if legenda_vertical else 44),
            "legend": {**legenda, "icon": "circle", "itemWidth": 10, "itemHeight": 10, "itemGap": 12,
                       "data": [nomes[tp] for tp in tipos], "textStyle": {"color": TEMA["texto"], "fontSize": 12},
                       "inactiveColor": TEMA["inativo"]},
            "tooltip": tooltip(trigger="item", formatter=_tooltip_matriz(rotulo_x, rotulo_y)),
            **_eixos(nome_x, nome_y), "series": series}


def rastro(periodos, xs, ys, quadrantes: dict[str, tuple[str, str]], nome_x: str, nome_y: str,
           modo: str = "Movimento (início → atual)", rotulo_x: str = "X", rotulo_y: str = "Y") -> dict:
    """Trajetória de um item no plano, em três modos: "Animado" (linha do tempo que toca sozinha),
    "Movimento (início → atual)" (seta) e "Caminho completo" (todos os períodos)."""
    n = len(periodos)
    if not n:
        return {"title": {"text": "Sem histórico", "textStyle": {"color": TEMA["texto"]}}}
    xy = [[float(a), float(b)] for a, b in zip(xs, ys)]
    dica = tooltip(trigger="item", formatter=_tooltip_ponto(rotulo_x, rotulo_y))
    grade = _grade()

    if modo == "Animado":
        def quadro(k: int) -> list[dict]:
            return [_quadrantes(quadrantes),
                    {"type": "line", "name": "_trajetoria", "data": xy[:k + 1], "symbol": "none", "silent": True,
                     "smooth": .25, "lineStyle": {"color": "rgba(0,184,230,.6)", "width": 2.5, "shadowBlur": 10,
                                                  "shadowColor": CIANO}},
                    {"type": "scatter", "name": "_anteriores", "silent": True, "symbolSize": 9, "data": xy[:k],
                     "itemStyle": {"color": TEMA["anterior"], "borderColor": "#fff"}},
                    destaque(str(periodos[k]), *xy[k], 22, str(periodos[k]))]
        return {"baseOption": {**base(), "grid": {**grade, "bottom": 96}, "tooltip": dica, **_eixos(nome_x, nome_y),
                               "timeline": {"axisType": "category", "data": [str(p) for p in periodos],
                                            "currentIndex": 0, "autoPlay": True, "loop": True, "playInterval": 900,
                                            "left": "6%", "right": "6%", "bottom": 8,
                                            "lineStyle": {"color": TEMA["linha"]},
                                            "label": {"color": TEMA["fraco"], "fontSize": 11},
                                            "itemStyle": {"color": TEMA["inativo"]},
                                            "checkpointStyle": {"color": CIANO, "borderColor": "#fff",
                                                                "shadowBlur": 10, "shadowColor": CIANO},
                                            "controlStyle": {"color": TEMA["texto"], "borderColor": TEMA["texto"]},
                                            "progress": {"lineStyle": {"color": CIANO}, "itemStyle": {"color": CIANO},
                                                         "label": {"color": TEMA["valor"]}},
                                            "emphasis": {"label": {"color": TEMA["valor"]},
                                                         "controlStyle": {"color": CIANO, "borderColor": CIANO}}},
                               "series": quadro(0)},
                "options": [{"series": quadro(k)} for k in range(n)]}

    series = [_quadrantes(quadrantes)]
    if modo == "Caminho completo":
        series += [{"type": "line", "name": "_caminho", "data": xy, "symbol": "none", "silent": True, "smooth": .25,
                    "z": 6, "lineStyle": {"color": TEMA["caminho"], "width": 2}},
                   {"type": "scatter", "name": "Histórico", "z": 7, "animationDelay": cascata(80),
                    "data": [{"name": str(periodos[i]), "value": xy[i], "symbolSize": 8 + 8 * i / max(n - 1, 1)}
                             for i in range(n)],
                    "itemStyle": {"color": TEMA["anterior"], "borderColor": "#fff"}}]
    series += [{"type": "line", "name": "_movimento", "data": [xy[0], xy[-1]], "symbol": ["none", "arrow"],
                "symbolSize": 14, "silent": True, "z": 8,
                "lineStyle": {"color": CIANO, "width": 3, "shadowBlur": 12, "shadowColor": CIANO}},
               {"type": "scatter", "name": f"Início · {periodos[0]}", "z": 9, "symbolSize": 16,
                "data": [{"name": f"Início · {periodos[0]}", "value": xy[0]}],
                "itemStyle": {"color": "#fff", "borderColor": "#5b6b7d", "borderWidth": 2.5}},
               destaque(f"Atual · {periodos[-1]}", *xy[-1], 22, f"Atual · {periodos[-1]}")]
    return {**base(), "grid": grade, "legend": {"show": False}, "tooltip": dica, **_eixos(nome_x, nome_y),
            "series": series}


def cenario(fundo, atual, simulado, quadrantes: dict[str, tuple[str, str]], nome_x: str, nome_y: str) -> dict:
    """Plano com os demais itens em cinza, a posição atual (aro) e a simulada (ciano pulsando), ligadas por uma
    seta. fundo: [(x, y)]; atual / simulado: (x, y)."""
    ax, ay = (round(float(v), 3) for v in atual)
    sx, sy = (round(float(v), 3) for v in simulado)
    series = [_quadrantes(quadrantes),
              {"type": "scatter", "name": "Rede", "silent": True, "symbolSize": 7, "tooltip": {"show": False},
               "data": [[round(float(x), 3), round(float(y), 3)] for x, y in fundo],
               "itemStyle": {"color": TEMA["inativo"]}},
              {"type": "scatter", "name": "Atual", "z": 8, "symbolSize": 16, "data": [{"name": "Atual", "value": [ax, ay]}],
               "itemStyle": {"color": "rgba(255,255,255,.7)", "borderColor": "#5b6b7d", "borderWidth": 2.5}}]
    if (ax, ay) != (sx, sy):
        series.append({"type": "line", "name": "_seta", "silent": True, "z": 9, "symbol": ["none", "arrow"],
                       "symbolSize": 14, "data": [[ax, ay], [sx, sy]],
                       "lineStyle": {"color": CIANO, "width": 3, "shadowBlur": 12, "shadowColor": CIANO}})
    series.append(destaque("Simulado", sx, sy, 20, "Simulado"))
    return {**base(), "grid": _grade(), "legend": {"show": False},
            "tooltip": tooltip(trigger="item", formatter=_tooltip_ponto(nome_x, nome_y)),
            **_eixos(nome_x, nome_y), "series": series}


def bolhas(grupos: list[tuple[str, str, list[dict]]], quadrantes: dict[str, tuple[str, str]], nome_x: str,
           nome_y: str, rotulos: bool = True) -> dict:
    """Bolhas rotuladas sobre os quadrantes, um grupo por cor. grupos: [(nome, cor, [{nome, x, y, tamanho,
    tip (HTML do tooltip)}])]; a legenda aparece com mais de um grupo."""
    series = [_quadrantes(quadrantes)]
    for nome, cor, pontos in grupos:
        series.append({"type": "scatter", "name": nome, "clip": False, "animationDelay": cascata(30),
                       "data": [{"name": p["nome"], "value": [round(float(p["x"]), 3), round(float(p["y"]), 3)],
                                 "symbolSize": p.get("tamanho", 12), "tip": p.get("tip", "")} for p in pontos],
                       "itemStyle": {"color": cor, "opacity": .85, "borderColor": mistura(cor, "#0f2540", .35),
                                     "borderWidth": 1.2, "shadowBlur": 6, "shadowColor": rgba(cor, .4)},
                       "label": {"show": rotulos, "position": "top", "color": TEMA["fraco"], "fontSize": 10,
                                 "formatter": "{b}"},
                       "labelLayout": {"hideOverlap": True},
                       "emphasis": {"scale": 1.25, "itemStyle": {"borderColor": CIANO, "borderWidth": 2}}})
    return {**base(), "grid": _grade(top=40),
            "legend": {"show": len(grupos) > 1, "top": 0, "right": 0, "icon": "circle", "itemWidth": 10,
                       "itemHeight": 10, "data": [g[0] for g in grupos],
                       "textStyle": {"color": TEMA["texto"], "fontSize": 12}, "inactiveColor": TEMA["inativo"]},
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                "function (p) { return (p.data && p.data.tip) ? p.data.tip : p.name; }")),
            **_eixos(nome_x, nome_y), "series": series}
