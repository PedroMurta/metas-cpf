"""Peças comuns das abas: formatos pt-BR e cores do estudo (assunto SEST verde, SENAT laranja, os dois juntos azul)."""
import io

import streamlit as st

from common import painel as gt
from common.painel.classico import ASSUNTOS, CONTEXTO
from recortes import ANO_CORRENTE, COMBINADA

CINZA = CONTEXTO


def assunto(entidade: str) -> str:
    """SEST verde, SENAT laranja, SEST + SENAT institucional azul."""
    return {"SEST": "sest", "SENAT": "senat"}.get(entidade, "institucional")


def cor(entidade: str) -> str:
    return ASSUNTOS[assunto(entidade)]


def contados(f) -> str:
    """Nome do que a meta conta na visão escolhida: contagem de 12 meses exatos ou CPFs distintos no ano civil."""
    return "CPFs novos" if f.doze else "CPFs distintos"


def regra_contagem(f) -> str:
    juntos = " Quem é atendido no SEST e no SENAT da mesma unidade conta uma vez." if f.entidade == COMBINADA else ""
    return ("CPFs novos: a pessoa conta na 1ª vez na unidade ou quando volta depois de 12 meses ou mais." if f.doze else
            "CPFs distintos: cada pessoa conta uma vez por unidade e por ano, de janeiro a dezembro.") + juntos


# O que entra em cada base da proposta (entidade → escopo).
ENTRA = {"SEST": {1: "Odontologia, fisioterapia, psicologia e nutrição", 2: "Todas as especialidades, sem as campanhas"},
         "SENAT": {1: "Cursos presenciais, sem palestras e sem Educação de Jovens e Adultos", 2: "Todos os cursos e modalidades, com ensino a distância e palestras"},
         COMBINADA: {1: "As 4 especialidades do SEST e os cursos filtrados do SENAT", 2: "Tudo do SEST (sem campanhas) e tudo do SENAT"}}


def num(v, casas: int = 0) -> str:
    return gt.br(v, casas)


def pct(v, casas: int = 1, sinal: bool = False) -> str:
    return gt.br(v * 100, casas, sinal=sinal, sufixo="%")


def esforco_padrao(p: dict) -> str:
    """Esforço padrão = o delta Nacional em módulo; * = a média encontrada é negativa."""
    return pct(p["delta"], 2) + ("*" if p["nacional"] < 0 else "")


NOTA_MODULO = "* A média encontrada é negativa (queda). Ela entra em módulo, isto é, sem o sinal, para estimular a retomada do crescimento."


def nota_media(marca: str = "¹") -> str:
    """Nota de rodapé: a média é geométrica, e por quê."""
    return (f"{marca} Média geométrica: o crescimento constante que, repetido todo ano, leva do número de 2023 ao de 2026. Usamos a geométrica porque cada ano cresce sobre o "
            "resultado do ano anterior; com a média simples das variações anuais, a conta não chegaria ao mesmo número de 2026.")


def mil(v) -> str:
    """Número curto: 1.258.800 → "1,26 M"; 623.100 → "623,1 mil"; abaixo de 10 mil, por extenso."""
    if abs(v) >= 999_950:            # daqui para cima "mil" arredondaria para 1.000,0
        return f"{gt.br(v / 1e6, 2)} M"
    return f"{gt.br(v / 1e3, 1)} mil" if abs(v) >= 1e4 else gt.br(v, 0)


def lx(v, casas: int = 0) -> str:
    """Número pt-BR para LaTeX (vírgula decimal sem espaço)."""
    return gt.br(v, casas).replace(",", "{,}")


def rotulos_anos(anos) -> list[str]:
    """Anos do eixo; o ano corrente sempre marcado como projeção."""
    return [f"{a}\nprojeção" if a == ANO_CORRENTE else str(a) for a in anos]


def conta(linhas: list[tuple[str, str]]) -> None:
    """Conta passo a passo (rótulo → valor)."""
    st.html("<div class='streamlit-conta'>" + "".join(f"<div><span>{a}</span><b>{b}</b></div>" for a, b in linhas)
            + "</div>")


def baixar_excel(df, nome: str, chave: str) -> None:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    st.download_button("Baixar Excel", buf.getvalue(), file_name=nome, key=chave,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
