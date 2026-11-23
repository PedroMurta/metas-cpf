"""Proposta 3 · esperado + fator de mercado, por unidade: meta de CPFs distintos = base + delta × (1 + esforço), com exemplo de 1.000
pessoas, a conta real, a evolução e as metas por unidade."""
import pandas as pd
import streamlit as st

import modelo as M
from abas.comum import assunto, baixar_excel, conta, cor, mil, num, pct, rotulos_anos
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import divergente
from scripts import dados as D

FAIXAS = ["0 a 0,25", "0,25 a 0,50", "0,50 a 0,75", "0,75 a 1"]


def render(f) -> None:
    rotulos = D.ESCOPO[f.entidade]
    escopo = st.pills("Especialidades", list(rotulos), default=1, key="p3_escopo", format_func=rotulos.get) or 1
    p = D.mercado(f.entidade, escopo)
    m, r, u, uid = p["metas"], p["resumo"], p["unidades"], f.unidade

    with gt.cartao("p3_resumo"):
        gt.cabecalho(f"Proposta 3 · {f.entidade}", f"Esperado de 2027 + fator de mercado: {num(len(m))} unidades",
                     f"{rotulos[escopo]}: base e esperado da Proposta {escopo}. O acréscimo é calculado em cada unidade e cresce com o mercado dela.")
        gt.kpis([("CPFs distintos 2026", mil(r["base"]), "estimativa", ""),
                 ("Esperado 2027", mil(r["esperado"]), f"{pct(r['esperado'] / r['base'] - 1, 1, sinal=True)} · cada unidade no próprio ritmo", ""),
                 ("Meta 2027", mil(r["meta"]), f"{pct(r['nacional_pct'], 1, sinal=True)} sobre a estimativa de 2026", ""),
                 ("Meta abaixo de 2026", num(r["negativas"]), "unidade(s)", "")])

    with gt.cartao("p3_regra"):
        _exemplo(f, r)

    with gt.cartao("p3_conta"):
        _conta_real(p, uid)

    with gt.cartao("p3_faixas"):
        g = m.groupby("fe").agg(unidades=("base", "size"), base=("base", "sum"), meta=("meta", "sum")).reindex(M.ESFORCOS, fill_value=0)
        gt.cabecalho("Faixas do fator de mercado", f"A faixa com mais unidades é a de esforço de {pct(g.unidades.idxmax(), 0)}: "
                     f"{num(g.unidades.max())} unidades", f"{num(len(m))} unidades com meta · 2026 é estimativa")
        gt.tabela(pd.DataFrame({
            "Fator de mercado": FAIXAS, "Potencial": M.POTENCIAL, "Esforço": [pct(e, 0) for e in M.ESFORCOS],
            "Unidades": g.unidades.map(num).values, "CPFs 2026 (estimativa)": g.base.map(mil).values, "Meta 2027": g.meta.map(mil).values,
            "Sobre 2026": [pct(a / b - 1, 1, sinal=True) if b else "—" for a, b in zip(g.meta, g.base)]}))

    with gt.cartao("p3_evolucao"):
        hist, obs = D.historico(p, f.entidade, uid)
        x = m.loc[uid] if uid in m.index else m[["base", "esperado", "meta"]].sum()
        vals, i = [*hist.tolist(), x.esperado, x.meta], len(hist) - 1
        neg, _, pos = divergente(assunto(f.entidade))
        gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}: meta de {pct(x.meta / x.base - 1, 1, sinal=True)} em 2027",
                     "CPFs distintos por ano; 2026 é estimativa. Esperado: cada unidade segue o próprio ritmo. Os selos de 2027 comparam com "
                     f"2026.{obs}")
        gt.grafico(f"evo_p3_{f.entidade}_{escopo}_{uid}", gt.evolucao(
            [*rotulos_anos(hist.index), "2027\nesperado", "2027\nmeta"], vals, cor(f.entidade), textos=[mil(v) for v in vals],
            cores_var=(neg, pos), apagadas=[i, i + 1], comparar={i + 2: i}), 380)

    with gt.cartao("p3_unidades"):
        mm = m.loc[u.index]
        gt.cabecalho("Metas por unidade", "Meta de 2027 em CPFs distintos", "Acréscimo = (esperado − base) × esforço, em cada unidade")
        gt.tabela(pd.DataFrame({
            "Unidade": u.rotulo, "Conselho": u.conselho_curto, "CPFs 2026 (estimativa)": mm.base.map(num),
            "Esperado 2027": mm.esperado.map(num), "Penetração": mm.penetracao.map(lambda v: pct(v, 1) if pd.notna(v) else "—"),
            "Fator de mercado": mm.fm.map(lambda v: num(v, 2)), "Esforço": mm.fe.map(lambda v: pct(v, 0)),
            "Acréscimo": (mm.meta - mm.esperado).map(num),
            "Meta 2027": [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in zip(mm.meta, mm.meta_pct)]}),
            destaque=("Unidade", D.nome_unidade(p, uid)) if uid != D.NACIONAL else None, texto=2, altura=480)
        baixar_excel(pd.DataFrame({
            "unidade": u.rotulo, "conselho": u.conselho_curto, "base_2026_estimativa": mm.base.round(0), "esperado_2027": mm.esperado,
            "delta": mm.delta.round(1), "mercado": mm.mercado, "penetracao": mm.penetracao.round(4),
            "percentil_mercado": mm.p_mercado.round(4), "percentil_lacuna": mm.p_lacuna.round(4), "fator_mercado": mm.fm.round(4),
            "potencial": mm.potencial, "esforco": mm.fe, "meta_2027": mm.meta, "meta_pct": mm.meta_pct.round(4)}),
            f"meta_2027_proposta3_{f.entidade.lower()}_{'todas' if escopo == 2 else 'inicial'}.xlsx", "xls_p3")

    nota(f"Unidade com esperado abaixo de 2026 ({num(r['sem_esforco'])}) fica no próprio crescimento, sem esforço: o fator de mercado não aumenta "
         "a queda. Mercado e percentil do mercado: planilha da área (Saúde B2C no SEST, Educação B2B no SENAT). 2026 é estimativa: "
         "realizado até outubro e projeção para novembro e dezembro.")


def _exemplo(f, r: dict) -> None:
    gt.cabecalho("Como a meta é calculada", "Exemplo: uma unidade com 1.000 pessoas em 2026 (estimativa)",
                 "Números inventados e arredondados, só para mostrar a conta")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1, st.container(border=True):
        st.markdown("**Passo 1. Esperado e delta**  \nA unidade segue o próprio ritmo.")
        st.latex(r"\text{Esperado} = 1.000 + 10\% = 1.100")
        st.latex(r"\boxed{\text{Delta} = 1.100 - 1.000 = 100\ \text{pessoas}}")
        st.caption("O delta é o que a unidade cresceria sozinha: 751 pessoas em 2023 e 1.000 em 2026 (estimativa) = 10% ao ano.")
    with c2, st.container(border=True):
        st.markdown("**Passo 2. Fator de mercado (FM)**  \n60% da posição do mercado e 40% da posição da lacuna.")
        st.latex(r"\text{Penetração} = \frac{1.000}{10.000} = 10\%")
        st.latex(r"\text{Lacuna} = 100\% - 10\% = 90\%")
        st.latex(r"FM = 0{,}60\,(0{,}70) + 0{,}40\,(0{,}80)")
        st.latex(r"\boxed{FM = 0{,}42 + 0{,}32 = 0{,}74}")
        st.caption("Mercado de 10.000 pessoas (" + ("saúde" if f.entidade == "SEST" else "educação") + "). 0,70 é o percentil do mercado na "
                   "planilha e 0,80 a posição da lacuna entre as unidades: 0 é a menor e 1 a maior.")
    with c3, st.container(border=True):
        st.markdown("**Passo 3. Meta**  \nFM de 0,74: potencial alto, esforço de 15%.")
        st.latex(r"\text{Meta} = \text{Base} + \text{Delta} \times (1 + \text{Esforço})")
        st.latex(r"1.000 + 100 \times 1{,}15 = 1.115")
        st.latex(r"\boxed{1.100 + 15 = 1.115\ \text{pessoas}}")
        st.caption("É o esperado (1.100) mais 15% do delta (15 pessoas).")
    st.markdown("**A mesma unidade em cada faixa do fator de mercado**")
    gt.tabela(pd.DataFrame({"FM": FAIXAS, "Potencial": M.POTENCIAL, "Esforço": [pct(e, 0) for e in M.ESFORCOS], "Esperado": "1.100",
                            "Acréscimo": [f"100 × {pct(e, 0)} = {num(100 * e)}" for e in M.ESFORCOS],
                            "Meta 2027": [num(1100 + 100 * e) for e in M.ESFORCOS]}), destaque=("Potencial", "Alto"))


def _conta_real(p: dict, uid: int) -> None:
    m, r = p["metas"], p["resumo"]
    if uid == D.NACIONAL:
        gt.cabecalho("A conta real", "Nacional: a soma das metas das unidades", "Escolha uma unidade na barra lateral para ver a conta dela")
        conta([("Base: CPFs distintos 2026", f"{num(r['base'])} (estimativa)"),
               ("Esperado 2027", f"{num(r['esperado'])} ({pct(r['esperado'] / r['base'] - 1, 1, sinal=True)})"),
               ("Acréscimo do mercado", num(r["meta"] - r["esperado"])),
               ("Meta 2027", f"{num(r['meta'])} ({pct(r['nacional_pct'], 1, sinal=True)})")])
        return
    u = m.loc[uid]
    gt.cabecalho("A conta real", f"{D.nome_unidade(p, uid)}: meta de {num(u.meta)} CPFs em 2027 ({pct(u.meta_pct, 1, sinal=True)})",
                 f"Potencial {u.potencial.lower()} · esforço de {pct(u.fe, 0)}")
    conta([("Base: CPFs distintos 2026", f"{num(u.base)} (estimativa)"),
           ("Esperado 2027", f"{num(u.esperado)} ({pct(u.esperado / u.base - 1, 1, sinal=True)})"),
           ("Delta", f"{num(u.esperado)} − {num(u.base)} = {num(u.delta)}"),
           ("Penetração e lacuna", f"{num(u.base)} ÷ {num(u.mercado)} = {pct(u.penetracao, 1)} · lacuna {pct(1 - u.penetracao, 1)}"
            if pd.notna(u.penetracao) else "sem mercado na planilha"),
           ("Fator de mercado", f"0,60 × {num(u.p_mercado, 2)} + 0,40 × {num(u.p_lacuna, 2)} = {num(u.fm, 2)}"),
           ("Esforço", f"{pct(u.fe, 0)} (potencial {u.potencial.lower()})"),
           ("Meta", f"{num(u.base)} + {num(u.delta)} × {num(1 + u.fe, 2)} = {num(u.meta)}" if u.delta > 0 else
            f"esperado abaixo de 2026: fica no próprio crescimento, sem esforço = {num(u.meta)}")])
