"""Aba Comparação: as propostas lado a lado em cada base (seleção inicial: P1 e P3; todas as especialidades: P2 e P3), no Nacional, no
gráfico e por unidade."""
import pandas as pd
import streamlit as st

from abas.comum import assunto, baixar_excel, contados, cor, mil, num, pct, rotulos_anos
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import divergente
from scripts import dados as D


def _base(f, escopo: int) -> tuple[dict, pd.DataFrame, list[str]]:
    """(proposta de gap da base, estimativa × esperado × metas por unidade, nomes das propostas)."""
    p, m3 = D.gap(escopo, f.entidade, ano=f.ano), D.mercado(f.entidade, escopo, f.ano)["metas"]
    m, nomes = p["metas"], [f"Proposta {escopo}", "Proposta 3"]
    return p, pd.DataFrame({"base": m.cpf0, "esperado": m.sem_meta, nomes[0]: m[f"meta_pessoas_{f.peso}"],
                            nomes[1]: m3.meta}).astype(float), nomes


def render(f) -> None:
    k, rotulos = f.peso, D.ESCOPO[f.entidade]
    minimo = ", com mínimo" if f.entidade == "SEST" else ""
    regra = {"Proposta 1": f"Esperado + {k}% do gap{minimo}", "Proposta 2": f"Esperado + {k}% do gap{minimo}", "Proposta 3": "Delta Nacional com esforço ou esperado, o maior" if f.entidade == "SEST" else "Esperado + mercado"}

    with gt.cartao("comp_nacional"):
        bases = {e: _base(f, e) for e in (1, 2)}
        gt.cabecalho("Nacional", f"Esperado de 2027: {mil(bases[1][1].esperado.sum())} com {rotulos[1].lower()} e "
                                 f"{mil(bases[2][1].esperado.sum())} com {rotulos[2].lower()}",
                     f"{f.entidade} · {contados(f)} · 2026 é estimativa · Propostas 1 e 2 no cenário de {k}%")
        linhas = []
        for e, (_, t, nomes) in bases.items():
            s = t.sum()
            linhas += [{"Proposta": n, "Especialidades": rotulos[e], "Regra": regra[n], "2026 (estimativa)": mil(s.base),
                        "Esperado 2027": mil(s.esperado), "Meta 2027": mil(s[n]), "Sobre 2026": pct(s[n] / s.base - 1, 1, sinal=True),
                        "Sobre o esperado": num(s[n] - s.esperado)} for n in nomes]
        linhas.sort(key=lambda l: l["Proposta"])
        gt.tabela(pd.DataFrame(linhas), texto=3)

    escopo = st.pills("Especialidades da comparação", list(rotulos), default=1, key="comp_escopo", format_func=rotulos.get) or 1
    p, t, nomes = bases[escopo]
    uid, s = f.unidade, t.sum()

    with gt.cartao("comp_evolucao"):
        hist, obs = D.historico(p, f.entidade, uid)
        x = t.loc[uid] if uid in t.index else s
        vals, i = [*hist.tolist(), x.esperado, *[x[n] for n in nomes]], len(hist) - 1
        neg, _, pos = divergente(assunto(f.entidade))
        gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}: esperado de {pct(x.esperado / x.base - 1, 1, sinal=True)} em 2027; "
                                 + "; ".join(f"{n}, {pct(x[n] / x.base - 1, 1, sinal=True)}" for n in nomes),
                     f"{rotulos[escopo]}. {contados(f)} por ano; 2026 é estimativa. Os selos de 2027 comparam com 2026.{obs}")
        gt.grafico(f"evo_comp_{f.chave}_{escopo}_{k}_{uid}", gt.evolucao(
            [*rotulos_anos(hist.index), "2027\nesperado", *[f"2027\n{n}" for n in nomes]], vals, cor(f.entidade),
            textos=[mil(v) for v in vals], cores_var=(neg, pos), apagadas=[i, i + 1],
            comparar={j: i for j in range(i + 1, len(vals))}), 380)

    with gt.cartao("comp_unidades"):
        u = p["unidades"]
        tt = t.loc[u.index]
        gt.cabecalho("Por unidade", "Estimativa de 2026, esperado e meta de 2027 em cada proposta",
                     f"{rotulos[escopo]}. Entre parênteses, quanto a meta representa sobre a estimativa de 2026")
        df = pd.DataFrame({"Unidade": u.rotulo, "2026 (estimativa)": tt.base.map(num), "Esperado 2027": tt.esperado.map(num)})
        bruto = pd.DataFrame({"unidade": u.rotulo, "conselho": u.conselho_curto, "base_2026_estimativa": tt.base.round(0),
                              "esperado_2027": tt.esperado})
        for n in nomes:
            df[n] = [f"{num(v)} ({pct(v / b - 1, 1, sinal=True)})" for v, b in zip(tt[n], tt.base)]
            bruto[n.lower().replace(" ", "")], bruto[f"{n.lower().replace(' ', '')}_pct"] = tt[n], (tt[n] / tt.base - 1).round(4)
        gt.tabela(df, destaque=("Unidade", D.nome_unidade(p, uid)) if uid != D.NACIONAL else None, texto=1, altura=520)
        baixar_excel(bruto, f"meta_2027_comparacao_{f.chave.lower()}_{'todas' if escopo == 2 else 'inicial'}.xlsx", "xls_comparacao")

    nota("Com todas as especialidades entram mais pessoas, por isso compare os aumentos e não os totais. "
         "Nas Propostas 1 e 2, quem está na referência ou abaixo recebe a mediana nacional, que pode ser menor que o esperado dela."
         + (" Nenhuma unidade cresce menos que o delta Nacional. Na base com todas, as campanhas ficam fora." if f.entidade == "SEST" else ""))
