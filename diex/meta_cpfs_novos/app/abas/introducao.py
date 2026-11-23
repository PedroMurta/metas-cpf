"""Aba Introdução: o que é CPF distinto, por que 2026 é estimativa e as três propostas em resumo."""
import pandas as pd
import streamlit as st

from abas.comum import mil, num, pct
from common import painel as gt
from scripts import dados as D


def render(f) -> None:
    with gt.cartao("intro_cpf"):
        gt.cabecalho("O que a meta conta", "CPF distinto: cada pessoa conta uma vez por unidade e por ano",
                     "O ano vai de janeiro a dezembro")
        st.markdown(
            "- Dez atendimentos da mesma pessoa na mesma unidade valem 1 CPF distinto.\n"
            "- Uma pessoa atendida em duas unidades conta uma vez em cada.\n"
            "- A meta pede mais pessoas diferentes. Tratamentos longos continuam.")

    with gt.cartao("intro_2026"):
        gt.cabecalho("2026 é estimativa", "Os números de 2026 somam o realizado até outubro e a projeção de novembro e dezembro",
                     "Toda meta de 2027 parte dessa estimativa e deve ser recalculada quando o ano fechar")
        st.markdown("Exemplo: se até outubro a unidade costuma ter 80% dos CPFs do ano e já tem 800, a estimativa do ano é "
                    "800 ÷ 0,8 = **1.000**.")

    with gt.cartao("intro_esperado"):
        k, rot = f.peso, D.ESCOPO[f.entidade]
        m1, m2 = D.gap(1, f.entidade)["metas"], D.gap(2, f.entidade)["metas"]
        m3 = {e: D.mercado(f.entidade, e)["metas"] for e in (1, 2)}
        gt.cabecalho("O ponto de partida", f"O esperado de 2027 é {mil(m1.sem_meta.sum())} com {rot[1].lower()} e {mil(m2.sem_meta.sum())} com "
                                           f"{rot[2].lower()}", f"{f.entidade} · {num(len(m1))} unidades · CPFs distintos")
        st.markdown("É o que acontece se cada unidade seguir o próprio ritmo, sem meta. Exemplo: 751 pessoas em 2023 e 1.000 em 2026 "
                    "(estimativa) = 10% ao ano, e o esperado de 2027 é 1.000 + 10% = **1.100**. Cada proposta acrescenta algo a esse valor, "
                    "sempre unidade por unidade.\n\nCom todas as especialidades, cada pessoa conta uma vez na unidade, mesmo atendida em várias"
                    + (". As campanhas ficam fora." if f.entidade == "SEST" else "."))
        gt.tabela(pd.DataFrame([{"Especialidades": rot[e], "Usado em": usado, "2026 (estimativa)": mil(x.cpf0.sum()),
                                 "Esperado 2027": mil(x.sem_meta.sum()), "Crescimento esperado": pct(x.sem_meta.sum() / x.cpf0.sum() - 1, 1, sinal=True)}
                                for e, x, usado in ((1, m1, "Propostas 1 e 3"), (2, m2, "Propostas 2 e 3"))]), texto=2)

    with gt.cartao("intro_propostas"):
        unid = "atendimentos" if f.entidade == "SEST" else "horas"
        nums = lambda b, m: f"{mil(b.sum())} → {mil(m.sum())} ({pct(m.sum() / b.sum() - 1, 1, sinal=True)})"
        cartoes = [("Proposta 1", f"Esperado + {k}% do gap. {rot[1]}.", f"Gap: quanto a unidade passa da referência do grupo em {unid} por pessoa.",
                    f"1.100 + {k}% × 20% × 1.000 = {num(1100 + 2 * k)}", [nums(m1.cpf0, m1[f"meta_pessoas_{k}"])]),
                   ("Proposta 2", f"Esperado + {k}% do gap. {rot[2]}.", "Referência: unidades com 5 anos ou mais em 2023, aplicada a todas.",
                    f"1.100 + {k}% × 40% × 1.000 = {num(1100 + 4 * k)}", [nums(m2.cpf0, m2[f"meta_pessoas_{k}"])]),
                   ("Proposta 3", "Esperado + fator de mercado, com as duas bases.", "Quanto maior o mercado e a parte ainda não atendida, maior o esforço (5% a 20%).",
                    "1.100 + 15% × 100 = 1.115", [f"{rot[e]}: {nums(m3[e].base, m3[e].meta)}" for e in (1, 2)])]
        gt.cabecalho("As três propostas", "O que muda é o acréscimo ao esperado", f"{f.entidade} · CPFs distintos · Nacional")
        for col, (nome, frase, detalhe, ex, totais) in zip(st.columns(3, gap="small"), cartoes):
            with col, st.container(border=True):
                st.markdown(f"**{nome}**  \n{frase}\n\n{detalhe}\n\nExemplo com 1.000 pessoas:  \n{ex}\n\n2026 (estimativa) → meta 2027:  \n"
                            + "  \n".join(f"**{t}**" for t in totais))
        if f.entidade == "SENAT":
            st.caption("Nas Propostas 1 e 2, o SENAT também pode ter a meta em horas-aula: o botão fica no topo de cada aba.")
