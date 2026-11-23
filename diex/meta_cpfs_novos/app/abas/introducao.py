"""Aba Introdução: o que é CPF distinto, por que 2026 é estimativa e as três propostas em resumo."""
import pandas as pd
import streamlit as st

from abas.comum import contados, mil, num, pct
from common import painel as gt
from scripts import dados as D


def render(f) -> None:
    with gt.cartao("intro_cpf"):
        if f.doze:
            gt.cabecalho("O que a meta conta", "A pessoa conta na 1ª vez na unidade ou quando volta depois de 12 meses ou mais",
                         "Vale a data do último atendimento na unidade. Para contar de janeiro a dezembro, escolha Ano completo, acima das abas")
            st.markdown(
                "Exemplo: a pessoa foi atendida na unidade em 10/02/2025.\n"
                "- Se voltar em **10/02/2026** ou depois, sem outro atendimento no meio, conta de novo.\n"
                "- Se voltar em **05/02/2026**, não conta: ainda não completou 12 meses.\n"
                "- Se veio também em 15/08/2025, só conta de novo a partir de **15/08/2026**.\n"
                "- Quem é atendido em duas unidades pode contar nas duas. Só valem os atendimentos das especialidades escolhidas.\n\n"
                "Quem faz tratamento contínuo conta uma vez, no começo. Já o **gap** e a **penetração** usam todas as pessoas atendidas no ano.")
        else:
            gt.cabecalho("O que a meta conta", "CPF distinto: cada pessoa conta uma vez por ano em cada unidade", "O ano vai de janeiro a dezembro")
            st.markdown(
            "- Dez atendimentos da mesma pessoa na mesma unidade valem 1 CPF distinto.\n"
            "- Uma pessoa atendida em duas unidades conta uma vez em cada.\n"
            "- A meta pede que mais pessoas diferentes sejam atendidas. Tratamentos longos continuam.")

    with gt.cartao("intro_2026"):
        gt.cabecalho("2026 é estimativa", "2026 é o realizado até outubro mais a projeção de novembro e dezembro",
                     "A meta de 2027 parte do ano completo de 2026 e precisa ser refeita quando o ano fechar")
        st.markdown("Exemplo: se até outubro a unidade costuma ter 80% dos CPFs do ano e já tem 800, a estimativa do ano é "
                    "800 ÷ 0,8 = **1.000**.")

    with gt.cartao("intro_esperado"):
        k, rot = f.peso, D.ESCOPO[f.entidade]
        m1, m2 = D.gap(1, f.entidade, ano=f.ano)["metas"], D.gap(2, f.entidade, ano=f.ano)["metas"]
        p3 = {e: D.mercado(f.entidade, e, f.ano) for e in (1, 2)}
        m3, g = {e: p3[e]["metas"] for e in p3}, {e: p3[e]["nacional"] for e in p3}
        gt.cabecalho("O ponto de partida", f"O esperado de 2027 é {mil(m1.sem_meta.sum())} com {rot[1].lower()} e {mil(m2.sem_meta.sum())} com "
                                           f"{rot[2].lower()}", f"{f.entidade} · {num(len(m1))} unidades · {contados(f)}")
        st.markdown("Esperado é o resultado se cada unidade continuar crescendo no ritmo dos últimos anos. Exemplo: 751 pessoas em 2023 e 1.000 em 2026 "
                    "(estimativa) = 10% ao ano, e o esperado de 2027 é 1.000 + 10% = **1.100**. " + (
                        "As Propostas 1 e 2 somam um acréscimo a esse valor. A Proposta 3 compara o esperado com o crescimento Nacional mais um esforço e fica com o "
                        f"maior. Nas três, nenhuma unidade cresce menos que o **delta Nacional**: quanto as unidades com 5 anos ou mais em 2023 cresceram, juntas, em média por ano, de 2023 a 2026 "
                        f"({pct(g[1], 1)} com {rot[1].lower()} e {pct(g[2], 1)} com todas)." if g[1] else
                        "Cada proposta soma um acréscimo a esse valor, unidade por unidade.") + "\n\nCom todas as especialidades, a pessoa conta uma vez na unidade, mesmo que passe por várias"
                    + (". As campanhas ficam fora." if f.entidade == "SEST" else "."))
        gt.tabela(pd.DataFrame([{"Especialidades": rot[e], "Usado em": usado, "2026 (estimativa)": mil(x.cpf0.sum()),
                                 "Esperado 2027": mil(x.sem_meta.sum()), "Crescimento esperado": pct(x.sem_meta.sum() / x.cpf0.sum() - 1, 1, sinal=True)}
                                for e, x, usado in ((1, m1, "Propostas 1 e 3"), (2, m2, "Propostas 2 e 3"))]), texto=2)

    with gt.cartao("intro_propostas"):
        unid = "atendimentos" if f.entidade == "SEST" else "horas"
        nums = lambda b, m: f"{mil(b.sum())} → {mil(m.sum())} ({pct(m.sum() / b.sum() - 1, 1, sinal=True)})"
        cartoes = [("Proposta 1", f"Esperado + {k}% do gap. {rot[1]}.", f"O gap mostra quanto a unidade faz a mais de {unid} por pessoa do que a referência do grupo dela." + (f" Crescimento mínimo: {pct(g[1], 1)}." if g[1] else ""),
                    f"1.100 + {k}% × 20% × 1.000 = {num(1100 + 2 * k)}", [nums(m1.cpf0, m1[f"meta_pessoas_{k}"])]),
                   ("Proposta 2", f"Esperado + {k}% do gap. {rot[2]}.", "A mesma conta, com todas as especialidades. A referência vem das unidades com 5 anos ou mais em 2023 e vale para todas." + (f" Crescimento mínimo: {pct(g[2], 1)}." if g[2] else ""),
                    f"1.100 + {k}% × 40% × 1.000 = {num(1100 + 4 * k)}", [nums(m2.cpf0, m2[f"meta_pessoas_{k}"])]),
                   ("Proposta 3", f"Delta Nacional ({pct(g[1], 1)} ou {pct(g[2], 1)}) mais um esforço, ou o esperado da unidade, se for maior." if g[1] else "Esperado + fator de mercado, com as duas bases.", "O esforço vai de 5% a 20%. Ele aumenta com o tamanho do mercado e com a parte que a unidade ainda não atende.",
                    "1.000 + 100 × 1,15 = 1.115 (delta de 10%)" if g[1] else "1.100 + 15% × 100 = 1.115", [f"{rot[e]}: {nums(m3[e].base, m3[e].meta)}" for e in (1, 2)])]
        gt.cabecalho("As três propostas", "O que muda de uma para outra é a conta do crescimento" if g[1] else "O que muda de uma para outra é o acréscimo", f"{f.entidade} · {contados(f)} · Nacional")
        for col, (nome, frase, detalhe, ex, totais) in zip(st.columns(3, gap="small"), cartoes):
            with col, st.container(border=True):
                st.markdown(f"**{nome}**  \n{frase}\n\n{detalhe}\n\nExemplo com 1.000 pessoas:  \n{ex}\n\n2026 (estimativa) → meta 2027:  \n"
                            + "  \n".join(f"**{t}**" for t in totais))
        if f.entidade == "SENAT":
            st.caption("Nas Propostas 1 e 2, o SENAT também pode ter meta em horas-aula. O botão fica no topo da aba.")
