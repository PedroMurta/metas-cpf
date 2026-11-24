"""Aba Proposta (a antiga Proposta 3) · fator de mercado, por unidade: base + esforço padrão (delta Nacional em módulo) × (1 + esforço de mercado). Com a
fórmula explicada, um exemplo de 1.000 pessoas, a conta real, a evolução e as metas por unidade."""
import math

import numpy as np
import pandas as pd
import streamlit as st

import modelo as M
from abas.comum import ENTRA, assunto, baixar_excel, conta, contados, cor, lx, mil, num, pct, regra_contagem, rotulos_anos
from charts import ilustracoes as I
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import divergente
from scripts import dados as D

MERCADO_EX, LACUNA_EX = .70, .50   # posições da unidade inventada
FM_EX = M.PESO_MERCADO * MERCADO_EX + M.PESO_LACUNA * LACUNA_EX
FAIXAS = ["0 a 0,25", "0,25 a 0,50", "0,50 a 0,75", "0,75 a 1"]


def render(f) -> None:
    rotulos = D.ESCOPO[f.entidade]
    escopo = st.pills("Especialidades", list(rotulos), default=1, key=f"p3_escopo_{f.entidade}", format_func=rotulos.get) or 1
    p = D.mercado(f.entidade, escopo, f.ano)
    m, r, u, uid, g = p["metas"], p["resumo"], p["unidades"], f.unidade, p["delta"]

    with gt.cartao("p3_regra"):
        _formula(f, p, escopo)
    with gt.cartao("p3_exemplo"):
        _exemplo(f, p)

    with gt.cartao("p3_faixas"):
        fx = m.groupby("fe").agg(unidades=("base", "size"), base=("base", "sum"), meta=("meta", "sum")).reindex(M.ESFORCOS, fill_value=0)
        gt.cabecalho("Faixas do fator de mercado", f"A faixa com mais unidades é a de esforço de mercado de {pct(fx.unidades.idxmax(), 0)}: "
                     f"{num(fx.unidades.max())} unidades", f"{num(len(m))} unidades com meta · 2026 é projeção")
        gt.tabela(pd.DataFrame({
            "Fator de mercado": FAIXAS, "Potencial": M.POTENCIAL, "Esforço de mercado": [pct(e, 0) for e in M.ESFORCOS],
            "Unidades": fx.unidades.map(num).values, "CPFs 2026 (projeção)": fx.base.map(mil).values, "Meta 2027": fx.meta.map(mil).values,
            "Sobre 2026": [pct(a / b - 1, 1, sinal=True) if b else "—" for a, b in zip(fx.meta, fx.base)]}))

    with gt.cartao("p3_conta"):
        _conta_real(f, p, uid)

    with gt.cartao("p3_evolucao"):
        hist, obs = D.historico(p, f.entidade, uid)
        x = m.loc[uid] if uid in m.index else m[["base", "partida", "meta"]].sum()
        vals, i = [*hist.tolist(), x.partida, x.meta], len(hist) - 1
        neg, _, pos = divergente(assunto(f.entidade))
        gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}: meta de {pct(x.meta / x.base - 1, 1, sinal=True)} em 2027",
                     f"{contados(f)} por ano; 2026 é projeção. Os selos de 2027 comparam com 2026.{obs}")
        gt.grafico(f"evo_p3_{f.chave}_{escopo}_{uid}", gt.evolucao(
            [*rotulos_anos(hist.index), "2027\nesforço padrão", "2027\nmeta"], vals, cor(f.entidade), textos=[mil(v) for v in vals],
            cores_var=(neg, pos), apagadas=list(range(i, len(vals) - 1)), comparar={j: i for j in range(i + 1, len(vals))}), 380)
        st.caption(f"**Esforço padrão:** 2026 mais {pct(g, 2)}, igual para todas as unidades.  \n**Meta:** 2026 mais o esforço padrão e o esforço de mercado de cada unidade.")

    with gt.cartao("p3_unidades"):
        mm = m.loc[u.index]
        gt.cabecalho("Metas por unidade", f"Meta de 2027 em {contados(f)}", "Base mais o esforço padrão, igual para todas, e o esforço de mercado de cada unidade")
        gt.tabela(pd.DataFrame({
            "Unidade": u.rotulo, "Conselho": u.conselho_curto, "CPFs 2026 (projeção)": mm.base.map(num),
            "Com o esforço padrão": mm.partida.map(num), "Penetração": mm.penetracao.map(lambda v: pct(v, 1) if pd.notna(v) else "—"),
            "Fator de mercado": mm.fm.map(lambda v: num(v, 2)), "Esforço de mercado": mm.fe.map(lambda v: pct(v, 0)),
            "Meta 2027": [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in zip(mm.meta, mm.meta_pct)]}),
            destaque=("Unidade", D.nome_unidade(p, uid)) if uid != D.NACIONAL else None, texto=2, altura=480)
        baixar_excel(pd.DataFrame({
            "unidade": u.rotulo, "conselho": u.conselho_curto, "base_2026_projecao": mm.base.round(0),
            "base_mais_esforco_padrao": mm.partida.round(0),
            "esforco_padrao": mm.delta.round(1), "atendidos_2026_projecao": mm.pessoas.round(0), "mercado": mm.mercado, "penetracao": mm.penetracao.round(4),
            "percentil_mercado": mm.p_mercado.round(4), "percentil_lacuna": mm.p_lacuna.round(4), "fator_mercado": mm.fm.round(4),
            "potencial": mm.potencial, "esforco_de_mercado": mm.fe, "meta_2027": mm.meta, "meta_pct": mm.meta_pct.round(4)}),
            f"meta_2027_proposta_{f.chave.lower()}_{'todas' if escopo == 2 else 'selecao'}.xlsx", "xls_p3")

    with gt.cartao("p3_resumo"):
        gt.cabecalho(f"Proposta · {f.entidade}", f"Todas as unidades crescem {pct(g, 1)} (esforço padrão), e o esforço de mercado acrescenta mais em umas e menos em outras",
                     f"{ENTRA[f.entidade][escopo]}. {num(len(m))} unidades; sem o esforço de mercado, a meta seria de {pct(g, 1, sinal=True)} para todas.")
        gt.kpis([(f"{contados(f)} 2026", mil(r["base"]), "projeção", ""),
                 ("2026 + esforço padrão", mil(r["partida"]), f"{pct(g, 1, sinal=True)} · igual para todas", ""),
                 ("Meta 2027", mil(r["meta"]), f"{pct(r['nacional_pct'], 1, sinal=True)} sobre a projeção de 2026", ""),
                 ("Menor e maior meta", f"{pct(r['minimo'], 1, sinal=True)} a {pct(r['maximo'], 1, sinal=True)}", "por unidade, sobre 2026", "")])

    nota(f"{regra_contagem(f)} A penetração usa todas as pessoas atendidas no ano. O esforço padrão vem do crescimento de {pct(p['nacional'], 2, sinal=True)} ao ano, em média, das unidades com pelo menos 5 anos "
         "de inauguração em 2023 e anos completos, com a mesma forma de contar. " + {
             "SEST": "O mercado e a posição dele vêm da planilha da área (mercado de saúde). ", "SENAT": "O mercado e a posição dele vêm da planilha da área (mercado de educação). "}.get(
             f.entidade, "O mercado é a soma dos dois da planilha da área (saúde e educação); a mesma pessoa pode estar nos dois, e aí a penetração fica menor do que é. ")
         + "2026 é projeção com base histórica.")


def _grade(colunas: list[str], linhas: list[list[str]], destaque: int | None = None) -> None:
    """Tabela com linhas e colunas marcadas e texto que quebra; `destaque` = linha em negrito."""
    corpo = "".join(f"<tr{' class=streamlit-grade-forte' if k == destaque else ''}>" + "".join(f"<td>{v}</td>" for v in l) + "</tr>" for k, l in enumerate(linhas))
    st.html(f"<div class='streamlit-grade'><table><thead><tr>{''.join(f'<th>{c}</th>' for c in colunas)}</tr></thead><tbody>{corpo}</tbody></table></div>")


def _quadro(col, titulo: str):
    """Quadrado com título, para os passos da conta."""
    q = col.container(border=True, height="stretch")
    q.markdown(f"**{titulo}**")
    return q


def _formula(f, p: dict, escopo: int) -> None:
    real, g, t = p["nacional"], p["delta"], D.maduras(f.entidade, D.selecao_proposta(escopo, f.entidade), f.medida, f.ano)["total"].contagem
    pm, pl = lx(M.PESO_MERCADO, 2), lx(M.PESO_LACUNA, 2)
    gt.cabecalho("Como a meta é calculada", "Meta = base + [esforço padrão × (1 + esforço de mercado)]", regra_contagem(f) + " Os números do fator de mercado são de uma unidade inventada.")
    a, b = st.columns(2, gap="small")
    with _quadro(a, "1. Esforço padrão (delta Nacional)"):
        st.markdown("Soma das unidades com pelo menos 5 anos de inauguração em 2023:")
        _grade(["Ano", contados(f)], [["2023", mil(t.iloc[0])], ["2026 (projeção)", mil(t.iloc[-1])], ["Média por ano", pct(real, 2, sinal=True)]], 2)
        if real < 0:
            st.latex(rf"\text{{Esforço padrão}} = |\,{lx(real * 100, 2)}\%\,|")
        st.latex(rf"\boxed{{\text{{Esforço padrão}} = {lx(g * 100, 2)}\%}}")
        st.caption("A porcentagem é igual para todas as unidades." + ("" if real > 0 else " A média é negativa (queda) e entra em módulo, isto é, sem o sinal, para estimular a retomada do crescimento."))
    with _quadro(b, "2. Fator de mercado (FM)"):
        _grade(["Componente", "Peso", "Por quê"], [
            ["Mercado potencial", pct(M.PESO_MERCADO, 0), "É a principal medida da oportunidade disponível."],
            ["Penetração atual / lacuna", pct(M.PESO_LACUNA, 0), "Mostra quanto desse mercado ainda não foi alcançado."], ["Total", "100%", ""]], 2)
        st.latex(rf"FM = {pm}\,({lx(MERCADO_EX, 2)}) + {pl}\,({lx(LACUNA_EX, 2)})")
        st.latex(rf"FM = {lx(M.PESO_MERCADO * MERCADO_EX, 2)} + {lx(M.PESO_LACUNA * LACUNA_EX, 2)}")
        st.latex(rf"\boxed{{FM = {lx(FM_EX, 2)}}}")
        st.caption("O 0,60 e o 0,40 são os pesos. O 0,70 e o 0,50 são o lugar da unidade em duas listas, explicadas abaixo.")
    st.markdown("**De onde vêm o 0,70 e o 0,50?**  \nFazemos duas listas com todas as unidades. Uma vai da unidade com o **menor mercado** até a que tem o **maior mercado**. A outra vai da que tem a "
                "**menor lacuna** até a que tem a **maior lacuna**. Em cada lista, a primeira unidade vale **0**, a última vale **1** e as outras ficam entre elas. O número é o lugar da unidade na lista.")
    I.quadros([
        ("Lista das unidades por tamanho do mercado: 0,70", I.fila(cor(f.entidade), MERCADO_EX, "7 em cada 10 têm mercado menor", "Unidades em ordem de tamanho do mercado; a do exemplo está no 0,70."),
         "No 0,70, o mercado dela é maior que o de <strong>7 em cada 10</strong> unidades."),
        ("Lista das unidades por tamanho da lacuna: 0,50", I.fila(cor(f.entidade), LACUNA_EX, "5 em cada 10 têm lacuna menor", "Unidades em ordem de tamanho da lacuna; a do exemplo está no 0,50."),
         "No 0,50, ela está <strong>no meio da lista</strong>: 5 em cada 10 unidades têm lacuna menor.")])
    st.caption("Por que usar as listas? Mercado é contado em pessoas e lacuna em porcentagem. Nas listas, os dois vão de 0 a 1 e podem ser somados. Quanto mais perto de 1, mais espaço para crescer.")
    a, b = st.columns(2, gap="small")
    k = int(np.searchsorted(M.FAIXAS_FM, FM_EX))
    with _quadro(a, "3. Potencial e esforço de mercado"):
        _grade(["FM", "Potencial", "Esforço de mercado"], [[x, y, pct(z, 0)] for x, y, z in zip(FAIXAS, M.POTENCIAL, M.ESFORCOS)], k)
        st.caption(f"Com FM de {num(FM_EX, 2)}, o potencial é {M.POTENCIAL[k].lower()} e o esforço de mercado é de {pct(M.ESFORCOS[k], 0)}.")
    with _quadro(b, "4. Fórmula"):
        st.markdown("A meta fica:")
        st.latex(r"Meta = Base + [\,Delta \times (1 + FE)\,]")
        st.markdown(f"Em que:\n- **Base:** {contados(f)} projetados para o fechamento de 2026;\n- **Delta:** esforço padrão, em CPFs;\n- **FE:** esforço de mercado. Sem ele, a meta é a base mais o esforço padrão.")


def _exemplo(f, p: dict) -> None:
    g = round(p["delta"], 2 if p["delta"] >= .01 else 4)               # delta pequeno (SEST + SENAT, 0,27%) não some no arredondamento
    casas = 0 if g >= .01 else 2
    at, mk = ("1.600", "80.000") if f.doze else ("1.000", "50.000")   # atendidos no ano (12 meses: mais que os contados); penetração de 2%
    padrao, k = 1000 * g, int(np.searchsorted(M.FAIXAS_FM, FM_EX))
    esforco, meta = M.ESFORCOS[k], math.ceil(round(1000 + padrao * (1 + M.ESFORCOS[k]), 6))
    gt.cabecalho("Exemplo", f"Uma unidade com 1.000 CPFs em 2026 e esforço padrão de {pct(g, casas)}", "Unidade inventada e números arredondados.")
    a, b = st.columns(2, gap="small")
    with _quadro(a, "A unidade tem"):
        st.markdown(f"- base projetada: **1.000 CPFs**;\n- esforço padrão (delta): {pct(g, casas)} de 1.000 = **{num(padrao, 1 if casas else 0)} CPFs**;\n- penetração: {at} ÷ {mk} = 2%, e lacuna de 98%;\n"
                    f"- fator de mercado: **{num(FM_EX, 2)}** (potencial {M.POTENCIAL[k].lower()});\n- esforço de mercado correspondente: **{pct(esforco, 0)}**.")
    with _quadro(b, "A conta"):
        st.latex(rf"Meta = 1.000 + [\,{lx(padrao, 1 if casas else 0)} \times (1 + {lx(esforco, 2)})\,]")
        st.latex(rf"Meta = 1.000 + {lx(padrao * (1 + esforco), 1)}")
        st.latex(rf"\boxed{{Meta = {num(meta)}\ CPFs}}")
        st.caption("Arredondado para cima.")


def _conta_real(f, p: dict, uid: int) -> None:
    m, r, g = p["metas"], p["resumo"], p["delta"]
    base = (f"Base: {contados(f)} 2026", lambda v: f"{num(v)} (projeção)")
    if uid == D.NACIONAL:
        gt.cabecalho("A conta real", "Nacional: a soma das metas das unidades", "Escolha uma unidade na barra lateral para ver a conta dela")
        conta([(base[0], base[1](r["base"])), ("Esforço padrão", f"{num(r['base'])} × {pct(g, 2)} = {num(r['partida'] - r['base'])}"),
               ("Esforço de mercado", f"{num(r['meta'] - r['partida'])} (soma das unidades)"), ("Meta 2027", f"{num(r['meta'])} ({pct(r['nacional_pct'], 1, sinal=True)})")])
        return
    u = m.loc[uid]
    gt.cabecalho("A conta real", f"{D.nome_unidade(p, uid)}: meta de {num(u.meta)} CPFs em 2027 ({pct(u.meta_pct, 1, sinal=True)})", f"Potencial {u.potencial.lower()} · esforço de mercado de {pct(u.fe, 0)}")
    tem = pd.notna(u.penetracao)
    conta([(base[0], base[1](u.base)), ("Esforço padrão", f"{num(u.base)} × {pct(g, 2)} = {num(u.delta)}"),
           ("Mercado potencial", f"{num(u.mercado)} pessoas (lugar na lista: {num(u.p_mercado, 2)})" if pd.notna(u.mercado) else "sem mercado na planilha"),
           ("Penetração e lacuna (atendidos no ano)", f"{num(u.pessoas)} ÷ {num(u.mercado)} = {pct(u.penetracao, 1)} · lacuna {pct(1 - u.penetracao, 1)} (lugar na lista: {num(u.p_lacuna, 2)})"
            if tem else "sem mercado na planilha"),
           ("Fator de mercado", f"60% × {num(u.p_mercado, 2)} + 40% × {num(u.p_lacuna, 2)} = {num(u.fm, 2)}" if tem else num(u.fm, 2)),
           ("Esforço de mercado", f"{pct(u.fe, 0)} (potencial {u.potencial.lower()})"),
           ("Meta", f"{num(u.base)} + [{num(u.delta)} × (1 + {num(u.fe, 2)})] = {num(u.meta)}")])
