"""Aba 2 · Crescimento de clientes: cópia de ~/estudos/diex/proposicao_meta/dashboard/tabs/crescimento.py."""
import numpy as np
import pandas as pd
import streamlit as st

from charts.echarts import grafico as render_chart
from charts.tables import dataframe_ptbr
from charts.plots import CORES_NEGOCIO, fig_evolucao, titulo
from charts.theme import PLOTLY_CONFIG, fmt_number
from scripts.crescimento_dados import (PESSOA_UNICA, REGRA_META, carregar, cpfs, distintos_rotulo, recorte,
                                      tabela_crescimento)

CHOQUES = {"Turma SEST": "Turma SEST entra no SIGOP em 2020", "À Distância Livre": "EaD entra no SIGOP em 2023",
           "Campanha": "Campanha entra no SIGOP em ago/2020"}

COMO_LER = """
**Como ler estes números**

- CPFs por unidade somados: soma os CPFs distintos de cada unidade. Quem foi atendido em duas unidades conta duas vezes
    no conselho e no Nacional. É a mesma soma usada na meta por unidade.
- CPFs distintos (nacional, no conselho ou na unidade): cada pessoa conta uma vez no recorte escolhido.
- SEST e SENAT são contados à parte. Somar os dois não dá o número de pessoas do Nacional.
- Quem usou odontologia e fisioterapia conta uma vez no total, mesmo com as duas especialidades marcadas.
- Turma SEST e Campanha passaram a ser registradas no SIGOP em 2020, e o EaD do SENAT em 2023. A comparação com os anos
    anteriores a esses marcos fica distorcida.
"""

pct = lambda v: f"{'+' if v >= 0 else ''}{fmt_number(v, 2)}%"

# Seleção inicial: SEST nas quatro áreas da meta; SENAT presencial, sem Palestras e sem EJA.
PADRAO_ESP = {"SEST": {"Odontologia", "Fisioterapia", "Nutrição", "Psicologia"},
              "SENAT_FORA": {"Palestras", "Educação de Jovens e Adultos"}}
PADRAO_MOD = {"SENAT": {"Presencial"}}


def _bloco(ent: str, base: pd.DataFrame, cat: pd.DataFrame, a0: int, a1: int,
           escopo: str) -> tuple[pd.Series | None, dict]:
    """Filtro de especialidades + gráfico de evolução de uma entidade. Devolve a série e as séries por especialidade."""
    c = cat[cat.entidade == ent]
    todas = sorted(c.especialidade.unique())
    padrao = ([e for e in todas if e in PADRAO_ESP["SEST"]] if ent == "SEST" else
              [e for e in todas if e not in PADRAO_ESP["SENAT_FORA"]] if ent == "SENAT" else todas)
    esp = st.pills(f"Especialidades {ent}", todas, selection_mode="multi", default=padrao or todas, key=f"esp_{ent}")
    mods = sorted(c.modalidade.unique())
    if len(mods) > 1:
        padrao_mod = [m for m in mods if m in PADRAO_MOD.get(ent, mods)]
        mods = st.pills(f"Modalidade {ent}", mods, selection_mode="multi", default=padrao_mod or mods, key=f"mod_{ent}")
    itens = c[c.especialidade.isin(esp) & c.modalidade.isin(mods)]
    if itens.empty:
        st.warning("Selecione ao menos uma especialidade e uma modalidade.")
        return None, {}

    b = base[base.entidade == ent]
    serie = lambda g: cpfs(b, int(np.bitwise_or.reduce(g.bit.to_numpy()))).loc[a0:a1]
    s = serie(itens)
    if len(s) < 2:
        st.info(f"Sem dados de {ent} suficientes no período.")
        return None, {}

    notas = [v for k, v in CHOQUES.items() if k in {ent, *itens.especialidade, *itens.modalidade}]
    sub = (f"{escopo}. Os percentuais mostram a variação sobre o ano anterior. "
           f"{itens.especialidade.nunique()} de {len(todas)} especialidades" + "".join(f". {n}" for n in notas) + ".")
    render_chart(fig_evolucao(s.rename_axis("ano").reset_index(name="cpfs"), "ano", "cpfs", CORES_NEGOCIO[ent],
                                 titulo(f"{ent}: {pct(100 * (s.iloc[-1] / s.iloc[0] - 1))} entre {s.index[0]} e {s.index[-1]}", sub)),
                    width="stretch", config=PLOTLY_CONFIG)
    return s, {f"{ent} · {e}": serie(g) for e, g in itens.groupby("especialidade")}


def render(f=None):   # cópia literal da aba de origem; usa os próprios filtros, não os da barra lateral
    p, cat, unid = carregar()
    anos = sorted(p.ano.unique())

    c1, c2, c3 = st.columns([1.1, 1.6, 2])
    nivel = c1.radio("Nível", ["Nacional", "Conselho", "Unidade"], horizontal=True)
    regra = c2.radio("Contagem", [REGRA_META, PESSOA_UNICA], index=0, horizontal=True,
                     format_func=lambda r: distintos_rotulo(nivel) if r == PESSOA_UNICA else r,
                     disabled=nivel == "Unidade",
                     help="Somados: soma os CPFs distintos de cada unidade, e a mesma pessoa pode contar mais de uma "
                          "vez. Distintos: cada pessoa conta uma vez no recorte escolhido.")
    nome = None
    if nivel == "Conselho":
        nome = c3.selectbox("Conselho", sorted(unid.conselho.unique()))
    elif nivel == "Unidade":
        nome = c3.selectbox("Unidade", sorted(unid.unidade.unique()), index=None, placeholder="Digite para buscar")
        if not nome:
            st.info("Escolha uma unidade para ver a evolução.")
            return
    a0, a1 = st.select_slider("Período", options=anos, value=(anos[0], anos[-1]))
    if a0 == a1:
        st.warning("Escolha um período com pelo menos dois anos.")
        return

    st.caption("Seleção inicial: SEST nas quatro áreas da meta (odontologia, fisioterapia, nutrição e psicologia); "
               "SENAT só presencial, sem Palestras e sem Educação de Jovens e Adultos. Clique nos botões para "
               "incluir ou tirar.")
    base = recorte(p, unid, nivel, nome, regra)
    escopo = ("CPFs distintos na unidade" if nivel == "Unidade" else
              distintos_rotulo(nivel) if regra == PESSOA_UNICA else
              "CPFs distintos por unidade, somados; uma pessoa pode aparecer em mais de uma unidade")
    series, por_esp = {}, {}
    for col, ent in zip(st.columns(2), ["SENAT", "SEST"]):
        with col:
            s, e = _bloco(ent, base, cat, a0, a1, escopo)
            if s is not None:
                series[ent], por_esp = s, por_esp | e
    with st.expander("Campanha (categoria separada, fora da meta)"):
        s, e = _bloco("Campanha", base, cat, a0, a1, escopo)
        if s is not None:
            series["Campanha"], por_esp = s, por_esp | e

    if series:
        dist = pd.DataFrame(series).T
        dataframe_ptbr(tabela_crescimento(dist), width="stretch", hide_index=True,
                     column_config={str(a): st.column_config.NumberColumn(format="localized") for a in dist.columns})

    if por_esp:
        dist = pd.DataFrame(por_esp).T.dropna(how="all")
        with st.expander("Tabela por especialidade"):
            dataframe_ptbr(tabela_crescimento(dist, "Especialidade"), width="stretch", hide_index=True,
                         column_config={str(a): st.column_config.NumberColumn(format="localized") for a in dist.columns})

    st.info(COMO_LER)
