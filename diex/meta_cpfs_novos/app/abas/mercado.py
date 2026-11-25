"""Aba Proposta (a antiga Proposta 3), por unidade: base + crescimento padrão (delta Nacional em módulo) × (1 + esforço de mercado). Com a fórmula explicada,
um exemplo fictício, a conta real, a evolução e as metas por unidade. O fator de mercado segue na conta, mas fora da tela (pedido de 25/11)."""
import pandas as pd
import streamlit as st

import modelo as M
from abas.comum import ENTRA, assunto, baixar_excel, conta, contados, cor, do_publico, entra, lx, mil, num, pct, publico_nota, regra_contagem, rotulos_anos
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import divergente
from scripts import dados as D


def render(f) -> None:
    rotulos = D.ESCOPO[f.entidade]
    escopo = st.pills("Cenário", list(rotulos), default=1, key=f"p3_escopo_{f.entidade}", format_func=rotulos.get) or 1
    p = D.mercado(f.entidade, escopo, f.ano)
    m, r, u, uid, g = p["metas"], p["resumo"], p["unidades"], f.unidade, p["delta"]

    with gt.cartao("p3_cenarios"):
        _cenarios(f, rotulos, escopo)
    with gt.cartao("p3_regra"):
        _formula(f, p, escopo)
    with gt.cartao("p3_exemplo"):
        _exemplo(f, p)

    with gt.cartao("p3_faixas"):
        fx = m.groupby("fe").agg(unidades=("base", "size"), base=("base", "sum"), meta=("meta", "sum")).reindex(M.ESFORCOS, fill_value=0)
        gt.cabecalho("Faixas do esforço de mercado", f"A faixa com mais unidades é a de {pct(fx.unidades.idxmax(), 0)}: "
                     f"{num(fx.unidades.max())} unidades", f"{num(len(m))} unidades com meta · 2026 é projeção")
        gt.tabela(pd.DataFrame({
            "Espaço para crescer": M.POTENCIAL, "Esforço de mercado": [pct(e, 0) for e in M.ESFORCOS],
            "Unidades": fx.unidades.map(num).values, "CPFs 2026 (projeção)": fx.base.map(mil).values, "Meta 2027": fx.meta.map(mil).values,
            "Sobre 2026": [pct(a / b - 1, 1, sinal=True) if b else "—" for a, b in zip(fx.meta, fx.base)]}))

    with gt.cartao("p3_conta"):
        _conta_real(f, p, uid)

    with gt.cartao("p3_evolucao"):
        _evolucao_publico(f, p, escopo) if f.publico else _evolucao(f, p, escopo)

    with gt.cartao("p3_unidades"):
        mm = m.loc[u.index]
        gt.cabecalho("Metas por unidade", f"Meta de 2027 em {contados(f, meio=True)}", "Base mais o crescimento padrão, igual para todas, e o esforço de mercado de cada unidade")
        pub = D.serie_publico(f.entidade, escopo, f.publico).xs(M.ANO_CORRENTE, level="ano").reindex(u.index) if f.publico else None
        gt.tabela(pd.DataFrame({
            "Unidade": u.rotulo, "Conselho": u.conselho_curto, "CPFs 2026 (projeção)": mm.base.map(num),
            **({f"{f.publico} 2026": [f"{num(v)} ({pct(v / b, 0)})" for v, b in zip(pub, mm.base)]} if f.publico else {}),
            "Com o crescimento padrão": mm.partida.map(num), "Penetração": mm.penetracao.map(lambda v: pct(v, 1) if pd.notna(v) else "—"),
            "Esforço de mercado": mm.fe.map(lambda v: pct(v, 0)),
            "Meta 2027": [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in zip(mm.meta, mm.meta_pct)]}),
            destaque=("Unidade", D.nome_unidade(p, uid)) if uid != D.NACIONAL else None, texto=2, altura=480)
        baixar_excel(pd.DataFrame({
            "unidade": u.rotulo, "conselho": u.conselho_curto, "base_2026_projecao": mm.base.round(0),
            **({f"{f.publico.lower()}_2026_projecao": pub.round(0)} if f.publico else {}),
            "base_mais_crescimento_padrao": mm.partida.round(0),
            "crescimento_padrao": mm.delta.round(1), "atendidos_2026_projecao": mm.pessoas.round(0), "mercado": mm.mercado, "penetracao": mm.penetracao.round(4),
            "espaco_para_crescer": mm.potencial, "esforco_de_mercado": mm.fe, "meta_2027": mm.meta, "meta_pct": mm.meta_pct.round(4)}),
            f"meta_2027_proposta_{f.chave.lower()}_cenario_{'b' if escopo == 2 else 'a'}.xlsx", "xls_p3")

    with gt.cartao("p3_resumo"):
        gt.cabecalho(f"Proposta · {D.nome(f.entidade)} · {rotulos[escopo]}", f"Todas as unidades crescerão {pct(g, 2)} (crescimento padrão), e o esforço de mercado acrescentará mais em umas e menos em outras",
                     f"{ENTRA[f.entidade][escopo]}. {num(len(m))} unidades; sem o esforço de mercado, a meta seria de {pct(g, 2, sinal=True)} para todas.")
        gt.kpis([(f"{contados(f)} 2026", mil(r["base"]), "projeção", ""),
                 ("2026 + crescimento padrão", mil(r["partida"]), f"{pct(g, 2, sinal=True)} · igual para todas", ""),
                 ("Meta 2027", mil(r["meta"]), f"{pct(r['nacional_pct'], 1, sinal=True)} sobre a projeção de 2026", ""),
                 ("Menor e maior meta", f"{pct(r['minimo'], 1, sinal=True)} a {pct(r['maximo'], 1, sinal=True)}", "por unidade, sobre 2026", "")])

    nota(f"{regra_contagem(f)} {publico_nota(f)}A penetração usa todas as pessoas atendidas no ano. O crescimento padrão vem do crescimento de {pct(p['nacional'], 2, sinal=True)} ao ano, em média, das unidades com pelo menos 5 anos "
         "de inauguração em 2023 e anos completos, com a mesma forma de contar. " + {
             "SEST": "O mercado potencial (saúde) vem de um estudo da ESPM. ", "SENAT": "O mercado potencial (educação) vem de um estudo da ESPM. "}.get(
             f.entidade, "O mercado potencial é a soma de saúde e educação, de um estudo da ESPM; a mesma pessoa pode estar nos dois, e aí a penetração fica menor do que é. ")
         + "2026 é projeção com base histórica.")


def _evolucao(f, p: dict, escopo: int) -> None:
    m, uid, g = p["metas"], f.unidade, p["delta"]
    hist, obs = D.historico(p, f.entidade, uid)
    x = m.loc[uid] if uid in m.index else m[["base", "partida", "meta"]].sum()
    vals, i = [*hist.tolist(), x.partida, x.meta], len(hist) - 1
    neg, _, pos = divergente(assunto(f.entidade))
    gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}: meta de {pct(x.meta / x.base - 1, 1, sinal=True)} em 2027",
                 f"{contados(f)} por ano; 2026 é projeção. Os selos de 2027 comparam com 2026.{obs}")
    gt.grafico(f"evo_p3_{f.chave}_{escopo}_{uid}", gt.evolucao(
        [*rotulos_anos(hist.index), "2027\ncrescimento padrão", "2027\nmeta"], vals, cor(f.entidade), textos=[mil(v) for v in vals],
        cores_var=(neg, pos), apagadas=list(range(i, len(vals) - 1)), comparar={j: i for j in range(i + 1, len(vals))}), 380)
    st.caption(f"**Crescimento padrão:** 2026 mais {pct(g, 2)}, igual para todas as unidades.  \n**Meta:** 2026 mais o crescimento padrão e o esforço de mercado de cada unidade.")


def _evolucao_publico(f, p: dict, escopo: int) -> None:
    """Novos CPFs só do público escolhido, até a projeção de 2026. A meta é uma só e fica no texto."""
    m, uid = p["metas"], f.unidade
    hist, obs = D.historico(p, f.entidade, uid, f.publico, escopo)
    x = m.loc[uid] if uid in m.index else m[["base", "meta"]].sum()
    parte, (neg, _, pos) = hist.iloc[-1] / x.base, divergente(assunto(f.entidade))
    gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}{do_publico(f)}: {mil(hist.iloc[-1])} em 2026 (projeção), {pct(parte, 1)} do total",
                 f"{contados(f)} por ano, só do público escolhido; 2026 é projeção.{obs.replace(' e 2027', '')}")
    gt.grafico(f"evo_p3_{f.chave}_{escopo}_{uid}", gt.evolucao(rotulos_anos(hist.index), hist.tolist(), cor(f.entidade), textos=[mil(v) for v in hist],
                                                               cores_var=(neg, pos), apagadas=[len(hist) - 1]), 380)
    st.caption(f"**A meta de 2027 é uma só, para todos os públicos:** {mil(x.meta)} ({pct(x.meta / x.base - 1, 1, sinal=True)} sobre a projeção de 2026, de {mil(x.base)}).")


def _grade(colunas: list[str], linhas: list[list[str]], destaque: int | None = None) -> None:
    """Tabela com linhas e colunas marcadas e texto que quebra; `destaque` = linha em negrito."""
    corpo = "".join(f"<tr{' class=streamlit-grade-forte' if k == destaque else ''}>" + "".join(f"<td>{v}</td>" for v in l) + "</tr>" for k, l in enumerate(linhas))
    st.html(f"<div class='streamlit-grade'><table><thead><tr>{''.join(f'<th>{c}</th>' for c in colunas)}</tr></thead><tbody>{corpo}</tbody></table></div>")


def _quadro(col, titulo: str):
    """Quadrado com título, para os passos da conta."""
    q = col.container(border=True, height="stretch")
    q.markdown(f"**{titulo}**")
    return q


def _cenarios(f, rotulos: dict, escopo: int) -> None:
    """O que entra em cada cenário da entidade, com o escolhido no título."""
    gt.cabecalho(f"{D.nome(f.entidade)} · cenário escolhido", f"{rotulos[escopo]}: {entra(f.entidade, escopo)}", "Use o seletor acima para trocar de cenário. Toda a aba muda junto.")
    r = {n: D.mercado(f.entidade, n, f.ano)["resumo"] for n in rotulos}
    _grade(["Cenário", "O que entra", "2026 (projeção)", "Meta 2027"], [
        [nome, ENTRA[f.entidade][n], mil(r[n]["base"]), f"{mil(r[n]['meta'])} ({pct(r[n]['nacional_pct'], 1, sinal=True)})"] for n, nome in rotulos.items()], list(rotulos).index(escopo))
    if "EJA" in ENTRA[f.entidade][1]:
        st.caption("EJA: Educação de Jovens e Adultos.")


def _formula(f, p: dict, escopo: int) -> None:
    real, g, t = p["nacional"], p["delta"], D.maduras(f.entidade, D.selecao_proposta(escopo, f.entidade), f.medida, f.ano)["total"].contagem
    gt.cabecalho("Como a meta é calculada", "Meta = base + [crescimento padrão × (1 + esforço de mercado)]", regra_contagem(f))
    a, b = st.columns(2, gap="small")
    with _quadro(a, "1. Crescimento padrão (crescimento médio Nacional)"):
        st.markdown("Soma das unidades com pelo menos 5 anos de inauguração em 2023:")
        _grade(["Ano", contados(f)], [["2023", mil(t.iloc[0])], ["2026 (projeção)", mil(t.iloc[-1])], ["Média por ano", pct(real, 2, sinal=True)]], 2)
        if real < 0:
            st.latex(rf"\text{{Crescimento padrão}} = |\,{lx(real * 100, 2)}\%\,|")
        st.latex(rf"\boxed{{\text{{Crescimento padrão}} = {lx(g * 100, 2)}\%}}")
        st.caption("A porcentagem será igual para todas as unidades.")
        if real < 0:
            st.caption("Quando o crescimento médio for negativo, a porcentagem entrará sem o sinal, como esforço para recuperar parte da queda.")
    with _quadro(b, "2. Esforço de mercado"):
        _grade(["Espaço para crescer", "Esforço de mercado"], [[y, pct(z, 0)] for y, z in zip(M.POTENCIAL, M.ESFORCOS)])
        st.caption("Quanto mais espaço a unidade tiver para crescer, maior será. O espaço vem do mercado potencial (estudo da ESPM) e da lacuna, a parte do mercado que falta atender.")
    st.markdown("**3. Fórmula**")
    st.latex(r"\text{Meta} = \text{Base} + [\,\text{Crescimento padrão} \times (1 + \text{Esforço de mercado})\,]")
    st.markdown(f"Em que:\n- **Base:** {contados(f, meio=True)} projetados para o fechamento de 2026;\n- **Crescimento padrão:** a porcentagem igual para todas, aplicada sobre a base;\n"
                "- **Esforço de mercado:** o acréscimo de cada unidade sobre o crescimento padrão.")


def _exemplo(f, p: dict) -> None:
    x, b_ex = M.exemplo(p["delta"]), num(M.BASE_EX)
    g, padrao, meta, casas = x["g"], x["padrao"], x["meta"], 0 if x["inteiro"] else 1
    gt.cabecalho("Exemplo fictício", f"Uma unidade com {b_ex} CPFs em 2026 e crescimento padrão de {pct(g, 2)}", "O crescimento padrão é o real do cenário escolhido.")
    a, b = st.columns(2, gap="small")
    with _quadro(a, "A unidade tem"):
        st.markdown(f"- base: **{b_ex} CPFs**;\n- crescimento padrão: {pct(g, 2)} de {b_ex} = **{num(padrao, casas)} CPFs**;\n- esforço de mercado: **{pct(M.FE_EX, 0)}**.")
    with _quadro(b, "A conta"):
        st.latex(rf"Meta = {b_ex} + [\,{lx(padrao, casas)} \times (1 + {lx(M.FE_EX, 2)})\,]")
        st.latex(rf"Meta = {b_ex} + {lx(padrao + x['mercado'], 2)}")
        st.latex(rf"\boxed{{Meta = {num(meta)}\ CPFs}}")
        st.caption("Arredondado para cima.")


def _conta_real(f, p: dict, uid: int) -> None:
    m, r, g = p["metas"], p["resumo"], p["delta"]
    base = (f"Base: {contados(f, meio=True)} 2026", lambda v: f"{num(v)} (projeção)")
    if uid == D.NACIONAL:
        gt.cabecalho("A conta real", "Nacional: a soma das metas das unidades", "Escolha uma unidade na barra lateral para ver a conta dela")
        conta([(base[0], base[1](r["base"])), ("Crescimento padrão", f"{num(r['base'])} × {pct(g, 2)} = {num(r['partida'] - r['base'])}"),
               ("Esforço de mercado", f"{num(r['meta'] - r['partida'])} (soma das unidades)"), ("Meta 2027", f"{num(r['meta'])} ({pct(r['nacional_pct'], 1, sinal=True)})")])
        return
    u = m.loc[uid]
    gt.cabecalho("A conta real", f"{D.nome_unidade(p, uid)}: meta de {num(u.meta)} CPFs em 2027 ({pct(u.meta_pct, 1, sinal=True)})", f"Espaço para crescer {u.potencial.lower()} · esforço de mercado de {pct(u.fe, 0)}")
    tem = pd.notna(u.penetracao)
    conta([(base[0], base[1](u.base)), ("Crescimento padrão", f"{num(u.base)} × {pct(g, 2)} = {num(u.delta)}"),
           ("Mercado potencial", f"{num(u.mercado)} pessoas" if pd.notna(u.mercado) else "sem mercado potencial"),
           ("Penetração e lacuna (atendidos no ano)", f"{num(u.pessoas)} ÷ {num(u.mercado)} = {pct(u.penetracao, 1)} · lacuna {pct(1 - u.penetracao, 1)}"
            if tem else "sem mercado potencial"),
           ("Esforço de mercado", f"{pct(u.fe, 0)} (espaço para crescer {u.potencial.lower()})"),
           ("Meta", f"{num(u.base)} + [{num(u.delta)} × (1 + {num(u.fe, 2)})] = {num(u.meta)}")])
