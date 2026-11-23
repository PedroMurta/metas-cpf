"""Barra lateral no padrão da Matriz (cartões por seção, common.painel.casca.secao_lateral): Entidade, Filtros (unidade,
conselho) e Cenário (parte do gap, Propostas 1 e 2). As abas só leem o objeto."""
from dataclasses import dataclass, replace

import streamlit as st

import recortes as R
from common.painel.casca import secao_lateral
from scripts import dados as D

TODOS = "Todos"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

VISOES = ["12 meses", "Ano completo"]


@dataclass(frozen=True)
class Filtros:
    entidade: str      # SEST ou SENAT
    unidade: int
    peso: int          # % do gap: 10, 15 ou 20
    ano: bool = False  # visão: ano completo (True) ou 12 meses (False, o padrão); SENAT é sempre ano completo

    @property
    def doze(self) -> bool:
        return self.entidade == "SEST" and not self.ano

    @property
    def chave(self) -> str:
        return f"{self.entidade}_{'12m' if self.doze else 'ano'}"

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


def visao(f: Filtros) -> Filtros:
    """Seletor único acima das abas (só SEST): muda todas as propostas juntas. O bloco existe nas duas entidades para as abas não
    voltarem à primeira quando a entidade muda."""
    with st.container():
        if f.entidade != "SEST":
            st.caption("SENAT: CPFs distintos no ano completo, até a decisão das lideranças sobre a regra de 12 meses.")
            return replace(f, ano=True)
        v = st.pills("Como contar as pessoas", VISOES, default=VISOES[0], key="visao",
                     help="12 meses: 1ª vez na unidade, ou 12 meses ou mais desde o último atendimento nela. "
                          "Ano completo: cada pessoa conta uma vez por unidade, de janeiro a dezembro.") or VISOES[0]
    return replace(f, ano=v == VISOES[1])
