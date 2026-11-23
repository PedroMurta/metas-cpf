"""Peças comuns das abas: formatos pt-BR e cores do estudo (assunto SEST verde, SENAT laranja, os dois juntos azul)."""
import io

import streamlit as st

from common import painel as gt
from common.painel.classico import ASSUNTOS, CONTEXTO
from recortes import ANO_CORRENTE

CINZA = CONTEXTO


def assunto(entidade: str) -> str:
    """SEST verde, SENAT laranja, SEST + SENAT institucional azul."""
    return {"SEST": "sest", "SENAT": "senat"}.get(entidade, "institucional")


def cor(entidade: str) -> str:
    return ASSUNTOS[assunto(entidade)]


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


def baixar_excel(df, nome: str, chave: str) -> None:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    st.download_button("Baixar Excel", buf.getvalue(), file_name=nome, key=chave,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
