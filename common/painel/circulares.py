"""Gráficos circulares: radar, medidor de % da meta, anel de execução, rosca de composição e velocímetro com zonas."""
from __future__ import annotations

import json

from streamlit_echarts import JsCode

from .tema import (AZUL, CIANO, FONTE, NAVY, TEMA, base, br, escala_execucao, legenda, mistura, rgba,
                        situacao_maior, situacao_menor, tooltip)

_EXCEDENTE = {"type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 1, "colorStops": [
    {"offset": 0, "color": AZUL}, {"offset": 1, "color": CIANO}]}
_TRILHO_ANEL = "rgba(15,37,64,.09)"


def _polar(raio: list[str], categorias: list[str]) -> dict:
    return {"polar": {"radius": raio, "center": ["50%", "50%"]},
            "angleAxis": {"max": 100, "startAngle": 90, "clockwise": True, "show": False},
            "radiusAxis": {"type": "category", "data": categorias, "show": False}}


def _texto_centro(texto: str, rich: dict, altura_linha: int | None = None) -> list[dict]:
    # texto de "graphic" usa fill (não color)
    estilo = {"text": texto, "rich": rich, "align": "center"}
    if altura_linha:
        estilo["lineHeight"] = altura_linha
    return [{"type": "text", "left": "center", "top": "middle", "silent": True, "style": estilo}]


def _ponta(categoria, valor, cor_brilho: str = CIANO, tamanho: int = 8) -> dict:
    """Ponto branco pulsando na ponta do traço excedente."""
    return {"type": "effectScatter", "coordinateSystem": "polar", "name": "_ponta", "silent": True, "z": 4,
            "data": [[categoria, valor]], "symbolSize": tamanho, "tooltip": {"show": False},
            "rippleEffect": {"scale": 3, "brushType": "stroke", "period": 2.4},
            "itemStyle": {"color": "#fff", "shadowBlur": 10, "shadowColor": cor_brilho}}


def radar(categorias: list[str], series: list[dict]) -> dict:
    """Radar 0–1: linha com brilho na cor de cada série, área em degradê do centro para fora; séries com
    dashed=True (período anterior) tracejadas e sem área. series: {name, value, color, dashed?}."""
    dados = []
    for s in series:
        cor, ant = s["color"], bool(s.get("dashed"))
        dados.append({
            "name": s["name"], "value": [round(float(v), 3) for v in s["value"]],
            "symbol": "circle", "symbolSize": 5 if ant else 8,
            "lineStyle": {"color": cor, "width": 2 if ant else 3, "type": "dashed" if ant else "solid",
                          "opacity": .75 if ant else 1, "shadowBlur": 0 if ant else 12, "shadowColor": cor},
            "itemStyle": {"color": cor, "borderColor": "#fff", "borderWidth": 0 if ant else 2},
            "areaStyle": {"opacity": 0} if ant else {"color": {"type": "radial", "x": .5, "y": .5, "r": .5, "colorStops": [
                {"offset": 0, "color": rgba(cor, .06)}, {"offset": 1, "color": rgba(cor, .38)}]}}})
    nomes = json.dumps(list(categorias), ensure_ascii=False)
    return {**base(),
            "legend": {"top": 0, "left": "center", "icon": "roundRect", "itemWidth": 14, "itemHeight": 4,
                       "textStyle": {"color": TEMA["texto"], "fontSize": 12}, "inactiveColor": TEMA["inativo"]},
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                "function (p) { var c = " + nomes + "; var v = p.value || []; "
                "var f = function (x) { return Number(x).toLocaleString('pt-BR', {minimumFractionDigits: 3, "
                "maximumFractionDigits: 3}); }; var h = '<b>' + String(p.name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</b><br>'; "
                "c.forEach(function (n, i) { h += '<span style=\"opacity:.75\">' + n + ':</span> <b>' + f(v[i]) + "
                "'</b><br>'; }); return h; }")),
            "radar": {"center": ["50%", "55%"], "radius": "66%", "splitNumber": 4, "shape": "polygon",
                      "indicator": [{"name": c, "max": 1} for c in categorias],
                      "axisName": {"color": TEMA["texto"], "fontSize": 12, "fontWeight": 600, "fontFamily": FONTE},
                      "splitLine": {"lineStyle": {"color": TEMA["linha"]}},
                      "splitArea": {"areaStyle": {"color": ["transparent", "rgba(0,149,204,.035)"]}},
                      "axisLine": {"lineStyle": {"color": TEMA["linha"]}}},
            "series": [{"type": "radar", "data": dados, "animationDuration": 1400, "animationEasing": "cubicOut",
                        "emphasis": {"lineStyle": {"width": 4}}}]}


def medidor(pct: float, cor: str | None = None, rotulo: str = "da meta", tamanho_pct: int = 26,
            maior_melhor: bool = False) -> dict:
    """Anel de % da meta: até 100% na cor da situação; o que passa de 100% vira um segundo traço (ciano quando
    é bom, vermelho escuro quando é ruim, como custo acima da meta) com ponto pulsando. No centro, % e rótulo."""
    cor = cor or (situacao_maior(pct) if maior_melhor else situacao_menor(pct))
    excesso = CIANO if maior_melhor else mistura(TEMA["situacao"][0], "#000000", .3)
    series = [{"type": "bar", "coordinateSystem": "polar", "roundCap": True, "barWidth": 12, "name": "% da meta",
               "showBackground": True, "backgroundStyle": {"color": _TRILHO_ANEL},
               "data": [{"value": round(min(pct, 100), 2), "itemStyle": {"color": cor}}],
               "itemStyle": {"shadowBlur": 10, "shadowColor": cor}, "animationDuration": 1400,
               "animationEasing": "cubicOut"}]
    if pct > 100:
        extra = round(min(pct - 100, 100), 2)
        series += [{"type": "bar", "coordinateSystem": "polar", "roundCap": True, "barWidth": 12, "barGap": "-100%",
                    "z": 3, "name": "Acima da meta", "data": [extra],
                    "itemStyle": {"color": excesso, "borderColor": "#fff", "borderWidth": 2, "shadowBlur": 12,
                                  "shadowColor": excesso}, "animationDuration": 1000, "animationDelay": 1300},
                   _ponta(0, extra, excesso, 7)]
    rich = {"p": {"fill": TEMA["valor"], "fontSize": tamanho_pct, "fontWeight": 800, "fontFamily": FONTE,
                  "lineHeight": tamanho_pct + 4},
            "r": {"fill": TEMA["fraco"], "fontSize": 11, "fontFamily": FONTE, "lineHeight": 14}}
    texto = f"{{p|{pct:.0f}%}}" + (f"\n{{r|{rotulo}}}" if rotulo else "")
    return {**base(), "tooltip": {"show": False}, **_polar(["70%", "88%"], ["a"]),
            "graphic": _texto_centro(texto, rich), "series": series}


def anel(item: dict) -> dict:
    """Anel de execução de uma meta: até 100% na cor da escala_execucao (≥100 azul, ≥95 verde forte, ≥90 verde,
    ≥80 âmbar, <80 vermelho); acima disso, segundo traço ciano com borda branca e brilho (até uma volta extra) e
    ponto pulsando na ponta. No centro: Executado, Meta e Saldo. item: {nome, real, meta, pct, publico?}, com
    publico = [(nome, valor), ...] opcional (divisão do executado, mostrada no tooltip)."""
    pct, cor = item["pct"], escala_execucao(item["pct"])
    n = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731
    saldo = item["real"] - item["meta"]
    publico = [(nome, float(v)) for nome, v in item.get("publico") or []]
    total_pub = sum(v for _, v in publico)
    linhas_pub = "".join(f"<br>{nome} <b>{n(v)}</b> ({br(v / total_pub * 100, 1)}%)" for nome, v in publico
                         if total_pub)
    dado = {"name": item["nome"], "real": item["real"], "meta": item["meta"], "pct": round(pct, 2),
            "pub": linhas_pub}
    series = [{"type": "bar", "coordinateSystem": "polar", "name": "Execução", "roundCap": True, "barWidth": 16,
               "showBackground": True, "backgroundStyle": {"color": _TRILHO_ANEL},
               "data": [{**dado, "value": round(min(pct, 100), 2), "itemStyle": {"color": cor}}],
               "itemStyle": {"shadowBlur": 10, "shadowColor": cor}, "animationDuration": 1400,
               "animationEasing": "cubicOut"}]
    if pct > 100:
        extra = round(min(pct - 100, 100), 2)
        series += [{"type": "bar", "coordinateSystem": "polar", "name": "Acima da meta", "roundCap": True,
                    "barWidth": 16, "barGap": "-100%", "z": 3, "data": [{**dado, "value": extra}],
                    "itemStyle": {"color": _EXCEDENTE, "borderColor": "#fff", "borderWidth": 2, "shadowBlur": 14,
                                  "shadowColor": CIANO},
                    "animationDuration": 1100, "animationDelay": 1300, "animationEasing": "cubicOut"},
                   _ponta(item["nome"], extra)]
    pilula = lambda c: {"fill": c, "fontWeight": 700, "fontSize": 13, "fontFamily": FONTE,  # noqa: E731
                        "borderColor": c, "borderWidth": 1.5, "borderRadius": 12, "padding": [3, 10]}
    rich = {"r": {"fill": TEMA["fraco"], "fontSize": 11, "fontFamily": FONTE, "lineHeight": 16},
            "e": pilula(cor), "m": pilula(TEMA["texto"]),
            "s": pilula(TEMA["situacao"][2] if saldo >= 0 else TEMA["situacao"][0])}
    texto = (f"{{r|Executado}}\n{{e|{n(item['real'])}}}\n{{r|Meta}}\n{{m|{n(item['meta'])}}}\n"
             f"{{r|Saldo}}\n{{s|{'+' if saldo > 0 else ''}{n(saldo)}}}")
    return {**base(),
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                "function (p) { var d = p.data || {}; if (d.meta == null) return ''; "
                "var n = function (v) { return Number(v).toLocaleString('pt-BR'); }; var s = d.real - d.meta; "
                "return '<b>' + d.name + '</b><br>Executado <b>' + n(d.real) + '</b><br>Meta <b>' + n(d.meta) + "
                "'</b><br>Saldo <b>' + (s > 0 ? '+' : '') + n(s) + '</b><br>Execução <b>' + "
                "Number(d.pct).toLocaleString('pt-BR', {maximumFractionDigits: 0}) + '%</b>' + (d.pub || ''); }")),
            **_polar(["74%", "92%"], [item["nome"]]), "graphic": _texto_centro(texto, rich, 26), "series": series}


def velocimetro(indice: float, minimo: float, meta: float, maximo: float) -> dict:
    """Velocímetro de 0 ao máximo com zonas: abaixo do mínimo (vermelho), mínimo–meta (verde) e meta–máximo
    (âmbar); ponteiro com brilho na cor da situação (perto da meta verde, no intervalo âmbar, fora vermelho)."""
    ruim, medio, bom = TEMA["situacao"]
    cor = bom if abs(indice - meta) <= .5 else medio if minimo <= indice <= maximo else ruim
    return {**base(), "tooltip": {"show": False},
            "series": [{"type": "gauge", "min": 0, "max": maximo, "startAngle": 210, "endAngle": -30,
                        "radius": "92%", "center": ["50%", "58%"], "progress": {"show": False},
                        "axisLine": {"roundCap": True, "lineStyle": {"width": 12, "color": [
                            [minimo / maximo, rgba(ruim, .35)], [meta / maximo, rgba(bom, .35)],
                            [1, rgba(medio, .35)]]}},
                        "pointer": {"length": "58%", "width": 5, "itemStyle": {"color": cor, "shadowBlur": 10,
                                                                                 "shadowColor": cor}},
                        "anchor": {"show": True, "size": 12, "itemStyle": {"color": cor, "borderColor": "#fff",
                                                                           "borderWidth": 2}},
                        "axisTick": {"show": False}, "splitLine": {"show": False}, "title": {"show": False},
                        "axisLabel": {"distance": -30, "fontSize": 10, "color": TEMA["fraco"], "formatter": JsCode(
                            "function (v) { return v.toLocaleString('pt-BR', {maximumFractionDigits: 1}); }")},
                        "detail": {"formatter": br(indice, 2), "fontSize": 24, "fontWeight": 800, "color": cor,
                                   "offsetCenter": [0, "48%"], "fontFamily": FONTE},
                        "data": [{"value": round(min(max(indice, 0), maximo), 2)}],
                        "animationDuration": 1400, "animationEasing": "cubicOut"}]}


def rosca(nomes, valores, cores, valor_centro: str, rotulo_centro: str, unidade: str = "") -> dict:
    """Composição em até 3 fatias (nome, valor, cor): total no centro, % de cada fatia na legenda (sem rótulo na
    fatia, que corta em cartão estreito). unidade: texto do tooltip depois do valor ("pessoas")."""
    vals = [float(v) for v in valores]
    total = sum(vals) or 1
    parte = {n: br(100 * v / total, 1, sufixo="%") for n, v in zip(nomes, vals)}
    dados = [{"name": n, "value": round(v, 1), "itemStyle": {"color": c, "shadowBlur": 10, "shadowColor": rgba(c, .35)}}
             for n, v, c in zip(nomes, vals, cores) if v > 0]
    return {**base(),
            "tooltip": tooltip(trigger="item", formatter=JsCode(
                "function (p) { return '<b>' + String(p.name).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</b><br>' + Number(p.value).toLocaleString('pt-BR', "
                f"{{maximumFractionDigits: 0}}) + ' {unidade} (' + p.percent.toLocaleString('pt-BR') + '%)'; }}")),
            "legend": legenda(left="center", right=None, top=None, bottom=0, itemWidth=12, itemHeight=10,
                              formatter=JsCode("function (n) { var p = " + json.dumps(parte, ensure_ascii=False)
                                               + "; return n + '  ' + p[n]; }")),
            "graphic": [{"type": "text", "left": "center", "top": "42%", "style": {
                "text": f"{valor_centro}\n{rotulo_centro}", "textAlign": "center", "fill": NAVY,
                "font": f"800 17px {FONTE}", "lineHeight": 22}}],
            "series": [{"type": "pie", "radius": ["52%", "78%"], "center": ["50%", "45%"], "padAngle": 2,
                        "itemStyle": {"borderRadius": 8, "borderColor": "#fff", "borderWidth": 2},
                        "label": {"show": False}, "labelLine": {"show": False}, "data": dados,
                        "emphasis": {"scale": True, "scaleSize": 6}}]}
