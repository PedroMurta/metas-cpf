"""Tabela HTML SEST SENAT: números em pt-BR, cabeçalho e primeira coluna fixos, sem alterar o DataFrame fonte."""
from __future__ import annotations

import unicodedata
from html import escape

import pandas as pd
import streamlit as st
from pandas.api.types import is_bool_dtype, is_numeric_dtype

from .classico import fmt_numero, formatar_percentuais

PERCENTUAL = ("pct", "percentual", "participacao", "crescimento", "variacao", "cumprimento", "captura", "taxa")
MOEDA = ("r$", "moeda", "preco", "custo", "receita", "valor")


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))


def _formatador(nome: str):
    """Formato pelo nome da coluna: '%' ou termos percentuais → 2 casas (+'%' se o nome não tiver);
    moeda → 'R$ 1.234,56'; inteiros → '1.234'; demais → 2 casas."""
    rotulo = _sem_acentos(nome)
    percentual = "%" in rotulo or any(t in rotulo for t in PERCENTUAL)
    moeda = any(t in rotulo for t in MOEDA)

    def formatar(valor):
        if pd.isna(valor):
            return "—"
        if moeda:
            return f"R$ {fmt_numero(valor, 2)}"
        numero = float(valor)
        if not percentual and numero.is_integer():
            return fmt_numero(numero, 0)
        return fmt_numero(numero, 2) + ("%" if percentual and "%" not in rotulo else "")

    return formatar


def _texto(valor) -> str:
    return "—" if valor is None or (not isinstance(valor, str) and pd.isna(valor)) else formatar_percentuais(str(valor))


def tabela(dados, titulo: str = "", altura_max: int = 520, mostrar_indice: bool = False,
           formatos: dict | None = None) -> None:
    """Tabela clara em cartão. Longas rolam com o cabeçalho fixo; largas rolam com a 1ª coluna fixa.

    `formatos` sobrepõe o formato inferido: {"Coluna": lambda v: ...}.
    """
    dados = dados if isinstance(dados, pd.DataFrame) else pd.DataFrame(dados)
    if mostrar_indice:
        dados = dados.reset_index()
    numericas = {c for c in dados.columns if is_numeric_dtype(dados[c].dtype) and not is_bool_dtype(dados[c].dtype)}
    fmt = {c: (_formatador(str(c)) if c in numericas else _texto) for c in dados.columns}
    fmt.update(formatos or {})
    cab = "".join(f"<th>{escape(_texto(c))}</th>" for c in dados.columns)
    linhas = "".join(
        "<tr>" + "".join(f'<td class="{"num" if c in numericas else ""}">{escape(fmt[c](v))}</td>'
                         for c, v in zip(dados.columns, linha)) + "</tr>"
        for linha in dados.itertuples(index=False, name=None))
    rotulo = f'<div class="streamlit-tabela-titulo">{escape(titulo)}</div>' if titulo else ""
    st.html(f'<div class="streamlit-tabela">{rotulo}<div class="streamlit-tabela-rolagem" '
            f'style="max-height:{altura_max}px"><table><thead><tr>{cab}</tr></thead>'
            f"<tbody>{linhas}</tbody></table></div></div>")
