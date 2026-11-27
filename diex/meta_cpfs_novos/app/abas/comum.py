"""Peças comuns das abas: formatos pt-BR e cores do estudo (assunto SEST verde, SENAT laranja, os dois juntos azul)."""
import io

import streamlit as st

from common import painel as gt
from common.painel.classico import ASSUNTOS, CONTEXTO
from recortes import ANO_CORRENTE, COMBINADA
from scripts import dados as D

CINZA = CONTEXTO


def assunto(entidade: str) -> str:
    """SEST verde, SENAT laranja, SEST + SENAT institucional azul."""
    return {"SEST": "sest", "SENAT": "senat"}.get(entidade, "institucional")


def cor(entidade: str) -> str:
    return ASSUNTOS[assunto(entidade)]


def contados(f, meio: bool = False) -> str:
    """Nome do que a meta conta na visão escolhida: contagem de 12 meses exatos ou CPFs distintos no ano civil (`meio`: no meio da frase)."""
    return (("novos CPFs" if meio else "Novos CPFs") if f.doze else "CPFs distintos")


TODOS_PUBLICOS = "Todos os públicos"


def do_publico(f) -> str:
    """Público do filtro, para o rótulo dos gráficos e tabelas que mudam com ele (os outros usam TODOS_PUBLICOS)."""
    return {None: TODOS_PUBLICOS, "Transporte": "Transporte (com dependentes)"}.get(f.publico, f.publico)


def regra_contagem(f) -> str:
    juntos = " Quem é atendido no SEST e no SENAT da mesma unidade contará uma vez." if f.entidade == COMBINADA else ""
    return ("Novos CPFs: a pessoa contará na 1ª vez na unidade ou quando voltar depois de 12 meses ou mais." if f.doze else
            "CPFs distintos: cada pessoa contará uma vez por unidade e por ano, de janeiro a dezembro.") + juntos


def publico_nota(f) -> str:
    """Como o público é definido (só com o filtro ligado), para as notas de rodapé."""
    return "" if not f.publico else ("Público: a classe do cliente no dia em que foi contado, como está no SIGOP; o dependente segue o titular, e os empregados do SEST SENAT entram no transporte. "
                                     + ("No cenário B, as turmas do SEST usam o cadastro atual. " if f.entidade != "SENAT" else ""))


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


def grade(colunas: list[str], linhas: list[list[str]], destaque: int | None = None) -> None:
    """Tabela com linhas e colunas marcadas e texto que quebra; `destaque` = linha em negrito."""
    corpo = "".join(f"<tr{' class=streamlit-grade-forte' if k == destaque else ''}>" + "".join(f"<td>{v}</td>" for v in l) + "</tr>" for k, l in enumerate(linhas))
    st.html(f"<div class='streamlit-grade'><table><thead><tr>{''.join(f'<th>{c}</th>' for c in colunas)}</tr></thead><tbody>{corpo}</tbody></table></div>")


def cenarios_aviso(entidade: str) -> None:
    if "EJA" in ENTRA[entidade][1]:
        st.caption("EJA: Educação de Jovens e Adultos.")


def baixar_excel(df, nome: str, chave: str) -> None:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    st.download_button("Baixar Excel", buf.getvalue(), file_name=nome, key=chave,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def cenario(f, prefixo: str, rotulo: str = "Cenário") -> int:
    """Seletor de cenário da aba (as duas bases da proposta) com o quadro do que entra em cada um. Abas Análise e Perfil dos CPFs."""
    rotulos = D.ESCOPO[f.entidade]
    escopo = st.pills(rotulo, list(rotulos), default=1, key=f"{prefixo}_esc_{f.entidade}", format_func=rotulos.get) or 1
    with gt.cartao(f"{prefixo}_cenarios"):
        gt.cabecalho(f"{D.nome(f.entidade)} · {do_publico(f)} · cenário escolhido", f"{rotulos[escopo]}: {entra(f.entidade, escopo)}",
                     "Use o seletor acima para trocar de cenário e a barra lateral para trocar de público. Toda a aba muda junto.")
        grade(["Cenário", "O que entra"], [[nome, ENTRA[f.entidade][n]] for n, nome in rotulos.items()], list(rotulos).index(escopo))
        cenarios_aviso(f.entidade)
    return escopo
