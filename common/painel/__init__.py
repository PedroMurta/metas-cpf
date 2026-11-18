"""Pacote visual compartilhado dos apps Streamlit (SEST SENAT · GEPLANE · Núcleo de Dados).

Projetos importam daqui em vez de copiar o template:

    from common import painel as gt                      # cartões, KPIs e gráficos ECharts (vidro)
    from common.painel.casca import aplicar_tema, cabecalho, rodape
    from common.painel.classico import tema_plotly, fmt_pct   # visual clássico e formatos pt-BR (notebooks)

Classes CSS próprias sempre com prefixo `streamlit-` (vidro: `streamlit-vidro-`) para não colidir em produção.
Imports preguiçosos: common.painel.classico funciona em notebooks sem carregar o streamlit_echarts.
"""
from importlib import import_module

_ORIGEM = {
    **dict.fromkeys("anel medidor radar rosca velocimetro".split(), "circulares"),
    **dict.fromkeys("achado aplicar_css cabecalho cartao divisao ficha frase indicador_empresas kpis selo_meta "
                    "tabela titulo_caixa valores_meta vazio".split(), "componentes"),
    **dict.fromkeys("barras_agrupadas barras_divergentes barras_h barras_proporcao colunas desvio dispersao empilhado "
                    "faixa_linha faixa_ranking linha_meta mapa_calor piramide pontos pontos_ranking ranking saldo "
                    "serie_temporal".split(), "graficos"),
    **dict.fromkeys("bolhas cenario matriz rastro".split(), "plano"),
    **dict.fromkeys("AZUL CIANO NAVY TEMA br escala_execucao grafico mistura rgba situacao_alvo situacao_maior "
                    "situacao_menor".split(), "tema"),
}
__all__ = list(_ORIGEM)


def __getattr__(nome: str):
    if nome not in _ORIGEM:
        raise AttributeError(f"common.painel não tem '{nome}'")
    valor = getattr(import_module(f".{_ORIGEM[nome]}", __name__), nome)
    globals()[nome] = valor
    return valor
