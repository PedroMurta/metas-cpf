"""Apresentação curta que abre sobre o painel (arquivo gerado por docs/apresentacao/simples/montar.py, servido por enableStaticServing)."""
from pathlib import Path

import streamlit as st

APP = Path(__file__).resolve().parents[1]


def abrir_ao_entrar() -> None:
    """Carrega o script que abre a apresentação uma vez por aba e atende o botão da barra lateral."""
    js = (APP / "apresentacao.js").read_text(encoding="utf-8").replace("__VERSAO__", (APP / "apresentacao_versao.txt").read_text().strip())
    with st.container(key="apresentacao_js"):
        st.html(f"<script>{js}</script>", unsafe_allow_javascript=True)


def botao() -> None:
    st.html('<button id="apresentacao-btn" type="button" class="streamlit-apresentacao-btn">Ver a explicação</button>')
