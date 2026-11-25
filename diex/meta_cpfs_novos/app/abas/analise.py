"""Aba Análise: crescimento dos CPFs distintos de 2023 a 2026 nas unidades maduras (5+ anos em 2023, anos completos),
com a média geométrica (só "média" na tela, explicada na nota)."""
import numpy as np
import pandas as pd
import streamlit as st

from abas.comum import CINZA, assunto, contados, cor, do_publico, entra, mil, nota_media, num, pct, publico_nota, regra_contagem, rotulos_anos
from common.metas import media_geometrica
from common.painel.classico import FORTE, divergente
from common import painel as gt
from common.painel.casca import nota
from scripts import dados as D

FAIXAS = [(-np.inf, 0, "Queda"), (0, .05, "0% a\n5%"), (.05, .10, "5% a\n10%"), (.10, .20, "10% a\n20%"),
          (.20, np.inf, "20% ou\nmais")]


def _recorte(f) -> tuple[tuple, str]:
    """Recorte próprio da aba: as duas bases da proposta, na entidade escolhida."""
    rotulos = D.ESCOPO[f.entidade]
    escopo = st.pills("Cenário da análise", list(rotulos), default=1, key=f"an_esc_{f.entidade}", format_func=rotulos.get) or 1
    return (f.entidade, D.selecao_proposta(escopo, f.entidade), f.medida, f.ano, f.publico), f"{D.nome(f.entidade)}{do_publico(f)} · {rotulos[escopo]}: {entra(f.entidade, escopo)}"


def _evolucao(f, a, chave, rotulo) -> None:
    """Colunas ano a ano com o selo da variação (Nacional das unidades maduras ou a unidade do filtro)."""
    s = a["serie"]
    if f.unidade in a["pessoas"].index:
        serie, nome = s.xs(f.unidade, level="id_unidade").contagem, a["unidades"].rotulo.get(f.unidade)
    else:
        serie, nome = a["total"].contagem, f"{D.nome(f.entidade)}{do_publico(f)}, {len(a['pessoas'])} unidades analisadas"
    v = serie / serie.iloc[0] - 1
    anos = len(serie) - 1
    g = media_geometrica(serie.iloc[0], serie.iloc[-1], anos)
    neg, _, pos = divergente(assunto(f.entidade))
    gt.cabecalho("Evolução", f"{nome}: {pct(v.iloc[-1], 1, sinal=True)} entre {serie.index[0]} e {serie.index[-1]}, "
                             f"média¹ de {pct(g, 1)} ao ano",
                 f"{contados(f)} na unidade. Os selos mostram a variação sobre o ano anterior; a linha tracejada, a "
                 f"média¹ de {pct(g, 1)} ao ano. {rotulo}. "
                 f"{serie.index[-1]} é projeção (barra clara).")
    rot = rotulos_anos(serie.index)
    gt.grafico(f"an_evo_{hash(chave)}_{f.unidade}", gt.evolucao(
        rot, serie.tolist(), cor(f.entidade), textos=[mil(x) for x in serie], cores_var=(neg, pos),
        apagadas=[len(rot) - 1],
        tendencia={"nome": f"{pct(g, 1, sinal=True)} ao ano", "valores": [serie.iloc[0] * (1 + g) ** i for i in range(anos + 1)],
                   "cor": FORTE}), 360)


def render(f) -> None:
    chave, rotulo = _recorte(f)
    a = D.maduras(*chave)
    t, cp, u = a["total"], a["pessoas"], a["unidades"]
    g = a["geometrica"]
    destaque = cor(f.entidade)
    medida = f.rotulo_medida if chave[2] == f.medida else chave[2]
    n = len(cp)
    var = t.loc[2026] / t.loc[2023] - 1
    var25 = t.loc[2025] / t.loc[2023] - 1
    gn = media_geometrica(t.contagem.iloc[0], t.contagem.iloc[-1], len(t) - 1)

    with gt.cartao("an_kpis", compacto=True):
        gt.kpis([
            ("Unidades analisadas", num(n), f"de {num(a['n_total'])} · inauguradas até {a['inaug_ate']}", ""),
            (f"{contados(f)} 2023→2026 (projeção)", pct(var.contagem, 1, sinal=True),
             f"{pct(var25.contagem, 1, sinal=True)} até 2025, só anos fechados", ""),
            ("Média¹", pct(gn, 1, sinal=True), "crescimento por ano · Nacional", ""),
        ])

    with gt.cartao("an_evolucao"):
        _evolucao(f, a, chave, rotulo)

    col1, col2 = st.columns([2, 3], gap="medium")
    with col1, gt.cartao("an_faixas"):
        cont = [int(((g >= lo) & (g < hi)).sum()) for lo, hi, _ in FAIXAS]
        rot = [x for *_, x in FAIXAS]
        topo = rot[int(np.argmax(cont))]
        gt.cabecalho("Média¹", f"A faixa mais comum é {'a de queda' if topo == 'Queda' else topo.replace(chr(10), ' ')}: "
                                   f"{num(max(cont))} unidades",
                     f"{contados(f)} de 2023 a 2026, por unidade")
        cores = [CINZA] * len(cont)
        cores[int(np.argmax(cont))] = destaque
        gt.grafico(f"an_faixas_{hash(chave)}", gt.colunas(rot, cont, cores, casas=0), 300)

    with col2, gt.cartao("an_anos"):
        c = a["cres"]
        linhas = []
        for ano in (2024, 2025, 2026):
            for m, nome in (("contagem", contados(f)), ("producao", medida.capitalize()))[:1 if f.publico else 2]:     # a produção não é aberta por público
                v = c[m][ano].replace([np.inf, -np.inf], np.nan).dropna()
                linhas.append({"Ano": f"{ano}{' (projeção)' if ano == 2026 else ''}", "Medida": nome,
                               "Total": pct(t.loc[ano, m] / t.loc[ano - 1, m] - 1, 1, sinal=True),
                               "Metade das unidades": f"{pct(v.quantile(.25), 1)} a {pct(v.quantile(.75), 1)}",
                               "Com queda": num((v < 0).sum())})
        gt.cabecalho("Ano a ano", "Variação de cada ano sobre o anterior",
                     "Total: soma das unidades · metade das unidades: as do meio, sem o quarto mais baixo e o mais alto")
        gt.tabela(pd.DataFrame(linhas), texto=2)

    with gt.cartao("an_unidades"):
        gt.cabecalho("Por unidade", f"{contados(f)} de cada unidade analisada",
                     f"{rotulo} · ordem por tipologia e número · 2026 é projeção")
        ids = u.index
        df = pd.DataFrame({"Unidade": u.rotulo, "Conselho": u.conselho_curto})
        for ano in (2023, 2024, 2025, 2026):
            df[f"{ano} (projeção)" if ano == 2026 else str(ano)] = cp.loc[ids, ano].map(num)
        df["Média¹"] = g.loc[ids].map(lambda v: pct(v, 1, sinal=True))
        nome = u.rotulo.get(f.unidade) if f.unidade != D.NACIONAL else None
        gt.tabela(df, destaque=("Unidade", nome) if nome else None, texto=2, altura=480)

    nota(f"{regra_contagem(f)} {publico_nota(f)}"
         f"Unidades inauguradas até {a['inaug_ate']} (5 anos ou mais em 2023) e com produção nos 12 meses de 2023, "
         "2024 e 2025 no recorte escolhido. Assim, abertura de unidade ou de especialidade no meio do período não "
         "infla o crescimento. 2026 é projeção com base histórica.")
    nota(nota_media())
