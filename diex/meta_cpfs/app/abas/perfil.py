"""Aba 3 · Perfil dos clientes atendidos: painel interativo (público, sexo, idade, frequência, evolução e empresas).

Filtros da própria aba (público, sexo, faixa etária) cruzam todos os gráficos, sobre unidade, especialidade e ano da
barra lateral. 2026 = projetado: contagens escaladas ao total projetado (D.perfil_projetado), exceto a faixa de
frequência, que só vai até o último ano fechado.
"""
from common import painel as gt
import modelo as M
import numpy as np
import pandas as pd
import streamlit as st
from scripts import dados as D

from abas.comum import (CORES_FREQ, CORES_IDADE, CORES_INSTRUCAO, CORES_PUBLICO, CORES_SEXO,
                        DADOS_ATE, FRASE_PUBLICO, PROJECAO, SEST, mil, num, pagina, pct, recorte, titulo_nivel)

FECHADO = M.ANO_BASE - 1
TOP_EMPRESAS = 15
FORA_RANKING = ("Sem empresa no cadastro",)
MIN_CELULA = 20      # pessoas mínimas para mostrar atend./pessoa numa célula ou categoria
SEXOS = ["Feminino", "Masculino", "Não informado"]
DIMENSOES = {"Público": ("publico", D.PUBLICOS, CORES_PUBLICO), "Sexo": ("sexo", SEXOS, CORES_SEXO),
             "Faixa etária": ("faixa_etaria", D.FAIXAS_IDADE, CORES_IDADE),
             "Frequência": ("faixa_freq", D.FAIXAS_FREQ, CORES_FREQ)}
MEDIDAS = ["Pessoas", "% das pessoas", "Atendimentos por pessoa"]


def _quem(campo: str, valor: str) -> str:
    """Categoria em texto corrido para os achados: "Mulheres", "Pessoas de 18 a 29 anos", "Quem teve 1 atendimento"."""
    if campo == "publico":
        return FRASE_PUBLICO[valor]
    if valor == "Não informado":
        return {"sexo": "Pessoas sem sexo informado", "faixa_etaria": "Pessoas sem idade informada"}[campo]
    if campo == "sexo":
        return "Mulheres" if valor == "Feminino" else "Homens"
    if campo == "faixa_etaria":
        return f"Pessoas {_anos(valor)}"
    return f"Quem teve {valor} atendimento{'' if valor == '1' else 's'}"


def _anos(faixa: str) -> str:
    """"30 a 39" → "de 30 a 39 anos"; "60 ou mais" → "com 60 anos ou mais"."""
    return "com 60 anos ou mais" if faixa == "60 ou mais" else f"de {faixa} anos"


def _escolha(chave: str, opcoes: list[str]) -> str:
    """Valor atual de um seletor antes de desenhá-lo (o achado do cabeçalho vem antes do controle)."""
    v = st.session_state.get(chave)
    return v if v in opcoes else opcoes[0]


def _ano(a: int) -> str:
    return str(a)


def _filtros(p: pd.DataFrame) -> dict[str, list]:
    """Barra de filtros da aba: cada grupo de pílulas filtra todos os gráficos abaixo. Devolve {campo: seleção}."""
    sel = {}
    with gt.cartao("perfil_filtros", compacto=True):
        c1, c2, c3 = st.columns([5, 3, 6], gap="medium")
        grupos = [(c1, "Público", "publico", [x for x in D.PUBLICOS if x in set(p.publico)]),
                  (c2, "Sexo", "sexo", [x for x in SEXOS if x in set(p.sexo)]),
                  (c3, "Faixa etária", "faixa_etaria", [x for x in D.FAIXAS_IDADE if x in set(p.faixa_etaria)])]
        for col, rotulo, campo, opcoes in grupos:
            with col:
                sel[campo] = st.pills(rotulo, opcoes, selection_mode="multi", default=opcoes,
                                      key=f"pf_{campo}") or opcoes
    return sel


def _aplicar(df: pd.DataFrame, sel: dict[str, list]) -> pd.DataFrame:
    for campo, valores in sel.items():
        df = df[df[campo].isin(valores)]
    return df


def _kpis(p: pd.DataFrame, ano: int) -> None:
    a, ant = p[p.ano == ano], p[p.ano == ano - 1]
    pes, at = a.pessoas.sum(), a.atendimentos.sum()

    def var(atual, antes):
        if not antes:
            return "", ""
        v = atual / antes - 1
        return f"{'▲' if v >= 0 else '▼'} {pct(abs(v))} sobre {_ano(ano - 1)}", "pos" if v >= 0 else "neg"

    pub = a.groupby("publico").pessoas.sum()
    with gt.cartao("perfil_kpis", compacto=True):
        gt.kpis([(f"Pessoas · {_ano(ano)}", num(pes), *var(pes, ant.pessoas.sum())),
                 ("Atendimentos", num(at), *var(at, ant.atendimentos.sum())),
                 ("Atendimentos por pessoa", num(at / pes, 2) if pes else "—", "média no ano", ""),
                 ("Transporte", pct(pub.get("Transporte", 0) / pes) if pes else "—", "trabalhadores titulares", "")])


def _composicao(f, p: pd.DataFrame, ano: int) -> None:
    a = p[p.ano == ano]
    total = a.pessoas.sum()
    sexo = a.groupby("sexo").pessoas.sum().reindex(SEXOS).dropna()
    sexo = sexo[sexo / total >= .005]   # fatia invisível (ex.: sexo não informado ~0%) só polui a rosca
    pub = a.groupby("publico").pessoas.sum().reindex(D.PUBLICOS).dropna()
    pub = 100 * pub / total
    pub = pub[pub >= .1]   # categoria com menos de 0,1% (ex.: múltiplos perfis) não aparece
    ano_freq = min(ano, FECHADO)
    fr = p[p.ano == ano_freq].groupby("faixa_freq").pessoas.sum().reindex(D.FAIXAS_FREQ).fillna(0)
    c1, c2, c3 = st.columns([4, 5, 5], gap="small")
    fem = sexo.get("Feminino", 0) / total
    with c1, gt.cartao("perfil_sexo"):
        gt.cabecalho("Sexo", f"Mulheres são {pct(fem)} das pessoas", f"{recorte(f, _ano(ano))}.")
        gt.grafico(f"pf_sexo_{f.nivel}_{f.esp}_{ano}", gt.rosca(sexo.index.tolist(), sexo.tolist(),
                   [CORES_SEXO[s] for s in sexo.index], mil(total), "pessoas", "pessoas"), 260)
    with c2, gt.cartao("perfil_pub"):
        maior = pub.idxmax()
        gt.cabecalho("Público", f"{FRASE_PUBLICO[maior]} são {pct(pub[maior] / 100)} das pessoas",
                     f"{recorte(f, _ano(ano))}. Dependentes são a família dos trabalhadores.")
        gt.grafico(f"pf_pub_{f.nivel}_{f.esp}_{ano}", gt.barras_h(
            pub.index.tolist(), pub.tolist(), [CORES_PUBLICO[k] for k in pub.index], casas=1, sufixo="%"), 260)
    with c3, gt.cartao("perfil_freq"):
        nota = (f" {M.ANO_BASE} ainda não fechou: a frequência só sai com o ano completo."
                if ano > FECHADO else "")
        fr = 100 * fr / fr.sum() if fr.sum() else fr
        gt.cabecalho("Frequência", f"{pct(fr.get('1', 0) / 100)} vieram uma vez só em {ano_freq}",
                     f"{recorte(f, str(ano_freq))}. % das pessoas por número de atendimentos no ano.{nota}")
        if fr.sum():
            gt.grafico(f"pf_freq_{f.nivel}_{f.esp}_{ano_freq}", gt.barras_h(
                [f"{k} atend." for k in fr.index], fr.tolist(), [CORES_FREQ[k] for k in fr.index], casas=1,
                sufixo="%"), 260)


def _idade(f, p: pd.DataFrame, ano: int) -> None:
    a = p[p.ano == ano]
    faixas = [x for x in D.FAIXAS_IDADE if x != "Não informado"]
    total = a.pessoas.sum()
    x = a.pivot_table("pessoas", "faixa_etaria", "sexo", aggfunc="sum").reindex(index=faixas, columns=SEXOS)
    x = x.fillna(0)
    c1, c2 = st.columns([1, 1], gap="small")
    with c1, gt.cartao("perfil_piramide"):
        grupos = (x[["Masculino", "Feminino"]] / (total or 1)).stack()
        faixa, sexo = grupos.idxmax()
        gt.cabecalho("Idade e sexo", f"{_quem('sexo', sexo)} {_anos(faixa)} são o maior grupo: {pct(grupos.max())}",
                     f"{recorte(f, _ano(ano))}. % das pessoas em cada faixa e sexo; idade no ano.")
        if total:
            gt.grafico(f"pf_pir_{f.nivel}_{f.esp}_{ano}", gt.piramide(
                faixas, (100 * x["Masculino"] / total).tolist(), (100 * x["Feminino"] / total).tolist(),
                ("Masculino", "Feminino"), (CORES_SEXO["Masculino"], CORES_SEXO["Feminino"])), 330)
    with c2, gt.cartao("perfil_apc_idade"):
        g = a[a.faixa_etaria.isin(faixas)].groupby("faixa_etaria")[["pessoas", "atendimentos"]].sum()
        apc = (g.atendimentos / g.pessoas).where(g.pessoas >= MIN_CELULA).reindex(faixas[::-1]).dropna()
        achado = (f"Pessoas {_anos(apc.idxmax())} voltam mais: {num(apc.max(), 1)} atendimentos por pessoa"
                  if len(apc) else "Sem pessoas suficientes por faixa etária")
        gt.cabecalho("Idade e frequência", achado,
                     f"{recorte(f, _ano(ano))}. Atendimentos ÷ pessoas de cada faixa; faixa com menos de {MIN_CELULA} "
                     "pessoas não aparece. Use os filtros de público e sexo no topo para comparar grupos.")
        if len(apc):
            gt.grafico(f"pf_apc_idade_{f.nivel}_{f.esp}_{ano}", gt.barras_h(
                apc.index.tolist(), apc.tolist(), [CORES_IDADE[k] for k in apc.index], casas=1), 330)


def _cadastro(f, c: pd.DataFrame, ano: int) -> None:
    """Grau de instrução (18 anos ou mais)."""
    adultos = [x for x in D.FAIXAS_IDADE if x not in ("0 a 11", "12 a 17", "Não informado")]
    a = c[(c.ano == ano) & c.faixa_etaria.isin(adultos)]
    inst = a.groupby("instrucao").pessoas.sum().reindex(D.INSTRUCAO).fillna(0)
    with gt.cartao("perfil_instrucao"):
        if not inst.sum():
            gt.cabecalho("Escolaridade", "Sem pessoas de 18 anos ou mais neste recorte", f"{recorte(f, _ano(ano))}.")
        else:
            parte = inst / inst.sum()
            sem = parte["Não informado"]
            info = inst.drop("Não informado")
            maior = info.idxmax()
            gt.cabecalho("Escolaridade", f"{maior} é o grau mais comum: {pct(info[maior] / info.sum())} de quem "
                         "informou", f"{recorte(f, _ano(ano))}. Pessoas de 18 anos ou mais; {pct(sem)} sem grau de "
                         "instrução no cadastro (barra cinza). Mestrado e doutorado entram em pós-graduação.")
            gt.grafico(f"pf_inst_{f.nivel}_{f.esp}_{ano}", gt.barras_h(
                inst.index.tolist(), (100 * parte).tolist(), [CORES_INSTRUCAO[k] for k in inst.index], casas=1,
                sufixo="%"), 330)


def _evolucao(f, p: pd.DataFrame) -> None:
    dim, med = _escolha("pf_dim", list(DIMENSOES)), _escolha("pf_med", MEDIDAS)
    campo, ordem, cores = DIMENSOES[dim]
    anos = [a for a in D.ANOS if a <= FECHADO] if campo == "faixa_freq" else D.ANOS
    g = p[p.ano.isin(anos)].groupby(["ano", campo])[["pessoas", "atendimentos"]].sum()
    pes = g.pessoas.unstack().reindex(index=anos, columns=[c for c in ordem if c in set(p[campo])]).fillna(0)
    pes = pes.loc[:, pes.sum() > 0]
    apc = (g.atendimentos.unstack().reindex(index=anos, columns=pes.columns) / pes).where(pes >= MIN_CELULA)
    parte = pes.div(pes.sum(axis=1).replace(0, np.nan), axis=0)
    pv = parte.dropna(how="all")                          # só anos com atendimento (unidade nova começa depois)
    a0, a1 = _ano(pv.index[0] if len(pv) else anos[0]), _ano(anos[-1])
    if len(pv) < 2:
        achado = "Ainda não há anos suficientes para comparar"
    elif med == "Atendimentos por pessoa":
        ini_, fim_ = apc.bfill().iloc[0], apc.ffill().iloc[-1]
        dif = (fim_ - ini_).abs().dropna()
        c = dif.idxmax() if len(dif) else None
        achado = (f"{_quem(campo, c)}: de {num(ini_[c], 2)} para {num(fim_[c], 2)} atendimentos por pessoa "
                  f"entre {a0} e {a1}") if c is not None else "Ainda não há anos suficientes para comparar"
    else:
        c = (pv.iloc[-1] - pv.iloc[0]).abs().idxmax()
        achado = f"{_quem(campo, c)} passaram de {pct(pv[c].iloc[0])} para {pct(pv[c].iloc[-1])} das pessoas"
    with gt.cartao("perfil_evol"):
        gt.cabecalho("Evolução", achado,
                     f"{recorte(f)}, {a0} a {a1}. {PROJECAO[:-1]}, com a mesma composição dos "
                     f"meses já fechados; a frequência só vai até {FECHADO}, porque {M.ANO_BASE} ainda não fechou. Clique na "
                     "legenda para ligar ou desligar categorias.")
        c1, c2 = st.columns([1, 1], gap="medium")
        with c1:
            st.segmented_control("Ver por", list(DIMENSOES), default="Público", key="pf_dim")
        with c2:
            st.segmented_control("Medida", MEDIDAS, default="Pessoas", key="pf_med")
        rot = [_ano(a) for a in anos]
        chave = f"pf_evol_{f.nivel}_{f.esp}_{dim}_{med}"
        if med == "Atendimentos por pessoa":
            series = [{"nome": c, "valores": apc[c].tolist(), "cor": cores[c]} for c in apc.columns]
            gt.grafico(chave, gt.serie_temporal(rot, series, casas=2), 340)
            return
        pc = med.startswith("%")
        val = 100 * parte if pc else pes
        series = [(c, val[c].tolist(), cores[c]) for c in val.columns]
        gt.grafico(chave, gt.empilhado(rot, series, casas=1 if pc else 0, sufixo="%" if pc else ""), 340)


def _empresas(f, ano: int) -> None:
    e = D.empresas(f.nivel, ano, f.esp).astype({"pessoas": float, "atendimentos": float})
    if e.empty:
        return
    nota = ""
    if ano == M.ANO_BASE:   # mesmo fator da projeção do total; a lista e a ordem não mudam
        bruto = D.perfil(f.nivel, f.esp).query("ano == @ano")
        proj = D.perfil_projetado(f.nivel, f.esp).query("ano == @ano")
        e["pessoas"] *= proj.pessoas.sum() / bruto.pessoas.sum()
        e["atendimentos"] *= proj.atendimentos.sum() / bruto.atendimentos.sum()
        nota = f" {PROJECAO[:-1]}; a lista de empresas é a dos meses já fechados."
    titulares = e.pessoas.sum()
    sem = e[e.empresa.isin(FORA_RANKING)].pessoas.sum()
    demais = e[e.empresa.str.startswith("Demais empresas")]
    nomeadas = e[~e.empresa.isin(FORA_RANKING) & ~e.empresa.str.startswith("Demais empresas")]
    top = nomeadas.head(TOP_EMPRESAS)
    minimo = 5
    parte_top = top.pessoas.sum() / (titulares - sem) if titulares > sem else None
    with gt.cartao("empresas_kpis", compacto=True):
        gt.kpis([("Titulares com empresa", pct(1 - sem / titulares), "no cadastro", ""),
                 (f"Empresas com {minimo}+ pessoas", num(len(nomeadas)), _ano(ano), ""),
                 ("Demais empresas", num(demais.empresas.sum()), f"com até {minimo - 1} pessoas cada", ""),
                 (f"{len(top)} maiores", pct(parte_top) if parte_top is not None else "—",
                  "dos titulares com empresa", "")])
    if top.empty:
        gt.vazio(f"Nenhuma empresa com {minimo} ou mais pessoas atendidas.")
        return
    with gt.cartao("empresas"):
        medida = st.segmented_control("Ver", ["Pessoas atendidas", "Atendimentos por pessoa"],
                                      default="Pessoas atendidas", key="pf_empresas_medida") or "Pessoas atendidas"
        detalhe = (f"{recorte(f, _ano(ano))}. Titulares (trabalhadores, sem os dependentes); empresa do cadastro atual "
                   f"(nome fantasia ou razão social). Empresas com menos de {minimo} pessoas ficam em \"Demais "
                   f"empresas\".{nota}")
        nomes, chave, altura = top.empresa.str.title().tolist(), f"empresas_{f.nivel}_{f.esp}_{ano}", 36 + 26 * len(top)
        if medida == "Pessoas atendidas":
            gt.cabecalho("Empresas", f"As {len(top)} maiores empresas somam {pct(parte_top or 0)} dos titulares com "
                         "empresa", detalhe)
            gt.grafico(chave, gt.barras_h(nomes, top.pessoas.round(0).tolist(), SEST, casas=0), altura)
        else:
            media = e.atendimentos.sum() / titulares
            apc = top.atendimentos / top.pessoas
            gt.cabecalho("Empresas", f"Cada titular teve, em média, {num(media, 2)} atendimentos",
                         f"Atendimentos da empresa ÷ pessoas atendidas da empresa, para as mesmas empresas do ranking "
                         f"de pessoas. Linha tracejada: média de todos os titulares. {detalhe}")
            gt.grafico(f"{chave}_apc", gt.barras_h(
                nomes, apc.tolist(), SEST, casas=2, referencia=round(media, 2), ref_texto=f"média {num(media, 2)}",
                maximo=max(apc.max(), media) * 1.18), altura)
        with st.expander("Ver a lista completa"):
            t = pd.concat([nomeadas, demais, e[e.empresa.isin(FORA_RANKING)]])
            gt.tabela(pd.DataFrame({"Empresa": t.empresa.str.title(), "Pessoas": [num(v) for v in t.pessoas],
                                    "Atendimentos": [num(v) for v in t.atendimentos],
                                    "Atend. por pessoa": [num(a / b, 2) for a, b in zip(t.atendimentos, t.pessoas)]}),
                      altura=420)


def render(f) -> None:
    pagina("Quem é atendido", f"Perfil dos clientes atendidos · {titulo_nivel(f)}",
           f"Agenda SEST, {_ano(f.ano)}. Idade, escolaridade e empresa vêm do cadastro atual da pessoa. "
           f"{PROJECAO} Nenhum CPF ou CNPJ aparece no painel.")
    p = D.perfil_projetado(f.nivel, f.esp)
    if p[p.ano == f.ano].empty:
        gt.vazio(f"Sem atendimentos em {_ano(f.ano)} para este recorte.")
        return
    sel = _filtros(p)
    p, c = _aplicar(p, sel), _aplicar(D.cadastro_projetado(f.nivel, f.esp), sel)
    if p[p.ano == f.ano].empty:
        gt.vazio("Nenhuma pessoa com essa combinação de filtros.")
        return
    _kpis(p, f.ano)
    _composicao(f, p, f.ano)
    _idade(f, p, f.ano)
    _cadastro(f, c, f.ano)
    _evolucao(f, p)
    st.subheader("Empresas dos trabalhadores atendidos")
    _empresas(f, f.ano)
