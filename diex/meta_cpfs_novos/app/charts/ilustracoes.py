"""Desenhos explicativos da Introdução (SVG embutido como imagem, com texto alternativo). Cores só de common.painel.classico."""
import base64
from html import escape

import streamlit as st

from common.painel.classico import CONTEXTO, CONTEXTO2, FORTE, GRADE, TEXTO

BRANCO = "white"


# Peças --------------------------------------------------------------------------------------------------------------
def _svg(corpo: str, alt: str, w: int = 320, h: int = 160) -> str:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w * 2}" height="{h * 2}" '
           f'font-family="Inter, Arial, sans-serif">{corpo}</svg>')
    return f'<img alt="{escape(alt, quote=True)}" src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}">'


def _t(x, y, texto, cor=TEXTO, tam=12, peso=500, anc="middle") -> str:
    return f'<text x="{x}" y="{y}" fill="{cor}" font-size="{tam}" font-weight="{peso}" text-anchor="{anc}">{escape(texto)}</text>'


def _pessoa(x, y, cor, e=1.0) -> str:
    """Pessoa com os pés em (x, y), altura de 34 × e."""
    return (f'<g transform="translate({x},{y}) scale({e})" fill="{cor}"><circle cx="0" cy="-27" r="7"/>'
            f'<path d="M-11 0 v-6 a11 11 0 0 1 22 0 v6 z"/></g>')


def _predio(x, y, cor, e=1.0, rotulo="") -> str:
    """Unidade com a base em (x, y): telhado, janelas e porta."""
    jan = "".join(f'<rect x="{a}" y="{b}" width="8" height="8" rx="1" fill="{BRANCO}"/>' for a in (-21, -4, 13) for b in (-40, -26))
    return (f'<g transform="translate({x},{y}) scale({e})"><rect x="-28" y="-48" width="56" height="48" rx="4" fill="{cor}"/>{jan}'
            f'<rect x="-6" y="-13" width="12" height="13" rx="1" fill="{BRANCO}"/></g>' + (_t(x, y + 15, rotulo, TEXTO, 11) if rotulo else ""))


def _selo(x, y, texto, cor, vale=True) -> str:
    w = len(texto) * 6.6 + 18
    return (f'<rect x="{x - w / 2}" y="{y - 14}" width="{w}" height="20" rx="10" fill="{cor if vale else BRANCO}" stroke="{cor}"/>'
            + _t(x, y, texto, BRANCO if vale else cor, 11, 700))


def _seta(x1, y, x2, cor=CONTEXTO2) -> str:
    return (f'<path d="M{x1} {y} H{x2 - 6}" stroke="{cor}" stroke-width="2.5" fill="none"/>'
            f'<path d="M{x2 - 8} {y - 5} L{x2} {y} L{x2 - 8} {y + 5} z" fill="{cor}"/>')


def _vale(v: bool, x, y, cor) -> str:
    return _selo(x, y, "novo CPF" if v else "não conta", cor if v else CONTEXTO2, v)


def quadros(itens: list[tuple[str, str, str]]) -> None:
    """Grade de quadros (título, desenho, texto em HTML simples), lado a lado no computador (quatro = 2 × 2) e empilhados no celular."""
    st.html(f'<div class="streamlit-ilus{" streamlit-ilus-pares" if len(itens) in (2, 4) else ""}">' + "".join(
        f'<div class="streamlit-ilus-quadro"><b>{t}</b>{img}<p>{txt}</p></div>' for t, img, txt in itens) + "</div>")


# Contagem -----------------------------------------------------------------------------------------------------------
def visitas(pontos: list[tuple[int, str, bool]], cor: str, alt: str, trecho: tuple[int, int, str] | None = None) -> str:
    """Linha do tempo de uma pessoa: (x, data, conta) em cada visita; trecho = (x inicial, x final, legenda)."""
    c = f'<path d="M14 92 H306" stroke="{CONTEXTO}" stroke-width="3" stroke-linecap="round"/>'
    for x, data, vale in pontos:
        k = cor if vale else CONTEXTO2
        c += _vale(vale, x, 24, cor) + _pessoa(x, 78, k) + f'<circle cx="{x}" cy="92" r="7" fill="{k if vale else BRANCO}" stroke="{k}" stroke-width="2.5"/>' + _t(x, 116, data, FORTE, 11, 600)
    if trecho:
        a, b, leg = trecho
        c += f'<path d="M{a} 126 v7 H{b} v-7" fill="none" stroke="{TEXTO}" stroke-width="1.5"/>' + _t((a + b) / 2, 150, leg, TEXTO, 12, 600)
    return _svg(c, alt)


def anos_civis(cor: str, anos: list[tuple[str, list[int], str]], alt: str) -> str:
    """Dois anos civis, cada um com as visitas (posição de 0 a 100) e a contagem."""
    c = ""
    for i, (ano, visitas_, selo) in enumerate(anos):
        x0 = 12 + i * 152
        c += f'<rect x="{x0}" y="42" width="144" height="72" rx="10" fill="{BRANCO}" stroke="{CONTEXTO}" stroke-width="1.5"/>' + _selo(x0 + 72, 24, selo, cor)
        c += f'<path d="M{x0 + 10} 96 H{x0 + 134}" stroke="{GRADE}" stroke-width="3"/>'
        c += "".join(_pessoa(x0 + 14 + v * 1.16, 90, cor if j == 0 else CONTEXTO2, .8) for j, v in enumerate(visitas_))
        c += _t(x0 + 20, 109, "jan", TEXTO, 10) + _t(x0 + 124, 109, "dez", TEXTO, 10) + _t(x0 + 72, 136, ano, FORTE, 14, 700)
    return _svg(c, alt)


def varios_para_um(rotulos: list[str], cor: str, alt: str) -> str:
    """Caixas (atendimentos, especialidades ou entidades) que viram uma pessoa contada."""
    n, alto = len(rotulos), 30
    y0 = 78 - (n * (alto + 6) - 6) / 2
    c = "".join(f'<rect x="10" y="{y0 + i * (alto + 6)}" width="130" height="{alto}" rx="8" fill="{BRANCO}" stroke="{CONTEXTO2}"/>'
                + _t(75, y0 + i * (alto + 6) + 20, r, FORTE, 12, 600) for i, r in enumerate(rotulos))
    return _svg(c + _seta(152, 78, 205) + _pessoa(255, 92, cor, 1.5) + _selo(255, 122, "conta 1", cor), alt)


def duas_unidades(cor: str, alt: str) -> str:
    return _svg(_predio(60, 88, CONTEXTO2, 1, "Unidade A") + _predio(260, 88, CONTEXTO2, 1, "Unidade B") + _pessoa(160, 88, cor, 1.4)
                + f'<path d="M136 70 H98 M184 70 H222" stroke="{cor}" stroke-width="2.5" stroke-dasharray="4 4"/>' + _selo(60, 130, "conta 1", cor) + _selo(260, 130, "conta 1", cor), alt)


# Período ------------------------------------------------------------------------------------------------------------
def anos_usados(cor: str, alt: str) -> str:
    c = ""
    for i, a in enumerate((2023, 2024, 2025, 2026)):
        x, est = 8 + i * 56, a == 2026
        c += (f'<rect x="{x}" y="44" width="52" height="62" rx="10" fill="{cor}" fill-opacity="{.35 if est else 1}" stroke="{cor}"' + (' stroke-dasharray="5 4"' if est else "") + "/>"
              + _t(x + 26, 80, str(a), FORTE if est else BRANCO, 15, 700))
    return _svg(c + _t(118, 128, "anos da análise", FORTE, 12, 700) + _seta(232, 75, 256) + f'<rect x="260" y="44" width="52" height="62" rx="10" fill="{BRANCO}" stroke="{cor}" stroke-width="2"/>'
                + _t(286, 80, "2027", cor, 15, 700) + _t(286, 128, "meta", FORTE, 12, 700), alt)


def maturidade(cor: str, alt: str) -> str:
    return _svg(_predio(52, 92, cor, 1) + _predio(120, 92, cor, 1) + _predio(188, 92, cor, 1) + _predio(272, 92, CONTEXTO, .8)
                + f'<path d="M228 34 V112" stroke="{CONTEXTO2}" stroke-dasharray="4 4"/>' + _t(120, 30, "5 anos ou mais", FORTE, 12, 700) + _t(272, 30, "menos de 5", TEXTO, 12, 600)
                + _selo(120, 128, "entra na conta", cor) + _selo(272, 128, "fica fora", CONTEXTO2, False), alt)


def projecao(cor: str, alt: str) -> str:
    c = ""
    for i, m in enumerate("JFMAMJJASOND"):
        x, proj, alt_ = 14 + i * 24.6, i >= 10, 46 + (i * 17 % 29)
        c += (f'<rect x="{x}" y="{118 - alt_}" width="18" height="{alt_}" rx="4" fill="{cor}" fill-opacity="{.3 if proj else 1}" stroke="{cor}"' + (' stroke-dasharray="4 3"' if proj else "") + "/>"
              + _t(x + 9, 134, m, TEXTO, 11))
    return _svg(c + _selo(134, 28, "realizado até outubro", cor) + _t(285, 28, "projeção", FORTE, 12, 700), alt)


# Termos -------------------------------------------------------------------------------------------------------------
def multidao(cor: str, alt: str) -> str:
    pess = "".join(_pessoa(112 + (i % 9) * 24, 58 + (i // 9) * 40, CONTEXTO2, .8) for i in range(27))
    return _svg(pess + _predio(48, 122, cor, 1.2), alt)


def pontos100(cor: str, n: int, alt: str) -> str:
    c = "".join(f'<circle cx="{22 + (i % 20) * 14.5}" cy="{30 + (i // 20) * 20}" r="5.6" fill="{cor if i < n else GRADE}" stroke="{cor if i < n else CONTEXTO}"/>' for i in range(100))
    return _svg(c + _selo(80, 148, f"penetração {n}%", cor) + _selo(236, 148, f"lacuna {100 - n}%", CONTEXTO2, False), alt)


def termometro(cor: str, esforcos: list[str], potencial, fm: float, alt: str) -> str:
    """Régua do fator de mercado de 0 a 1: quatro faixas, com o potencial e o esforço de cada uma."""
    c = "".join(f'<rect x="{10 + i * 75}" y="58" width="73" height="34" rx="6" fill="{cor}" fill-opacity="{.15 + .2 * i}"/>' + _t(46 + i * 75, 81, e, FORTE, 15, 700) + _t(46 + i * 75, 112, p, TEXTO, 11, 600)
                for i, (e, p) in enumerate(zip(esforcos, potencial)))
    x = 10 + fm * 300
    return _svg(c + f'<path d="M{x - 7} 42 h14 l-7 11 z" fill="{FORTE}"/>' + _t(x, 34, f"FM {fm:.2f}".replace(".", ","), FORTE, 12, 700)
                + _t(12, 134, "0: pouco espaço", TEXTO, 11, 500, "start") + _t(308, 134, "1: muito espaço", TEXTO, 11, 500, "end"), alt)


def fila(cor: str, posicao: float, legenda: str, alt: str) -> str:
    """Onze unidades em fila, da menor (0) à maior (1); a da `posicao` em destaque e a legenda das que ficam atrás."""
    k, c = round(posicao * 10), ""
    for i in range(11):
        h, x = 16 + i * 5.2, 12 + i * 27.6
        c += f'<rect x="{x}" y="{104 - h}" width="20" height="{h}" rx="4" fill="{cor if i == k else CONTEXTO}"/>' + _t(x + 10, 119, f"{i / 10:.1f}".replace(".", ",") if 0 < i < 10 else str(i // 10), FORTE if i == k else TEXTO, 10, 700 if i == k else 500)
    x = 22 + k * 27.6
    c += _selo(x, 104 - 16 - k * 5.2 - 10, f"{posicao:.2f}".replace(".", ","), cor)
    return _svg(c + f'<path d="M12 127 v7 H{4 + k * 27.6} v-7" fill="none" stroke="{TEXTO}" stroke-width="1.5"/>' + _t(12, 150, legenda, TEXTO, 12, 600, "start"), alt)


def mesmo_passo(cor: str, alt: str) -> str:
    c = ""
    for i, h in enumerate((34, 52, 70)):
        x, extra = 46 + i * 94, h * .24
        c += f'<rect x="{x}" y="{122 - h}" width="46" height="{h}" rx="5" fill="{CONTEXTO2}"/><rect x="{x}" y="{122 - h - extra - 2}" width="46" height="{extra}" rx="5" fill="{cor}"/>' + _t(x + 23, 118 - h - extra - 4, "+7%", FORTE, 12, 700)
    return _svg(c + "".join(_t(69 + i * 94, 140, f"Unidade {u}", TEXTO, 11) for i, u in enumerate("ABC")), alt)


def barra_meta(cor: str, total: str, partes: list[tuple[str, str, float]], alt: str) -> str:
    """2026 (1.000) na base e as partes empilhadas: (texto dentro, texto ao lado, opacidade); sem texto dentro = faixa fina."""
    c, y = f'<rect x="30" y="92" width="92" height="58" rx="6" fill="{CONTEXTO2}"/>' + _t(76, 126, "1.000", FORTE, 14, 700) + _t(134, 126, "2026", TEXTO, 13, 500, "start"), 90
    for dentro, lado, op in partes:
        h = 30 if dentro else 14
        c += f'<rect x="30" y="{y - h}" width="92" height="{h}" rx="5" fill="{cor}" fill-opacity="{op}"/>' + _t(76, y - h / 2 + 5, dentro, FORTE, 13, 700) + _t(134, y - h / 2 + 5, lado, TEXTO, 13, 500, "start")
        y -= h + 2
    return _svg(c + _t(76, y - 8, total, FORTE, 17, 800), alt)
