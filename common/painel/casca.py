"""Casca SEST SENAT dos apps Streamlit: tema, barra superior, KPIs, notas e rodapé.

Uso no ponto de entrada do app:
    st.set_page_config(page_title="Nome do estudo", layout="wide")
    aplicar_tema()                       # tokens + casca + vidro (+ CSS do estudo, se passar)
    cabecalho("Nome do estudo")          # SEST SENAT | GEPLANE · NÚCLEO DE DADOS — NOME DO ESTUDO

Classes CSS sempre com prefixo `streamlit-`.
"""
import base64
from functools import cache
from html import escape
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"
AREA = "GEPLANE · Núcleo de Dados"   # autoria fixa dos painéis; a gerência demandante não entra na barra
FONTES = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@900&family=Inter:wght@300;400;500;600;700&display=swap');
@import url('https://use.typekit.net/lfm6vcy.css');
"""


@cache
def _ler(*arquivos: Path) -> str:
    return "\n".join(a.read_text(encoding="utf-8") for a in arquivos)


@cache
def _logo() -> str:
    return base64.b64encode((ASSETS / "logo-light.png").read_bytes()).decode("ascii")


def aplicar_tema(*css_extra: Path, topo: bool = False) -> None:
    """Fontes, tokens Claro, casca e vidro num único <style>. `topo=True` para st.navigation(position="top").
    `css_extra`: CSS próprios do estudo (prefixo streamlit-). Chamar uma vez por página."""
    base = [ASSETS / "variaveis-claro.css", ASSETS / "casca.css", ASSETS / "vidro.css"]
    base += [ASSETS / "nav_topo.css"] if topo else []
    st.html(f"<style>{FONTES}\n{_ler(*base, *css_extra)}</style>")


def cabecalho(titulo: str, etapa: str = "") -> None:
    """Barra navy fixa: logo | GEPLANE · Núcleo de Dados — título do estudo ao centro.
    `etapa` (opcional) mostra a tag de seção e o h1 da página."""
    st.html(
        f'''<header class="streamlit-header" aria-label="SEST SENAT">
            <div class="streamlit-header-left">
                <img class="streamlit-header-logo" src="data:image/png;base64,{_logo()}" alt="SEST SENAT">
                <span class="streamlit-header-divider" aria-hidden="true"></span>
                <span class="streamlit-header-area">{escape(AREA.upper())}</span>
            </div>
            <div class="streamlit-header-title">{escape(titulo)}</div>
            <div class="streamlit-header-right" aria-hidden="true"></div>
        </header>'''
    )
    if etapa:
        st.html(f'<div class="streamlit-section-tag">{escape(etapa)}</div>')
        st.title(titulo)


def kpi(rotulo: str, valor: str, ajuda: str = "", nota: str = "", delta: str = "",
        bom: bool | None = None) -> str:
    """HTML de um cartão; textos já formatados em pt-BR.

    kpi("Pessoas atendidas", "12.345", "cada pessoa conta uma vez no ano", "em relação a 2025 (11.800)", "+4,62%")
    `bom=True/False` pinta o delta; sem `bom`, o delta fica neutro.
    """
    ajuda_html = f"<br><span>{escape(ajuda)}</span>" if ajuda else ""
    classe = "" if bom is None else ' class="streamlit-sobe"' if bom else ' class="streamlit-desce"'
    partes = ([f"<span{classe}>{escape(delta)}</span>"] if delta else []) + ([escape(nota)] if nota else [])
    nota_html = f'<div class="streamlit-kpi-nota">{" ".join(partes)}</div>' if partes else ""
    return (f'<div class="streamlit-kpi"><div class="streamlit-kpi-rotulo">{escape(rotulo)}{ajuda_html}</div>'
            f'<div class="streamlit-kpi-valor">{escape(valor)}</div>{nota_html}</div>')


def kpis(cartoes: list[str]) -> None:
    """Faixa de KPIs: até 4 por linha, 2 em tablet, 1 no celular."""
    st.html(f'<div class="streamlit-kpis" style="--kpi-cols:{min(len(cartoes), 4) or 1}">{"".join(cartoes)}</div>')


def nota(html: str) -> None:
    """Nota de rodapé com barra azul. Recebe HTML confiável."""
    st.html(f'<div class="streamlit-nota">{html}</div>')


def rodape() -> None:
    st.html(f'<footer class="streamlit-footer">SEST SENAT · {escape(AREA)}</footer>')
