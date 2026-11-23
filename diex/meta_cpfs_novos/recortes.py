"""Pessoas, CPFs novos e produção para qualquer seleção de grupos (recorte), a partir dos parquets de preparar.py.

    recorte("SEST", ["Odontologia", "Fisioterapia"])   # None = todos os grupos da entidade
    producao("SENAT", ["Presencial", "Híbrido"])

Para a seleção C (bits): pessoa = máscara_t & C ≠ 0; CPF novo = pessoa e máscara_(t−1) & C = 0 (2026-11-19: atendida na
unidade no ano e não atendida nela no ano anterior, dentro do mesmo recorte); *_corte = só meses 1..CORTE.
"""
from pathlib import Path

import duckdb
import pandas as pd

AQUI = Path(__file__).parent
DADOS = AQUI / "dados"
GRUPOS, MASCARAS, PRODUCAO, RECORTES = (DADOS / f"{n}.parquet" for n in ("grupos", "mascaras", "producao", "recortes"))
CORTE = 10            # último mês fechado do ano corrente
ANO_CORRENTE = 2026
COMBINADA = "SEST + SENAT"   # entidade da Proposta 2: pessoa conta uma vez na unidade, seja atendida no SEST ou no SENAT


def grupos(entidade: str | None = None) -> pd.DataFrame:
    filtro = f"WHERE entidade = '{entidade}'" if entidade else ""
    return duckdb.sql(f"SELECT entidade, grupo, ordem, bit FROM '{GRUPOS}' {filtro} ORDER BY entidade, ordem").df()


def bits(entidade: str, selecao: list[str] | None = None) -> int:
    g = grupos(entidade)
    if selecao is not None:
        faltam = set(selecao) - set(g.grupo)
        assert not faltam, f"grupos inexistentes em {entidade}: {faltam}"
        g = g[g.grupo.isin(selecao)]
    return int(g.bit.sum())


def recorte(entidade: str, selecao: list[str] | None = None) -> pd.DataFrame:
    """Unidade × ano: pessoas, novos, pessoas_corte, novos_corte no recorte."""
    c = bits(entidade, selecao)
    if not MASCARAS.exists():           # painel publicado: só os recortes prontos, sem as máscaras (preparar.apoio)
        r = duckdb.sql(f"SELECT * EXCLUDE chave FROM '{RECORTES}' WHERE entidade = '{entidade}' AND chave = {c} ORDER BY id_unidade, ano").df()
        assert len(r), f"recorte não publicado: {entidade} {selecao}"
        return r
    return duckdb.sql(f"""
        SELECT id_unidade, entidade, ano,
               coalesce(sum(pessoas) FILTER (WHERE m_ano & {c} <> 0), 0) AS pessoas,
               coalesce(sum(pessoas) FILTER (WHERE m_ano & {c} <> 0 AND m_ant & {c} = 0), 0) AS novos,
               coalesce(sum(pessoas) FILTER (WHERE m_corte & {c} <> 0), 0) AS pessoas_corte,
               coalesce(sum(pessoas) FILTER (WHERE m_corte & {c} <> 0 AND m_ant & {c} = 0), 0) AS novos_corte
        FROM '{MASCARAS}'
        WHERE entidade = '{entidade}' AND m_ano & {c} <> 0
        GROUP BY ALL ORDER BY id_unidade, ano
    """).df()


def producao(entidade: str, selecao: list[str] | None = None) -> pd.DataFrame:
    """Unidade × ano: atendimentos e horas no ano e até o CORTE, no recorte; meses = meses com produção no ano."""
    filtro = "" if selecao is None else "AND grupo IN (SELECT unnest($sel))"
    return duckdb.execute(f"""
        SELECT id_unidade, entidade, ano,
               sum(atendimentos) AS atendimentos, sum(horas) AS horas, sum(atend_sem_cpf) AS atend_sem_cpf,
               sum(atendimentos) FILTER (WHERE ate_corte) AS atendimentos_corte,
               sum(horas) FILTER (WHERE ate_corte) AS horas_corte,
               bit_count(bit_or(meses)) AS meses
        FROM '{PRODUCAO}'
        WHERE entidade = $ent {filtro}
        GROUP BY ALL ORDER BY id_unidade, ano
    """, {"ent": entidade, **({"sel": selecao} if selecao is not None else {})}).df()


def novos_area(entidade: str, area: str, selecao: list[str] | None = None) -> pd.DataFrame:
    """Unidade × ano: novos na área (não atendidos nela em t−1) e, entre eles, os novos também para a unidade no
    recorte (não atendidos em nenhum grupo da seleção em t−1). A razão é a conversão de pessoa a mais na área em CPF
    novo da unidade (regra A)."""
    c, a = bits(entidade, selecao), bits(entidade, [area])
    return duckdb.sql(f"""
        SELECT id_unidade, ano,
               coalesce(sum(pessoas) FILTER (WHERE m_ant & {a} = 0), 0) AS novos_area,
               coalesce(sum(pessoas) FILTER (WHERE m_ant & {c} = 0), 0) AS novos_area_unidade
        FROM '{MASCARAS}'
        WHERE entidade = '{entidade}' AND m_ano & {a} <> 0
        GROUP BY ALL ORDER BY id_unidade, ano
    """).df()
