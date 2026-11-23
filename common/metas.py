"""Peças comuns às metas por unidade (diex/meta_cpfs, diex/meta_cpfs_novos): grupos de porte, referência do grupo e a
regra do meta_cpfs (ritmo + peso × distância ao P25; na referência ou abaixo, mediana nacional; sem histórico
completo, mediana dos próprios crescimentos)."""
import numpy as np
import pandas as pd

GRUPO_MINIMO = 5   # grupo de Sturges com menos unidades se junta ao vizinho


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


def referencia(valor: pd.Series, grupo: pd.Series, quantil: float = 0.25) -> pd.Series:
    """Quantil (interpolação linear) de `valor` nas unidades do grupo, repetido em cada unidade."""
    return valor.groupby(grupo).transform(lambda s: s.quantile(quantil)).rename("referencia")


def media_geometrica(inicial, final, anos):
    """Taxa anual constante que leva de `inicial` a `final` em `anos`: (final ÷ inicial)^(1/anos) − 1."""
    return (final / inicial) ** (1 / anos) - 1


# Regra do meta_cpfs (2026-11-12), movida para cá em 2026-11-19 para valer também nos CPFs novos -----------------
def crescimentos(cp: pd.DataFrame, ini: int, ano_base: int) -> pd.DataFrame:
    """Crescimento de pessoas de cada ano (ini+1 … ano-base) sobre o anterior."""
    return pd.DataFrame({a: cp[a] / cp[a - 1] - 1 for a in range(ini + 1, ano_base + 1)})


def meta(base: pd.DataFrame, cp: pd.DataFrame, peso: float, ini: int, ano_base: int) -> pd.DataFrame:
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


def sem_historico(r: pd.DataFrame, cp: pd.DataFrame, ano_base: int) -> pd.DataFrame:
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


def cenarios(r: pd.DataFrame, pesos) -> pd.DataFrame:
    """Meta (%) e meta em pessoas com outros pesos da distância, sobre o resultado de `meta`.

    Só o esforço de quem usa a fórmula muda; ritmo, distância e mediana nacional são os mesmos. Colunas
    `meta_pct_{p}` e `meta_pessoas_{p}` (p em %, ex.: 15); 
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
