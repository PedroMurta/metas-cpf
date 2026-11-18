"""Tema do glass-template (vidro claro): cores, tooltip de vidro, formatadores pt-BR e a função que desenha o gráfico.

Para adaptar a outro projeto, ajuste CIANO / AZUL / NAVY e TEMA (por exemplo, o acento ciano ou as cores de situação);
todas as funções do pacote leem daqui.
"""
from __future__ import annotations

import math

from streamlit_echarts import JsCode, st_echarts

CIANO, AZUL, NAVY, CORAL = "#00b8e6", "#0095cc", "#0f2540", "#f87171"
FONTE = "Inter, sans-serif"

TEMA = {
    "texto": "#1a2332", "fraco": "#5a6a7e", "linha": "rgba(15,37,64,.14)", "corte": "rgba(15,37,64,.3)",
    "quad_rotulo": "rgba(15,37,64,.5)", "quad_opacidade": .32, "meta": "rgba(15,37,64,.45)",
    "trilho": "rgba(15,37,64,.06)", "valor": NAVY, "inativo": "rgba(15,37,64,.2)", "caminho": "rgba(15,37,64,.3)",
    "anterior": "rgba(15,37,64,.45)", "rotulo_fundo": "rgba(255,255,255,.88)", "rotulo_texto": NAVY,
    "moldura": "rgba(15,37,64,.28)", "borda_bolha": "rgba(255,255,255,.95)",
    "notas": ("#b91c1c", "#d97706", "#15803d"),     # nota 0–1: < 0,5 / < 0,8 / ≥ 0,8
    "situacao": ("#c94040", "#d97706", "#1a9e6e"),  # ruim / no limite / bom
    "tooltip": {"backgroundColor": "rgba(255,255,255,.78)", "borderColor": "rgba(255,255,255,.95)", "borderWidth": 1,
                "padding": [10, 14], "confine": True, "textStyle": {"color": NAVY, "fontFamily": FONTE, "fontSize": 13},
                "extraCssText": "border-radius:14px;backdrop-filter:blur(14px) saturate(160%);"
                                "-webkit-backdrop-filter:blur(14px) saturate(160%);"
                                "box-shadow:0 10px 30px rgba(15,37,64,.18);"},
}

BRL_JS = ("function (v) { const a = Math.abs(v); return 'R$ ' + (a >= 1e6 ? (v / 1e6).toLocaleString('pt-BR', "
          "{maximumFractionDigits: 1}) + ' mi' : a >= 1e3 ? (v / 1e3).toLocaleString('pt-BR', "
          "{maximumFractionDigits: 0}) + ' mil' : v.toLocaleString('pt-BR')); }")


# ---------------------------------------------------------------- cores

def rgba(cor: str, alfa: float) -> str:
    h = cor.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alfa})"


def mistura(a: str, b: str, t: float) -> str:
    """Mistura duas cores hex (t = 0 → a, t = 1 → b)."""
    ca, cb = (tuple(int(c.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for c in (a, b))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def degrade(cor: str, vertical: bool = False, invertido: bool = False, clareia: float = .3) -> dict:
    """Degradê da cor clara para a cor cheia (barras)."""
    stops = [{"offset": 0, "color": mistura(cor, "#ffffff", clareia)}, {"offset": 1, "color": cor}]
    if invertido:
        stops = stops[::-1]
    return {"type": "linear", "x": 0, "y": 0, "x2": 0 if vertical else 1, "y2": 1 if vertical else 0,
            "colorStops": stops}


def situacao_maior(pct: float) -> str:
    """Maior é melhor (execução da meta): ≥100 verde, ≥70 âmbar, abaixo vermelho."""
    ruim, medio, bom = TEMA["situacao"]
    return bom if pct >= 100 else medio if pct >= 70 else ruim


ESCALA_EXECUCAO = ((100, "#1f6fd1"), (95, "#0e9f5f"), (90, "#5cbf8d"), (80, "#d97706"), (0, "#c94040"))


def escala_execucao(pct: float) -> str:
    """Execução da meta em 5 faixas: ≥100 azul, 95–99 verde forte, 90–94 verde, 80–89 âmbar, <80 vermelho."""
    return next(cor for limite, cor in ESCALA_EXECUCAO if pct >= limite)


def situacao_alvo(pct: float, verde: float = 15, amarelo: float = 20) -> str:
    """Perto de 100% é melhor (régua simétrica, ex.: orçamento): |pct − 100| ≤ verde → verde, ≤ amarelo → âmbar,
    o resto vermelho. Padrão: 85–115% verde, 80–85% e 115–120% âmbar."""
    ruim, medio, bom = TEMA["situacao"]
    d = abs(pct - 100)
    return bom if d <= verde else medio if d <= amarelo else ruim


def situacao_menor(pct: float) -> str:
    """Menor é melhor (custo): até 100% verde, acima vermelho."""
    ruim, _, bom = TEMA["situacao"]
    return bom if pct <= 100 else ruim


# ---------------------------------------------------------------- números

def br(v: float, casas: int = 2, sinal: bool = False, sufixo: str = "") -> str:
    """Número pt-BR para rótulos montados no Python ("+0,12", "84,5%")."""
    txt = f"{v:+,.{casas}f}" if sinal else f"{v:,.{casas}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".") + sufixo


def num_js(casas: int = 2, sufixo: str = "") -> JsCode:
    """Formatter que recebe o valor (eixos, valueFormatter)."""
    return JsCode("function (v) { return (v == null || isNaN(v)) ? '—' : Number(v).toLocaleString('pt-BR', "
                  f"{{minimumFractionDigits: {casas}, maximumFractionDigits: {casas}}}) + '{sufixo}'; }}")


def finito(v) -> float | None:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, 4) if math.isfinite(v) else None


# ---------------------------------------------------------------- peças das opções

def base() -> dict:
    return {"backgroundColor": "transparent", "textStyle": {"fontFamily": FONTE, "color": TEMA["fraco"]},
            "animationDuration": 1600, "animationEasing": "cubicOut", "tooltip": dict(TEMA["tooltip"])}


def tooltip(**extra) -> dict:
    return {**TEMA["tooltip"], **extra}


def eixo_categoria(rotulos, **extra) -> dict:
    return {"type": "category", "data": list(map(str, rotulos)), "axisTick": {"show": False},
            "axisLine": {"lineStyle": {"color": TEMA["linha"]}},
            "axisLabel": {"color": TEMA["fraco"], "fontSize": 11}, **extra}


def eixo_valor(formatter=None, **extra) -> dict:
    rot = {"color": TEMA["fraco"], "fontSize": 11}
    if formatter is not None:
        rot["formatter"] = formatter
    return {"type": "value", "splitLine": {"show": False}, "axisLabel": rot, **extra}


def legenda(**extra) -> dict:
    return {"top": 0, "right": 0, "icon": "roundRect", "itemWidth": 14, "itemHeight": 4,
            "textStyle": {"color": TEMA["texto"], "fontSize": 12}, "inactiveColor": TEMA["inativo"], **extra}


def pulso(x, y, cor: str = CIANO, tamanho: int = 9) -> dict:
    """Ponto pulsando sem parar (último mês, unidade escolhida...)."""
    return {"type": "effectScatter", "name": "_pulso", "silent": True, "z": 6, "symbolSize": tamanho,
            "data": [[x, y]], "tooltip": {"show": False},
            "rippleEffect": {"scale": 3.2, "brushType": "stroke", "period": 2.4},
            "itemStyle": {"color": cor, "shadowBlur": 12, "shadowColor": cor}}


def destaque(nome: str, x, y, tamanho: float, rotulo: str, extra: dict | None = None,
             posicao: str = "top") -> dict:
    """Ponto ciano pulsando sem parar, com etiqueta de vidro (unidade escolhida, período atual...)."""
    return {"type": "effectScatter", "name": nome, "z": 10,
            "data": [{"name": nome, "value": [x, y], **(extra or {})}], "symbolSize": tamanho,
            "rippleEffect": {"scale": 3.2, "brushType": "stroke", "period": 2.4},
            "itemStyle": {"color": CIANO, "borderColor": "#fff", "borderWidth": 2, "shadowBlur": 16, "shadowColor": CIANO},
            "label": {"show": True, "position": posicao, "distance": 12 if posicao == "top" else 10,
                      "color": TEMA["rotulo_texto"], "fontWeight": 700, "fontSize": 12, "formatter": rotulo,
                      "backgroundColor": TEMA["rotulo_fundo"], "borderColor": CIANO, "borderWidth": 1,
                      "borderRadius": 8, "padding": [5, 9] if posicao == "top" else [4, 8]}}


def cascata(passo: int = 60, inicio: int = 0) -> JsCode:
    """animationDelay: um item depois do outro."""
    return JsCode(f"function (i) {{ return {inicio} + i * {passo}; }}")


# ---------------------------------------------------------------- desenho

def normalizar(valor):
    """numpy / pandas / datas → tipos JSON (sem isso o st_echarts recebe objetos que não serializa)."""
    if isinstance(valor, dict):
        return {k: normalizar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [normalizar(v) for v in valor]
    if hasattr(valor, "isoformat") and hasattr(valor, "year"):
        return valor.isoformat()[:10]
    if hasattr(valor, "tolist"):
        return normalizar(valor.tolist())
    if hasattr(valor, "item"):
        return normalizar(valor.item())
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if valor is not None and type(valor).__name__ in ("NAType", "NaTType"):
        return None
    return valor


def grafico(chave: str, opcoes: dict, altura: int = 320) -> None:
    """Desenha as opções ECharts (largura total do container)."""
    st_echarts(options=normalizar(opcoes), height=f"{altura}px", width="100%", key=chave)
