"""Barra lateral no padrão da Matriz (cartões por seção, common.painel.casca.secao_lateral): Entidade e Filtros (unidade). As abas
só leem o objeto."""
from dataclasses import dataclass, replace

import streamlit as st

import recortes as R
from common.painel.casca import secao_lateral
from scripts import dados as D
from scripts.apresentacao import botao

VISOES = ["12 meses", "Exercício anual"]
TODOS = "Todos"
VISAO_ANUAL = False     # exercício anual oculto (decisão de 25/11: vale a contagem de 12 meses)


@dataclass(frozen=True)
class Filtros:
    entidade: str      # SEST, SENAT ou SEST + SENAT
    unidade: int
    ano: bool = False  # visão: exercício anual (True) ou 12 meses (False, o padrão)
    publico: str | None = None   # Transporte, Comunidade ou todos (None): não muda a meta
    peso: int = 10     # % do gap: só nas abas ocultas (Propostas 1 e 2)

    @property
    def doze(self) -> bool:
        return not self.ano

    @property
    def chave(self) -> str:
        return f"{self.entidade.replace(' + ', '_')}_{'12m' if self.doze else 'ano'}{'_' + self.publico.lower() if self.publico else ''}"

    @property
    def medida(self) -> str:
        return D.medida(self.entidade)

    @property
    def rotulo_medida(self) -> str:
        return self.medida


def filtros() -> Filtros:
    with st.sidebar:
        with secao_lateral("Entidade", "entidade"):
            entidade = st.pills("Entidade", list(R.ENTIDADES), default="SEST", key="sb_entidade", format_func=D.nome,
                                label_visibility="collapsed") or "SEST"

        p = D.mercado(entidade)              # as unidades são as mesmas nas duas bases e nas duas visões
        u = p["unidades"]
        with secao_lateral("Filtros", "filtros"):
            ids = [D.NACIONAL, *u.index.tolist()]
            unidade = st.selectbox("Unidade", ids, key="sb_unidade", format_func=lambda i: D.nome_unidade(p, i),
                                   help="Nacional soma as unidades com meta.")

        with secao_lateral("Público", "publico"):
            publico = st.pills("Público", [TODOS, *R.PUBLICOS], default=TODOS, key="sb_publico", label_visibility="collapsed") or TODOS
            st.caption("Transporte inclui os dependentes. O filtro muda a aba Análise e, na Proposta, a Evolução e a tabela por unidade. A meta não muda.")

        botao()
        st.caption(f":material/event_available: **{R.ANO_CORRENTE} é projeção** com base histórica.")
    return Filtros(entidade, int(unidade), publico=None if publico == TODOS else publico)


def visao(f: Filtros) -> Filtros:
    """Seletor único acima das abas: muda a contagem em todas elas. Com o exercício anual oculto, fica só a de 12 meses, sem seletor."""
    if not VISAO_ANUAL:
        return f
    with st.container():
        v = st.pills("Como contar as pessoas", VISOES, default=VISOES[0], key="visao",
                     help="12 meses: 1ª vez na unidade, ou 12 meses ou mais desde o último atendimento nela. "
                          "Exercício anual: cada pessoa contará uma vez por unidade, de janeiro a dezembro.") or VISOES[0]
        f = replace(f, ano=v == VISOES[1])
    return f
