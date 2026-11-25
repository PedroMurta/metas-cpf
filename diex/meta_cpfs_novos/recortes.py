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
GRUPOS, MASCARAS, PRODUCAO, RECORTES, CONTAGEM, CONTAGEM_MES, PUBLICO = (DADOS / f"{n}.parquet" for n in (
    "grupos", "mascaras", "producao", "recortes", "contagem", "contagem_mensal", "publico"))
CORTE = 10            # último mês fechado do ano corrente
ANO_CORRENTE = 2026
COMBINADA = "SEST + SENAT"   # pessoa conta uma vez na unidade, seja atendida no SEST ou no SENAT
ENTIDADES = ("SEST", "SENAT", COMBINADA)
PUBLICOS = ("Transporte", "Comunidade")     # Transporte inclui os dependentes
AREAS_SEST = ["Odontologia", "Fisioterapia", "Psicologia", "Nutrição"]
SENAT_FORA = {"Palestras", "Educação de Jovens e Adultos"}   # fora das especialidades filtradas do SENAT (como no meta_cpfs)
CAMPANHA = "Campanha · "     # prefixo dos tipos de campanha (SEST)
SEP = " · "                  # grupo SENAT = "<tipo de curso> · <modalidade>"; na COMBINADA, "<entidade> · <grupo>"


def sql(consulta: str, params: dict | None = None) -> pd.DataFrame:
    """Consulta numa conexão própria: a conexão padrão do módulo é uma só e recusa chamadas simultâneas (várias pessoas no painel)."""
    with duckdb.connect() as con:
        return con.execute(consulta, params).df() if params else con.execute(consulta).df()


def grupos(entidade: str | None = None) -> pd.DataFrame:
    filtro = f"WHERE entidade = '{entidade}'" if entidade else ""
    return sql(f"SELECT entidade, grupo, ordem, bit FROM '{GRUPOS}' {filtro} ORDER BY entidade, ordem")


def bits(entidade: str, selecao: list[str] | None = None) -> int:
    g = grupos(entidade)
    if selecao is not None:
        faltam = set(selecao) - set(g.grupo)
        assert not faltam, f"grupos inexistentes em {entidade}: {faltam}"
        g = g[g.grupo.isin(selecao)]
    return int(g.bit.sum())


def selecao(entidade: str, escopo: int) -> list[str]:
    """As duas bases da proposta. Escopo 1: SEST nas 4 áreas, SENAT presencial sem Palestras e sem EJA. Escopo 2: todas as especialidades
    (SEST sem campanhas). SEST + SENAT: a união das duas."""
    if entidade == COMBINADA:
        return [e + SEP + g for e in ("SEST", "SENAT") for g in selecao(e, escopo)]
    g = grupos(entidade).grupo.tolist()
    if escopo == 2:
        return [x for x in g if not x.startswith(CAMPANHA)]
    if entidade == "SEST":
        return [x for x in g if x in AREAS_SEST]
    return [x for x in g if x.rpartition(SEP)[2] == "Presencial" and x.rpartition(SEP)[0] not in SENAT_FORA]


def recorte(entidade: str, selecao: list[str] | None = None) -> pd.DataFrame:
    """Unidade × ano: pessoas, novos, pessoas_corte, novos_corte no recorte."""
    c = bits(entidade, selecao)
    if not MASCARAS.exists():           # painel publicado: só os recortes prontos, sem as máscaras (preparar.apoio)
        r = sql(f"SELECT * EXCLUDE chave FROM '{RECORTES}' WHERE entidade = '{entidade}' AND chave = {c} ORDER BY id_unidade, ano")
        assert len(r), f"recorte não publicado: {entidade} {selecao}"
        return r
    return sql(f"""
        SELECT id_unidade, entidade, ano,
               coalesce(sum(pessoas) FILTER (WHERE m_ano & {c} <> 0), 0) AS pessoas,
               coalesce(sum(pessoas) FILTER (WHERE m_ano & {c} <> 0 AND m_ant & {c} = 0), 0) AS novos,
               coalesce(sum(pessoas) FILTER (WHERE m_corte & {c} <> 0), 0) AS pessoas_corte,
               coalesce(sum(pessoas) FILTER (WHERE m_corte & {c} <> 0 AND m_ant & {c} = 0), 0) AS novos_corte
        FROM '{MASCARAS}'
        WHERE entidade = '{entidade}' AND m_ano & {c} <> 0
        GROUP BY ALL ORDER BY id_unidade, ano
    """)


def producao(entidade: str, selecao: list[str] | None = None) -> pd.DataFrame:
    """Unidade × ano: atendimentos e horas no ano e até o CORTE, no recorte; meses = meses com produção no ano."""
    filtro = "" if selecao is None else "AND grupo IN (SELECT unnest($sel))"
    return sql(f"""
        SELECT id_unidade, entidade, ano,
               sum(atendimentos) AS atendimentos, sum(horas) AS horas, sum(atend_sem_cpf) AS atend_sem_cpf,
               sum(atendimentos) FILTER (WHERE ate_corte) AS atendimentos_corte,
               sum(horas) FILTER (WHERE ate_corte) AS horas_corte,
               bit_count(bit_or(meses)) AS meses
        FROM '{PRODUCAO}'
        WHERE entidade = $ent {filtro}
        GROUP BY ALL ORDER BY id_unidade, ano
    """, {"ent": entidade, **({"sel": selecao} if selecao is not None else {})})


def novos_area(entidade: str, area: str, selecao: list[str] | None = None) -> pd.DataFrame:
    """Unidade × ano: novos na área (não atendidos nela em t−1) e, entre eles, os novos também para a unidade no
    recorte (não atendidos em nenhum grupo da seleção em t−1). A razão é a conversão de pessoa a mais na área em CPF
    novo da unidade (regra A)."""
    c, a = bits(entidade, selecao), bits(entidade, [area])
    return sql(f"""
        SELECT id_unidade, ano,
               coalesce(sum(pessoas) FILTER (WHERE m_ant & {a} = 0), 0) AS novos_area,
               coalesce(sum(pessoas) FILTER (WHERE m_ant & {c} = 0), 0) AS novos_area_unidade
        FROM '{MASCARAS}'
        WHERE entidade = '{entidade}' AND m_ano & {a} <> 0
        GROUP BY ALL ORDER BY id_unidade, ano
    """)


def contagem(entidade: str, selecao: list[str] | None = None, publico: str | None = None) -> pd.DataFrame:
    """Unidade × ano: pessoas contadas pela regra de 12 meses exatos (contagem.py), no ano e até o CORTE; `publico`: só as dele (publico.py)."""
    filtro = f"AND publico = '{publico}'" if publico else ""
    r = sql(f"""SELECT id_unidade, ano, contagem, contagem_corte FROM '{PUBLICO if publico else CONTAGEM}'
                       WHERE entidade = '{entidade}' AND chave = {bits(entidade, selecao)} {filtro}""")
    assert len(r), f"contagem de 12 meses não preparada: {entidade} {selecao}"
    return r


def contagem_mensal(entidade: str, selecao: list[str], ids) -> pd.DataFrame:
    """Ano × mês: pessoas contadas (12 meses exatos) somando as unidades `ids`: contagem, com o histórico desde 2018, e partida, sem
    nada antes de 2023 (as duas só diferem em 2023)."""
    return sql(f"""
        SELECT ano, mes, sum(contagem)::BIGINT AS contagem, sum(partida)::BIGINT AS partida
        FROM '{CONTAGEM_MES}' WHERE entidade = $e AND chave = $c AND id_unidade IN (SELECT unnest($ids))
        GROUP BY ALL ORDER BY ano, mes
    """, {"e": entidade, "c": bits(entidade, selecao), "ids": [int(i) for i in ids]})
