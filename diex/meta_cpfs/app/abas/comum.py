"""Peças comuns das abas: título de página, formatação pt-BR, cores do estudo e textos a partir dos filtros."""
from html import escape

from common import painel as gt
import modelo as M
import streamlit as st
from scripts import dados as D

# Cores do estudo (storytelling: contexto em cinza, achado em azul/ciano). Nunca hex solto nas páginas.
CONTEXTO, CONTEXTO_CLARO = "#94a3b8", "#cbd5e1"
DESTAQUE, FORTE = gt.AZUL, gt.NAVY
# Linhas de crescimento (aba Conceitos): produção em destaque ciano, meta em azul-claro, pessoas em cinza-escuro.
COR_PRODUCAO, COR_META, COR_PESSOAS = gt.CIANO, "#7cc6e0", "#5a6a7e"
# Painel (aba Perfil): assunto "Saúde e Qualidade de Vida (SEST)" do design system (core/assuntos.md), cor base verde.
# Categorias e faixas em tons da mesma matiz e neutros do tema; nunca paleta multicolorida.
SEST, BRANCO = "#1f8f5f", "#ffffff"


def _tom(t: float) -> str:
    """Tom do verde SEST: t < 0 clareia (rumo ao branco), t > 0 escurece (rumo ao navy)."""
    return gt.mistura(SEST, BRANCO, -t) if t < 0 else gt.mistura(SEST, gt.NAVY, t)


def _escala(cores: list[str], n: int) -> list[str]:
    """n cores interpoladas ao longo de `cores` (do claro ao forte)."""
    out = []
    for i in range(n):
        t = i / max(n - 1, 1) * (len(cores) - 1)
        k = min(int(t), len(cores) - 2)
        out.append(gt.mistura(cores[k], cores[k + 1], t - k))
    return out


ESCALA_SEST = [_tom(-.6), SEST, _tom(.7)]                        # faixas ordenadas: claro → escuro
CORES_PUBLICO = {"Transporte": _tom(.55), "Dependentes": SEST, "Comunidade": _tom(-.5),
                 "Múltiplos perfis": _tom(-.75), "Não informado": CONTEXTO_CLARO}
ROSA = "#cc5a8a"   # feminino: pedido do usuário (exceção à matiz única), rosa suave que conversa com navy e verde
CORES_SEXO = {"Feminino": ROSA, "Masculino": gt.NAVY, "Não informado": CONTEXTO_CLARO}
CORES_IDADE = dict(zip(D.FAIXAS_IDADE[:-1], _escala(ESCALA_SEST, len(D.FAIXAS_IDADE) - 1)))
CORES_IDADE["Não informado"] = CONTEXTO_CLARO
CORES_FREQ = dict(zip(D.FAIXAS_FREQ, _escala(ESCALA_SEST, len(D.FAIXAS_FREQ))))
CORES_INSTRUCAO = dict(zip(D.INSTRUCAO[:-1], _escala(ESCALA_SEST, len(D.INSTRUCAO) - 1)))
CORES_INSTRUCAO["Não informado"] = CONTEXTO_CLARO
CORES_STATUS = {"Retidos": CONTEXTO, "Reativados": CONTEXTO_CLARO, "Novos": gt.AZUL}
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MESES_NOME = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
              "novembro", "dezembro"]
MES_CORTE = MESES_NOME[M.CORTE - 1]
PARCIAL = f"{M.ANO_BASE} até {MESES[M.CORTE - 1]}"
DADOS_ATE = f"com dados até {MES_CORTE}"
_RESTO = " e ".join(", ".join(MESES_NOME[M.CORTE:]).rsplit(", ", 1))
# ano-base sem asterisco (pedido do usuário em 18/11); esta frase diz o que o número do ano-base contém
PROJECAO = (f"{M.ANO_BASE}: realizado até {MES_CORTE} e projeção para {_RESTO}." if _RESTO
            else f"{M.ANO_BASE}: ano completo.")
FRASE_PUBLICO = {"Transporte": "Trabalhadores do transporte", "Dependentes": "Dependentes",
                 "Comunidade": "Pessoas da comunidade", "Múltiplos perfis": "Pessoas com mais de um perfil",
                 "Não informado": "Pessoas sem público informado"}
ROTULO_ANO = {a: str(a) for a in D.ANOS}


def num(v, casas: int = 0) -> str:
    return gt.br(v, casas)


def pct(f, casas: int = 1, sinal: bool = False) -> str:
    return gt.br(100 * f, casas, sinal=sinal, sufixo="%")


def mil(v, casas: int = 1) -> str:
    return gt.br(v / 1e3, casas, sufixo=" mil")


def pagina(secao: str, titulo: str, descricao: str) -> None:
    st.html(f"<div class='streamlit-section-tag'>{escape(secao)}</div>")
    st.header(titulo)
    st.caption(descricao)


def _nome_proprio(texto: str) -> str:
    return " ".join(p.lower() if p.lower() in ("do", "da", "de", "dos", "das", "e") else p for p in texto.title().split())


def nome_cidade(texto: str) -> str:
    """"BRASÍLIA/DF" → "Brasília/DF"; "SÃO PAULO (VILA JAGUARA)/SP" → "São Paulo (Vila Jaguara)/SP"."""
    nome, sep, resto = texto.partition("/")
    return _nome_proprio(nome) + sep + resto


def cidade(f) -> str:
    return nome_cidade(f.cidade)


def onde(f) -> str:
    """Local em texto corrido: "no país" ou "em Brasília/DF"."""
    return "no país" if f.nivel == D.NACIONAL else f"em {cidade(f)}"


def recorte(f, ano=None) -> str:
    """Início do detalhe dos cartões: "No país, odontologia, 2025"."""
    partes = [inicio(onde(f))] + ([f.esp.lower()] if f.esp != D.TODAS else []) + ([str(ano)] if ano else [])
    return ", ".join(partes)


def titulo_nivel(f) -> str:
    """"Nacional" ou "Brasília/DF", com a área quando houver."""
    base = "Nacional" if f.nivel == D.NACIONAL else cidade(f)
    return base if f.esp == D.TODAS else f"{base} · {f.esp}"


def rotulo_ano(a: int) -> str:
    return PARCIAL if a == M.ANO_BASE else str(a)


def inicio(texto: str) -> str:
    """Primeira letra maiúscula sem mexer no resto (str.capitalize rebaixa os nomes)."""
    return texto[:1].upper() + texto[1:]
