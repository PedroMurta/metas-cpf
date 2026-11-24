"""Ponto de entrada: `uv run streamlit run diex/meta_cpfs_novos/app/meta_cpfs_novos.py` (da raiz do repositório).

Visual, tema e componentes vêm de common.painel (compartilhado); aqui ficam só as abas do estudo.
Lê os parquets de diex/meta_cpfs_novos/dados/ (extrair.py → preparar.py) pelo modelo.
"""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
for pasta in (APP.parents[2], APP.parent, APP):   # raiz (common), projeto (modelo, recortes) e app
    if str(pasta) not in sys.path:
        sys.path.insert(0, str(pasta))

import streamlit as st  # noqa: E402

from abas import analise, comparacao, introducao, mercado  # noqa: E402
from common.painel.casca import aplicar_tema, cabecalho, rodape  # noqa: E402
from scripts.sidebar import filtros, visao  # noqa: E402

st.set_page_config(page_title="Meta de CPFs novos", layout="wide")
aplicar_tema(APP / "estudo.css", filtros=True)   # casca + barra lateral no padrão da Matriz (common/painel)
cabecalho("Meta de CPFs novos")

f = visao(filtros())
ABAS = {"Introdução": introducao.render, "Proposta": mercado.render, "Comparação": comparacao.render,
        "Análise": analise.render}   # ocultas a pedido: "Mês a mês" (abas/mensal.py, 23/11) e Propostas 1 e 2 (abas/gap.py, 24/11)
for aba, render in zip(st.tabs(list(ABAS)), ABAS.values()):
    with aba:
        render(f)

rodape()
