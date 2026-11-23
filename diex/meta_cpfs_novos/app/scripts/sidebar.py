"""Barra lateral no padrão da Matriz (cartões por seção, common.painel.casca.secao_lateral): Entidade, Filtros (unidade,
conselho) e Cenário (parte do gap, Propostas 1 e 2). As abas só leem o objeto."""
from dataclasses import dataclass

import streamlit as st

import recortes as R
from common.painel.casca import secao_lateral
from scripts import dados as D

TODOS = "Todos"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@dataclass(frozen=True)
class Filtros:
    entidade: str      # SEST ou SENAT
    unidade: int
    peso: int          # % do gap: 10, 15 ou 20

    @property
    def medida(self) -> str:
        return D.medida(self.entidade)

    @property
    def rotulo_medida(self) -> str:
        return self.medida


def filtros() -> Filtros:
    with st.sidebar:
        with secao_lateral("Entidade", "entidade"):
            entidade = st.pills("Entidade", ["SEST", "SENAT"], default="SEST", key="sb_entidade",
                                label_visibility="collapsed") or "SEST"

        p = D.gap(1, entidade)               # a Proposta 1 tem a lista mais ampla de unidades
        u = p["unidades"]
        with secao_lateral("Filtros", "filtros"):
            conselho = st.session_state.get("sb_conselho", TODOS)
            lista = u if conselho == TODOS else u[u.conselho_curto == conselho]
            ids = [D.NACIONAL, *lista.index.tolist()]
            if st.session_state.get("sb_unidade") not in ids:
                st.session_state["sb_unidade"] = D.NACIONAL
            unidade = st.selectbox("Unidade", ids, key="sb_unidade", format_func=lambda i: D.nome_unidade(p, i),
                                   help="Nacional soma as unidades com meta. O conselho só filtra a lista.")
            st.selectbox("Conselho", [TODOS, *sorted(u.conselho_curto.dropna().unique())], key="sb_conselho",
                         help="Filtra a lista de unidades. Não soma as unidades do conselho.")

        with secao_lateral("Cenário", "cenario"):
            peso = st.pills("Parte do gap pedida como esforço", D.PESOS, default=D.PESOS[0], key="sb_peso",
                            format_func=lambda w: f"{w}%") or D.PESOS[0]
            st.caption("Vale nas Propostas 1 e 2. Na Proposta 3 o esforço sai do fator de mercado.")

        st.caption(f":material/event_available: **{R.ANO_CORRENTE} é estimativa**: realizado até "
                   f"{MESES[R.CORTE - 1]} (SIGOP) e projeção para novembro e dezembro.")
    return Filtros(entidade, int(unidade), int(peso))
