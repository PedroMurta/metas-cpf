"""Proposta 3 · fator de mercado, por unidade. SEST: a maior entre base + delta Nacional × (1 + esforço) e o esperado da unidade; SENAT: esperado da própria unidade + esforço. Com exemplo de 1.000
pessoas, a conta real, a evolução e as metas por unidade."""
import pandas as pd
import streamlit as st

import modelo as M
from abas.comum import assunto, baixar_excel, conta, contados, cor, mil, num, pct, regra_contagem, rotulos_anos
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import divergente
from scripts import dados as D

FAIXAS = ["0 a 0,25", "0,25 a 0,50", "0,50 a 0,75", "0,75 a 1"]


def render(f) -> None:
    rotulos = D.ESCOPO[f.entidade]
    escopo = st.pills("Especialidades", list(rotulos), default=1, key="p3_escopo", format_func=rotulos.get) or 1
    p = D.mercado(f.entidade, escopo, f.ano)
    m, r, u, uid, g = p["metas"], p["resumo"], p["unidades"], f.unidade, p["nacional"]
    base_nome = "Delta Nacional" if g else "Esperado"

    with gt.cartao("p3_resumo"):
        gt.cabecalho(f"Proposta 3 · {f.entidade}", (f"Cresce {pct(g, 1)} (delta Nacional) mais o esforço, ou fica com o esperado, se for maior" if g else
                      f"Esperado de 2027 + fator de mercado: {num(len(m))} unidades"),
                     f"{rotulos[escopo]}: base da Proposta {escopo}. " + (
                         f"{num(len(m))} unidades; em {num(r['no_esperado'])} delas vale o esperado." if g else
                         "O acréscimo aumenta com o mercado de cada unidade."))
        gt.kpis([(f"{contados(f)} 2026", mil(r["base"]), "estimativa", ""),
                 (f"2026 + {base_nome}" if g else "Esperado 2027", mil(r["partida"]), f"{pct(r['partida'] / r['base'] - 1, 1, sinal=True)} · "
                  + ("igual para todas" if g else "cada unidade no próprio ritmo"), ""),
                 ("Meta 2027", mil(r["meta"]), f"{pct(r['nacional_pct'], 1, sinal=True)} sobre a estimativa de 2026", ""),
                 ("Menor meta", pct(r["minimo"], 1, sinal=True), "a unidade que menos cresce", "") if g else
                 ("Meta abaixo de 2026", num(r["negativas"]), "unidade(s)", "")])

    with gt.cartao("p3_regra"):
        _exemplo(f, g, m)

    with gt.cartao("p3_faixas"):
        fx = m.groupby("fe").agg(unidades=("base", "size"), base=("base", "sum"), meta=("meta", "sum")).reindex(M.ESFORCOS, fill_value=0)
        gt.cabecalho("Faixas do fator de mercado", f"A faixa com mais unidades é a de esforço de {pct(fx.unidades.idxmax(), 0)}: "
                     f"{num(fx.unidades.max())} unidades", f"{num(len(m))} unidades com meta · 2026 é estimativa" + (" · o crescimento inclui as unidades em que vale o esperado" if g else ""))
        gt.tabela(pd.DataFrame({
            "Fator de mercado": FAIXAS, "Potencial": M.POTENCIAL, "Esforço": [pct(e, 0) for e in M.ESFORCOS],
            "Unidades": fx.unidades.map(num).values, "CPFs 2026 (estimativa)": fx.base.map(mil).values, "Meta 2027": fx.meta.map(mil).values,
            "Sobre 2026": [pct(a / b - 1, 1, sinal=True) if b else "—" for a, b in zip(fx.meta, fx.base)]}))

    with gt.cartao("p3_conta"):
        _conta_real(f, p, uid)

    with gt.cartao("p3_evolucao"):
        hist, obs = D.historico(p, f.entidade, uid)
        x = m.loc[uid] if uid in m.index else m[["base", "esperado", "partida", "meta"]].sum()
        vals, i = [*hist.tolist(), *([x.partida, x.esperado] if g else [x.partida]), x.meta], len(hist) - 1
        neg, _, pos = divergente(assunto(f.entidade))
        gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}: meta de {pct(x.meta / x.base - 1, 1, sinal=True)} em 2027",
                     f"{contados(f)} por ano; 2026 é estimativa. " + (f"Delta Nacional: todas crescem {pct(g, 1)}, sem esforço. " if g else "") + "Esperado: cada unidade continua no ritmo dela." + f" Os selos de 2027 comparam com "
                     f"2026.{obs}")
        gt.grafico(f"evo_p3_{f.chave}_{escopo}_{uid}", gt.evolucao(
            [*rotulos_anos(hist.index), *(["2027\ndelta Nacional"] if g else []), "2027\nesperado", "2027\nmeta"], vals, cor(f.entidade), textos=[mil(v) for v in vals],
            cores_var=(neg, pos), apagadas=list(range(i, len(vals) - 1)), comparar={j: i for j in range(i + 1, len(vals))}), 380)

    with gt.cartao("p3_unidades"):
        mm = m.loc[u.index]
        gt.cabecalho("Metas por unidade", f"Meta de 2027 em {contados(f)}", "Vale o maior: o delta Nacional com esforço ou o esperado da unidade" if g else "Acréscimo = (esperado − base) × esforço, em cada unidade")
        gt.tabela(pd.DataFrame({
            "Unidade": u.rotulo, "Conselho": u.conselho_curto, "CPFs 2026 (estimativa)": mm.base.map(num),
            "Esperado 2027": mm.esperado.map(num), **({"Delta Nacional com esforço": mm.meta_delta.map(num)} if g else {}), "Penetração": mm.penetracao.map(lambda v: pct(v, 1) if pd.notna(v) else "—"),
            "Fator de mercado": mm.fm.map(lambda v: num(v, 2)), "Esforço": mm.fe.map(lambda v: pct(v, 0)),
            **({"Vale": mm.no_esperado.map({True: "Esperado", False: "Delta com esforço"})} if g else {"Acréscimo": (mm.meta - mm.partida).map(num)}),
            "Meta 2027": [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in zip(mm.meta, mm.meta_pct)]}),
            destaque=("Unidade", D.nome_unidade(p, uid)) if uid != D.NACIONAL else None, texto=2, altura=480)
        baixar_excel(pd.DataFrame({
            "unidade": u.rotulo, "conselho": u.conselho_curto, "base_2026_estimativa": mm.base.round(0), "esperado_proprio_2027": mm.esperado,
            "partida_2027": mm.partida.round(0),
            "delta": mm.delta.round(1), "atendidos_2026_estimativa": mm.pessoas.round(0), "mercado": mm.mercado, "penetracao": mm.penetracao.round(4),
            "percentil_mercado": mm.p_mercado.round(4), "percentil_lacuna": mm.p_lacuna.round(4), "fator_mercado": mm.fm.round(4),
            "potencial": mm.potencial, "esforco": mm.fe, "meta_pelo_delta": mm.meta_delta, "vale_o_esperado": mm.no_esperado.map({True: "sim", False: "não"}), "meta_2027": mm.meta, "meta_pct": mm.meta_pct.round(4)}),
            f"meta_2027_proposta3_{f.chave.lower()}_{'todas' if escopo == 2 else 'inicial'}.xlsx", "xls_p3")

    nota(f"{regra_contagem(f)} A penetração usa todas as pessoas atendidas no ano. " + (
         f"O delta Nacional, {pct(g, 2)} ao ano, usa as unidades com 5 anos ou mais em 2023 e anos completos, com a mesma forma de contar. " if g else
         f"As {num(r['sem_esforco'])} unidades com esperado abaixo de 2026 ficam sem esforço, para o fator de mercado não aumentar a queda. ")
         + "O mercado e a posição dele vêm da planilha da área (Saúde B2C no SEST, Educação B2B no SENAT). 2026 é estimativa: "
         "realizado até outubro e projeção para novembro e dezembro.")


def _exemplo(f, g: float | None, m: pd.DataFrame) -> None:
    gt.cabecalho("Como a meta é calculada", "Exemplo: uma unidade com 1.000 pessoas contadas em 2026 (estimativa)",
                 regra_contagem(f) + " Números inventados e arredondados.")
    at, mk = ("1.600", "80.000") if f.doze else ("1.000", "50.000")   # atendidos no ano (12 meses: mais que os contados); penetração de 2%
    with st.container(border=True):
        st.markdown("**Passo 1. Delta Nacional**  \nÉ o mesmo crescimento para todas as unidades." if g else "**Passo 1. Esperado e delta**  \nA unidade continua no ritmo dos últimos anos.")
        st.latex(r"1.000 + 10\% = 1.100")
        st.latex(r"\boxed{\text{Delta} = 100\ \text{pessoas}}")
        st.caption(f"O exemplo usa 10%. O valor real é {pct(g, 2)}: quanto as unidades com 5 anos ou mais em 2023 cresceram, juntas, em média por ano, de 2023 a 2026." if g else
                   "O delta é o que a unidade cresceria sozinha: 751 em 2023 e 1.000 em 2026 (estimativa) = 10% ao ano.")
    with st.container(border=True):
        st.markdown("**Passo 2. Fator de mercado (FM)**  \nMostra quanto espaço a unidade tem para crescer.")
        pesos = [pct(M.PESO_MERCADO, 0), pct(M.PESO_LACUNA, 0)]
        gt.tabela(pd.DataFrame([
            {"Componente": "Mercado potencial", "Peso": pesos[0], "Por quê": "É a principal medida da oportunidade disponível."},
            {"Componente": "Penetração atual / lacuna", "Peso": pesos[1], "Por quê": "Mostra quanto desse mercado ainda não foi alcançado."},
            {"Componente": "Total", "Peso": "100%", "Por quê": "Os dois somados dão o FM."}]), texto=3, total=lambda l: l["Componente"] == "Total")
        st.latex(rf"\text{{Penetração}} = \frac{{{at}}}{{{mk}}} = 2\%")
        st.latex(r"\text{Lacuna} = 100\% - 2\% = 98\%")
        st.latex(rf"\begin{{aligned}}FM = {{}}&{pesos[0][:-1]}\% \times 0{{,}}70\\ &+ {pesos[1][:-1]}\% \times 0{{,}}50\end{{aligned}}")
        st.latex(r"\boxed{FM = 0{,}42 + 0{,}20 = 0{,}62}")
        st.caption("Penetração é a parte do mercado que a unidade atendeu no ano. Lacuna é o que falta. No FM entram posições de 0 a 1 na fila das unidades: com 0,70, 7 em cada "
                   "10 têm mercado menor; com 0,50, metade tem lacuna menor. A lacuna entra como posição porque, em quase todas as unidades, ela passa de "
                   f"{pct((1 - m.penetracao).quantile(.05), 0)} e o número sozinho quase não mostra diferença entre elas.")
    with st.container(border=True):
        st.markdown("**Passo 3. Potencial e esforço**  \nCom FM de 0,62, o potencial é alto e o esforço é de 15%.")
        gt.tabela(pd.DataFrame({"FM": FAIXAS, "Potencial": M.POTENCIAL, "Esforço": [pct(e, 0) for e in M.ESFORCOS]}), destaque=("Potencial", "Alto"))
    with st.container(border=True):
        _meta_exemplo(g)


def _meta_exemplo(g: float | None) -> None:
    st.markdown("**Passo 4. Meta**  \n" + ("Vale o maior: o delta Nacional com esforço ou o esperado da unidade, que é o ritmo dela nos últimos anos." if g else
                                          "Base mais o delta com esforço."))
    if not g:
        st.latex(r"\begin{aligned}\text{Meta} = {}&\text{Base} + \text{Delta}\\ &\times (1 + \text{Esforço})\end{aligned}")
        st.latex(r"\boxed{1.000 + 100 \times 1{,}15 = 1.115\ \text{pessoas}}")
        st.caption("É o esperado (1.100) mais 15% do delta (15 pessoas).")
        return
    st.markdown("Delta com esforço (as 100 pessoas do delta mais 15% delas):")
    st.latex(r"1.000 + 100 \times 1{,}15 = 1.115")
    gt.tabela(pd.DataFrame([
        {"Se o esperado da unidade for": "1.080", "Delta com esforço": "1.115", "Maior": "Delta com esforço", "Meta 2027": "1.115"},
        {"Se o esperado da unidade for": "1.150", "Delta com esforço": "1.115", "Maior": "Esperado", "Meta 2027": "1.150"}]))


def _conta_real(f, p: dict, uid: int) -> None:
    m, r, g = p["metas"], p["resumo"], p["nacional"]
    if uid == D.NACIONAL:
        gt.cabecalho("A conta real", "Nacional: a soma das metas das unidades", "Escolha uma unidade na barra lateral para ver a conta dela")
        conta([(f"Base: {contados(f)} 2026", f"{num(r['base'])} (estimativa)"),
               (f"2026 + delta Nacional" if g else "Esperado 2027", f"{num(r['partida'])} ({pct(r['partida'] / r['base'] - 1, 1, sinal=True)})"),
               ("Acréscimo do mercado", num(r["meta_delta"] - r["partida"])),
               *([("Unidades com esperado maior", f"{num(r['no_esperado'])} unidades: {num(r['meta'] - r['meta_delta'])} a mais")] if g else []),
               ("Meta 2027", f"{num(r['meta'])} ({pct(r['nacional_pct'], 1, sinal=True)})")])
        return
    u = m.loc[uid]
    gt.cabecalho("A conta real", f"{D.nome_unidade(p, uid)}: meta de {num(u.meta)} CPFs em 2027 ({pct(u.meta_pct, 1, sinal=True)})",
                 f"Potencial {u.potencial.lower()} · esforço de {pct(u.fe, 0)}")
    conta([(f"Base: {contados(f)} 2026", f"{num(u.base)} (estimativa)"),
           *([("Delta Nacional", f"{num(u.base)} × {pct(g, 2)} = {num(u.delta)}")] if g else [
               ("Esperado 2027", f"{num(u.esperado)} ({pct(u.esperado / u.base - 1, 1, sinal=True)})"),
               ("Delta", f"{num(u.esperado)} − {num(u.base)} = {num(u.delta)}")]),
           ("Mercado potencial", f"{num(u.mercado)} pessoas (posição {num(u.p_mercado, 2)})" if pd.notna(u.mercado) else "sem mercado na planilha"),
           ("Penetração e lacuna (atendidos no ano)", f"{num(u.pessoas)} ÷ {num(u.mercado)} = {pct(u.penetracao, 1)} · lacuna {pct(1 - u.penetracao, 1)} (posição {num(u.p_lacuna, 2)})"
            if pd.notna(u.penetracao) else "sem mercado na planilha"),
           ("Fator de mercado", f"60% × {num(u.p_mercado, 2)} + 40% × {num(u.p_lacuna, 2)} = {num(u.fm, 2)}"),
           ("Esforço", f"{pct(u.fe, 0)} (potencial {u.potencial.lower()})"),
           *([("Delta com esforço", f"{num(u.base)} + {num(u.delta)} × {num(1 + u.fe, 2)} = {num(u.meta_delta)}"),
              ("Esperado da unidade", f"{num(u.esperado)} ({pct(u.esperado / u.base - 1, 1, sinal=True)})"),
              ("Meta", f"o maior: {'esperado' if u.no_esperado else 'delta com esforço'} = {num(u.meta)}")] if g else [
              ("Meta", f"{num(u.base)} + {num(u.delta)} × {num(1 + u.fe, 2)} = {num(u.meta)}" if u.delta > 0 else
               f"esperado abaixo de 2026, sem esforço = {num(u.meta)}")])])
