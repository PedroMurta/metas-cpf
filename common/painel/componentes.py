"""Componentes HTML do tema vidro: cartão, cabeçalho de cartão, faixa de KPIs, fichas, tabela e frases.

Cada componente escreve com st.html; o visual vem de assets/vidro.css (carregue uma vez com aplicar_css()).
"""
from __future__ import annotations

import math
from html import escape
from pathlib import Path

import streamlit as st

from .tema import br, escala_execucao

_CSS = Path(__file__).with_name("assets") / "vidro.css"


def aplicar_css() -> None:
    """Carrega o CSS do tema (uma vez por página, no ponto de entrada, depois do CSS base do app)."""
    st.html(f"<style>{_CSS.read_text(encoding='utf-8')}</style>")


def cartao(nome: str, compacto: bool = False, centro: bool = False):
    """st.container que vira cartão de vidro (key "gt_<nome>"; compacto = menos respiro, para KPIs e resumos).
    Cartões lado a lado em st.columns ficam com a mesma altura (a do mais alto); centro=True centraliza na
    vertical o último elemento (medidor, velocímetro) no espaço que sobra."""
    return st.container(key=f"gt_{'c_' if compacto else ''}{'m_' if centro else ''}{nome}")


def cabecalho(kicker: str, achado: str, detalhe: str = "") -> None:
    """Topo do cartão: kicker ciano com traço (omitido se vazio), o achado (título) e um detalhe (fonte, regra de
    cor...)."""
    topo = f"<span>{escape(kicker)}</span>" if kicker else ""
    st.html(f'<div class="streamlit-vidro-cab">{topo}<b>{escape(achado)}</b><p>{escape(detalhe)}</p></div>')


def _classe(direcao: str) -> str:
    """"pos"/"neg"/"" → classe CSS com prefixo."""
    return f"streamlit-{direcao}" if direcao else ""


def achado(titulo: str, detalhe: str = "") -> None:
    """Achado da página, fora de cartão (título em negrito + detalhe)."""
    st.html(f'<div class="streamlit-vidro-achado"><b>{escape(titulo)}</b><p>{escape(detalhe)}</p></div>')


def kpis(cartoes: list[tuple[str, str, str, str]], colunas: int = 4) -> None:
    """Faixa de KPIs em cascata: (rótulo, valor, nota, direção "pos"|"neg"|"")."""
    html = "".join(f'<div style="animation-delay:{i * 110}ms"><span>{escape(r)}</span><b>{escape(v)}</b>'
                   f'<em class="{_classe(d)}">{escape(n)}</em></div>' for i, (r, v, n, d) in enumerate(cartoes))
    st.html(f'<div class="streamlit-vidro-kpis" style="--colunas:{colunas}">{html}</div>')


def indicador_empresas(rotulo: str, empresas: list[dict]) -> None:
    """Caixinha de um indicador com uma coluna por empresa: nota 0–1 com barra, % executado e, se vier, a variação
    contra o período anterior. empresas: {nome, cor, norm (0..1), exec (%), var? (None | %)}."""
    blocos = []
    for k, e in enumerate(empresas):
        var = ""
        if e.get("var") is not None:
            sobe = e["var"] >= 0
            var = f'<i class="{"streamlit-pos" if sobe else "streamlit-neg"}">{"↑" if sobe else "↓"} {br(abs(e["var"]), 1)}% vs anterior</i>'
        blocos.append(f'<div style="--cor:{e["cor"]};--w:{e["norm"] * 100:.0f}%;--atraso:{k * 160}ms">'
                      f'<span>{escape(e["nome"])}</span><b>{br(e["norm"], 3)}</b>'
                      f'<div class="streamlit-trilho"><div></div></div>'
                      f'<small>Executado<br><strong>{br(e["exec"], 1)}%</strong></small>{var}</div>')
    st.html(f'<div class="streamlit-vidro-ind"><p>{escape(rotulo)}</p><div>{"".join(blocos)}</div></div>')


def selo_meta(nome: str, subtitulo: str, pct: float) -> None:
    """Topo de cartão com nome, subtítulo e selo "% da meta" (acima de 100%: borda dupla ciano pulsando)."""
    st.html(f'<div class="streamlit-vidro-selo"><div><b>{escape(nome)}</b><span>{escape(str(subtitulo))}</span></div>'
            f'<em class="{"streamlit-acima" if pct > 100 else ""}" style="--cor:{escala_execucao(pct)}">'
            f"{pct:.0f}% da meta</em></div>")


def divisao(titulo: str, partes: list[tuple[str, float, str]], unidade: str = "") -> None:
    """Barra fina segmentada com a divisão de um total (nome, valor, cor) e uma linha por parte com % e valor.
    Ex.: público transporte × comunidade sob o anel de uma especialidade."""
    total = sum(max(v, 0) for _, v, _ in partes)
    if not total:
        return
    fmt = lambda v: br(v, 0)  # noqa: E731
    barra = "".join(f'<i style="--cor:{c};flex:{max(v, 0) / total:.4f}" title="{escape(n)}"></i>' for n, v, c in partes)
    linhas = "".join(f'<li style="--cor:{c}"><span>{escape(n)}</span><b>{br(v / total * 100, 1)}%</b>'
                     f'<small>{fmt(v)}{" " + escape(unidade) if unidade else ""}</small></li>' for n, v, c in partes)
    st.html(f'<div class="streamlit-vidro-div"><span>{escape(titulo)}</span><div>{barra}</div><ul>{linhas}</ul></div>')


def titulo_caixa(nome: str, subtitulo: str = "") -> None:
    """Topo de cartão pequeno (nome + subtítulo), sem selo."""
    st.html(f'<div class="streamlit-vidro-selo"><div><b>{escape(nome)}</b><span>{escape(subtitulo)}</span></div></div>')


def ficha(kicker: str, valor: str, selo: str, detalhes: list[tuple[str, str]], cor: str, *, titulo: str = "",
          texto_html: str = "", valor_texto: bool = False) -> None:
    """Ficha-resumo: kicker, título opcional, valor grande na cor da situação, selo, linhas "rótulo: valor" e um
    parágrafo opcional (HTML confiável, montado por quem chama). valor_texto: valor é palavra, não número."""
    partes = [f"<span>{escape(kicker)}</span>"]
    if titulo:
        partes.append(f"<b>{escape(titulo)}</b>")
    partes.append(f'<strong{" class=streamlit-texto" if valor_texto else ""}>{escape(valor)}</strong>')
    if selo:
        partes.append(f"<em>{escape(selo)}</em>")
    partes += [f"<small><b>{escape(r)}:</b> {escape(v)}</small>" if r else f"<small>{escape(v)}</small>"
               for r, v in detalhes]
    if texto_html:
        partes.append(f'<p class="streamlit-texto">{texto_html}</p>')
    st.html(f'<div class="streamlit-vidro-ficha" style="--cor:{cor}">{"".join(partes)}</div>')


def valores_meta(meta: float, real: float, rodape: str = "", rotulos: tuple[str, str, str] = ("Meta", "Realizado",
                 "Variação"), maior_melhor: bool = False, fmt=None) -> None:
    """Meta, Realizado e Variação (acima/abaixo; azul quando é bom, vermelho quando é ruim) em três caixinhas lado a lado; em cartão
    estreito (< 330 px) viram três linhas "rótulo · valor · selo".
    maior_melhor=False (custo): ficar abaixo é bom; True (receita): ficar acima é bom."""
    fmt = fmt or (lambda v: "R$ " + br(v, 2))
    var = real - meta
    acima = var >= 0 if maior_melhor else var > 0
    bom = acima if maior_melhor else not acima
    st.html(f'<div class="streamlit-vidro-valores-c"><div class="streamlit-vidro-valores"><div><span>{escape(rotulos[0])}</span><b>{fmt(meta)}</b></div>'
            f'<div><span>{escape(rotulos[1])}</span><b>{fmt(real)}</b></div>'
            f'<div><span>{escape(rotulos[2])}</span><b>{fmt(abs(var))}</b>'
            f'<i class="{"streamlit-pos" if bom else "streamlit-neg"}">{"acima" if acima else "abaixo"}</i></div>'
            f"<small>{escape(str(rodape))}</small></div></div>")


def frase(html: str) -> None:
    """Frase de resumo (HTML confiável; <b> sai em ciano)."""
    st.html(f'<div class="streamlit-vidro-frase">{html}</div>')


def vazio(texto: str) -> None:
    st.html(f'<p class="streamlit-vidro-vazio">{escape(texto)}</p>')


def tabela(df, *, destaque: tuple | None = None, classes: dict | None = None, texto: int = 1,
           altura: int | None = None, total=None) -> None:
    """Tabela de vidro: cabeçalho e 1ª coluna fixos, hover ciano, colunas a partir de `texto` alinhadas à direita
    em números tabulares. Os valores entram já formatados (strings); vazio = "—".
    destaque: (coluna, valor) → linha de referência; classes: {coluna: f(valor) → "pos"|"neg"|""};
    total: f(linha) → True para a linha de total (negrito)."""
    colunas = list(df.columns)
    corpo = []
    for linha in df.to_dict("records"):
        cls = (["streamlit-destaque"] if destaque and linha.get(destaque[0]) == destaque[1] else []) + \
              (["streamlit-total"] if total and total(linha) else [])
        celulas = []
        for k, c in enumerate(colunas):
            v = linha[c]
            sem = v is None or v == "" or (isinstance(v, float) and math.isnan(v))
            classe = (["streamlit-num"] if k >= texto else []) + ([_classe(classes[c](v))] if classes and c in classes and not sem else [])
            celulas.append(f'<td class="{" ".join(classe)}">{"—" if sem else escape(str(v))}</td>')
        corpo.append(f'<tr class="{" ".join(cls)}">{"".join(celulas)}</tr>')
    estilo = f' style="max-height:{altura}px"' if altura else ""
    st.html(f'<div class="streamlit-vidro-tabela"{estilo}><table><thead><tr>{"".join(f"<th>{escape(str(c))}</th>" for c in colunas)}'
            f'</tr></thead><tbody>{"".join(corpo)}</tbody></table></div>')
