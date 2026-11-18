"""Dados da aba Crescimento de clientes, copiados de ~/estudos/diex/proposicao_meta/dashboard/data.py.

Única mudança: o cadastro de unidades (id, nome, conselho) vem da base padrão em vez de volume_especialidade.parquet.
perfil_cpf.parquet = fetch('perfil_cpf', ano_ini=2019, ano_fim=2025) (queries/perfil_cpf.sql).
"""
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


DADOS = Path(__file__).resolve().parents[2] / "dados"
REGRA_META, PESSOA_UNICA = "CPFs por unidade somados", "CPFs distintos no recorte"   # rótulo na tela: distintos_rotulo()


@st.cache_data
def carregar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Perfil de uso com bitmask de itens, catálogo de itens (especialidade|modalidade) e cadastro de unidades."""
    p = pd.read_parquet(DADOS / "perfil_cpf.parquet")
    cat = (p[["entidade", "itens"]].explode("itens").rename(columns={"itens": "item"})
           .drop_duplicates().sort_values(["entidade", "item"]).reset_index(drop=True))
    cat[["especialidade", "modalidade"]] = cat.item.str.split("|", expand=True)
    cat["bit"] = np.left_shift(np.int64(1), cat.index.to_numpy(dtype="int64"))
    bit = dict(zip(cat.item, cat.bit))
    p["bits"] = p.pop("itens").map(lambda t: sum(int(bit[i]) for i in t)).astype("int64")
    ids = p.loc[p.id_unidade > 0, "id_unidade"].unique()
    unid = (pd.read_parquet(DADOS / "unidades.parquet").query("id_unidade in @ids").reset_index(drop=True)
            .fillna({"conselho": ""}).replace({"conselho": {"": "Sem regional"}}))
    return p, cat, unid


def distintos_rotulo(nivel: str) -> str:
    """Rótulo da contagem deduplicada conforme o nível: "CPFs distintos nacional", "... no conselho", "... na unidade"."""
    return {"Nacional": "CPFs distintos nacional", "Conselho": "CPFs distintos no conselho"}.get(
        nivel, "CPFs distintos na unidade")


def recorte(p: pd.DataFrame, unid: pd.DataFrame, nivel: str, nome: str | None, regra: str) -> pd.DataFrame:
    """Seleciona o nível nativo ou, explicitamente, a soma das contagens distintas por unidade."""
    if nivel == "Unidade":
        return p[(p.nivel == "unidade") & p.id_unidade.isin(unid.loc[unid.unidade == nome, "id_unidade"])]
    if regra == PESSOA_UNICA:
        return p[p.nivel == "nacional"] if nivel == "Nacional" else p[(p.nivel == "conselho") & (p.conselho == nome)]
    u = p[p.nivel == "unidade"]
    return u if nivel == "Nacional" else u[u.id_unidade.isin(unid.loc[unid.conselho == nome, "id_unidade"])]


def cpfs(p: pd.DataFrame, mascara: int) -> pd.Series:
    """Pessoas distintas por ano que usaram ao menos um item da máscara, no nível já selecionado."""
    return p.loc[(p.bits.to_numpy() & mascara) != 0].groupby("ano").cpfs.sum()


def tabela_crescimento(dist: pd.DataFrame, nomes: str = "Negócio") -> pd.DataFrame:
    """Valores por ano + variação ano a ano + acumulado do período."""
    from charts.theme import fmt_number
    pct = lambda v: "—" if pd.isna(v) else f"{'+' if v >= 0 else ''}{fmt_number(v, 1)}%"  # noqa: E731
    yoy = dist.div(dist.shift(axis=1)).sub(1).mul(100).iloc[:, 1:]
    yoy.columns = [f"{a - 1}→{a}" for a in yoy.columns]
    a0, a1 = dist.columns[0], dist.columns[-1]
    yoy[f"{a0}→{a1}"] = 100 * (dist[a1] / dist[a0] - 1)
    t = dist.round(0).astype("Int64").join(yoy.map(pct))
    t.columns = t.columns.map(str)
    return t.reset_index(names=nomes)
