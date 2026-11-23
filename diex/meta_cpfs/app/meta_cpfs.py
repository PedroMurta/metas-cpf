"""Entrada do Streamlit Cloud: mantém o caminho já publicado e abre o painel das propostas de meta 2027."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[2] / "meta_cpfs_novos" / "app" / "meta_cpfs_novos.py"), run_name="__main__")
