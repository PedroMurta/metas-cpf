"""Aba Comparação: a proposta nas seis bases (SEST, SENAT e os dois juntos, nos cenários A e B), no Nacional e por unidade."""
import pandas as pd
import streamlit as st

from abas.comum import TODOS_PUBLICOS, baixar_excel, contados, cor, entra, mil, num, pct
from common import painel as gt
from common.painel.casca import nota
from recortes import ENTIDADES
from scripts import dados as D

ESCOPOS = D.CENARIOS


def render(f) -> None:
    linhas = [(e, n) for n in ESCOPOS for e in ENTIDADES]
    p = {k: D.mercado(*k, f.ano) for k in linhas}
    r = {k: x["resumo"] for k, x in p.items()}

    with gt.cartao("comp_nacional"):
        maior = max(r, key=lambda k: r[k]["nacional_pct"])
        gt.cabecalho(f"Nacional · {TODOS_PUBLICOS}", f"Maior alta: {D.nome(maior[0])}, cenário {ESCOPOS[maior[1]][-1]}, {pct(r[maior]['nacional_pct'], 1, sinal=True)}",
                     f"{contados(f)} · 2026 é projeção · {num(len(p[linhas[0]]['metas']))} unidades")
        gt.tabela(pd.DataFrame([{
            "Entidade": D.nome(k[0]), "Cenário": ESCOPOS[k[1]][-1], "2026 proj.": mil(r[k]["base"]), "Crescimento padrão": pct(p[k]["delta"], 2),
            "Meta 2027": mil(r[k]["meta"]), "Sobre 2026": pct(r[k]["nacional_pct"], 1, sinal=True), "Por unidade": f"{pct(r[k]['minimo'], 1, sinal=True)} a {pct(r[k]['maximo'], 1, sinal=True)}"} for k in linhas]), texto=2)
        st.caption("Crescimento padrão: igual para todas as unidades. Por unidade: a menor e a maior meta, sobre 2026. SEST SENAT não é a soma das duas linhas: quem é atendido nos dois, na mesma unidade, contará uma vez.")

    with gt.cartao("comp_crescimento"):
        gt.cabecalho(f"Crescimento da meta · {TODOS_PUBLICOS}", "Quanto a meta de 2027 pedirá a mais que a projeção de 2026", f"{contados(f)} · soma das unidades")
        gt.grafico(f"comp_cresc_{f.chave}", gt.barras_h([f"{D.nome(k[0])} · {ESCOPOS[k[1]]}" for k in linhas], [x["nacional_pct"] * 100 for x in r.values()],
                                                        [cor(k[0]) for k in linhas], textos=[pct(x["nacional_pct"], 1, sinal=True) for x in r.values()]), 300)

    escopo = st.pills("Cenário da comparação", list(ESCOPOS), default=1, key="comp_escopo", format_func=ESCOPOS.get) or 1
    with gt.cartao("comp_unidades"):
        u, uid = p["SEST", escopo]["unidades"], f.unidade
        gt.cabecalho(f"Por unidade · {TODOS_PUBLICOS}", "Projeção de 2026 e meta de 2027 em cada entidade",
                     f"{ESCOPOS[escopo]}. Entre parênteses, quanto a meta representa sobre a projeção de 2026")
        df = pd.DataFrame({"Unidade": u.rotulo})
        bruto = pd.DataFrame({"unidade": u.rotulo, "conselho": u.conselho_curto})
        for e in ENTIDADES:
            m, c = p[e, escopo]["metas"].loc[u.index], e.lower().replace(" + ", "_")
            df[f"{D.nome(e)} 2026"], df[f"{D.nome(e)} meta 2027"] = m.base.map(num), [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in zip(m.meta, m.meta_pct)]
            bruto[f"{c}_2026_projecao"] = m.base.round(0)
            bruto[f"{c}_meta_2027"], bruto[f"{c}_meta_pct"] = m.meta, m.meta_pct.round(4)
        gt.tabela(df, destaque=("Unidade", D.nome_unidade(p["SEST", escopo], uid)) if uid != D.NACIONAL else None, texto=1, altura=520)
        baixar_excel(bruto, f"meta_2027_comparacao_{'12m' if f.doze else 'ano'}_cenario_{'b' if escopo == 2 else 'a'}.xlsx", "xls_comparacao")

    nota(" ".join(f"{D.nome(e)}, cenário {ESCOPOS[n][-1]}: {entra(e, n)}." for n in ESCOPOS for e in ENTIDADES) + " No cenário B entram mais pessoas, por isso compare os aumentos e não os totais. "
         "EJA: Educação de Jovens e Adultos.")
