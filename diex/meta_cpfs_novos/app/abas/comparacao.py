"""Aba Comparação: a proposta nas seis bases (SEST, SENAT e SEST + SENAT, com a seleção menor e com todas), no Nacional e por unidade."""
import pandas as pd
import streamlit as st

from abas.comum import ENTRA, NOTA_MODULO, baixar_excel, contados, cor, esforco_padrao, mil, num, pct
from common import painel as gt
from common.painel.casca import nota
from recortes import ENTIDADES
from scripts import dados as D

ESCOPOS = {1: "4 do SEST e filtradas do SENAT", 2: "Todas, sem campanhas"}


def render(f) -> None:
    linhas = [(e, n) for n in ESCOPOS for e in ENTIDADES]
    p = {k: D.mercado(*k, f.ano) for k in linhas}
    r = {k: x["resumo"] for k, x in p.items()}

    with gt.cartao("comp_nacional"):
        maior = max(r, key=lambda k: r[k]["nacional_pct"])
        gt.cabecalho("Nacional", f"Maior alta: {maior[0]} com {'todas as especialidades' if maior[1] == 2 else D.ESCOPO[maior[0]][1].lower()}, {pct(r[maior]['nacional_pct'], 1, sinal=True)}",
                     f"{contados(f)} · 2026 é projeção · {num(len(p[linhas[0]]['metas']))} unidades")
        gt.tabela(pd.DataFrame([{
            "Entidade": k[0], "Especialidades": D.ESCOPO[k[0]][k[1]], "2026 proj.": mil(r[k]["base"]), "Esforço padrão": esforco_padrao(p[k]),
            "Meta 2027": mil(r[k]["meta"]), "Sobre 2026": pct(r[k]["nacional_pct"], 1, sinal=True), "Por unidade": f"{pct(r[k]['minimo'], 1, sinal=True)} a {pct(r[k]['maximo'], 1, sinal=True)}"} for k in linhas]), texto=2)
        st.caption("Esforço padrão: igual para todas as unidades. Por unidade: a menor e a maior meta, sobre 2026. SEST + SENAT não é a soma das duas linhas: quem é atendido nos dois, na mesma unidade, conta uma vez."
                   + ("  \n" + NOTA_MODULO.replace("*", r"\*", 1) if any(x["nacional"] < 0 for x in p.values()) else ""))

    with gt.cartao("comp_crescimento"):
        gt.cabecalho("Crescimento da meta", "Quanto a meta de 2027 pede a mais que a projeção de 2026", f"{contados(f)} · soma das unidades · seleção: 4 especialidades do SEST e cursos filtrados do SENAT")
        gt.grafico(f"comp_cresc_{f.chave}", gt.barras_h([f"{k[0]} ({'todas' if k[1] == 2 else 'seleção'})" for k in linhas], [x["nacional_pct"] * 100 for x in r.values()],
                                                        [cor(k[0]) for k in linhas], textos=[pct(x["nacional_pct"], 1, sinal=True) for x in r.values()]), 300)

    escopo = st.pills("Especialidades da comparação", list(ESCOPOS), default=1, key="comp_escopo", format_func=ESCOPOS.get) or 1
    with gt.cartao("comp_unidades"):
        u, uid = p["SEST", escopo]["unidades"], f.unidade
        gt.cabecalho("Por unidade", "Projeção de 2026 e meta de 2027 em cada entidade",
                     f"{ESCOPOS[escopo]}. Entre parênteses, quanto a meta representa sobre a projeção de 2026")
        df = pd.DataFrame({"Unidade": u.rotulo})
        bruto = pd.DataFrame({"unidade": u.rotulo, "conselho": u.conselho_curto})
        for e in ENTIDADES:
            m, c = p[e, escopo]["metas"].loc[u.index], e.lower().replace(" + ", "_")
            df[f"{e} 2026"], df[f"{e} meta 2027"] = m.base.map(num), [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in zip(m.meta, m.meta_pct)]
            bruto[f"{c}_2026_projecao"] = m.base.round(0)
            bruto[f"{c}_meta_2027"], bruto[f"{c}_meta_pct"] = m.meta, m.meta_pct.round(4)
        gt.tabela(df, destaque=("Unidade", D.nome_unidade(p["SEST", escopo], uid)) if uid != D.NACIONAL else None, texto=1, altura=520)
        baixar_excel(bruto, f"meta_2027_comparacao_{'12m' if f.doze else 'ano'}_{'todas' if escopo == 2 else 'selecao'}.xlsx", "xls_comparacao")

    nota(f"SEST: {ENTRA['SEST'][1].lower()}. SENAT: cursos presenciais, sem palestras e sem Educação de Jovens e Adultos. Com todas as especialidades entram mais pessoas, por isso "
         "compare os aumentos e não os totais.")
