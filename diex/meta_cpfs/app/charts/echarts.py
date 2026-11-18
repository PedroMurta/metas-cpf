"""Configuração compartilhada para gráficos ECharts do dashboard."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import html
import json
import math
import re
import zlib

import numpy as np
import streamlit as st
from streamlit_echarts import JsCode, st_echarts

from common import painel as gt
from common.painel.tema import CIANO, TEMA as GT, pulso as gt_pulso
from charts.theme import formatar_percentuais


ASSUNTOS = {
    "institucional": "#0095cc",
    "sest": "#1f8f5f",
    "senat": "#e07b1a",
    "comunicacao": "#6b4fbb",
    "transporte": "#c99a12",
}
FORTE = "#0f2540"
CONTEXTO = "#c5ced8"
CONTEXTO2 = "#94a3b8"
TEXTO = "#5a6a7e"
GRADE = "#e5e9ef"
ALERTA = "#c94040"
SUCESSO = "#1a9e6e"
FONTE = "Inter, sans-serif"


def destaque(assunto: str = "institucional") -> str:
    return ASSUNTOS[assunto]


def destacar(categorias, alvos, assunto: str = "institucional") -> list[str]:
    alvos = {alvos} if isinstance(alvos, str) else set(alvos)
    return [destaque(assunto) if categoria in alvos else CONTEXTO for categoria in categorias]


def sequencial(n: int, assunto: str = "institucional") -> list[str]:
    a, b, c = "#f1f5f9", destaque(assunto), FORTE

    def mistura(cor_a: str, cor_b: str, proporcao: float) -> str:
        canais_a = [int(cor_a[i:i + 2], 16) for i in (1, 3, 5)]
        canais_b = [int(cor_b[i:i + 2], 16) for i in (1, 3, 5)]
        canais = [round(x + (y - x) * proporcao) for x, y in zip(canais_a, canais_b)]
        return "#" + "".join(f"{canal:02x}" for canal in canais)

    cores = []
    for indice in range(n):
        posicao = indice / max(n - 1, 1)
        if posicao <= 0.5:
            cores.append(mistura(a, b, posicao * 2))
        else:
            cores.append(mistura(b, c, (posicao - 0.5) * 2))
    return cores


def divergente(assunto: str = "institucional") -> list[str]:
    return [ALERTA if assunto == "institucional" else FORTE, GRADE, destaque(assunto)]


def tema_echarts(assunto: str = "institucional") -> dict:
    eixo = {
        "axisLine": {"lineStyle": {"color": GRADE}},
        "axisTick": {"show": False},
        "axisLabel": {"color": TEXTO, "fontSize": 12},
        "splitLine": {"show": False},
    }
    return {
        "color": [destaque(assunto), CONTEXTO2, CONTEXTO],
        "backgroundColor": "transparent",
        "textStyle": {"fontFamily": FONTE, "color": TEXTO},
        "legend": {"textStyle": {"color": TEXTO, "fontSize": 12}},
        "tooltip": dict(GT["tooltip"]),
        "categoryAxis": deepcopy(eixo),
        "valueAxis": {**deepcopy(eixo), "axisLine": {"show": False}},
        "animationDuration": 900,
        "animationDurationUpdate": 800,
        "animationEasing": "cubicOut",
    }


def _cor_legada(cor, padrao: str) -> str:
    if isinstance(cor, list):
        return padrao
    if not isinstance(cor, str):
        return padrao
    cor = cor.lower().strip()
    if cor in {"rgba(0,0,0,0)", "rgba(0, 0, 0, 0)", "transparent"}:
        return "rgba(0,0,0,0)"
    alfa = 1.0
    if cor.startswith("rgb"):
        partes = re.findall(r"[\d.]+", cor)
        if len(partes) < 3:
            return padrao
        alfa = float(partes[3]) if len(partes) > 3 else 1.0
        cor = "#" + "".join(f"{int(float(valor)):02x}" for valor in partes[:3])
    equivalencias = {
        "#0c64a3": destaque(), "#00689d": destaque(), "#0095cc": destaque(),
        "#3298cb": CONTEXTO2, "#2a78d6": destaque(), "#4a81bf": destaque(), "#87bed8": CONTEXTO,
        "#005a86": destaque(), "#1484b8": CONTEXTO2, "#53a8d1": CONTEXTO, "#94c9e2": CONTEXTO,
        "#1f8f5f": ASSUNTOS["sest"], "#15803d": SUCESSO, "#0ca30c": SUCESSO,
        "#ea580c": ASSUNTOS["senat"], "#e07b1a": ASSUNTOS["senat"], "#d26a32": ASSUNTOS["senat"],
        "#d97706": ASSUNTOS["transporte"], "#c99a12": ASSUNTOS["transporte"],
        "#c0392b": ALERTA, "#b91c1c": ALERTA, "#e06666": ALERTA,
        "#7627d6": CONTEXTO2, "#8fac1b": CONTEXTO2, "#94a3b8": CONTEXTO2,
        "#6b7280": TEXTO, "#c5ced8": CONTEXTO, "#ffffff": "#ffffff", "white": "#ffffff", "black": FORTE,
    }
    cor = equivalencias.get(cor, cor if re.fullmatch(r"#[0-9a-f]{6}", cor) else padrao)
    if alfa < 1:
        canais = ", ".join(str(int(cor[i:i + 2], 16)) for i in (1, 3, 5))
        return f"rgba({canais}, {alfa:g})"
    return cor


def _dados_lista(valor):
    if valor is None:
        return []
    if hasattr(valor, "tolist"):
        return valor.tolist()
    return list(valor) if isinstance(valor, (tuple, list)) else [valor]


def _rotulo_titulo(texto):
    return texto if isinstance(texto, str) else (texto or {}).get("text", "")


def _numero_ptbr(valor, casas: int | None = None, sinal: bool = False) -> str:
    if valor is None:
        return "—"
    numero = float(valor)
    if casas is None:
        casas = 0 if numero.is_integer() else 2
    exibicao = f"{abs(numero):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    prefixo = "+" if sinal and numero >= 0 else "−" if numero < 0 else ""
    return prefixo + exibicao


def _rotulo_ptbr(texto) -> str:
    return formatar_percentuais(texto) if isinstance(texto, str) else str(texto)


def _texto_rico(html: str, estilo: str) -> str:
    """Converte <br> e <b> do Plotly em linhas de texto rico do ECharts."""
    linhas = []
    for linha in re.split(r"<br\s*/?>", html, flags=re.I):
        partes = re.split(r"(<b>.*?</b>)", linha, flags=re.I)
        trechos = []
        for parte in partes:
            negrito = parte.lower().startswith("<b>")
            texto = _rotulo_ptbr(re.sub(r"<[^>]+>", "", parte)).replace("|", "/").replace("}", ")")
            if texto:
                trechos.append(f"{{{estilo}{'b' if negrito else ''}|{texto}}}")
        linhas.append("".join(trechos))
    return "\n".join(linhas)


def _tooltip_ptbr(template: str | None, contexto: dict, fallback: str) -> str:
    if not template:
        return fallback
    template = re.sub(r"<extra>.*?</extra>", "", template, flags=re.S)
    conteudo = re.sub(r"%\{[^}]+\}", "", template)

    def formatar(match):
        expressao = match.group(1)
        campo, separador, formato = expressao.partition(":")
        data_format = ""
        if "|" in campo:
            campo, data_format = campo.split("|", 1)
        if campo == "fullData.name":
            valor = contexto.get("name", "")
        elif campo.startswith("customdata["):
            indice = int(re.search(r"\d+", campo).group())
            dados = contexto.get("customdata") or []
            valor = dados[indice] if indice < len(dados) else ""
        else:
            valor = contexto.get(campo, "")
        if data_format and valor:
            try:
                valor = datetime.fromisoformat(str(valor).replace("Z", "+00:00")).strftime(data_format)
            except ValueError:
                pass
        if isinstance(valor, (int, float)) and not isinstance(valor, bool):
            casas_match = re.search(r"\.(\d+)f", formato)
            casas = int(casas_match.group(1)) if casas_match else None
            percentual = "%" in conteudo
            moeda = "R$" in conteudo
            if percentual or moeda:
                casas = 2
            valor = _numero_ptbr(valor, casas, sinal="+" in formato)
        elif campo == "text":
            valor = _rotulo_ptbr(valor)
        return str(valor)

    return re.sub(r"%\{([^}]+)\}", formatar, template).strip()


def _normalizar(valor):
    if isinstance(valor, dict):
        return {chave: _normalizar(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_normalizar(item) for item in valor]
    if getattr(getattr(valor, "dtype", None), "kind", "") == "M":
        return [None if texto == "NaT" else texto for texto in np.datetime_as_string(valor, unit="D").tolist()]
    if hasattr(valor, "isoformat") and hasattr(valor, "year"):
        return valor.isoformat()[:10]
    if hasattr(valor, "tolist"):
        return _normalizar(valor.tolist())
    if hasattr(valor, "item"):
        return _normalizar(valor.item())
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    return valor


def _de_plotly(fig) -> dict:
    """Converte os tipos de figura legados em opções nativas do ECharts."""
    figura = _normalizar(fig.to_plotly_json())
    for indice, trace in enumerate(fig.data):
        for campo in ("x", "y", "z", "measure", "text", "customdata"):
            valor = getattr(trace, campo, None)
            if valor is not None:
                figura["data"][indice][campo] = _normalizar(valor)
    layout, traces = figura.get("layout", {}), figura.get("data", [])
    horizontal = any(t.get("type") == "bar" and t.get("orientation") == "h" for t in traces)
    margens = layout.get("margin", {}) or {}
    categorias = []
    for trace in traces:
        eixo = "y" if horizontal and trace.get("type") == "bar" else "x"
        for item in _dados_lista(trace.get(eixo)):
            if item is not None and not isinstance(item, (list, dict)):
                categoria = str(item)
                if categoria not in categorias:
                    categorias.append(categoria)
    if categorias and all(re.fullmatch(r"[+-]?\d+(?:\.\d+)?", item) for item in categorias):
        categorias.sort(key=float)
    datas = bool(categorias) and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", item) for item in categorias)
    if datas:
        categorias.sort()

    xaxis = layout.get("xaxis", {})
    yaxis = layout.get("yaxis", {})
    visivel_x, visivel_y = xaxis.get("visible", True), yaxis.get("visible", True)
    margem_esquerda = max(68 if not horizontal and yaxis.get("title") else 8, margens.get("l", 8))
    margem_inferior = max(40 if xaxis.get("title") else 8, margens.get("b", 8))
    titulo = _rotulo_titulo(layout.get("title", {}).get("text", ""))
    legenda = layout.get("legend") or {}
    mostra_legenda = layout.get("showlegend", len(traces) > 1)
    legenda_embaixo = (legenda.get("y") or 1) < 0
    # O título é renderizado fora do gráfico: a margem que o Plotly reservava para ele vira área útil.
    margem_superior = margens.get("t", 24) - (84 if titulo else 0)
    margem_superior = max(40 if mostra_legenda and not legenda_embaixo else 16, margem_superior)
    opcoes = {
        "grid": {"left": max(8, min(24, margens.get("l", 8))) if horizontal else margem_esquerda,
                 "right": max(72 if horizontal else 16, margens.get("r", 16)),
                 "top": margem_superior, "bottom": (max(margem_inferior, 48) + (28 if xaxis.get("title") else 0)
                            if mostra_legenda and legenda_embaixo else margem_inferior),
                 "containLabel": True},
        "legend": {"show": mostra_legenda, "type": "scroll", **({"bottom": 0} if legenda_embaixo else {"top": 0}),
                   "orient": "horizontal" if legenda.get("orientation") == "h" else "vertical"},
        "series": [],
        "_titulo": titulo,
        "_altura": layout.get("height", 380),
    }
    eixo_x = {"type": "value" if horizontal else "category", "data": None if horizontal else categorias,
              "axisLabel": {"show": xaxis.get("showticklabels", True) and visivel_x, "color": TEXTO,
                            "fontSize": 12},
              "axisLine": {"show": visivel_x}, "axisTick": {"show": visivel_x},
              "splitLine": {"show": xaxis.get("showgrid", False) and visivel_x,
                            "lineStyle": {"color": GRADE}}}
    eixo_y = {"type": "category" if horizontal else "value",
              "data": categorias if horizontal else None,
              "axisLabel": {"show": yaxis.get("showticklabels", True) and visivel_y, "color": TEXTO,
                            "fontSize": 12},
              "axisLine": {"show": visivel_y}, "axisTick": {"show": visivel_y},
              "splitLine": {"show": yaxis.get("showgrid", True) and visivel_y,
                            "lineStyle": {"color": GRADE}}}
    if horizontal:
        eixo_y["axisLabel"].update({"width": 170, "overflow": "truncate", "ellipsis": "..."})
        eixo_y["inverse"] = yaxis.get("autorange") == "reversed"
    else:
        eixo_x["inverse"] = xaxis.get("autorange") == "reversed"
    for eixo, fonte in ((eixo_x, xaxis), (eixo_y, yaxis)):
        titulo_eixo = fonte.get("title")
        if titulo_eixo:
            eixo["name"] = _rotulo_titulo(titulo_eixo)
            eixo["nameLocation"] = "middle"
            eixo["nameGap"] = 42
        faixa = fonte.get("range")
        if faixa and eixo["type"] == "value":
            eixo["min"], eixo["max"] = faixa
        sufixo = fonte.get("ticksuffix")
        if sufixo:
            percentual = sufixo == "%"
            casas = "{ minimumFractionDigits: 2, maximumFractionDigits: 2 }" if percentual else \
                "{ maximumFractionDigits: 2 }"
            eixo["axisLabel"]["formatter"] = JsCode(
                f"function (valor) {{ return Number(valor).toLocaleString('pt-BR', {casas}) + '{sufixo}'; }}"
            )
        elif eixo["type"] == "value":
            if fonte.get("tickformat") in {"~s", "s"}:
                eixo["axisLabel"]["formatter"] = JsCode(
                    "function (valor) { const n = Number(valor); const a = Math.abs(n); "
                    "const d = a >= 1e6 ? 1e6 : a >= 1e3 ? 1e3 : 1; "
                    "const u = a >= 1e6 ? ' mi' : a >= 1e3 ? ' mil' : ''; "
                    "return (n / d).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + u; }"
                )
            else:
                eixo["axisLabel"]["formatter"] = JsCode(
                    "function (valor) { return Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 2 }); }"
                )
    if datas:
        eixo_x["axisLabel"]["formatter"] = JsCode(
            "function (valor) { const m = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']; "
            "return m[Number(valor.slice(5, 7)) - 1] + '/' + valor.slice(2, 4); }"
        )
    opcoes["xAxis"], opcoes["yAxis"] = eixo_x, eixo_y

    modo = layout.get("barmode")
    n_barras = sum(trace.get("type") == "bar" for trace in traces)
    box_traces = [trace for trace in traces if trace.get("type") == "box"]
    if box_traces:
        amostras_por_grupo = {}
        com_outliers = any(box_trace.get("boxpoints", "outliers") is not False for box_trace in box_traces)
        unidade = re.search(r"%\{y[^}]*\}\s*([^<%]*)", box_traces[0].get("hovertemplate") or "")
        unidade = unidade.group(1).strip() if unidade else _rotulo_titulo(yaxis.get("title"))
        for box_trace in box_traces:
            xs = _dados_lista(box_trace.get("x"))
            ys = _dados_lista(box_trace.get("y"))
            grupos_trace = xs or [box_trace.get("name", "")]
            for grupo, valor in zip(grupos_trace, ys):
                amostras_por_grupo.setdefault(str(grupo), []).append(float(valor))
        nomes_box, caixas, outliers = [], [], []
        for grupo, amostras in amostras_por_grupo.items():
            ordenados = sorted(amostras)
            q1, mediana, q3 = np.quantile(ordenados, [0.25, 0.5, 0.75], method="linear")
            if com_outliers:
                limite_i, limite_s = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
            else:
                limite_i, limite_s = ordenados[0], ordenados[-1]
            dentro = [valor for valor in ordenados if limite_i <= valor <= limite_s]
            indice_grupo = len(nomes_box)
            nomes_box.append(grupo)
            caixa = [min(dentro), q1, mediana, q3, max(dentro)]
            rotulos = ["Máximo" + (" sem outliers" if com_outliers else ""), "P75", "Mediana", "P25",
                       "Mínimo" + (" sem outliers" if com_outliers else "")]
            linhas = [f"{rotulo}: {_numero_ptbr(valor, 2)}" for rotulo, valor in zip(rotulos, caixa[::-1])]
            caixas.append({"value": caixa, "tooltip": f"<b>{grupo}</b> · {len(ordenados)} observações"
                           + (f"<br>{unidade}" if unidade else "") + "<br>" + "<br>".join(linhas)})
            outliers.extend({"value": [indice_grupo, valor],
                             "tooltip": f"{grupo} · outlier: {_numero_ptbr(valor, 2)} {unidade}".strip()}
                            for valor in ordenados if valor < limite_i or valor > limite_s)
        box_marker = box_traces[0].get("marker", {}) or {}
        box_color = _cor_legada(box_marker.get("color") or (box_traces[0].get("line", {}) or {}).get("color"),
                                destaque())
        opcoes["xAxis"] = {**eixo_x, "type": "category", "data": nomes_box}
        opcoes["yAxis"] = {**eixo_y, "type": "value", "data": None}
        opcoes["series"].append({"type": "boxplot", "name": "Distribuição", "data": caixas,
                                 "itemStyle": {"color": CONTEXTO, "borderColor": box_color}})
        if outliers:
            opcoes["series"].append({"type": "scatter", "name": "Outliers", "data": outliers,
                                     "itemStyle": {"color": box_color}, "symbolSize": 6})

    for indice, trace in enumerate(traces):
        tipo = trace.get("type", "scatter")
        if tipo == "box":
            continue
        nome = trace.get("name", "")
        cor_padrao = [destaque(), CONTEXTO2, CONTEXTO][indice % 3]
        marcador = trace.get("marker", {}) or {}
        cor_fonte = marcador.get("color") or (trace.get("line", {}) or {}).get("color")
        cores_ponto = cor_fonte if isinstance(cor_fonte, list) else None
        cor = _cor_legada(cor_fonte, cor_padrao)
        if tipo == "bar":
            horizontal_trace = trace.get("orientation") == "h"
            valores = _dados_lista(trace.get("x" if horizontal_trace else "y"))
            nomes = _dados_lista(trace.get("y" if horizontal_trace else "x"))
            textos = _dados_lista(trace.get("text"))
            customdata = _dados_lista(trace.get("customdata"))
            hovertemplate = trace.get("hovertemplate")
            pontos_por_categoria = {}
            for i, (categoria, valor) in enumerate(zip(nomes, valores)):
                ponto = {"value": valor}
                cor_item = _cor_legada(cores_ponto[i], cor) if cores_ponto and i < len(cores_ponto) else cor
                if cores_ponto or not cor_fonte:
                    ponto["itemStyle"] = {"color": cor_item}
                if i < len(textos) and textos[i] not in (None, ""):
                    ponto["labelText"] = _rotulo_ptbr(textos[i])
                dado_custom = customdata[i] if i < len(customdata) else []
                valor_x, valor_y = (valor, categoria) if horizontal_trace else (categoria, valor)
                fallback = f"{categoria}: {_numero_ptbr(valor)}"
                ponto["tooltip"] = _tooltip_ptbr(
                    hovertemplate,
                    {"x": valor_x, "y": valor_y, "text": textos[i] if i < len(textos) else "",
                     "customdata": dado_custom, "name": nome},
                    fallback,
                )
                pontos_por_categoria[str(categoria)] = ponto
            pontos = [pontos_por_categoria.get(categoria) for categoria in categorias]
            # Agrupadas dividem a largura da categoria; empilhadas e sobrepostas ocupam a mesma faixa.
            lado_a_lado = 1 if modo in {"stack", "relative", "overlay"} else max(n_barras, 1)
            largura = trace.get("width") if isinstance(trace.get("width"), (int, float)) else None
            serie = {"type": "bar", "name": nome, "data": pontos,
                     "barWidth": f"{(100 * largura if largura else 58) / lado_a_lado:.0f}%",
                     "barMaxWidth": None if largura else 48, "barMinWidth": 8,
                     "barGap": "0%" if modo in {"stack", "relative", "overlay"} else "30%"}
            if not cores_ponto:
                serie["itemStyle"] = {"color": cor}
            contorno = marcador.get("line") or {}
            if contorno.get("width") and isinstance(contorno.get("color"), str):
                serie.setdefault("itemStyle", {}).update({
                    "borderColor": _cor_legada(contorno["color"], CONTEXTO2), "borderWidth": contorno["width"]})
            if textos:
                empilhada_horizontal = horizontal_trace and modo in {"stack", "relative"}
                posicao = ("insideRight" if empilhada_horizontal
                           else "inside" if trace.get("textposition", "outside").startswith("inside")
                           else "right" if horizontal_trace else "top")
                cor_texto = _cor_legada((trace.get("textfont") or {}).get("color"), FORTE)
                serie["label"] = {
                    "show": indice == 0 if empilhada_horizontal else True,
                    "position": posicao,
                    "verticalAlign": "middle",
                    "color": cor_texto,
                    "fontSize": 14,
                    "formatter": JsCode(
                        "function (p) { return Number(p.value) >= 15 ? (p.data.labelText || '') : ''; }"
                        if empilhada_horizontal else
                        "function (p) { return p.data.labelText || ''; }"
                    ),
                }
            if modo in {"stack", "relative"}:
                serie["stack"] = "total"
            if modo == "overlay":
                serie["barGap"] = "-100%"
            opcoes["series"].append(serie)
        elif tipo == "scatter":
            xs, ys = _dados_lista(trace.get("x")), _dados_lista(trace.get("y"))
            modo_trace = trace.get("mode", "markers")
            serie_tipo = "line" if "lines" in modo_trace else "scatter"
            hovertemplate = trace.get("hovertemplate")
            customdata = _dados_lista(trace.get("customdata"))
            if serie_tipo == "line":
                valores_por_categoria = {str(x): y for x, y in zip(xs, ys)}
                indice_por_categoria = {str(x): indice for indice, x in enumerate(xs)}
                pontos = []
                for categoria in categorias:
                    valor = valores_por_categoria.get(categoria)
                    indice = indice_por_categoria.get(categoria)
                    contexto = {"x": categoria, "y": valor, "name": nome,
                                "customdata": customdata[indice] if indice is not None and indice < len(customdata) else []}
                    pontos.append({"value": valor,
                                   "tooltip": _tooltip_ptbr(hovertemplate, contexto,
                                                            f"{nome} · {categoria}: {_numero_ptbr(valor)}")
                                   if valor is not None else ""})
            else:
                opcoes["xAxis"] = {**eixo_x, "type": "value", "data": None}
                opcoes["yAxis"] = {**eixo_y, "type": "value", "data": None}
                pontos = []
                for indice, (x, y) in enumerate(zip(xs, ys)):
                    contexto = {"x": x, "y": y, "name": nome,
                                "customdata": customdata[indice] if indice < len(customdata) else []}
                    pontos.append({"value": [x, y],
                                   "tooltip": _tooltip_ptbr(hovertemplate, contexto,
                                                            f"{nome} · {_numero_ptbr(x)}: {_numero_ptbr(y)}")})
            linha = trace.get("line", {}) or {}
            serie = {"type": serie_tipo, "name": nome, "data": pontos,
                     "showSymbol": "markers" in modo_trace, "symbolSize": (marcador.get("size") or 8),
                     "lineStyle": {"color": cor, "width": linha.get("width", 2),
                                   "type": "dashed" if linha.get("dash") in {"dash", "dot"} else "solid"},
                     "itemStyle": {"color": cor}}
            if "spline" in str(linha.get("shape", "")):
                serie["smooth"] = True
            opcoes["series"].append(serie)
        elif tipo == "heatmap":
            xs, ys, zs = _dados_lista(trace.get("x")), _dados_lista(trace.get("y")), _dados_lista(trace.get("z"))
            textos = _dados_lista(trace.get("text"))
            hovertemplate = trace.get("hovertemplate")
            points = []
            for j, y in enumerate(ys):
                for i, x in enumerate(xs):
                    texto = textos[j][i] if j < len(textos) and i < len(textos[j]) else ""
                    contexto = {"x": x, "y": y, "z": zs[j][i], "text": texto, "name": nome}
                    fallback = f"{y}<br>{x}: {_numero_ptbr(zs[j][i], 2)}"
                    points.append({"value": [x, y, zs[j][i]], "labelText": _rotulo_ptbr(texto),
                                   "tooltip": _tooltip_ptbr(hovertemplate, contexto, fallback)})
            opcoes["xAxis"] = {"type": "category", "data": xs, "splitArea": {"show": True}}
            opcoes["yAxis"] = {"type": "category", "data": ys, "inverse": True, "splitArea": {"show": True}}
            valores_validos = [ponto["value"][2] for ponto in points if ponto["value"][2] is not None]
            minimo = trace.get("zmin") if trace.get("zmin") is not None else min(valores_validos)
            maximo = trace.get("zmax") if trace.get("zmax") is not None else max(valores_validos)
            opcoes["visualMap"] = {"min": minimo,
                                    "max": maximo,
                                    "calculable": False, "show": False, "inRange": {"color": divergente()}}
            opcoes["series"].append({"type": "heatmap", "name": nome, "data": points,
                                    "label": {"show": True, "color": FORTE, "fontSize": 12,
                                               "formatter": JsCode("function (p) { return p.data.labelText || p.data.value[2]; }")},
                                     "emphasis": {"itemStyle": {"shadowBlur": 4, "shadowColor": "rgba(0,0,0,.2)"}}})
        elif tipo == "waterfall":
            acumulado, base, valores, cores = 0, [], [], []
            measures = _dados_lista(trace.get("measure"))
            ys = _dados_lista(trace.get("y"))
            cor_de = lambda chave, padrao: _cor_legada(((trace.get(chave) or {}).get("marker") or {}).get("color"), padrao)
            cor_total, cor_sobe, cor_desce = cor_de("totals", CONTEXTO2), cor_de("increasing", SUCESSO), cor_de("decreasing", ALERTA)
            for measure, valor in zip(measures, ys):
                if measure == "absolute":
                    base.append(0)
                    acumulado = valor
                    valores.append(valor)
                    cores.append(cor_total)
                elif measure == "total":
                    base.append(0)
                    acumulado = valor if valor else acumulado
                    valores.append(acumulado)
                    cores.append(cor_total)
                else:
                    base.append(min(acumulado, acumulado + valor))
                    valores.append(abs(valor))
                    cores.append(cor_sobe if valor >= 0 else cor_desce)
                    acumulado += valor
            rotulos = [str(x) for x in _dados_lista(trace.get("x"))]
            textos = [_rotulo_ptbr(t) for t in _dados_lista(trace.get("text"))] or [_numero_ptbr(y) for y in ys]
            opcoes["series"].extend([
                {"type": "bar", "name": "", "stack": "waterfall", "data": base, "silent": True,
                 "itemStyle": {"color": "rgba(0,0,0,0)"}, "tooltip": {"show": False}},
                {"type": "bar", "name": nome, "stack": "waterfall", "barWidth": "58%", "barMaxWidth": 72,
                 "data": [{"value": v, "itemStyle": {"color": c}, "labelText": t, "tooltip": f"{r}: {t}"}
                          for v, c, t, r in zip(valores, cores, textos, rotulos)],
                 "label": {"show": True, "position": "top", "color": FORTE, "fontSize": 13,
                           "formatter": JsCode("function (p) { return p.data.labelText || ''; }")}},
            ])
    if opcoes["series"]:
        linhas_ref = []
        for forma in layout.get("shapes", []):
            if forma.get("type") == "line" and forma.get("y0") == forma.get("y1") and forma.get("yref", "y") != "paper":
                linhas_ref.append({"yAxis": forma["y0"], "lineStyle": {"color": CONTEXTO2, "type": "dashed"}})
            elif forma.get("type") == "line" and forma.get("x0") == forma.get("x1") and forma.get("xref", "x") != "paper":
                linhas_ref.append({"xAxis": forma["x0"], "lineStyle": {"color": CONTEXTO2, "type": "dashed"}})
        if linhas_ref:
            opcoes["series"][0]["markLine"] = {"symbol": ["none", "none"], "data": linhas_ref}
        anotacoes = layout.get("annotations", [])
        mark_points, graficos, rodapes = [], [], {}
        for anotacao in anotacoes:
            texto = re.sub(r"<br\s*/?>", "\n", anotacao.get("text", ""), flags=re.I)
            texto = re.sub(r"<[^>]+>", "", texto)
            texto = _rotulo_ptbr(texto)
            if not texto:
                continue
            font = anotacao.get("font", {}) or {}
            label = {"show": True, "formatter": texto, "color": _cor_legada(font.get("color"), TEXTO),
                     "fontSize": max(12, font.get("size", 11) + 1),
                     "backgroundColor": _cor_legada(anotacao.get("bgcolor"), "rgba(255,255,255,.92)"),
                     "borderColor": _cor_legada(anotacao.get("bordercolor"), CONTEXTO), "borderWidth": 1,
                     "borderRadius": 4, "padding": anotacao.get("borderpad", 4)}
            x_anotacao = anotacao.get("x")
            if (anotacao.get("yref") == "paper" and anotacao.get("xref", "x") != "paper" and not horizontal
                    and float(anotacao.get("y", 0)) < 0 and categorias):
                # Rodapé sob uma categoria: vira linhas extras do rótulo do eixo, alinhadas à barra.
                categoria = str(x_anotacao) if str(x_anotacao) in categorias else categorias[int(float(x_anotacao))]
                rodapes[categoria] = _texto_rico(anotacao.get("text", ""), "r")
                continue
            if anotacao.get("yref") == "paper":
                x = anotacao.get("x", 0)
                if anotacao.get("xref") == "paper":
                    esquerda = f"{max(0, min(100, 100 * float(x))):.1f}%"
                else:
                    pos = categorias.index(str(x)) if str(x) in categorias else int(float(x))
                    esquerda = f"{100 * pos / max(len(categorias), 1):.1f}%"
                topo = f"{max(0, min(100, 100 * (1 - float(anotacao.get('y', 0))))):.1f}%"
                graficos.append({"type": "text", "left": esquerda, "top": topo,
                                 "style": {"text": texto, "fill": label["color"],
                                           "font": f"{label['fontSize']}px {FONTE}",
                                           "backgroundColor": label["backgroundColor"],
                                           "borderColor": label["borderColor"], "borderWidth": 1,
                                           "padding": 4}})
            else:
                x_coord = anotacao.get("x")
                if str(x_coord) in categorias:
                    x_coord = str(x_coord)
                ancora_x, ancora_y = anotacao.get("xanchor", "auto"), anotacao.get("yanchor", "auto")
                label["position"] = ("right" if ancora_x == "left" else "left" if ancora_x == "right"
                                     else "top" if ancora_y == "bottom" else "bottom" if ancora_y == "top"
                                     else "inside")
                label["distance"] = 6
                label["offset"] = [anotacao.get("xshift", 0), -anotacao.get("yshift", 0)]
                if label["position"] == "right":
                    # Rótulo no fim da linha: abre espaço à direita para ele não ser cortado.
                    largura = 7 * max(len(linha) for linha in texto.split("\n")) + 24 + anotacao.get("xshift", 0)
                    opcoes["grid"]["right"] = max(opcoes["grid"]["right"], largura)
                mark_points.append({"coord": [x_coord, anotacao.get("y")], "name": texto,
                                    "label": label})
        if mark_points:
            opcoes["series"][0]["markPoint"] = {"symbol": "circle", "symbolSize": 1, "data": mark_points, "silent": True}
        if graficos:
            opcoes["graphic"] = graficos
        if rodapes:
            estilo = {"color": TEXTO, "fontSize": 11, "lineHeight": 15, "align": "center"}
            opcoes["xAxis"]["axisLabel"].update({
                "show": True, "interval": 0, "lineHeight": 18,
                "rich": {"r": estilo, "rb": {**estilo, "fontWeight": "bold", "color": FORTE}},
                "formatter": JsCode(
                    f"function (valor) {{ const r = {json.dumps(rodapes, ensure_ascii=False)}; "
                    "return r[valor] ? valor + '\\n' + r[valor] : valor; }"
                ),
            })
    # Linha sem marcador não tem ponto para o tooltip por item ("undefined"); o tooltip por eixo lista cada série no mês.
    eixo_x = opcoes.get("xAxis")
    if (isinstance(eixo_x, dict) and eixo_x.get("type") == "category"
            and any(s.get("type") == "line" and not s.get("showSymbol", True) for s in opcoes.get("series", []))):
        opcoes["tooltip"] = {"trigger": "axis", "formatter": JsCode(
            "function (params) { const ps = Array.isArray(params) ? params : [params]; "
            "return ps.filter(p => p.data && p.data.tooltip).map(p => p.marker + p.data.tooltip).join('<br>'); }")}
    return opcoes


def _titulo_partes(titulo: str) -> tuple[str, str]:
    """"<b>achado</b><br><span>detalhe</span>" (charts.plots.titulo) → (achado, detalhe) em texto puro."""
    def limpar(texto: str) -> str:
        texto = re.sub(r"<br\s*/?>", " · ", texto, flags=re.I)
        return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto))).strip(" ·")
    m = re.match(r"\s*<b>(.*?)</b>(.*)", titulo or "", re.S | re.I)
    return (limpar(m.group(1)), limpar(m.group(2))) if m else (limpar(titulo or ""), "")


def _valor_ponto(ponto):
    valor = ponto.get("value") if isinstance(ponto, dict) else ponto
    return valor[-1] if isinstance(valor, list) and valor else valor


def _hex(cor) -> bool:
    return isinstance(cor, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", cor) is not None


def _vidro(opcoes: dict) -> dict:
    """Acabamento glass-template sobre as opções já montadas (nativas ou vindas do Plotly): tooltip de vidro, eixos
    11px sem grade, barras arredondadas (trilho quando há uma série só), linhas com brilho, área em degradê e último
    ponto pulsando na série principal, legenda sem séries internas."""
    tip = opcoes.get("tooltip") or {}
    fixos = {"backgroundColor", "borderColor", "borderWidth", "textStyle", "extraCssText", "padding"}
    opcoes["tooltip"] = {**GT["tooltip"], **{k: v for k, v in tip.items() if k not in fixos}}

    eixos = []
    for nome in ("xAxis", "yAxis"):
        valor = opcoes.get(nome)
        eixos += [e for e in (valor if isinstance(valor, list) else [valor]) if isinstance(e, dict)]
    for eixo in eixos:
        eixo["splitLine"] = {**(eixo.get("splitLine") or {}), "show": False}
        rotulo = eixo.setdefault("axisLabel", {})
        rotulo["fontSize"] = 11
        if rotulo.get("color") in (None, TEXTO):
            rotulo["color"] = GT["fraco"]
        eixo["axisTick"] = {**(eixo.get("axisTick") or {}), "show": False}
        eixo.setdefault("axisLine", {}).setdefault("lineStyle", {})["color"] = GT["linha"]

    series = [s for s in opcoes.get("series") or [] if isinstance(s, dict)]
    eixo_x = opcoes.get("xAxis") if isinstance(opcoes.get("xAxis"), dict) else {}
    eixo_y = opcoes.get("yAxis") if isinstance(opcoes.get("yAxis"), dict) else {}
    horizontal = eixo_y.get("type") == "category"
    topo, base = ([0, 6, 6, 0], [6, 0, 0, 6]) if horizontal else ([6, 6, 0, 0], [0, 0, 6, 6])
    barras = [s for s in series if s.get("type") == "bar" and s.get("name", "") != ""]
    for serie in barras:
        estilo = serie.setdefault("itemStyle", {})
        if serie.get("stack"):
            estilo.setdefault("borderRadius", 2)
            continue
        dados = serie.get("data") or []
        if all(isinstance(p, dict) or p is None for p in dados):
            for ponto in dados:
                v = _valor_ponto(ponto) if ponto else None
                if isinstance(v, (int, float)):
                    ponto.setdefault("itemStyle", {}).setdefault("borderRadius", topo if v >= 0 else base)
        else:
            negativo = any(isinstance(v, (int, float)) and v < 0 for v in map(_valor_ponto, dados))
            estilo.setdefault("borderRadius", 3 if negativo else topo)
    if len(barras) == 1 and not barras[0].get("stack") and not any(s.get("type") == "line" for s in series):
        barras[0].setdefault("showBackground", True)
        barras[0].setdefault("backgroundStyle", {"color": GT["trilho"], "borderRadius": 6})

    linhas = [s for s in series if s.get("type") == "line" and not str(s.get("name", "")).startswith("_")]
    for serie in linhas:
        traco = serie.setdefault("lineStyle", {})
        cor = traco.get("color") or (serie.get("itemStyle") or {}).get("color")
        if cor == destaque():
            cor = traco["color"] = CIANO
            serie.setdefault("itemStyle", {})["color"] = CIANO
        if traco.get("type", "solid") == "solid" and _hex(cor):
            traco.setdefault("shadowBlur", 10)
            traco.setdefault("shadowColor", gt.rgba(cor, .45))
    solidas = [s for s in linhas if (s.get("lineStyle") or {}).get("type", "solid") == "solid"]
    if len(solidas) == 1 and not barras and eixo_x.get("type") == "category" and eixo_x.get("data"):
        serie = solidas[0]
        cor = (serie.get("lineStyle") or {}).get("color") or CIANO
        if _hex(cor):
            if len(linhas) == 1:
                serie.setdefault("areaStyle", {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1, "colorStops": [
                    {"offset": 0, "color": gt.rgba(cor, .28)}, {"offset": 1, "color": gt.rgba(cor, 0)}]}})
            valores = [_valor_ponto(p) for p in serie.get("data") or []]
            ultimo = next((i for i in range(len(valores) - 1, -1, -1) if isinstance(valores[i], (int, float))), None)
            if ultimo is not None and ultimo < len(eixo_x["data"]):
                opcoes["series"].append(gt_pulso(str(eixo_x["data"][ultimo]), valores[ultimo], cor))

    legenda = opcoes.get("legend")
    if isinstance(legenda, dict) and legenda.get("show", True):
        legenda.setdefault("icon", "roundRect")
        legenda.setdefault("itemWidth", 14)
        legenda.setdefault("itemHeight", 6)
        legenda["textStyle"] = {**(legenda.get("textStyle") or {}), "color": GT["texto"], "fontSize": 12}
        legenda.setdefault("inactiveColor", GT["inativo"])
        if "data" not in legenda:
            nomes = [s.get("name") for s in series if s.get("name") and not str(s["name"]).startswith("_")]
            legenda["data"] = list(dict.fromkeys(nomes))
    return opcoes


def grafico(opcoes, chave: str | None = None, altura: int | None = None, assunto: str = "institucional",
            *, key: str | None = None, width: str = "stretch", config: dict | None = None, container=None,
            kicker: str = "") -> None:
    """Desenha o gráfico num cartão de vidro (glass-template); o título vira o cabeçalho do cartão
    (achado + detalhe) e `kicker` é a etiqueta ciano opcional acima dele."""
    if hasattr(opcoes, "to_json"):
        opcoes = _de_plotly(opcoes)
    else:
        opcoes = deepcopy(opcoes)
    titulo = _rotulo_ptbr(opcoes.pop("_titulo", ""))
    altura = altura or opcoes.pop("_altura", 380)
    base = {
        "color": [destaque(assunto), CONTEXTO2, CONTEXTO],
        "backgroundColor": "transparent",
        "textStyle": {"fontFamily": FONTE, "color": TEXTO, "fontSize": 12},
        "grid": {"left": 8, "right": 16, "top": 24, "bottom": 8, "containLabel": True},
        "tooltip": {
            "confine": True,
            "formatter": JsCode(
                "function (params) { const p = Array.isArray(params) ? params[0] : params; "
                "const d = p.data || {}; return d.tooltip || `${p.seriesName || ''}<br>${p.name || ''}: ${p.value}`; }"
            ),
        },
        "animationDuration": 1600,
        "animationDelay": JsCode("function (index) { return index * 60; }"),
        "animationDurationUpdate": 800,
        "animationEasing": "cubicOut",
    }
    # Valor numpy/Timestamp quebra o json.dumps do Streamlit, que então envia as opções como texto.
    base.update(_normalizar(opcoes))
    base = _vidro(base)
    nome = key or chave or f"g{zlib.crc32(titulo.encode())}"
    kwargs = {"options": base, "theme": tema_echarts(assunto), "height": f"{altura}px",
              "width": "100%" if width == "stretch" else width, "key": nome}

    def desenhar():
        with gt.cartao(nome):
            if titulo or kicker:
                gt.cabecalho(kicker, *_titulo_partes(titulo))
            st_echarts(**kwargs)

    if container is None:
        desenhar()
    else:
        with container:
            desenhar()
