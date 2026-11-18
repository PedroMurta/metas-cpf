"""Aba 5 · Metas por unidade: a meta de cada unidade nos três cenários de peso do gap (10%, 15% e 20%), com o conselho da
barra lateral como recorte. Resumo, comparação dos cenários e tabela completa com download em Excel. Sem contagem de
unidades com meta nos textos e sem "caminho 1/2" (pedidos do usuário em 17/11)."""
from io import BytesIO

from common import painel as gt
import modelo as M
import pandas as pd
import streamlit as st
from scripts import dados as D

from abas.comum import COR_META, CONTEXTO, CONTEXTO_CLARO, DESTAQUE, PROJECAO, inicio, mil, nome_cidade, num, pagina, pct

BASE = str(M.ANO_BASE)
PESOS = list(D.pesos().values())
REGRAS = {"fórmula": "Fórmula", "mediana": "Mediana nacional", "própria": "Mediana própria"}
ORDEM = {"Meta (%), da maior para a menor": ("meta", False), "Meta em CPFs, da maior para a menor": ("cpfs", False),
         "Unidade (tipologia e número)": (["ordem_tip", "ordem_num"], True)}


def _onde(f) -> str:
    return "no país" if f.conselho == "Todos" else f"no conselho {nome_cidade(f.conselho)}"


def _cenario() -> int:
    with gt.cartao("mt_cenario", compacto=True):
        c1, c2 = st.columns([2, 3], gap="medium", vertical_alignment="center")
        with c1:
            p = st.segmented_control("Cenário", [f"{p}% do gap" for p in PESOS], default=f"{PESOS[0]}% do gap",
                                     key="mt_cenario") or f"{PESOS[0]}% do gap"
        with c2:
            gt.frase("Acima da referência, a meta é o ritmo da unidade mais uma parte do gap: 10%, 15% ou 20%. Na "
                     "referência ou abaixo, a <b>mediana nacional</b>; fora do cálculo, a <b>mediana do próprio "
                     "crescimento</b>. Essas duas não mudam entre cenários.")
    return int(p.split("%")[0])


def _resultado(p: int) -> None:
    serie, sem, metas = D.resultado_2027()
    anos = list(serie.index)
    rot = [str(a) for a in anos] + [f"{M.ANO_META}\nsem meta"] + [f"{M.ANO_META}\nmeta {k}%" for k in metas]
    vals = list(serie.values) + [sem] + list(metas.values())
    ant = [None] + vals[:len(anos) - 1] + [serie.iloc[-1]] * (1 + len(metas))
    textos = [f"{{v|{mil(v, 0)}}}" if a is None else
              f"{{{'pos' if v >= a else 'neg'}|{pct(v / a - 1, 1, sinal=True)}}}\n{{v|{mil(v, 0)}}}"
              for v, a in zip(vals, ant)]
    cores = [CONTEXTO] * len(anos) + [CONTEXTO_CLARO] + [DESTAQUE if k == p else COR_META for k in metas]
    ruim, _, bom = gt.TEMA["situacao"]
    rico = {"pos": {"color": bom, "fontWeight": 800, "fontSize": 12, "padding": [0, 0, 6, 0]},
            "neg": {"color": ruim, "fontWeight": 800, "fontSize": 12, "padding": [0, 0, 6, 0]},
            "v": {"color": gt.NAVY, "fontWeight": 700, "fontSize": 12}}
    with gt.cartao("mt_resultado"):
        gt.cabecalho(f"Resultado {M.ANO_META}",
                     f"Com a meta de {p}%, estimativa de {mil(metas[p])} CPFs distintos em {M.ANO_META}",
                     f"Soma dos CPFs distintos de cada unidade: não são atendimentos e não é o total do país. "
                     f"Acima de cada coluna, a variação sobre o ano anterior; nas de {M.ANO_META}, sobre "
                     f"{M.ANO_BASE}. {PROJECAO} {M.ANO_META}: estimativas sem meta (cada unidade no próprio ritmo) "
                     f"e com a meta de cada cenário. De {list(serie.index)[0]} a {M.ANO_BASE - 1}, valores da apresentação da meta.")
        gt.grafico(f"mt_resultado_{p}", gt.colunas(rot, [v / 1000 for v in vals], cores, casas=0, textos=textos,
                                                   rico=rico, largura=52), 400)


def _resumo(f, r: pd.DataFrame, p: int) -> None:
    base, meta = r.cpf0.sum(), r[f"meta_pessoas_{p}"].sum()
    with gt.cartao("mt_resumo", compacto=True):
        gt.cabecalho(f"Meta {M.ANO_META} · cenário {p}%", f"{mil(meta)} CPFs distintos em {M.ANO_META}, "
                     f"{pct(meta / base - 1, 1, sinal=True)} sobre {M.ANO_BASE}",
                     f"{inicio(_onde(f))}. Soma dos CPFs distintos de cada unidade: quem foi atendido em duas unidades "
                     "conta nas duas.")
        gt.kpis([(f"CPFs distintos {BASE}", mil(base), "projeção", ""),
                 (f"Meta {M.ANO_META}", mil(meta), f"cenário {p}%", ""),
                 ("CPFs a mais", mil(meta - base), f"sobre {M.ANO_BASE}", ""),
                 ("Meta da unidade do meio", pct(r[f"meta_pessoas_{p}"].div(r.cpf0).sub(1).median(), 1, sinal=True),
                  "metade das unidades acima, metade abaixo", "")])


def _comparacao(r: pd.DataFrame, p: int) -> None:
    base = r.cpf0.sum()
    tab = pd.DataFrame({
        "Cenário": [f"{k}% do gap" for k in PESOS],
        f"Meta {M.ANO_META} (CPFs)": [mil(r[f"meta_pessoas_{k}"].sum()) for k in PESOS],
        f"Sobre {M.ANO_BASE}": [pct(r[f"meta_pessoas_{k}"].sum() / base - 1, 1, sinal=True) for k in PESOS],
        "CPFs a mais": [mil(r[f"meta_pessoas_{k}"].sum() - base) for k in PESOS]})
    _, meio, _ = st.columns([1, 4, 1])
    with meio, gt.cartao("mt_comparacao"):
        gt.cabecalho("Os três cenários", "Quanto maior a parte do gap, maior a meta",
                     "Só a meta das unidades acima da referência muda de um cenário para outro.")
        gt.tabela(tab, destaque=("Cenário", f"{p}% do gap"))


def _excel(t: pd.DataFrame) -> bytes:
    buf = BytesIO()
    t.to_excel(buf, index=False, sheet_name=f"Meta {M.ANO_META}")
    return buf.getvalue()


def _tabela(f, r: pd.DataFrame, p: int) -> None:
    st.subheader("Meta de cada unidade")
    c1, c2, c3 = st.columns([2, 2, 3], gap="small")
    with c1:
        grupo = st.selectbox("Grupo de porte", ["Todos"] + sorted(r.grupo.dropna().unique()), key="mt_grupo")
    with c2:
        regra = st.segmented_control("Meta pela", ["Todas", *REGRAS.values()], default="Todas",
                                     key="mt_regra") or "Todas"
    with c3:
        ordem = st.selectbox("Ordenar por", list(ORDEM), key="mt_ordem")
    t = r if grupo == "Todos" else r[r.grupo == grupo]
    t = t if regra == "Todas" else t[t.regra.map(REGRAS) == regra]
    t = t.assign(meta=t[f"meta_pct_{p}"], cpfs=t[f"meta_pessoas_{p}"])
    col, asc = ORDEM[ordem]
    t = t.sort_values(col, ascending=asc)
    if t.empty:
        gt.vazio("Nenhuma unidade com esses filtros.")
        return
    numeros = pd.DataFrame({
        "Unidade": t.rotulo, "Conselho": t.conselho, "Grupo": t.grupo.fillna("-"), "Meta pela": t.regra.map(REGRAS),
        f"CPFs distintos {M.ANO_BASE} (projeção)": t.cpf0.round(0), "Atendimentos por CPF": t.apc.round(2),
        "Referência do grupo": t.referencia.round(2), "Ritmo (%)": (100 * t.ritmo.where(t.regra == "fórmula")).round(2),
        "Gap (%)": (100 * t.distancia.where(t.regra == "fórmula")).round(2),
        **{f"Meta {k}% do gap (%)": (100 * t[f"meta_pct_{k}"]).round(2) for k in PESOS},
        **{f"Meta {k}% do gap (CPFs)": t[f"meta_pessoas_{k}"].astype(int) for k in PESOS}})
    vis = pd.DataFrame({
        "Unidade": t.cidade.map(nome_cidade), "Grupo": t.grupo.fillna("-"), "Meta pela": t.regra.map(REGRAS),
        "Meta": t.meta.map(lambda v: pct(v, 2, sinal=True)), f"CPFs {M.ANO_META}": t.cpfs.map(num),
        f"CPFs {BASE}": t.cpf0.map(num), "Atend. por CPF": t.apc.map(lambda v: num(v, 2)),
        "Referência": t.referencia.map(lambda v: "-" if pd.isna(v) else num(v, 2)),
        "Ritmo": [pct(v, 2) if g == "fórmula" else "—" for v, g in zip(t.ritmo, t.regra)],
        "Gap": [pct(v, 2) if g == "fórmula" else "—" for v, g in zip(t.distancia, t.regra)]})
    with gt.cartao("mt_tabela"):
        gt.cabecalho(f"Cenário {p}%", f"Meta de CPFs distintos de {M.ANO_META} por unidade",
                     "Fórmula: acima da referência (ritmo mais parte do gap). Mediana nacional "
                     f"({pct(r.mediana_nacional.iloc[0], 2)}): na referência ou abaixo. "
                     "Mediana própria: fora do cálculo (mediana do próprio crescimento). Em "
                     "destaque, a unidade escolhida na barra lateral.")
        gt.tabela(vis, destaque=("Unidade", nome_cidade(f.cidade)) if f.cidade else None, altura=560)
    st.download_button("Baixar em Excel (três cenários)", _excel(numeros),
                       file_name=f"meta_cpfs_distintos_{M.ANO_META}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       icon=":material/download:")


def render(f) -> None:
    pagina("Resultado", "Metas por unidade",
           f"A meta de CPFs distintos de {M.ANO_META} de cada unidade. O conselho da barra lateral recorta a página.")
    r = D.metas_unidades(f.conselho)
    if r.empty:
        gt.vazio("Nenhuma unidade com meta neste conselho.")
        return
    p = _cenario()
    if f.conselho == "Todos":
        _resultado(p)
    _resumo(f, r, p)
    _comparacao(r, p)
    _tabela(f, r, p)
