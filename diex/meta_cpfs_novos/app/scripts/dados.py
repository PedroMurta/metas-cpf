"""Dados do painel: chamadas ao modelo com cache. Sem desenho."""
import re

import pandas as pd
import streamlit as st

import modelo as M
import recortes as R

COMBINADA = R.COMBINADA
CAMPANHA = "Campanha · "            # prefixo dos tipos de campanha (SEST)
CAMPANHAS = "Campanhas"             # item único na lista de especialidades; os tipos ficam num cartão à parte
ESCOPO = {"SEST": {1: "4 especialidades", 2: "Todas, sem campanhas"},
          "SENAT": {1: "Seleção inicial", 2: "Todas as especialidades"}}   # bases das propostas
AREAS_SEST = ["Odontologia", "Fisioterapia", "Psicologia", "Nutrição"]
SENAT_FORA = {"Palestras", "Educação de Jovens e Adultos"}   # fora da seleção inicial do SENAT (como no meta_cpfs)
SENAT_MODALIDADES = {"Presencial"}
SEP = " · "                                                 # grupo SENAT = "<tipo de curso> · <modalidade>"
PESOS = [round(100 * w) for w in M.PESOS]
NACIONAL = 0
TIPOLOGIAS = ["A", "B", "C", "CN", "D", "DN"]
NOME = re.compile(r"^UNIDADE\s+(?P<tip>CN|DN|A|B|C|D)\s+(?P<num>\d+)\s+-\s+(?P<cidade>.+)$")
REGRA = {"fórmula": "Acima da referência", "mediana": "Mediana nacional", "própria": "Mediana própria", "ritmo": "Ritmo das horas", "nacional": "Crescimento Nacional"}


def _rotular(u: pd.DataFrame) -> pd.DataFrame:
    """Rótulo "UNIDADE A - Nº 04 - BRASÍLIA/DF", conselho sem o prefixo e ordem por tipologia e número (como meta_cpfs)."""
    partes = u.unidade.str.extract(NOME)
    u = u.assign(rotulo=("UNIDADE " + partes.tip + " - Nº " + partes.num + " - " + partes.cidade).fillna(u.unidade),
                 conselho_curto=u.conselho.str.replace(r"^CONSELHO REGIONAL\s+(D[AOE]S?\s+)?", "", regex=True),
                 ordem_tip=partes.tip.map({t: i for i, t in enumerate(TIPOLOGIAS)}).fillna(len(TIPOLOGIAS)),
                 ordem_num=pd.to_numeric(partes.num, errors="coerce").fillna(9999))
    return u.sort_values(["ordem_tip", "ordem_num", "rotulo"])


@st.cache_data(show_spinner=False)
def grupos(entidade: str) -> list[str]:
    return R.grupos(entidade).grupo.tolist()


def senat_partes(grupo: str) -> tuple[str, str]:
    tipo, _, mod = grupo.rpartition(SEP)
    return tipo, mod


def _lista(selecao):
    return None if selecao is None else list(selecao)


def selecao_inicial(entidade: str) -> tuple[str, ...]:
    """SEST nas 4 áreas; SENAT presencial, sem Palestras e sem EJA."""
    if entidade == "SEST":
        return tuple(g for g in grupos("SEST") if g in AREAS_SEST)
    return tuple(g for g in grupos("SENAT") if senat_partes(g)[0] not in SENAT_FORA
                 and senat_partes(g)[1] in SENAT_MODALIDADES)


def selecao_proposta(n: int, entidade: str, campanhas: bool = False) -> tuple[str, ...] | None:
    """Especialidades das Propostas 1 (seleção inicial) e 2 (todas; no SEST, campanhas só com o botão)."""
    if n == 1:
        return selecao_inicial(entidade)
    if entidade == "SENAT" or campanhas:
        return None
    return tuple(g for g in grupos("SEST") if not g.startswith(CAMPANHA))


def medida(entidade: str) -> str:
    return "horas" if entidade == "SENAT" else "atendimentos"


def _proposta(n: int, entidade: str, campanhas: bool) -> dict:
    sel, med = _lista(selecao_proposta(n, entidade, campanhas)), medida(entidade)
    return M.proposta1(entidade, sel, med) if n == 1 else M.proposta2(entidade, sel, med)


@st.cache_data(show_spinner="Calculando a meta…")
def gap(n: int, entidade: str, campanhas: bool = False) -> dict:
    """Propostas 1 e 2 em CPFs distintos."""
    p = _proposta(n, entidade, campanhas)
    return p | {"unidades": _rotular(p["unidades"].loc[p["universo"]])}


@st.cache_data(show_spinner="Calculando a meta em horas…")
def horas(n: int) -> dict:
    """Propostas 1 e 2 do SENAT em horas-aula."""
    p = M.regra_horas("SENAT", _lista(selecao_proposta(n, "SENAT")), M.IDADE_P1)
    return p | {"unidades": _rotular(p["unidades"].loc[p["universo"]])}


@st.cache_data(show_spinner="Calculando a meta pelo fator de mercado…")
def mercado(entidade: str, escopo: int = 1) -> dict:
    """Proposta 3 sobre o esperado da seleção inicial (escopo 1) ou de todas as especialidades (escopo 2, sem campanhas)."""
    p = M.proposta3(entidade, _proposta(escopo, entidade, False))
    return p | {"unidades": _rotular(p["unidades"].loc[p["universo"]]), "resumo": M.resumo_mercado(p["metas"])}


def serie_de(p: dict, unidade: int, coluna: str = "pessoas") -> pd.Series:
    """Ano → valor da unidade ou, no Nacional, a soma das unidades com meta."""
    s = p["serie"][coluna]
    return s.xs(unidade, level="id_unidade") if unidade in p["metas"].index else s.groupby(level="ano").sum()


@st.cache_data(show_spinner=False)
def serie_todas(entidade: str, selecao: tuple[str, ...]) -> pd.Series:
    """CPFs distintos por ano somando todas as unidades (inclusive as sem meta), como na apresentação."""
    return R.recorte(entidade, list(selecao)).groupby("ano").pessoas.sum()


def historico(p: dict, entidade: str, unidade: int) -> tuple[pd.Series, str]:
    """CPFs distintos por ano (unidade ou Nacional) e a ressalva do Nacional do SEST, cujos anos fechados somam todas as
    unidades, como na apresentação."""
    h = serie_de(p, unidade)
    if not p["oficial"] or unidade in p["metas"].index:
        return h, ""
    todas = serie_todas(entidade, selecao_inicial(entidade))
    return todas.where(todas.index < M.ANO_CORRENTE).fillna(h), (
        f" Até 2025, todas as unidades, como na apresentação; 2026 e 2027, as {len(p['metas'])} com meta.")


def grupos_porte(m: pd.DataFrame) -> pd.DataFrame:
    """Por grupo de porte: faixa de produção, unidades, referência (P25 da produção por pessoa) e quantas acima."""
    g = m.assign(acima=m.apc > m.referencia, madura=m.get("madura", True)).groupby("grupo").agg(
        unidades=("producao", "size"), maduras=("madura", "sum"), de=("producao", "min"), ate=("producao", "max"),
        referencia=("referencia", "first"), acima=("acima", "sum"))
    return g.sort_values("de")


def nome_unidade(p: dict, unidade: int) -> str:
    return "Nacional" if unidade == NACIONAL else p["unidades"].rotulo.get(unidade, str(unidade))


@st.cache_data(show_spinner="Calculando as unidades maduras…")
def maduras(entidade: str, selecao: tuple[str, ...] | None, medida: str) -> dict:
    """Unidades com 5+ anos em 2023 e anos completos, em CPFs distintos (pessoa conta uma vez por unidade e ano):
    série, total, variação de cada ano sobre o anterior e, por unidade, os dois resumos do período 2023→2026:
    média aritmética das três variações anuais e crescimento constante (média geométrica, (fim ÷ início)^(1/3) − 1)."""
    from common.metas import media_geometrica
    s = M.maduras(entidade, None if selecao is None else list(selecao), medida)
    u = _rotular(M.unidades())
    total = s.groupby(level="ano")[M.METRICAS].sum()
    cp = s.pessoas.unstack()
    cres = {m: s[m].unstack().pct_change(axis=1).drop(columns=2023) for m in M.METRICAS}
    anos = cp.columns[-1] - cp.columns[0]
    return {"serie": s, "total": total, "pessoas": cp, "cres": cres,
            "aritmetica": cres["pessoas"].mean(axis=1),
            "geometrica": media_geometrica(cp[cp.columns[0]].where(cp[cp.columns[0]] > 0), cp[cp.columns[-1]], anos),
            "unidades": u.loc[u.index.intersection(cp.index, sort=False)], "n_total": len(u),
            "inaug_ate": M.ANO_MADURA - M.IDADE_MADURA}
