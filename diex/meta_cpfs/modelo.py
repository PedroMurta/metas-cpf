"""Meta de pessoas atendidas (CPFs distintos) por unidade na Agenda SEST: regra recomendada (2026-11-12).

Um passo por função, na ordem de docs/metodologia.md. Funções puras: recebem DataFrames e devolvem DataFrames/Series
indexados por id_unidade; leitura de dados e gravação ficam em gerar.py.

    acima da referência (fórmula):  meta = ritmo + PESO_DISTANCIA × (atend./pessoa − referência) ÷ atend./pessoa
    na referência ou abaixo:        meta = mediana nacional
    sem histórico completo:         meta = mediana dos próprios crescimentos (ano-base−2 … ano-base), como na
                                    apresentação de 17/11 (fica fora do cálculo do ritmo e da mediana; 2026-11-18)
    fora do universo:               sem meta (ex.: inauguradas há menos de 2 anos; como na apresentação; 2026-11-18)
    meta em pessoas                 = ⌈pessoas do ano-base × (1 + meta)⌉        (sem piso e sem teto)
    estimativa sem meta             = ⌈pessoas do ano-base × (1 + ritmo)⌉; sem histórico completo = a própria meta
"""
import numpy as np
import pandas as pd

ANO_BASE, ANO_META = 2026, 2027
CORTE = 10                         # último mês fechado do ano-base (dez = 12 com o ano fechado)
AREAS = ["odontologia", "fisioterapia", "psicologia", "nutricao"]
ANOS_FRACAO = (2023, 2024, 2025)   # anos que dão a fração do ano alcançada até o CORTE (passo 2)
JANELA = (2023, 2024, 2025)        # anos fechados exigidos com as 4 áreas e 12 meses; início do ritmo (passos 6–7)
IDADE_MINIMA = 2                   # anos desde a inauguração, no ano-base, para entrar no universo
GRUPO_MINIMO = 5                   # grupo de Sturges com menos unidades se junta ao vizinho
QUANTIL = 0.25                     # referência do grupo: P25 do atend./pessoa
PESO_DISTANCIA = 0.10              # parte da distância à referência pedida como esforço (regra aprovada)
PESOS_TESTE = (0.10, 0.15, 0.20)   # proposição: cenários de peso só para comparação; a meta oficial usa PESO_DISTANCIA


# Passo 1 · séries mensais -------------------------------------------------------------------------------------------
def preparar_mensal(m: pd.DataFrame, corte: int = CORTE, ano_base: int = ANO_BASE) -> pd.DataFrame:
    """Corta o ano-base no CORTE e soma as quatro áreas em `atendimentos` (se vierem separadas)."""
    m = m[~((m.ano == ano_base) & (m.mes > corte))].copy()
    if "atendimentos" not in m:
        m["atendimentos"] = m[AREAS].sum(axis=1)
    return m.sort_values(["id_unidade", "ano", "mes"]).reset_index(drop=True)


def pessoas_anuais(m: pd.DataFrame) -> pd.DataFrame:
    """Pessoas e atendimentos por unidade × ano (soma das entradas = pessoas distintas no ano)."""
    return m.groupby(["id_unidade", "ano"])[["entradas", "atendimentos"]].sum().rename(columns={"entradas": "cpfs"})


# Passo 2 · projeção do ano-base -------------------------------------------------------------------------------------
def fracoes(m: pd.DataFrame, corte: int = CORTE) -> pd.DataFrame:
    """Por unidade × ano: acumulado até o corte, total, fração do ano alcançada até o corte e se o ano foi completo."""
    total = m.groupby(["id_unidade", "ano"])[["atendimentos", "entradas"]].sum()
    ate = m[m.mes <= corte].groupby(["id_unidade", "ano"])[["atendimentos", "entradas"]].sum()
    meses = m[m.atendimentos > 0].groupby(["id_unidade", "ano"]).mes.nunique()
    f = pd.DataFrame({"cpf_ytd": ate.entradas, "at_ytd": ate.atendimentos,
                      "cpfs": total.entradas, "atendimentos": total.atendimentos})
    f["fc"], f["fa"] = f.cpf_ytd / f.cpfs, f.at_ytd / f.atendimentos
    f["completo"] = meses.reindex(f.index).eq(12)
    return f


def fracao_media(f: pd.DataFrame, anos=ANOS_FRACAO) -> pd.DataFrame:
    """Fração média da unidade só nos `anos` completos; sem nenhum completo, todos os anos (anos_ref = 0)."""
    w = f[f.index.get_level_values("ano").isin(list(anos))]
    ok = w[w.completo]
    todos = w.groupby(level="id_unidade")[["fc", "fa"]].mean()
    media = ok.groupby(level="id_unidade")[["fc", "fa"]].mean().reindex(todos.index).fillna(todos)
    media["anos_ref"] = ok.groupby(level="id_unidade").size().reindex(media.index).fillna(0).astype(int)
    return media


def projetar(f: pd.DataFrame, alvo: int = ANO_BASE, anos=ANOS_FRACAO) -> pd.DataFrame:
    """Total anual de `alvo` = acumulado até o corte ÷ fração média da unidade."""
    atual = f.xs(alvo, level="ano")[["cpf_ytd", "at_ytd"]]
    fr = fracao_media(f, anos).reindex(atual.index)
    return pd.DataFrame({"cpf_ytd": atual.cpf_ytd, "at_ytd": atual.at_ytd, "cpf0": atual.cpf_ytd / fr.fc,
                         "at0": atual.at_ytd / fr.fa, "anos_ref": fr.anos_ref}).dropna(subset=["cpf0"])


# Passo 3 · universo -------------------------------------------------------------------------------------------------
def universo(proj: pd.DataFrame, inauguracao: pd.Series, meta_at: pd.Series, ano_base: int = ANO_BASE) -> pd.DataFrame:
    """Critérios de entrada por unidade projetada; `entra` = todos verdadeiros.

    idade ≥ IDADE_MINIMA no ano-base; produção e pessoas positivas; meta de atendimentos pactuada positiva no ano da
    meta (ela não entra na conta, mas define quem tem meta institucional).
    """
    idade = ano_base - inauguracao.reindex(proj.index)
    c = pd.DataFrame({"idade": idade.ge(IDADE_MINIMA), "producao": proj.at0.gt(0) & proj.cpf0.gt(0),
                      "meta_atendimentos": meta_at.reindex(proj.index).gt(0)})
    c["entra"] = c.all(axis=1)
    return c


# Passo 4 · grupos de porte ------------------------------------------------------------------------------------------
def grupos_sturges(producao: pd.Series) -> pd.Series:
    """k = round(1 + log2 n) faixas de mesma largura entre a menor e a maior produção."""
    v = producao[producao > 0].dropna()
    k = int(round(1 + np.log2(v.size)))
    return (pd.cut(v, bins=k, labels=False) + 1).astype(int).rename("faixa")


def grupos_porte(producao: pd.Series, minimo: int = GRUPO_MINIMO) -> pd.Series:
    """Faixas de Sturges; a menor faixa com menos de `minimo` unidades se junta ao vizinho com menos unidades."""
    faixa = grupos_sturges(producao)
    blocos = [[g] for g in sorted(faixa.unique())]
    contar = lambda bloco: int(faixa.isin(bloco).sum())
    while len(blocos) > 1 and min(map(contar, blocos)) < minimo:
        i = min(range(len(blocos)), key=lambda j: contar(blocos[j]))
        j = min((v for v in (i - 1, i + 1) if 0 <= v < len(blocos)), key=lambda v: contar(blocos[v]))
        a, b = sorted((i, j))
        blocos[a:b + 1] = [blocos[a] + blocos[b]]
    rotulo = {g: f"G{b[0]}" if len(b) == 1 else f"G{b[0]}–G{b[-1]}" for b in blocos for g in b}
    return faixa.map(rotulo).rename("grupo")


# Passo 5 · referência do grupo --------------------------------------------------------------------------------------
def referencia(apc: pd.Series, grupo: pd.Series, quantil: float = QUANTIL) -> pd.Series:
    """P25 (interpolação linear) do atend./pessoa das unidades do grupo, repetido em cada unidade."""
    return apc.groupby(grupo).transform(lambda s: s.quantile(quantil)).rename("referencia")


# Passo 6 · unidades com meta ----------------------------------------------------------------------------------------
def quatro_areas(m: pd.DataFrame, anos=JANELA, ano_base: int = ANO_BASE) -> pd.Series:
    """True para a unidade com as quatro áreas e os 12 meses em cada ano de `anos` e as quatro áreas no ano-base.

    `m` mensal (já cortado no CORTE) com uma coluna por área. Abertura de área ou ano parcial inflaria o ritmo.
    """
    a = m.groupby(["id_unidade", "ano"])[AREAS].sum().gt(0).all(axis=1)
    meses = m[m.atendimentos > 0].groupby(["id_unidade", "ano"]).mes.nunique().eq(12)
    hist = (a & meses.reindex(a.index, fill_value=False)).unstack().reindex(columns=list(anos)).eq(True).all(axis=1)
    base = a.unstack().get(ano_base, pd.Series(dtype=bool)).reindex(hist.index).eq(True)
    return (hist & base).rename("com_meta")


# Passos 7–9 · ritmo, distância, mediana nacional e meta --------------------------------------------------------------
def media_geometrica(inicial, final, anos):
    """Taxa anual constante que leva de `inicial` a `final` em `anos`: (final ÷ inicial)^(1/anos) − 1."""
    return (final / inicial) ** (1 / anos) - 1


def crescimentos(cp: pd.DataFrame, ini: int = JANELA[0], ano_base: int = ANO_BASE) -> pd.DataFrame:
    """Crescimento de pessoas de cada ano (ini+1 … ano-base) sobre o anterior."""
    return pd.DataFrame({a: cp[a] / cp[a - 1] - 1 for a in range(ini + 1, ano_base + 1)})


def meta(base: pd.DataFrame, cp: pd.DataFrame, peso: float = PESO_DISTANCIA,
         ini: int = JANELA[0], ano_base: int = ANO_BASE) -> pd.DataFrame:
    """Meta de cada unidade com meta.

    `base`: cpf0, apc, referencia (só unidades com meta); `cp`: pessoas por unidade × ano, com o ano-base projetado.
    """
    cp = cp.reindex(base.index)
    cres = crescimentos(cp, ini, ano_base)
    acima = base.apc > base.referencia
    ritmo = media_geometrica(cp[ini], base.cpf0, ano_base - ini)
    distancia = np.maximum((base.apc - base.referencia) / base.apc, 0)
    propria = cres.median(axis=1)                       # mediana dos três crescimentos da unidade
    mediana_nacional = propria[~acima].median()             # mediana entre as unidades na referência ou abaixo
    esforco = peso * distancia
    pct = ritmo.where(acima, mediana_nacional) + esforco
    pessoas = np.ceil(base.cpf0 * (1 + pct))
    return pd.concat([cres.add_prefix("cresc_"), pd.DataFrame({
        "acima": acima, "ritmo": ritmo, "distancia": distancia, "esforco": esforco, "mediana_propria": propria,
        "mediana_nacional": mediana_nacional, "meta_pct": pct, "meta_pessoas": pessoas,
        "crescimento": pessoas / base.cpf0 - 1, "ritmo_normal": np.ceil(base.cpf0 * (1 + ritmo))})], axis=1)


# Proposição · cenários de peso --------------------------------------------------------------------------------------
def cenarios(r: pd.DataFrame, pesos=PESOS_TESTE) -> pd.DataFrame:
    """Meta (%) e meta em pessoas com outros pesos da distância, sobre o resultado de `meta`.

    Só o esforço de quem usa a fórmula muda; ritmo, distância e mediana nacional são os mesmos. Colunas
    `meta_pct_{p}` e `meta_pessoas_{p}` (p em %, ex.: 15); `meta_pessoas` usa PESO_DISTANCIA.
    """
    c = r[r.meta_pct.notna()]
    formula = c.regra.eq("fórmula")
    base = c.ritmo.where(formula, c.meta_pct)     # mediana nacional ou própria: igual em todos os cenários
    out = {}
    for p in pesos:
        pct = base + p * c.distancia.where(formula, 0)
        out[f"meta_pct_{round(100 * p)}"] = pct
        out[f"meta_pessoas_{round(100 * p)}"] = np.ceil(c.cpf0 * (1 + pct))
    return pd.DataFrame(out).reindex(r.index)


def resumo_cenarios(r: pd.DataFrame, pesos=PESOS_TESTE) -> pd.DataFrame:
    """Uma linha por peso: total nacional e distribuição das metas (todas as unidades com meta); a diferença para o
    próprio ritmo só nas unidades com histórico completo (as demais não têm ritmo)."""
    c = r[r.meta_pct.notna()]
    acima = c.regra.eq("fórmula")
    h = c.com_meta
    linhas = {}
    for p in pesos:
        k = round(100 * p)
        pct, pessoas = c[f"meta_pct_{k}"], c[f"meta_pessoas_{k}"]
        linhas[f"{k}%"] = {
            "meta_pessoas": pessoas.sum(), "nacional": pessoas.sum() / c.cpf0.sum() - 1,
            "sobre_ritmo": pessoas[h].sum() - c.ritmo_normal[h].sum(),
            "sobre_ritmo_pct": pessoas[h].sum() / c.ritmo_normal[h].sum() - 1,
            "unidade_do_meio": pessoas.div(c.cpf0).sub(1).median(), "maior": pct.max(),
            "esforco_tipico_pp": (p * c.distancia[acima]).median(),
            "acima_com_meta_menor_que_mediana": int((pct[acima] < c.mediana_nacional[acima]).sum()),
        }
    return pd.DataFrame(linhas).T


# Encadeamento -------------------------------------------------------------------------------------------------------
def calcular(mensal: pd.DataFrame, inauguracao: pd.Series, meta_at: pd.Series) -> pd.DataFrame:
    """Todos os passos. Uma linha por unidade do universo; as de fora do universo não recebem meta."""
    m = preparar_mensal(mensal)
    proj = projetar(fracoes(m))
    crit = universo(proj, inauguracao, meta_at)
    u = proj[crit.entra].copy()
    u["apc"] = u.at0 / u.cpf0
    u["grupo"] = grupos_porte(u.at0)
    u["referencia"] = referencia(u.apc, u.grupo)
    u["com_meta"] = quatro_areas(m).reindex(u.index, fill_value=False)
    u["meta_at"] = meta_at.reindex(u.index)
    cp = pessoas_anuais(m).cpfs.unstack()
    cp[ANO_BASE] = proj.cpf0
    r = u.join(meta(u[u.com_meta], cp))
    r["acima"] = r.acima.astype("boolean")   # vazio para quem não tem histórico completo
    r["universo"] = True                     # coluna mantida para o painel; hoje todas as linhas são do universo
    r = sem_historico(r, cp)
    return r.join(cenarios(r))


def sem_historico(r: pd.DataFrame, cp: pd.DataFrame, ano_base: int = ANO_BASE) -> pd.DataFrame:
    """Unidades do universo sem histórico completo (com_meta = False) recebem a mediana dos próprios crescimentos de
    ano-base−2 a ano-base (`mediana_propria`), como na apresentação. `regra` diz de onde vem a meta: "fórmula"
    (acima da referência), "mediana" (nacional: na referência ou abaixo) ou "própria" (sem histórico completo).
    `sem_meta`: estimativa sem meta (ritmo próprio; para quem não tem ritmo, a própria meta)."""
    r = r.copy()
    r["com_meta"] = r.com_meta.astype(bool)
    sem = ~r.com_meta
    cres = crescimentos(cp.reindex(r.index[sem]), ano_base - 3, ano_base)
    for a in cres:
        r.loc[sem, f"cresc_{a}"] = cres[a]
    propria = cres.median(axis=1)
    r["mediana_nacional"] = r.mediana_nacional.dropna().iloc[0]
    r.loc[sem, "mediana_propria"] = propria
    r.loc[sem, "meta_pct"] = propria
    r.loc[sem, "meta_pessoas"] = np.ceil(r.cpf0[sem] * (1 + propria))
    r.loc[sem, "crescimento"] = r.meta_pessoas[sem] / r.cpf0[sem] - 1
    r["sem_meta"] = r.ritmo_normal.where(r.com_meta, r.meta_pessoas)
    r["regra"] = np.select([r.com_meta & r.acima.fillna(False).astype(bool), r.com_meta], ["fórmula", "mediana"],
                           "própria")
    return r
