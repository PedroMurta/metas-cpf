"""Ponto de entrada: `uv run streamlit run diex/meta_cpfs/app/meta_cpfs.py` (da raiz do repositório).

Lê só os parquets de diex/meta_cpfs/dados/ (gerar.py e preparar_painel.py).
"""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
for pasta in (APP.parents[2], APP.parent, APP):   # raiz (common.painel, no deploy), projeto (modelo) e app
    if str(pasta) not in sys.path:
        sys.path.insert(0, str(pasta))

from common import painel as gt  # noqa: E402
import streamlit as st  # noqa: E402
from abas import conceitos, crescimento, metas, metodologia, perfil  # noqa: E402
from common.painel.casca import aplicar_tema, cabecalho, rodape  # noqa: E402
from scripts.sidebar import sidebar_filtros  # noqa: E402

st.set_page_config(page_title="Meta de CPFs distintos", layout="wide")
aplicar_tema(APP / "style_estudo.css")   # casca SEST SENAT + barra lateral, trilha e listas no padrão da Matriz
# trilha animada das pílulas (assets/filtros-animados.js, copiado da Matriz), injetada uma vez
st.html(f"<script>{(APP / 'assets/filtros-animados.js').read_text(encoding='utf-8')}</script>",
        unsafe_allow_javascript=True)
cabecalho("Meta de CPFs distintos")

f = sidebar_filtros()
ABAS = {"Conceitos e motivação": conceitos, "Crescimento de clientes": crescimento, "Perfil dos clientes": perfil,
        "Como a meta é calculada": metodologia, "Metas por unidade": metas}
for aba, modulo in zip(st.tabs(list(ABAS)), ABAS.values()):
    with aba:
        modulo.render(f)

rodape()
