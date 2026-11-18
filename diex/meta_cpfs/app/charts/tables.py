"""Formatação pt-BR para tabelas de apresentação, sem alterar os dados originais."""
from __future__ import annotations

import unicodedata
from html import escape

import pandas as pd
import streamlit as st
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from charts.theme import formatar_percentuais


def _sem_acentos(texto: str) -> str:
    return "".join(
        caractere for caractere in unicodedata.normalize("NFKD", texto.lower())
        if not unicodedata.combining(caractere)
    )


def _formatador_coluna(nome: str, serie: pd.Series):
    rotulo = _sem_acentos(nome)
    percentual = "%" in rotulo or any(
        termo in rotulo for termo in ("pct", "percentual", "participacao", "crescimento", "cumprimento", "captura")
    )
    moeda = any(termo in rotulo for termo in ("r$", "moeda", "preco", "custo", "receita"))
    sufixo_percentual = percentual and "%" not in rotulo

    def formatar(valor):
        if pd.isna(valor):
            return "—"
        if moeda:
            return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        numero = float(valor)
        if not percentual and numero.is_integer():
            return f"{int(valor):,}".replace(",", ".")
        texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{texto}%" if sufixo_percentual else texto

    return formatar


def _formatar_texto_ptbr(valor):
    return formatar_percentuais(valor)


def _texto(valor) -> str:
    return "—" if valor is None or (not isinstance(valor, str) and pd.isna(valor)) else \
        _formatar_texto_ptbr(str(valor))


def dataframe_ptbr(dados, hide_index: bool = True, titulo: str = "", altura_max: int = 520, **_):
    """Tabela de vidro (glass-template: classes streamlit-vidro-tabela), números em pt-BR; não altera o DataFrame fonte.

    Tabelas longas rolam dentro do cartão com o cabeçalho fixo; largas rolam na horizontal com a primeira coluna
    fixa. Argumentos do st.dataframe (width, key, column_config) são aceitos e ignorados.
    """
    if not isinstance(dados, pd.DataFrame):
        dados = pd.DataFrame(dados)
    if not hide_index:
        dados = dados.reset_index()
    numericas = {coluna for coluna in dados.columns
                 if is_numeric_dtype(dados[coluna].dtype) and not is_bool_dtype(dados[coluna].dtype)}
    formatadores = {coluna: (_formatador_coluna(str(coluna), dados[coluna]) if coluna in numericas else _texto)
                    for coluna in dados.columns}
    cab = "".join(f'<th class="{"num" if c in numericas else ""}">{escape(_texto(c))}</th>' for c in dados.columns)
    linhas = "".join(
        "<tr>" + "".join(f'<td class="{"num" if c in numericas else ""}">{escape(formatadores[c](v))}</td>'
                         for c, v in zip(dados.columns, linha)) + "</tr>"
        for linha in dados.itertuples(index=False, name=None))
    rotulo = f'<div class="streamlit-vidro-tb-titulo">{escape(titulo)}</div>' if titulo else ""
    st.html(f'<div class="streamlit-vidro-tb">{rotulo}<div class="streamlit-vidro-tabela" style="max-height:{altura_max}px">'
            f"<table><thead><tr>{cab}</tr></thead><tbody>{linhas}</tbody></table></div></div>")