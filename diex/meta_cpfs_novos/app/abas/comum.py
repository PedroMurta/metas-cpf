"""Peças comuns das abas: formatos pt-BR e cores do estudo (assunto SEST verde, SENAT laranja, os dois juntos azul)."""
import io

import streamlit as st

from common import painel as gt
from common.painel.classico import ASSUNTOS, CONTEXTO, FORTE
from recortes import ANO_CORRENTE

CINZA = CONTEXTO


def assunto(entidade: str) -> str:
    """SEST verde, SENAT laranja, SEST + SENAT institucional azul."""
    return {"SEST": "sest", "SENAT": "senat"}.get(entidade, "institucional")


def cor(entidade: str) -> str:
    return ASSUNTOS[assunto(entidade)]


def contados(f) -> str:
    """Nome do que a meta conta na visão escolhida: contagem de 12 meses exatos (SEST) ou CPFs distintos no ano completo."""
    return "CPFs contados" if f.doze else "CPFs distintos"


def regra_contagem(f) -> str:
    return ("CPFs contados: a pessoa conta na 1ª vez na unidade ou quando volta depois de 12 meses ou mais." if f.doze else
            "CPFs distintos: cada pessoa conta uma vez por unidade e por ano, de janeiro a dezembro.")


def num(v, casas: int = 0) -> str:
    return gt.br(v, casas)


def pct(v, casas: int = 1, sinal: bool = False) -> str:
    return gt.br(v * 100, casas, sinal=sinal, sufixo="%")


def mil(v) -> str:
    """Número curto: 1.258.800 → "1,26 M"; 623.100 → "623,1 mil"; abaixo de 10 mil, por extenso."""
    if abs(v) >= 999_950:            # daqui para cima "mil" arredondaria para 1.000,0
        return f"{gt.br(v / 1e6, 2)} M"
    return f"{gt.br(v / 1e3, 1)} mil" if abs(v) >= 1e4 else gt.br(v, 0)


def lx(v, casas: int = 0) -> str:
    """Número pt-BR para LaTeX (vírgula decimal sem espaço)."""
    return gt.br(v, casas).replace(",", "{,}")


def rotulos_anos(anos) -> list[str]:
    """Anos do eixo; o ano corrente sempre marcado como estimativa."""
    return [f"{a}\nestimativa" if a == ANO_CORRENTE else str(a) for a in anos]


def conta(linhas: list[tuple[str, str]]) -> None:
    """Conta passo a passo (rótulo → valor)."""
    st.html("<div class='streamlit-conta'>" + "".join(f"<div><span>{a}</span><b>{b}</b></div>" for a, b in linhas)
            + "</div>")


def baixar_planilha(df, pcts: set, aba: str, nome: str, chave: str) -> None:
    """Excel formatado com uma tabela só: cabeçalho navy, números com milhar e as colunas `pcts` em %."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = aba
    for j, c in enumerate(df.columns, 1):
        h = ws.cell(1, j, c)
        h.font, h.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor=FORTE.lstrip("#"))
        h.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(j)].width = 34 if j == 1 else 17
    for i, linha in enumerate(df.itertuples(index=False), 2):
        for j, v in enumerate(linha, 1):
            cel = ws.cell(i, j, None if isinstance(v, float) and v != v else v)
            if j > 1:
                cel.number_format = "+0.0%;-0.0%;0.0%" if df.columns[j - 1] in pcts else "#,##0"
    ws.freeze_panes = "B2"
    buf = io.BytesIO()
    wb.save(buf)
    st.download_button("Baixar Excel", buf.getvalue(), file_name=nome, key=chave,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def baixar_excel(df, nome: str, chave: str) -> None:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    st.download_button("Baixar Excel", buf.getvalue(), file_name=nome, key=chave,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
