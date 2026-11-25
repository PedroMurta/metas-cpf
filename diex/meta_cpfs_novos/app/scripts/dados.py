"""Dados do painel: chamadas ao modelo com cache. Sem desenho."""
import re

import pandas as pd
import streamlit as st

import modelo as M
import recortes as R
from common.painel.classico import MESES_PT

COMBINADA, AREAS_SEST = R.COMBINADA, R.AREAS_SEST
CENARIOS = {1: "Cenário A", 2: "Cenário B"}       # as duas bases da proposta (R.selecao), com os nomes da apresentação; o que entra está em comum.ENTRA
ESCOPO = {e: CENARIOS for e in R.ENTIDADES}
NOME_ENTIDADE = {COMBINADA: "SEST SENAT"}          # nome na tela
PESOS = [round(100 * w) for w in M.PESOS]
NACIONAL = 0
PARTIDA = "2023 partida"                 # coluna de 2023 sem histórico (aba Mês a mês)
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


def _lista(selecao):
    return None if selecao is None else list(selecao)


def selecao_proposta(n: int, entidade: str, campanhas: bool = False) -> tuple[str, ...] | None:
    """Especialidades de cada base (1 e 2); `campanhas` só na Proposta 2 do SEST (oculta)."""
    return None if n == 2 and campanhas and entidade == "SEST" else tuple(R.selecao(entidade, n))


def medida(entidade: str) -> str:
    return "horas" if entidade == "SENAT" else "atendimentos"


def _proposta(n: int, entidade: str, campanhas: bool, ano: bool = False) -> dict:
    sel, med = _lista(selecao_proposta(n, entidade, campanhas)), medida(entidade)
    p = (M.proposta1 if n == 1 else M.proposta2)(entidade, sel, med, ano)
    g = M.crescimento_nacional(entidade, sel, med, "contagem", ano)                   # delta Nacional
    return p | {"metas": M.com_piso(p["metas"], g if entidade == "SEST" else None), "ano": ano, "nacional": g}


@st.cache_data(show_spinner="Calculando a meta…")
def gap(n: int, entidade: str, campanhas: bool = False, ano: bool = False) -> dict:
    """Propostas 1 e 2 (ocultas): contagem de 12 meses ou, com `ano`, CPFs distintos no ano civil."""
    p = _proposta(n, entidade, campanhas, ano)
    return p | {"unidades": _rotular(p["unidades"].loc[p["universo"]])}


@st.cache_data(show_spinner="Calculando a meta em horas…")
def horas(n: int) -> dict:
    """Propostas 1 e 2 do SENAT em horas-aula."""
    p = M.regra_horas("SENAT", _lista(selecao_proposta(n, "SENAT")), M.IDADE_P1)
    return p | {"unidades": _rotular(p["unidades"].loc[p["universo"]])}


@st.cache_data(show_spinner="Calculando a meta…")
def mercado(entidade: str, escopo: int = 1, ano: bool = False) -> dict:
    """A proposta em uma das bases (escopo 1 ou 2 de R.selecao): delta Nacional (crescimento constante 2023→2026 das unidades maduras, na
    contagem da meta) em módulo, com o esforço do mercado."""
    b = _proposta(escopo, entidade, False, ano)
    p = M.proposta3(entidade, b, b["nacional"])
    return p | {"unidades": _rotular(p["unidades"].loc[p["universo"]]), "resumo": M.resumo_mercado(p["metas"])}


def rotulo_regra(m: pd.DataFrame, k: int) -> pd.Series:
    """Regra de cada unidade no cenário de k%: a que deu a meta ou o crescimento mínimo."""
    return m.regra.map(REGRA).mask(m[f"piso_{k}"], "Crescimento mínimo")


def serie_de(p: dict, unidade: int, s: pd.Series | None = None) -> pd.Series:
    """Ano → contagem (ou a série `s`) da unidade ou, no Nacional, a soma das unidades com meta."""
    s = p["serie"].contagem if s is None else s
    return s.xs(unidade, level="id_unidade") if unidade in p["metas"].index else s.groupby(level="ano").sum()


@st.cache_data(show_spinner="Separando o público…")
def serie_publico(entidade: str, escopo: int, publico: str) -> pd.Series:
    """Contagem do público por unidade com meta e ano, com 2026 projetado (a meta não muda)."""
    return M.por_publico(entidade, list(selecao_proposta(escopo, entidade)), medida(entidade), publico, mercado(entidade, escopo)["serie"].contagem)


@st.cache_data(show_spinner=False)
def serie_todas(entidade: str, selecao: tuple[str, ...], ano: bool = False, publico: str | None = None) -> pd.Series:
    """Contagem por ano (12 meses ou, com `ano`, CPFs distintos) somando todas as unidades (inclusive as sem meta)."""
    if ano:
        return R.recorte(entidade, list(selecao)).groupby("ano").pessoas.sum()
    return R.contagem(entidade, list(selecao), publico).groupby("ano").contagem.sum()


def _completar(t: pd.DataFrame, total: float) -> pd.DataFrame:
    """Meses de 2026 depois do corte = o que falta para a estimativa do ano, repartido pelo peso desses meses em 2023–2025."""
    fim = t.index[t.index > R.CORTE]
    peso = t.loc[fim, list(M.ANOS_FRACAO)].sum(axis=1)
    t = t.copy()
    t.loc[fim, R.ANO_CORRENTE] = (total - t.loc[:R.CORTE, R.ANO_CORRENTE].sum()) * peso / peso.sum()
    return t


@st.cache_data(show_spinner=False)
def mensal() -> dict:
    """SEST, 4 especialidades, unidades com meta: contagem de 12 meses por mês (linhas) em cinco colunas (2023 com histórico, 2023 como ponto
    de partida, 2024, 2025 e 2026) e o total do ano. 2026 = ano completo projetado: realizado até o corte + estimativa dos outros meses."""
    p = gap(1, "SEST")
    d = R.contagem_mensal("SEST", R.selecao("SEST", 1), p["universo"])
    t = d.pivot(index="mes", columns="ano", values="contagem").astype(float)
    t.insert(1, PARTIDA, d[d.ano == 2023].set_index("mes").partida)
    ano = t.sum()
    ano[R.ANO_CORRENTE] = p["metas"].cpf0.sum()
    t = _completar(t, ano[R.ANO_CORRENTE])
    return {"meses": t, "corte": t.loc[:R.CORTE].sum(), "ano": ano, "unidades": len(p["universo"]),
            "com_2023": int(p["serie"].contagem.xs(2023, level="ano").gt(0).sum())}


@st.cache_data(show_spinner=False)
def primeiro_estudo() -> pd.DataFrame:
    """Primeiro estudo (diex/meta_cpfs): CPFs distintos no ano civil, 4 especialidades, mesmas unidades com meta. Linhas = meses, janeiro até o
    corte e ano completo (2026 = estimativa oficial); colunas = anos desde 2023."""
    ids = [int(i) for i in gap(1, "SEST")["universo"]]
    oficial = pd.read_parquet(M.META_OFICIAL)
    assert set(oficial.index) == set(ids), "unidades do primeiro estudo diferentes das deste painel"
    m = R.sql(f"""SELECT ano, mes, sum(entradas)::DOUBLE AS cpfs FROM '{M.MENSAL_OFICIAL}'
                           WHERE ano >= 2023 AND id_unidade IN (SELECT unnest($ids)) AND NOT (ano = {R.ANO_CORRENTE} AND mes > {R.CORTE})
                           GROUP BY ALL""", {"ids": ids}).pivot(index="mes", columns="ano", values="cpfs")
    ate_corte, ano = m.loc[:R.CORTE].sum(), m.sum()
    ano[R.ANO_CORRENTE] = oficial.cpf0.sum()
    m = _completar(m, ano[R.ANO_CORRENTE])
    return pd.concat([m.set_axis(MESES_PT), ate_corte.rename(f"{MESES_PT[0]} a {MESES_PT[R.CORTE - 1].lower()}").to_frame().T,
                      ano.rename("Ano completo").to_frame().T])


def historico(p: dict, entidade: str, unidade: int, publico: str | None = None, escopo: int = 1) -> tuple[pd.Series, str]:
    """Contagem por ano (unidade ou Nacional) e a ressalva do Nacional do SEST, cujos anos fechados somam todas as unidades."""
    h = serie_de(p, unidade, serie_publico(entidade, escopo, publico) if publico else None)
    if not p["oficial"] or unidade in p["metas"].index:
        return h, ""
    todas = serie_todas(entidade, tuple(R.selecao(entidade, 1)), p["ano"], publico)
    return todas.where(todas.index < M.ANO_CORRENTE).fillna(h), (
        f" Até 2025, todas as unidades; 2026 e 2027, as {len(p['metas'])} com meta.")


def grupos_porte(m: pd.DataFrame) -> pd.DataFrame:
    """Por grupo de porte: faixa de produção, unidades, referência (P25 da produção por pessoa) e quantas acima."""
    g = m.assign(acima=m.apc > m.referencia, madura=m.get("madura", True)).groupby("grupo").agg(
        unidades=("producao", "size"), maduras=("madura", "sum"), de=("producao", "min"), ate=("producao", "max"),
        referencia=("referencia", "first"), acima=("acima", "sum"))
    return g.sort_values("de")


def nome(entidade: str) -> str:
    return NOME_ENTIDADE.get(entidade, entidade)


def nome_unidade(p: dict, unidade: int) -> str:
    return "Nacional" if unidade == NACIONAL else p["unidades"].rotulo.get(unidade, str(unidade))


@st.cache_data(show_spinner="Calculando as unidades analisadas…")
def maduras(entidade: str, selecao: tuple[str, ...] | None, medida: str, ano: bool = False, publico: str | None = None) -> dict:
    """Unidades com 5+ anos em 2023 e anos completos, na contagem da meta (12 meses exatos ou CPFs distintos):
    série, total, variação de cada ano sobre o anterior e, por unidade, a média geométrica 2023→2026, (fim ÷ início)^(1/3) − 1."""
    from common.metas import media_geometrica
    s = M.maduras(entidade, None if selecao is None else list(selecao), medida, ano=ano)
    if publico:
        s = s.assign(contagem=M.por_publico(entidade, list(selecao), medida, publico, s.contagem))
    u = _rotular(M.unidades())
    total = s.groupby(level="ano")[M.METRICAS].sum()
    cp = s.contagem.unstack()
    cres = {m: s[m].unstack().pct_change(axis=1).drop(columns=2023) for m in M.METRICAS}
    anos = cp.columns[-1] - cp.columns[0]
    return {"serie": s, "total": total, "pessoas": cp, "cres": cres,
            "geometrica": media_geometrica(cp[cp.columns[0]].where(cp[cp.columns[0]] > 0), cp[cp.columns[-1]], anos),
            "unidades": u.loc[u.index.intersection(cp.index, sort=False)], "n_total": len(u),
            "inaug_ate": M.ANO_MADURA - M.IDADE_MADURA}
