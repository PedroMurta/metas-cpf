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
    juntos = " Quem é atendido no SEST e no SENAT da mesma unidade contará uma vez." if f.entidade == COMBINADA else ""
    return ("CPFs novos: a pessoa contará na 1ª vez na unidade ou quando voltar depois de 12 meses ou mais." if f.doze else
            "CPFs distintos: cada pessoa contará uma vez por unidade e por ano, de janeiro a dezembro.") + juntos


# O que entra em cada base da proposta (entidade → escopo).
ENTRA = {"SEST": {1: "Odontologia, nutrição, psicologia e fisioterapia", 2: "Todos os serviços que têm inscrição"},
         "SENAT": {1: "Cursos presenciais, exceto palestras e EJA", 2: "Todos os cursos, com ensino a distância e palestras"},
         COMBINADA: {1: "As 4 especialidades do SEST e os cursos presenciais do SENAT, exceto palestras e EJA", 2: "Todos os serviços que têm inscrição e todos os cursos"}}


def entra(entidade: str, escopo: int) -> str:
    """O que entra no cenário, para o meio da frase (só a primeira letra minúscula)."""
    t = ENTRA[entidade][escopo]
    return t[0].lower() + t[1:]


def num(v, casas: int = 0) -> str:
    return gt.br(v, casas)


def pct(v, casas: int = 1, sinal: bool = False) -> str:
    return gt.br(v * 100, casas, sinal=sinal, sufixo="%")


def nota_media(marca: str = "¹") -> str:
    """Nota de rodapé: a média é geométrica, e por quê."""
    return (f"{marca} Média geométrica: o crescimento constante que, repetido todo ano, leva do número de 2023 ao de 2026. Usamos a geométrica porque cada ano cresce sobre o "
            "resultado do ano anterior; com a média simples das variações anuais, a conta não chegaria ao mesmo número de 2026.")


def mil(v) -> str:
    """Número curto: 1.258.800 → "1,26 milhão"; 623.100 → "623,1 mil"; abaixo de 10 mil, por extenso."""
    if abs(v) >= 999_950:            # daqui para cima "mil" arredondaria para 1.000,0
        return f"{gt.br(v / 1e6, 2)} {'milhão' if abs(v) < 2e6 else 'milhões'}"
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
