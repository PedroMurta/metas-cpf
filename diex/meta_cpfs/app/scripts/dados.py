"""Dados do painel: lê os parquets de dados/ (gerar.py e preparar_painel.py) e devolve recortes por nível e área.

Nível = id_unidade; 0 = Nacional (pessoas deduplicadas no país). Área = 'Todas as áreas' (as quatro juntas, pessoa
contada uma vez) ou uma especialidade. Sem desenho aqui. 2026 projetado pelo mesmo método da meta (modelo.projetar).
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

import modelo as M

DADOS = Path(__file__).resolve().parents[2] / "dados"
NACIONAL = 0
TODAS = "Todas as áreas"
ESPECIALIDADES = [TODAS, "Odontologia", "Fisioterapia", "Psicologia", "Nutrição"]
COL_META = {"Odontologia": "meta_odonto", "Fisioterapia": "meta_fisio", "Psicologia": "meta_psico",
            "Nutrição": "meta_nutri", TODAS: "meta_total"}
ANOS = list(range(2022, M.ANO_BASE + 1))
PUBLICOS = ["Transporte", "Dependentes", "Comunidade", "Múltiplos perfis", "Não informado"]
FAIXAS_IDADE = ["0 a 11", "12 a 17", "18 a 29", "30 a 39", "40 a 49", "50 a 59", "60 ou mais", "Não informado"]
FAIXAS_FREQ = ["1", "2 a 5", "6 a 10", "11 a 20", "mais de 20"]
INSTRUCAO = ["Sem instrução", "Fundamental incompleto", "Fundamental completo", "Médio incompleto", "Médio completo",
             "Superior incompleto", "Superior completo", "Pós-graduação", "Não informado"]
TIPOLOGIAS = ["A", "B", "C", "CN", "D", "DN"]
# Anos fechados da apresentação de 17/11 (meta_cpfs_distintos_2027.html; gerador/dados.json, serie_todas, do estudo
# proposicao_meta): soma dos CPFs distintos de cada unidade. O ano-base e 2027 vêm do modelo (resultado_2027).
APRESENTACAO_SERIE = {2019: 379_563, 2020: 312_816, 2021: 352_416, 2022: 384_938, 2023: 455_904, 2024: 504_120,
                      2025: 575_679}
NOME = re.compile(r"^UNIDADE\s+(?P<tip>CN|DN|A|B|C|D)\s+(?P<num>\d+)\s+-\s+(?P<cidade>.+)$")


def _ler(nome: str) -> pd.DataFrame:
    return pd.read_parquet(DADOS / f"{nome}.parquet")


@st.cache_data(show_spinner=False)
def unidades() -> pd.DataFrame:
    """Unidades com Agenda no período, com rótulo "UNIDADE A - Nº 04 - BRASÍLIA/DF", cidade, regional e a ordem
    por tipologia (A, B, C, CN, D, DN) e número."""
    ids = _ler("agenda_mensal").id_unidade.unique().tolist()
    cad = _ler("unidades").query("id_unidade in @ids").set_index("id_unidade")   # preparar_painel.base_padrao
    partes = cad.unidade.str.extract(NOME)
    cad["rotulo"] = ("UNIDADE " + partes.tip + " - Nº " + partes.num + " - " + partes.cidade).fillna(cad.unidade)
    cad["cidade"] = partes.cidade.fillna(cad.unidade)
    cad["ordem_tip"] = partes.tip.map({t: i for i, t in enumerate(TIPOLOGIAS)}).fillna(len(TIPOLOGIAS))
    cad["ordem_num"] = pd.to_numeric(partes.num, errors="coerce").fillna(9999)
    cad["conselho"] = cad.conselho.str.replace(r"^CONSELHO REGIONAL\s+(D[AOE]S?\s+)?", "", regex=True)
    return cad.sort_values(["ordem_tip", "ordem_num", "rotulo"])


@st.cache_data(show_spinner=False)
def _mensal(nivel: int, esp: str) -> pd.DataFrame:
    m = _ler("painel_mensal").query("id_unidade == @nivel and especialidade == @esp")
    return M.preparar_mensal(m.drop(columns="especialidade"))


@st.cache_data(show_spinner=False)
def anual(nivel: int, esp: str = TODAS) -> pd.DataFrame:
    """Pessoas, atendimentos e atendimentos por pessoa por ano; ANO_BASE projetado (coluna projetado)."""
    m = _mensal(nivel, esp)
    if m.empty:
        return pd.DataFrame(index=ANOS, columns=["cpfs", "atendimentos", "projetado", "apc"], dtype=float)
    a = M.pessoas_anuais(m).droplevel("id_unidade").astype(float)
    a["projetado"] = False
    proj = M.projetar(M.fracoes(m))
    if len(proj):
        a.loc[M.ANO_BASE, ["cpfs", "atendimentos", "projetado"]] = [proj.cpf0.iloc[0], proj.at0.iloc[0], True]
    a = a.reindex(ANOS)
    a["apc"] = a.atendimentos / a.cpfs
    return a


@st.cache_data(show_spinner=False)
def acumulado(nivel: int, esp: str = TODAS) -> pd.DataFrame:
    """Pessoas acumuladas no ano mês a mês (mês × ano)."""
    m = _mensal(nivel, esp)
    return m.pivot_table("entradas", "mes", "ano", aggfunc="sum").cumsum() if len(m) else pd.DataFrame()


@st.cache_data(show_spinner=False)
def meta_producao(nivel: int, esp: str = TODAS) -> pd.Series:
    """Meta de atendimentos pactuada por ano (total ou da área); Nacional = soma das unidades."""
    col = COL_META[esp]
    mt = _ler("meta_atendimentos").astype({col: float})
    mt["id_unidade"] = mt.cod_unidade_sigop.astype("Int64").replace({196: 141})
    if nivel != NACIONAL:
        mt = mt[mt.id_unidade == nivel]
    return mt.groupby("ano")[col].sum()


@st.cache_data(show_spinner=False)
def perfil(nivel: int, esp: str = TODAS) -> pd.DataFrame:
    p = _ler("perfil_pessoas").query("id_unidade == @nivel and especialidade == @esp").copy()
    p["top10"] = p.top10.astype(bool)
    return p


def _projetar(p: pd.DataFrame, nivel: int, esp: str) -> pd.DataFrame:
    """ANO_BASE escalado para o total projetado (pessoas e atendimentos à parte), supondo que a composição até o
    CORTE vale para o ano todo."""
    p = p.astype({"pessoas": float, "atendimentos": float})
    a, q = anual(nivel, esp), p.ano == M.ANO_BASE
    if q.any() and pd.notna(a.cpfs.get(M.ANO_BASE)):
        p.loc[q, "pessoas"] *= a.cpfs[M.ANO_BASE] / p.loc[q, "pessoas"].sum()
        p.loc[q, "atendimentos"] *= a.atendimentos[M.ANO_BASE] / p.loc[q, "atendimentos"].sum()
    return p


@st.cache_data(show_spinner=False)
def perfil_projetado(nivel: int, esp: str = TODAS) -> pd.DataFrame:
    """Perfil com ANO_BASE projetado (_projetar). Não vale para faixa_freq: quem veio 1 vez até outubro ainda pode
    voltar."""
    return _projetar(perfil(nivel, esp), nivel, esp)


@st.cache_data(show_spinner=False)
def cadastro_projetado(nivel: int, esp: str = TODAS) -> pd.DataFrame:
    """Grau de instrução e raça/cor informada (perfil_cadastro), com ANO_BASE projetado (_projetar). raca_informada
    só serve para medir o preenchimento do cadastro (7,6% em 2025), não para composição."""
    c = _ler("perfil_cadastro").query("id_unidade == @nivel and especialidade == @esp").copy()
    c["raca_informada"] = c.raca_informada.astype(bool)
    return _projetar(c, nivel, esp)


@st.cache_data(show_spinner=False)
def status(nivel: int, esp: str = TODAS) -> pd.DataFrame:
    """Novos, retidos e reativados por ano (base padrão; ano corrente parcial, até a carga da base)."""
    s = _ler("status_clientes").query("id_unidade == @nivel and especialidade == @esp")
    return s.pivot_table("pessoas", "ano", "status", aggfunc="sum").reindex(columns=["Novos", "Retidos", "Reativados"])


@st.cache_data(show_spinner=False)
def empresas(nivel: int, ano: int, esp: str = TODAS) -> pd.DataFrame:
    e = _ler("empresas").query("id_unidade == @nivel and ano == @ano and especialidade == @esp")
    return e.sort_values("pessoas", ascending=False)


@st.cache_data(show_spinner=False)
def areas_agenda(ano: int = M.ANO_BASE - 1) -> pd.DataFrame:
    return _ler("agenda_areas").query("ano == @ano")


@st.cache_data(show_spinner=False)
def meta(nivel: int) -> pd.Series | None:
    """Linha da meta da unidade (dados/meta_cpf_{ANO_META}.parquet) ou None (Nacional ou fora do universo)."""
    r = _ler(f"meta_cpf_{M.ANO_META}")
    return r.loc[nivel] if nivel in r.index else None


# Aba Metodologia: resultado da meta (dados/meta_cpf_{ANO_META}.parquet), por unidade, faixa de Sturges e grupo ------
@st.cache_data(show_spinner=False)
def metas() -> pd.DataFrame:
    """Uma linha por unidade do universo, com o rótulo do painel."""
    r = _ler(f"meta_cpf_{M.ANO_META}")
    r["com_meta"] = r.com_meta.astype(bool)
    r["universo"] = r.universo.astype(bool)
    return r.drop(columns="conselho").join(unidades()[["rotulo", "cidade", "conselho", "ordem_tip", "ordem_num"]])


@st.cache_data(show_spinner=False)
def faixas_sturges() -> pd.DataFrame:
    """As k faixas de Sturges (antes da junção): unidades, menor e maior produção e o grupo final (só o universo)."""
    r = metas().query("universo")
    return (pd.DataFrame({"faixa": M.grupos_sturges(r.at0), "grupo": r.grupo, "at0": r.at0})
            .groupby("faixa").agg(unidades=("at0", "size"), menor=("at0", "min"), maior=("at0", "max"),
                                  grupo=("grupo", "first")))


@st.cache_data(show_spinner=False)
def grupos() -> pd.DataFrame:
    """Por grupo: unidades, faixa de produção, referência (P25) e unidades com meta, acima e na referência ou abaixo."""
    r = metas().query("universo")
    g = r.groupby("grupo").agg(unidades=("at0", "size"), menor=("at0", "min"), maior=("at0", "max"),
                               referencia=("referencia", "first"), com_meta=("com_meta", "sum"))
    acima = r[r.com_meta].groupby("grupo").acima.agg(lambda s: int(s.astype(bool).sum()))
    g["acima"] = acima.reindex(g.index).fillna(0).astype(int)
    g["abaixo"] = g.com_meta - g.acima
    return g.sort_values("menor")


def pesos() -> dict[str, int]:
    """Peso da distância em % → sufixo das colunas meta_pct_{k} e meta_pessoas_{k}."""
    return {f"{round(100 * p)}%": round(100 * p) for p in M.PESOS_TESTE}


@st.cache_data(show_spinner=False)
def ate_corte(nivel: int, esp: str = TODAS) -> tuple[float, float]:
    """Pessoas e atendimentos do ANO_BASE até o CORTE (realizado, sem projeção)."""
    m = _mensal(nivel, esp)
    m = m[m.ano == M.ANO_BASE]
    return float(m.entradas.sum()), float(m.atendimentos.sum())


def metas_unidades(conselho: str = "Todos") -> pd.DataFrame:
    """Unidades com meta (todas as do universo; do conselho, se escolhido), na ordem tipologia e número. `regra`:
    "fórmula" (acima da referência), "mediana" (nacional: na referência ou abaixo) ou "própria" (sem histórico
    completo: mediana dos próprios crescimentos)."""
    r = metas()
    r = r[r.meta_pct.notna() & ((r.conselho == conselho) if conselho != "Todos" else True)]
    return r.sort_values(["ordem_tip", "ordem_num"])


@st.cache_data(show_spinner=False)
def resultado_2027() -> tuple[pd.Series, float, dict[int, float]]:
    """Soma dos CPFs distintos das unidades: anos fechados da apresentação + ano-base projetado, estimativa sem meta e
    meta de 2027 por cenário (modelo)."""
    r = metas()
    serie = pd.Series({**APRESENTACAO_SERIE, M.ANO_BASE: r.cpf0.sum()}, dtype=float)
    return serie, float(r.sem_meta.sum()), {p: float(r[f"meta_pessoas_{p}"].sum()) for p in pesos().values()}
