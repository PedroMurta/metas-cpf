"""Aba 1 · Conceitos e motivação: termos, recorte das quatro especialidades, concentração e evolução até 2026."""
from common import painel as gt
import modelo as M
import numpy as np
import streamlit as st
from scripts import dados as D

from abas.comum import (COR_META, COR_PESSOAS, COR_PRODUCAO, CONTEXTO, CONTEXTO_CLARO, DESTAQUE, MESES, PROJECAO, num,
                        pagina, pct, recorte)

FECHADO = M.ANO_BASE - 1
BASE = str(M.ANO_BASE)
TERMOS = [
    ("CPF distinto",
     "Cada pessoa conta uma vez por ano em cada unidade",
     ["Atendida 10 vezes no ano na mesma unidade: conta <b>1</b>.",
      "Atendida em Brasília e depois em Luziânia: conta <b>1 em Brasília e 1 em Luziânia</b>.",
      "No total nacional, a mesma pessoa conta uma vez só."]),
    ("Atendimento",
     "Cada consulta ou sessão realizada na Agenda SEST",
     ["Uma pessoa pode ter vários atendimentos no mesmo ano.",
      "A meta de produção da unidade é medida em atendimentos."]),
    ("Atendimentos por CPF",
     "Atendimentos ÷ CPFs distintos, na mesma unidade e no mesmo ano",
     ["Mostra quantas vezes, em média, cada pessoa foi atendida.",
      "1.000 atendimentos para 200 pessoas = <b>5 atendimentos por CPF</b>."]),
]


def _rotulo(a: int) -> str:
    return BASE if a == M.ANO_BASE else str(a)


def _variou(v: float, verbo: bool = True) -> str:
    """"subiu 84%" / "caiu 5%" (verbo=False omite o verbo repetido: "63%")."""
    texto = pct(abs(v), 0)
    return f"{'subiu' if v >= 0 else 'caiu'} {texto}" if verbo or v < 0 else texto


def _termos() -> None:
    st.subheader("Os termos")
    for col, (termo, definicao, exemplos) in zip(st.columns(3, gap="small"), TERMOS):
        with col, gt.cartao(f"termo_{termo}", compacto=True):
            gt.cabecalho("", termo, "")
            gt.frase(f"{definicao}.<ul class='lista'>{''.join(f'<li>{e}</li>' for e in exemplos)}</ul>")


def _quatro_especialidades() -> None:
    with gt.cartao("quatro_esp"):
        gt.cabecalho("", "Agenda SEST", "")
        gt.frase("Entram só <b>odontologia, fisioterapia, nutrição e psicologia</b>: são as principais áreas de "
                 "atendimento do SEST e existem em todas as unidades.")


def _motivacao() -> None:
    st.markdown("Hoje cada unidade tem uma meta de **atendimentos**. A proposta acrescenta uma meta de **CPFs "
                "distintos** (pessoas atendidas) nas quatro áreas da Agenda SEST: odontologia, fisioterapia, nutrição "
                "e psicologia. A ideia é que os atendimentos já combinados cheguem a mais gente. A meta de "
                "atendimentos continua a mesma.")


def _concentracao(f) -> None:
    st.subheader("1. Atendimentos concentrados em poucos CPFs")
    p = D.perfil(f.nivel, f.esp)
    anos = [a for a in D.ANOS if a <= FECHADO and (p.ano == a).any()]
    if not anos:
        gt.vazio("Sem atendimentos nos anos completos para este recorte.")
        return
    ano = st.segmented_control("Ano", anos, default=anos[-1], key="conc_ano") or anos[-1]
    serie = {a: p[(p.ano == a) & p.top10].atendimentos.sum() / p[p.ano == a].atendimentos.sum() for a in anos}
    a = p[p.ano == ano]
    top = a[a.top10]
    parte, pes_top = serie[ano], top.pessoas.sum() / a.pessoas.sum()
    area = "quatro áreas da Agenda SEST" if f.esp == D.TODAS else f.esp.lower()
    conta = "no país" if f.nivel == D.NACIONAL else "na unidade"
    c1, c2 = st.columns([2, 3], gap="large", vertical_alignment="center")
    with c1:
        st.markdown(f"Em {ano}, **10% das pessoas atendidas são responsáveis por {pct(parte, 2)} dos atendimentos** "
                    f"({num(top.pessoas.sum())} pessoas receberam {num(top.atendimentos.sum())} de "
                    f"{num(a.atendimentos.sum())} atendimentos).")
        st.markdown("Parte dos atendimentos que ficou com esses 10%, ano a ano: " + " · ".join(f"{x}: {pct(v, 2)}" for x, v in serie.items()) + ".")
    with c2, gt.cartao("concentracao"):
        gt.cabecalho("", f"10% das pessoas são responsáveis por {pct(parte, 2)} dos atendimentos",
                     f"{ano} · {area} · cada pessoa conta uma vez {conta}")
        gt.grafico(f"conc_{f.nivel}_{f.esp}_{ano}", gt.barras_proporcao(
            ["Pessoas distintas", "Atendimentos"],
            [("10% mais atendidas", [100 * pes_top, 100 * parte], DESTAQUE),
             ("Demais", [100 * (1 - pes_top), 100 * (1 - parte)], CONTEXTO_CLARO)], casas=2, rotulo=0), 260)


def _como_ler_crescimento() -> None:
    with gt.cartao("ler_crescimento", compacto=True):
        gt.frase("<b>Crescimentos se acumulam.</b> Subir 10% em um ano e mais 10% no outro dá 21% nos dois anos, "
                 "porque o segundo aumento é calculado sobre um número que já cresceu.")


def _crescimento(f) -> None:
    a, mp = D.anual(f.nivel, f.esp), D.meta_producao(f.nivel, f.esp)
    validos = a.cpfs.dropna()
    if validos.empty or np.isnan(a.cpfs.get(FECHADO, np.nan)):
        gt.vazio("Sem série suficiente para mostrar o crescimento.")
        return
    ini, fim = int(validos.index[0]), FECHADO          # só anos completos: a motivação não depende da projeção
    anos = [x for x in D.ANOS if ini <= x <= fim]
    base_meta = mp.get(ini, np.nan)
    idx = lambda s, b: [None if (v is None or np.isnan(v) or not b) else round(100 * v / b, 2) for v in s]  # noqa: E731
    prod = idx([a.atendimentos.get(x, np.nan) for x in anos], a.atendimentos[ini])
    cpf = idx([a.cpfs.get(x, np.nan) for x in anos], a.cpfs[ini])
    meta = idx([mp.get(x, np.nan) for x in anos], base_meta)
    cp, pr = a.cpfs[fim] / a.cpfs[ini] - 1, a.atendimentos[fim] / a.atendimentos[ini] - 1
    mt = mp.get(fim, np.nan) / base_meta - 1 if base_meta else np.nan
    texto_meta = f"a meta de produção {_variou(mt)}, " if not np.isnan(mt) else ""
    piso = 10 * int(min(v for v in meta + prod + cpf if v is not None) // 10) - 10   # eixo perto das linhas
    with gt.cartao("crescimento_ind"):
        gt.cabecalho("Meta, produção e CPFs distintos",
                     f"De {ini} a {fim}, {texto_meta}a produção {_variou(pr)} e os CPFs distintos, {_variou(cp, False)}",
                     f"{recorte(f)}. Em % do volume de {ini} ({ini} = 100%). Só anos completos.")
        gt.grafico(f"crescimento_{f.nivel}_{f.esp}", gt.serie_temporal([_rotulo(x) for x in anos], [
            {"nome": "Meta de atendimentos", "valores": meta, "cor": CONTEXTO_CLARO, "traco": "dashed",
             "simbolo": "emptyCircle"},
            {"nome": "Atendimentos realizados", "valores": prod, "cor": CONTEXTO, "simbolo": "emptyCircle"},
            {"nome": "CPFs distintos", "valores": cpf, "cor": DESTAQUE, "destaque": True, "area": False,
             "simbolo": "emptyCircle"},
        ], casas=2, sufixo="%", y_min=piso), 360)


def _atendimentos_por_cpf(f) -> None:
    apc = D.anual(f.nivel, f.esp).apc
    validos = apc.dropna()
    if validos.empty or np.isnan(apc[M.ANO_BASE]):
        return
    ini, fim = int(validos.index[0]), M.ANO_BASE
    with gt.cartao("apc_evolucao"):
        gt.cabecalho("Atendimentos por CPF",
                     f"Atendimentos por CPF: {num(apc[ini], 2)} ({ini}) → {num(apc[FECHADO], 2)} ({FECHADO}) → "
                     f"{num(apc[fim], 2)} ({M.ANO_BASE}, projeção)",
                     f"{recorte(f)}. Atendimentos ÷ CPFs distintos no ano. {PROJECAO[:-1]} (a mesma base usada "
                     "na meta).")
        anos = [x for x in D.ANOS if x >= ini]
        gt.grafico(f"apc_{f.nivel}_{f.esp}", gt.colunas(
            [_rotulo(x) for x in anos], [apc[x] for x in anos],
            [DESTAQUE if x == fim else CONTEXTO_CLARO for x in anos], casas=2), 300)


def render(f) -> None:
    pagina("Contexto", "Conceitos e motivação",
           "O que cada termo quer dizer e por que a meta passa a olhar para pessoas, e não só para atendimentos.")
    _termos()
    _quatro_especialidades()
    _motivacao()
    _concentracao(f)
    st.subheader("2. Meta de produção e produção crescem; a quantidade de CPFs distintos, não no mesmo ritmo")
    _como_ler_crescimento()
    _crescimento(f)
    _atendimentos_por_cpf(f)
