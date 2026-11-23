"""Propostas de meta 2027: um passo por função, sem I/O de extração (lê só os parquets de dados/ via recortes.py).

Passos: 1 base do recorte → 2 estimativa do ano corrente → 3 universo → 4 regra. Contagem (23/11): SEST em 12 meses exatos,
SENAT em CPFs distintos no ano civil; gap e penetração usam os atendidos no ano nos dois. As três propostas, nas mesmas unidades, partem da estimativa de 2026 e do ESPERADO de 2027 por unidade (o "sem meta" da apresentação):
  1. seleção inicial (SEST: 4 áreas, a meta da apresentação; SENAT: presencial): ritmo + parte do gap (10/15/20%);
  2. todas as especialidades (SEST sem campanhas), com base e esperado próprios: mesma regra, com a referência do grupo de porte
     calculada nas unidades maduras (5 anos em 2023) e aplicada a todas;
  3. fator de mercado: base + delta × (1 + esforço); SEST: delta = crescimento Nacional × base; SENAT: delta = esperado − base.
SENAT nas propostas 1 e 2: também meta em horas-aula (regra_horas).
"""
import duckdb
import numpy as np
import pandas as pd

from recortes import ANO_CORRENTE, COMBINADA, DADOS, contagem, producao, recorte

ANOS_FRACAO = (2023, 2024, 2025)   # anos fechados que dão a fração do ano alcançada até o CORTE
PESO_PROPRIA = 0.5                 # peso da fração da própria unidade na projeção (o resto é a nacional)
IDADE_P1 = (2, ANO_CORRENTE)       # (anos mínimos desde a inauguração, ano em que se conta): quem tem meta
IDADE_MADURA, ANO_MADURA = 5, 2023 # unidades maduras (inauguradas até 2018): referência da Proposta 2 e aba Análise
ANO_META = ANO_CORRENTE + 1
MEDIDAS = {"atendimentos": "Atendimentos", "horas": "Horas"}   # horas só fazem sentido no SENAT
METRICAS = ["pessoas", "novos", "contagem", "producao"]   # contagem: o que a meta conta (SEST: 12 meses exatos; SENAT: = pessoas)
ID_ASSIS = {196: 141}   # o planejamento usa o id 196 (desativado) para Assis/SP; o ativo no SIGOP é 141 (meta_cpfs/gerar.py)
AREAS_META = {"Odontologia", "Fisioterapia", "Psicologia", "Nutrição"}
META_OFICIAL = DADOS.parents[1] / "meta_cpfs" / "dados" / "meta_cpf_2027.parquet"
MENSAL_OFICIAL = META_OFICIAL.with_name("agenda_mensal.parquet")   # primeiro estudo: unidade × mês, pessoa no mês do 1º atendimento do ano


def unidades() -> pd.DataFrame:
    """Atributos atuais das unidades (preparar.apoio: base padrão SIGOP, ativas, sem DEX)."""
    return pd.read_parquet(DADOS / "unidades.parquet").set_index("id_unidade")


# Passo 1 · base do recorte ------------------------------------------------------------------------------------------
def base(entidade: str, selecao: list[str] | None = None, medida: str = "atendimentos", ano: bool = False) -> pd.DataFrame:
    """Unidade × ano: pessoas, novos, contagem e produção (atendimentos ou horas), no ano e até o CORTE. `ano`: visão do ano completo, em
    que a contagem são os CPFs distintos no ano civil também no SEST (no SENAT, sempre)."""
    r = recorte(entidade, selecao)
    p = producao(entidade, selecao)
    p = p.rename(columns={medida: "producao", f"{medida}_corte": "producao_corte"})[
        ["id_unidade", "ano", "producao", "producao_corte"]]
    b = r.merge(p, on=["id_unidade", "ano"], how="outer")
    c = None if ano else contagem(entidade, selecao)
    b = b.merge(c, on=["id_unidade", "ano"], how="left") if c is not None else b.assign(contagem=b.pessoas, contagem_corte=b.pessoas_corte)
    b = b.fillna(0)
    return b.set_index(["id_unidade", "ano"]).sort_index()


# Passo 2 · projeção do ano corrente ---------------------------------------------------------------------------------
def fracoes(b: pd.DataFrame, inauguracao: pd.Series, anos=ANOS_FRACAO) -> pd.DataFrame:
    """Fração do ano alcançada até o CORTE, por unidade e métrica = PESO_PROPRIA × média da própria unidade nos anos
    completos (unidade aberta o ano inteiro, ano > inauguração) + o resto × fração nacional desses mesmos anos
    (soma até o CORTE ÷ soma do ano). Sem ano completo → só a nacional (anos_ref = 0).

    Teste de 19/11 (2025 projetado com 2023–2024 e 2024 com 2023): meio a meio errou menos que só a própria ou só a
    nacional em todos os recortes; campanhas em novembro e dezembro são o que mais erra na unidade."""
    w = b[b.index.get_level_values("ano").isin(anos)]
    ano = w.index.get_level_values("ano")
    inaug = inauguracao.reindex(w.index.get_level_values("id_unidade")).to_numpy()
    completo = pd.Series(ano > inaug, index=w.index)
    f = pd.DataFrame({m: w[f"{m}_corte"] / w[m].where(w[m] > 0) for m in METRICAS})
    nacional = pd.Series({m: w.loc[completo, f"{m}_corte"].sum() / w.loc[completo, m].sum() for m in METRICAS})
    unid = f.index.get_level_values("id_unidade").unique()
    propria = f[completo].groupby(level="id_unidade").mean().reindex(unid)
    media = (PESO_PROPRIA * propria + (1 - PESO_PROPRIA) * nacional).fillna(nacional)
    media["anos_ref"] = completo.groupby(level="id_unidade").sum().reindex(media.index).fillna(0).astype(int)
    return media


def projetar(b: pd.DataFrame, inauguracao: pd.Series, alvo: int = ANO_CORRENTE) -> pd.DataFrame:
    """Ano corrente projetado = acumulado até o CORTE ÷ fração média da unidade; anos fechados ficam como estão."""
    fr = fracoes(b, inauguracao)
    atual = b.xs(alvo, level="ano")
    proj = pd.DataFrame({m: atual[f"{m}_corte"] / fr[m].reindex(atual.index) for m in METRICAS})
    proj["anos_ref"] = fr.anos_ref.reindex(atual.index)
    fechados = b.loc[b.index.get_level_values("ano") < alvo, METRICAS]
    serie = pd.concat([fechados, proj[METRICAS].assign(ano=alvo).set_index("ano", append=True)]).sort_index()
    serie["novos"] = serie.novos.clip(upper=serie.pessoas)
    serie["projetado"] = serie.index.get_level_values("ano") == alvo
    return serie


# Passo 3 · universo -------------------------------------------------------------------------------------------------
def meta_pactuada(entidade: str, ano: int = ANO_META) -> pd.Series:
    """Soma da meta pactuada da entidade no ano (atendimentos + horas: só serve para saber se é positiva)."""
    ents = ["SEST", "SENAT"] if entidade == COMBINADA else [entidade]
    m = pd.read_parquet(DADOS / "meta_pactuada.parquet").query("entidade in @ents and ano == @ano")
    ids = m.id_unidade.astype(int).replace(ID_ASSIS)
    return (m.meta_atendimentos.fillna(0) + m.meta_horas.fillna(0)).groupby(ids).sum()


def universo(serie: pd.DataFrame, u: pd.DataFrame, meta: pd.Series, ano: int = ANO_CORRENTE,
             idade: tuple[int, int] = IDADE_P1) -> pd.DataFrame:
    """Critérios por unidade; `entra` = todos verdadeiros. Unidade inativa ou fora da base SIGOP fica de fora."""
    atual = serie.xs(ano, level="ano").reindex(u.index)
    c = pd.DataFrame({
        "idade": (idade[1] - u.ano_inauguracao).ge(idade[0]),
        "producao": atual.producao.gt(0) & atual.pessoas.gt(0) & atual.novos.gt(0),
        "meta_pactuada": meta.reindex(u.index).gt(0),
    }, index=u.index)
    c["entra"] = c.all(axis=1)
    return c


def calcular(entidade: str, selecao: list[str] | None = None, medida: str = "atendimentos",
             idade: tuple[int, int] = IDADE_P1, ano: bool = False) -> dict:
    """Passos 1–3 para um recorte. Devolve a série (com o ano corrente projetado) e o universo."""
    u = unidades()
    b = base(entidade, selecao, medida, ano)
    b = b[b.index.get_level_values("id_unidade").isin(u.index)]
    serie = projetar(b, u.ano_inauguracao)
    return {"serie": serie, "universo": universo(serie, u, meta_pactuada(entidade), idade=idade), "unidades": u}


# Diagnóstico ---------------------------------------------------------------------------------------------------------
def decompor(serie: pd.DataFrame, ini: int, fim: int) -> pd.DataFrame:
    """Variação dos CPFs novos de `ini` a `fim` em três fatores (log, soma exata):
    novos = produção ÷ (produção por pessoa) × (% de novos)  →  Δln novos = Δln produção − Δln intensidade + Δln renovação.
    Cada fator em % equivalente: exp(componente) − 1."""
    a, b = serie.xs(ini, level="ano"), serie.xs(fim, level="ano")
    ok = a.index.intersection(b.index)
    a, b = a.loc[ok], b.loc[ok]
    a, b = a[(a[METRICAS] > 0).all(axis=1)], b[(b[METRICAS] > 0).all(axis=1)]
    ok = a.index.intersection(b.index)
    a, b = a.loc[ok], b.loc[ok]
    ln = lambda x: np.log(x)
    d = pd.DataFrame({
        "producao": ln(b.producao / a.producao),
        "intensidade": -ln((b.producao / b.pessoas) / (a.producao / a.pessoas)),
        "renovacao": ln((b.novos / b.pessoas) / (a.novos / a.pessoas)),
    })
    d["novos"] = d.sum(axis=1)
    return d


def testar_projecao(entidade: str, selecao: list[str] | None = None, medida: str = "atendimentos",
                    alvo: int = 2025, anos=(2023, 2024)) -> pd.DataFrame:
    """Projeção de um ano já fechado (`alvo`) com o mesmo método e só os `anos` anteriores, comparada ao realizado.
    Unidades do universo abertas antes de `alvo`. Uma linha por métrica: erro Nacional e erro por unidade."""
    r = calcular(entidade, selecao, medida)
    u, b = r["unidades"], base(entidade, selecao, medida)
    uni = r["universo"].index[r["universo"].entra]
    fr = fracoes(b[b.index.get_level_values("id_unidade").isin(u.index)], u.ano_inauguracao, anos)
    at = b.xs(alvo, level="ano")
    at = at[at.index.isin(uni) & (u.ano_inauguracao.reindex(at.index) < alvo)]
    linhas = {}
    for m in METRICAS:
        proj = at[f"{m}_corte"] / fr[m].reindex(at.index)
        e = (proj / at[m] - 1).replace([np.inf, -np.inf], np.nan).dropna()
        linhas[m] = {"nacional": proj.sum() / at[m].sum() - 1, "mediano": e.abs().median(),
                     "ate_5": (e.abs() <= 0.05).mean(), "acima_10": (e.abs() > 0.10).mean(), "unidades": e.size}
    return pd.DataFrame(linhas).T


# Passo 4 · regra do meta_cpfs nos CPFs novos -------------------------------------------------------------------------
# Igual ao meta_cpfs (common.metas.meta), trocando CPFs distintos por CPFs novos: acima da referência, ritmo dos novos
# 2023→2026 + peso × gap ao P25 da produção por pessoa no grupo de porte; na referência ou abaixo, mediana nacional;
# sem histórico completo, mediana dos próprios crescimentos 2024–2026.
JANELA = (2023, 2024, 2025)        # anos fechados exigidos com 12 meses de produção no recorte (histórico completo)
PESOS = (0.10, 0.15, 0.20)         # parte do gap pedida como esforço: cenários, como no meta_cpfs


def historico_completo(entidade: str, selecao: list[str] | None, serie: pd.DataFrame,
                       anos=JANELA) -> pd.Series:
    """Unidade com produção nos 12 meses de cada ano de `anos` no recorte e CPFs novos em todos os anos até o corrente
    (no meta_cpfs: as quatro áreas e 12 meses; aqui o recorte pode ter campanhas esporádicas, então só os 12 meses)."""
    p = producao(entidade, selecao)
    meses = p[p.ano.isin(anos)].pivot_table(index="id_unidade", columns="ano", values="meses").reindex(columns=list(anos))
    doze = meses.eq(12).all(axis=1)
    novos = serie.novos.unstack().reindex(columns=[*anos, ANO_CORRENTE]).gt(0).all(axis=1)
    return (doze.reindex(novos.index, fill_value=False) & novos).rename("com_meta")


def _metas(b: pd.DataFrame, cp: pd.DataFrame) -> pd.DataFrame:
    """Regra do meta_cpfs e cenários sobre `b` (cpf0, pessoas, producao, apc, grupo, referencia, com_meta) e a contagem por ano `cp`."""
    from common import metas as MT
    cp = cp.where(cp > 0)                        # ano sem contagem → crescimento vazio, não infinito
    res = b.join(MT.meta(b[b.com_meta], cp, PESOS[0], JANELA[0], ANO_CORRENTE))
    res["acima"] = res.acima.astype("boolean")
    res = MT.sem_historico(res, cp, ANO_CORRENTE)
    vazio = res.meta_pct.isna()                  # sem histórico e sem crescimentos próprios → mediana nacional
    res.loc[vazio, "meta_pct"] = res.mediana_nacional[vazio]
    res.loc[vazio, "regra"] = "mediana"
    res.loc[vazio, "meta_pessoas"] = np.ceil(res.cpf0[vazio] * (1 + res.meta_pct[vazio]))
    return res.join(MT.cenarios(res, PESOS))


def com_piso(m: pd.DataFrame, g: float | None) -> pd.DataFrame:
    """Crescimento mínimo das Propostas 1 e 2 (SEST, 23/11): nenhuma meta abaixo de base × (1 + delta Nacional). `piso_{k}` marca as
    unidades em que o mínimo vale no cenário de k%. Sem delta positivo (SENAT) não há piso."""
    ks = [round(100 * w) for w in PESOS]
    if g is None or g <= 0:
        return m.assign(**{f"piso_{k}": False for k in ks})
    m, minimo = m.copy(), np.ceil(m.cpf0 * (1 + g))
    for k in ks:
        m[f"piso_{k}"] = m[f"meta_pct_{k}"] < g
        m[f"meta_pessoas_{k}"] = np.maximum(m[f"meta_pessoas_{k}"], minimo)
        m[f"meta_pct_{k}"] = m[f"meta_pct_{k}"].clip(lower=g)
    m["meta_pct"], m["meta_pessoas"] = m[f"meta_pct_{ks[0]}"], m[f"meta_pessoas_{ks[0]}"]
    return m


def regra(entidade: str, selecao: list[str] | None = None, medida: str = "atendimentos", metrica: str = "contagem",
          idade: tuple[int, int] = IDADE_P1, ref_maduras: bool = False, ano: bool = False) -> dict:
    """Meta por unidade do universo, com os cenários de PESOS. Devolve série, universo e o resultado.
    metrica: o que a meta conta. "contagem" = regra de 12 meses exatos no SEST e CPFs distintos no SENAT (23/11); "pessoas" = CPFs
    distintos no ano civil (a regra original). `ano`: visão do ano completo (contagem = CPFs distintos no ano). O gap usa sempre a produção por pessoa atendida no ano.
    ref_maduras: P25 do grupo só com as unidades maduras (vale para todas do grupo; grupo sem madura usa o P25 do grupo)."""
    from common import metas as MT
    r = calcular(entidade, selecao, medida, idade, ano)
    uni = r["universo"].index[r["universo"].entra]
    s = r["serie"][r["serie"].index.get_level_values("id_unidade").isin(uni)]
    atual = s.xs(ANO_CORRENTE, level="ano")
    b = pd.DataFrame({"cpf0": atual[metrica], "pessoas": atual.pessoas, "producao": atual.producao,
                      "apc": atual.producao / atual.pessoas})
    b["grupo"] = MT.grupos_porte(b.producao)
    b["referencia"] = MT.referencia(b.apc, b.grupo)
    b["madura"] = (ANO_MADURA - r["unidades"].ano_inauguracao.reindex(b.index)) >= IDADE_MADURA
    if ref_maduras:
        b["referencia"] = b.grupo.map(b[b.madura].groupby("grupo").apc.quantile(0.25)).fillna(b.referencia)
    b["com_meta"] = historico_completo(entidade, selecao, s).reindex(b.index, fill_value=False)
    res = _metas(b, s[metrica].unstack())
    return {"serie": s, "universo": uni, "unidades": r["unidades"], "metas": res}


def serie_oficial(s: pd.DataFrame, of: pd.DataFrame) -> pd.DataFrame:
    """Série com pessoas e produção de 2026 iguais às da meta oficial (mesma estimativa da apresentação)."""
    s = s.copy()
    ids = s.xs(ANO_CORRENTE, level="ano").index
    for destino, origem in (("pessoas", "cpf0"), ("producao", "at0")):
        s.loc[pd.IndexSlice[:, ANO_CORRENTE], destino] = of[origem].reindex(ids).to_numpy()
    return s


def proposta1(entidade: str, selecao: list[str], medida: str, ano: bool = False) -> dict:
    """Seleção inicial. No SEST com as 4 áreas, grupos, referências, histórico completo e gap são os da meta oficial (pessoas
    atendidas no ano); a contagem que cresce é a de 12 meses exatos ou, com `ano`, a da própria meta oficial."""
    of = oficial(entidade, selecao)
    if of is None:
        return regra(entidade, selecao, medida, ano=ano) | {"oficial": False}
    r = calcular(entidade, selecao, medida, ano=ano)
    uni = r["universo"].index[r["universo"].entra]
    assert set(uni) == set(of.index), "universo difere da meta oficial"
    s = r["serie"][r["serie"].index.get_level_values("id_unidade").isin(uni)]
    s = serie_oficial(s, of)
    if ano:
        s["contagem"] = s.pessoas                # 2026 = estimativa oficial, a da apresentação
    b = of.loc[uni, ["apc", "grupo", "referencia"]].assign(pessoas=of.cpf0, producao=of.at0, com_meta=of.com_meta.astype(bool),
                                                           cpf0=s.contagem.xs(ANO_CORRENTE, level="ano"))
    return {"serie": s, "universo": uni, "unidades": r["unidades"], "metas": _metas(b, s.contagem.unstack()), "oficial": True}


def proposta2(entidade: str, todas: list[str] | None, medida: str, ano: bool = False) -> dict:
    """Mesma regra da Proposta 1 com todas as especialidades (pessoa conta uma vez na unidade, mesmo em várias), base e esperado
    próprios e referência do grupo de porte calculada nas unidades maduras."""
    return regra(entidade, todas, medida, ref_maduras=True, ano=ano) | {"oficial": False}


def regra_horas(entidade: str, selecao: list[str] | None, idade: tuple[int, int]) -> dict:
    """SENAT, meta em horas-aula: horas de 2026 (estimativa) × (1 + ritmo das horas 2023→2026). Sem histórico completo:
    crescimento Nacional das horas nas unidades maduras (decisão de 23/11; a mediana própria passava de +1.000%). O gap (horas por CPF acima do P25 do grupo) pede mais pessoas, não
    mais horas: fica só como informação, e por isso não há cenários."""
    from common import metas as MT
    r = calcular(entidade, selecao, "horas", idade)
    uni = r["universo"].index[r["universo"].entra]
    s = r["serie"][r["serie"].index.get_level_values("id_unidade").isin(uni)]
    h, atual = s.producao.unstack(), s.xs(ANO_CORRENTE, level="ano")
    h = h.where(h > 0)
    m = pd.DataFrame({"cpf0": atual.producao, "pessoas": atual.pessoas, "apc": atual.producao / atual.pessoas})
    m["grupo"] = MT.grupos_porte(m.cpf0)
    m["referencia"] = MT.referencia(m.apc, m.grupo)
    m["distancia"] = ((m.apc - m.referencia) / m.apc).clip(lower=0)
    m["com_meta"] = historico_completo(entidade, selecao, s).reindex(m.index, fill_value=False) & h[JANELA[0]].notna()
    m["ritmo"] = MT.media_geometrica(h[JANELA[0]], m.cpf0, ANO_CORRENTE - JANELA[0]).where(m.com_meta)
    nacional = crescimento_nacional("SENAT", selecao, "horas", "producao")
    m["regra"] = np.where(m.com_meta, "ritmo", "nacional")
    m["meta_pct"] = m.ritmo.fillna(nacional)
    m["meta"] = np.ceil(m.cpf0 * (1 + m.meta_pct))
    return {"serie": s, "universo": uni, "unidades": r["unidades"], "metas": m, "nacional": nacional}


# Análise · unidades maduras ------------------------------------------------------------------------------------------


def maduras(entidade: str, selecao: list[str] | None = None, medida: str = "atendimentos",
            idade: int = IDADE_MADURA, ano_ref: int = ANO_MADURA, ano: bool = False) -> pd.DataFrame:
    """Unidade × ano (2023–2026; 2026 projetado): pessoas, novos e produção das unidades com `idade`+ anos em `ano_ref`
    e anos completos no recorte (12 meses de produção em cada ano fechado de 2023 a 2025). Teste pedido em 19/11:
    crescimento sem o efeito de unidade nova ou de área que abriu no meio do período."""
    r = calcular(entidade, selecao, medida, ano=ano)
    u, s = r["unidades"], r["serie"]
    velhas = u.index[(ano_ref - u.ano_inauguracao) >= idade]
    completas = historico_completo(entidade, selecao, s)
    ids = velhas.intersection(completas.index[completas])
    return s[s.index.get_level_values("id_unidade").isin(ids)][METRICAS + ["projetado"]]


# Proposta 3 · fator de mercado (19/11; refeita em 23/11) --------------------------------------------------------------
# Meta = base + delta × (1 + FE), por unidade. Base = contagem do ano corrente (estimativa); delta = crescimento
# Nacional × base no SEST (23/11; a meta é a maior entre essa conta e o esperado da unidade) e esperado − base no SENAT. Delta negativo não leva esforço: a unidade fica no próprio crescimento. FE pela faixa do fator de mercado
# FM = 0,6 × percentil do mercado (planilha) + 0,4 × percentil da lacuna (1 − penetração; penetração = atendidos no ano ÷ mercado).
MERCADO_COLUNA = {"SEST": "saude", "SENAT": "educacao"}   # Saúde B2C (SEST) e Educação B2B (SENAT; título errado na planilha)
PESO_MERCADO, PESO_LACUNA = 0.6, 0.4
FAIXAS_FM = (0.25, 0.50, 0.75)                             # FM até 0,25 → 5%; até 0,50 → 10%; até 0,75 → 15%; acima → 20%
ESFORCOS = (0.05, 0.10, 0.15, 0.20)
POTENCIAL = ("Baixo", "Moderado", "Alto", "Muito alto")


def mercado() -> pd.DataFrame:
    """Mercado rateado e percentil por unidade (preparar.apoio: bases/fator_de_mercado.xlsx casada pelo código da unidade)."""
    return pd.read_parquet(DADOS / "mercado.parquet").set_index("id_unidade")


def crescimento_nacional(entidade: str, selecao: list[str] | None = None, medida: str = "atendimentos",
                         coluna: str = "pessoas", ano: bool = False) -> float:
    """Crescimento constante Nacional 2023→2026 nas unidades maduras do recorte (aba Análise), em CPFs distintos ou,
    com coluna="producao", em horas/atendimentos."""
    from common.metas import media_geometrica
    t = maduras(entidade, selecao, medida, ano=ano)[coluna].groupby(level="ano").sum()
    return float(media_geometrica(t.iloc[0], t.iloc[-1], t.index[-1] - t.index[0]))


def percentil(v: pd.Series) -> pd.Series:
    """Posição de 0 (menor) a 1 (maior), como o PERCENTIL da planilha de mercado."""
    return (v.rank(method="min") - 1) / (v.count() - 1)


def oficial(entidade: str, selecao: list[str] | None) -> pd.DataFrame | None:
    """Meta oficial de CPFs distintos (diex/meta_cpfs, a da apresentação) quando o recorte é o dela: SEST nas 4 áreas."""
    if entidade != "SEST" or selecao is None or set(selecao) != AREAS_META:
        return None
    return duckdb.sql(f"SELECT * FROM '{META_OFICIAL}'").df().set_index("id_unidade")


def proposta3(entidade: str, p: dict, nacional: float | None = None) -> dict:
    """Fator de mercado sobre a base de `p` (Proposta 1 ou 2), por unidade. Com `nacional` (SEST, 23/11), o delta é o crescimento
    Nacional × base, igual para todas: meta = o maior entre base × (1 + nacional × (1 + FE)) e o esperado da unidade (`no_esperado`). Sem ele
    (SENAT), o delta é o esperado da própria unidade − base, e delta negativo não leva esforço."""
    m1 = p["metas"]
    m = pd.DataFrame({"base": m1.cpf0, "esperado": m1.sem_meta}).astype(float)
    m["delta"] = m.esperado - m.base if nacional is None else m.base * nacional
    m["partida"] = m.base + m.delta                                    # SENAT: o próprio esperado; SEST: base + delta Nacional
    mk, coluna = mercado().reindex(m.index), MERCADO_COLUNA[entidade]
    m["mercado"] = mk[coluna]
    m["pessoas"] = m1.pessoas.astype(float)                            # atendidos no ano: gap e penetração não mudam com a contagem
    m["penetracao"] = m.pessoas / m.mercado.where(m.mercado > 0)
    m["p_mercado"] = mk[f"percentil_{coluna}"]                         # o da planilha, entre as 184 unidades dela
    m["p_lacuna"] = percentil(1 - m.penetracao).fillna(0)             # sem mercado → sem lacuna
    m["fm"] = PESO_MERCADO * m.p_mercado.fillna(0) + PESO_LACUNA * m.p_lacuna
    faixa = np.searchsorted(FAIXAS_FM, m.fm.to_numpy(), side="left")
    m["fe"], m["potencial"] = np.take(ESFORCOS, faixa), np.take(POTENCIAL, faixa)
    m["meta_delta"] = np.ceil(m.partida + m.delta.clip(lower=0) * m.fe)    # = base + delta × (1 + FE)
    m["meta"] = m.meta_delta if nacional is None else np.maximum(m.meta_delta, np.ceil(m.esperado))
    m["no_esperado"] = m.meta > m.meta_delta
    m["meta_pct"] = m.meta / m.base - 1
    return p | {"metas": m, "nacional": nacional}


def resumo_mercado(m: pd.DataFrame) -> dict:
    pct = m.meta_pct
    return {"base": m.base.sum(), "esperado": m.esperado.sum(), "partida": m.partida.sum(), "minimo": pct.min(), "no_esperado": int(m.no_esperado.sum()), "meta_delta": m.meta_delta.sum(), "meta": m.meta.sum(),
            "nacional_pct": m.meta.sum() / m.base.sum() - 1, "p10": pct.quantile(0.10), "p90": pct.quantile(0.90),
            "negativas": int((pct < 0).sum()), "sem_esforco": int((m.delta <= 0).sum())}
