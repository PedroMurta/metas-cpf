"""Entrada do Streamlit Cloud: mantém o caminho já publicado e abre o painel das propostas de meta 2027."""
import runpy
import sys
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parents[3]
# Depois de um push, o processo do Streamlit Cloud pode seguir com módulos antigos na memória (arquivo novo importando módulo antigo).
# Se algum .py mudou desde a última execução, descarta os módulos deste repositório e o cache de dados.
versao = hash(tuple(sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in RAIZ.rglob("*.py"))))
if getattr(sys, "_metas_cpf_versao", None) != versao:
    for nome, modulo in list(sys.modules.items()):
        arquivo = getattr(modulo, "__file__", None)
        if nome != "__main__" and arquivo and Path(arquivo).is_relative_to(RAIZ):
            sys.modules.pop(nome, None)
    st.cache_data.clear()
    sys._metas_cpf_versao = versao

runpy.run_path(str(RAIZ / "diex" / "meta_cpfs_novos" / "app" / "meta_cpfs_novos.py"), run_name="__main__")
