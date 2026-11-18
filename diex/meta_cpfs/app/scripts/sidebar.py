"""Barra lateral no padrão da Matriz (cartões por seção): Período (ano de referência) e Filtros (conselho → unidade,
especialidade). Devolve os filtros escolhidos; as abas só leem o objeto, sem tocar no session_state."""
from dataclasses import dataclass

import streamlit as st

import modelo as M
from scripts import dados as D
from abas.comum import PROJECAO

NACIONAL = "Nacional"
TODOS = "Todos"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


@dataclass(frozen=True)
class Filtros:
    nivel: int          # id_unidade; 0 = Nacional
    rotulo: str         # "Nacional" ou "UNIDADE A - Nº 04 - BRASÍLIA/DF"
    cidade: str         # "BRASÍLIA/DF" (vazio no Nacional)
    esp: str            # "Todas as áreas" ou uma especialidade
    ano: int            # ano de referência dos cartões de um ano só
    conselho: str = "Todos"   # conselho escolhido (só filtra listas; não soma unidades)


def _titulo(texto: str) -> None:
    st.html(f"<div class='streamlit-sb-sec-titulo'>{texto}</div>")


def _rotulo_ano(a: int) -> str:
    return str(a)


def sidebar_filtros() -> Filtros:
    u = D.unidades()
    with st.sidebar:
        with st.container(key="sb_card_periodo"):
            _titulo("Período")
            ano = st.pills("Ano de referência", D.ANOS, default=M.ANO_BASE - 1, format_func=_rotulo_ano,
                           key="sb_ano", label_visibility="collapsed") or M.ANO_BASE - 1
            st.caption(f"{PROJECAO} A frequência por pessoa só sai com o ano fechado." if ano == M.ANO_BASE
                       else f"Ano de referência dos cartões; as séries vão de {D.ANOS[0]} a {M.ANO_BASE}. {PROJECAO}")

        with st.container(key="sb_card_filtros"):
            _titulo("Filtros")
            # ordem da Matriz (unidade em cima); o conselho escolhido na rodada anterior já filtra a lista de unidades
            conselho = st.session_state.get("sb_conselho", TODOS)
            lista = u if conselho == TODOS else u[u.conselho == conselho]
            opcoes = [NACIONAL] + lista.rotulo.tolist()
            if st.session_state.get("sb_unidade") not in opcoes:
                st.session_state["sb_unidade"] = NACIONAL
            rotulo = st.selectbox("Unidade", opcoes, key="sb_unidade",
                                  help="Nacional conta cada pessoa uma vez no país; cada unidade conta as pessoas "
                                       "que atendeu. O conselho só filtra a lista de unidades.")
            conselho = st.selectbox("Conselho", [TODOS] + sorted(u.conselho.dropna().unique()), key="sb_conselho",
                         help="Filtra a lista de unidades. Não soma as unidades do conselho.")
            esp = st.selectbox("Especialidade", D.ESPECIALIDADES, key="sb_esp",
                               help="Todas as áreas conta a pessoa uma vez, mesmo atendida em mais de uma área.")

        st.caption(f":material/event_available: Dados até **{MESES[M.CORTE - 1]}/{M.ANO_BASE}** · Agenda SEST")

    nivel = D.NACIONAL if rotulo == NACIONAL else int(u.index[u.rotulo == rotulo][0])
    cidade = "" if nivel == D.NACIONAL else u.cidade[nivel]
    return Filtros(nivel, rotulo, cidade, esp, int(ano), conselho)
