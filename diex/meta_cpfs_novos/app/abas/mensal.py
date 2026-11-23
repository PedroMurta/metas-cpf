"""Aba Mês a mês: contagem de 12 meses do SEST no Nacional (4 especialidades), com 2023 em duas versões: com o histórico anterior e como
ponto de partida. Total do ano, barras por mês e tabela."""
import pandas as pd
import streamlit as st

from abas.comum import assunto, baixar_excel, baixar_planilha, cor, mil, num, pct, rotulos_anos
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import CONTEXTO, CONTEXTO2, MESES_PT, TEXTO, divergente
from recortes import ANO_CORRENTE, CORTE
from scripts import dados as D

ANOS = [2023, 2024, 2025, ANO_CORRENTE]
VERSOES = {2023: "2023 com histórico", D.PARTIDA: "2023 como ponto de partida"}
ROTULOS = [f"{m} ({ANO_CORRENTE} est.)" if i >= CORTE else m for i, m in enumerate(MESES_PT)]
PERIODO = f"{MESES_PT[0]} a {MESES_PT[CORTE - 1].lower()}"


def _anual(d: dict, inicio, topo: float) -> None:
    s = d["ano"][[inicio, *ANOS[1:]]]
    neg, _, pos = divergente(assunto("SEST"))
    v = s.iloc[1] / s.iloc[0] - 1
    gt.cabecalho("Total do ano", f"{VERSOES[inicio]}: {mil(s.iloc[0])} em 2023 e {mil(s.iloc[-1])} em {ANO_CORRENTE} (estimativa)",
                 "Usa os atendimentos desde outubro de 2018. Os selos mostram a variação sobre o ano anterior" if inicio == 2023 else
                 f"Em 2023, todos contam como 1ª vez. Por isso 2024 mostra {pct(v, 1, sinal=True)}, sem perda de público")
    op = gt.evolucao(rotulos_anos(ANOS), s.tolist(), cor("SEST"), textos=[mil(x) for x in s], cores_var=(neg, pos), apagadas=[len(ANOS) - 1])
    op["yAxis"] |= {"max": round(topo * 1.42, -4), "axisLabel": {"show": False}}                    # mesma escala nos dois gráficos
    for x in op["series"][1]["data"]:
        if x["value"]:
            x["value"] = topo * 1.28
    gt.grafico(f"mes_anual_{inicio}", op, 320)


def _mensal(d: dict, inicio) -> None:
    t = d["meses"][[inicio, *ANOS[1:]]]
    a, b = t.loc[:CORTE, 2025], t.loc[:CORTE, ANO_CORRENTE]
    if inicio == 2023:
        achado = f"Em {ANO_CORRENTE}, {int((b > a).sum())} dos {CORTE} meses ficaram acima de 2025"
        detalhe = f"2023 com histórico. {PERIODO} de {ANO_CORRENTE}: {num(b.sum())} pessoas, {pct(b.sum() / a.sum() - 1, 1, sinal=True)} sobre 2025"
    else:
        achado = f"Com 2023 como ponto de partida, janeiro de 2023 sozinho tem {mil(t.loc[1, inicio])} pessoas"
        detalhe = "Sem histórico, quem já era atendido antes também conta em 2023. De 2024 em diante, os valores são os do gráfico acima"
    gt.cabecalho("Mês a mês", achado, f"{detalhe}. Novembro e dezembro de {ANO_CORRENTE} são estimativa (barras claras)")
    cores = [CONTEXTO, CONTEXTO2, TEXTO, cor("SEST")]
    op = gt.barras_agrupadas(MESES_PT, [(str(c) if c != D.PARTIDA else "2023 (partida)", t[c].tolist(), k) for c, k in zip(t.columns, cores)], casas=0)
    op["series"][-1]["data"][CORTE:] = [{"value": v, "itemStyle": {"opacity": .45}} for v in op["series"][-1]["data"][CORTE:]]
    gt.grafico(f"mes_barras_{inicio}", op, 360)


def _tabela(d: dict) -> None:
    linhas = pd.concat([d["meses"].set_axis(ROTULOS), d["corte"].rename(PERIODO).to_frame().T,
                        d["ano"].rename("Ano").to_frame().T])
    partes = {"2023 hist.": linhas[2023], "2023 part.": linhas[D.PARTIDA], "2024": linhas[2024], "2025": linhas[2025],
              str(ANO_CORRENTE): linhas[ANO_CORRENTE]}
    var = {"23→24 hist.": (2023, 2024), "23→24 part.": (D.PARTIDA, 2024), "24→25": (2024, 2025),
           f"25→{ANO_CORRENTE % 100}": (2025, ANO_CORRENTE)}
    var = {k: linhas[b] / linhas[a] - 1 for k, (a, b) in var.items()}
    vazio = lambda s, f: s.map(lambda v: None if pd.isna(v) else f(v))
    df = pd.DataFrame({"Mês": linhas.index, **{k: vazio(s, num).to_numpy() for k, s in partes.items()},
                       **{k: vazio(s, lambda v: pct(v, 1, sinal=True)).to_numpy() for k, s in var.items()}})
    gt.cabecalho("Os números", "Pessoas contadas em cada mês e no ano",
                 f"Hist.: 2023 com histórico. Part.: 2023 como ponto de partida. Os dois jeitos de tratar 2023 dão os mesmos números de 2024 em diante. "
                 f"Novembro, dezembro e o total de {ANO_CORRENTE} são estimativa")
    gt.tabela(df, total=lambda l: l["Mês"] not in ROTULOS)
    baixar_excel(pd.DataFrame({"mes": linhas.index, **{k: s.to_numpy() for k, s in (partes | var).items()}}),
                 "contagem_mensal_sest_4_especialidades.xlsx", "xls_mensal")


def _comparacao(d: dict) -> None:
    """Uma tabela só: conta atual (primeiro estudo, CPFs distintos no ano) e contagem de 12 meses, 2025 × 2026, com o ano completo."""
    atual = D.primeiro_estudo()[[2025, ANO_CORRENTE]]
    doze = pd.concat([d["meses"], d["corte"].to_frame().T, d["ano"].to_frame().T])[[2025, ANO_CORRENTE]].set_axis(atual.index)
    nomes = [*ROTULOS, PERIODO, f"Ano completo ({ANO_CORRENTE} est.)"]
    df, pcts = pd.DataFrame({"Mês": nomes}), set()
    for rotulo, x in (("Atual", atual), ("12 meses", doze)):
        for a in x.columns:
            df[f"{rotulo} {a}"] = x[a].round(0).to_numpy()
        df[f"Var. {rotulo.lower()}"] = (x[ANO_CORRENTE] / x[2025] - 1).to_numpy()
        pcts.add(f"Var. {rotulo.lower()}")
    tela = df.copy()
    for c in df.columns[1:]:
        f = (lambda v: pct(v, 1, sinal=True)) if c in pcts else num
        tela[c] = [None if pd.isna(v) else f(v) for v in df[c]]
    ult = df.iloc[-1]
    gt.cabecalho("As duas contas", f"No ano completo, a conta atual cresce {pct(ult['Var. atual'], 1)} e a de 12 meses, {pct(ult['Var. 12 meses'], 1)}",
                 "Atual: primeiro estudo, CPFs distintos de janeiro a dezembro, no mês do 1º atendimento do ano. 12 meses: a regra desta aba. "
                 f"Novembro, dezembro e o total de {ANO_CORRENTE} são estimativa")
    gt.tabela(tela, total=lambda l: l["Mês"] not in ROTULOS)
    baixar_planilha(df, pcts, "Atual x 12 meses", "sest_4_especialidades_atual_x_12_meses.xlsx", "xls_duas_contas")


def render(f) -> None:
    if f.entidade != "SEST":
        with gt.cartao("mes_senat"):
            gt.cabecalho("Mês a mês", "A contagem de 12 meses vale só para o SEST", "O SENAT segue em CPFs distintos no ano até a decisão das lideranças")
            st.markdown("Escolha **SEST** na barra lateral para ver os números.")
        return
    d = D.mensal()
    with gt.cartao("mes_regra"):
        gt.cabecalho("Nacional", "Quantas pessoas contam em cada mês pela regra de 12 meses",
                     f"SEST · 4 especialidades · soma de {num(d['unidades'])} unidades com meta · o seletor de contagem e os filtros de unidade e de cenário não mudam esta aba")
        st.markdown("A pessoa conta na **1ª vez na unidade** ou quando volta **12 meses ou mais** depois do último atendimento nela, pela data exata. "
                    "O ano de 2023 aparece de duas formas:\n"
                    "- **Com histórico:** considera os atendimentos desde outubro de 2018.\n"
                    "- **Como ponto de partida:** ignora tudo antes de 2023, e todos os atendidos em 2023 contam como 1ª vez.")
    topo = float(d["ano"].max())
    for col, v in zip(st.columns(2, gap="medium"), VERSOES):
        with col, gt.cartao(f"mes_total_{'h' if v == 2023 else 'p'}"):
            _anual(d, v, topo)
    for v in VERSOES:
        with gt.cartao(f"mes_barras_{'h' if v == 2023 else 'p'}"):
            _mensal(d, v)
    with gt.cartao("mes_contas"):
        _comparacao(d)
    with gt.cartao("mes_tabela"):
        _tabela(d)
    nota("O Carnaval foi em março em 2025 e em fevereiro em 2026. Compare os dois meses juntos. Em 2023, "
         f"{d['com_2023']} das {d['unidades']} unidades tinham atendimento nas 4 especialidades. O total de {ANO_CORRENTE} é estimativa: realizado até outubro com projeção para novembro e dezembro, repartida entre os dois meses pelo peso deles em 2023 a 2025. "
         "As metas das propostas não mudam com esta aba.")
