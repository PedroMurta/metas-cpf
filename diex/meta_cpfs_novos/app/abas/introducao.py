"""Aba Introdução, ilustrada: o que conta como CPF, os anos da análise, a projeção de 2026, as palavras da meta e o resumo."""
import pandas as pd
import streamlit as st

import modelo as M
from abas.comum import ENTRA, NOTA_MODULO, contados, cor, esforco_padrao, mil, nota_media, num, pct, regra_contagem
from charts import ilustracoes as I
from common import painel as gt
from scripts import dados as D

AREA = {"SEST": "de saúde", "SENAT": "de educação", D.COMBINADA: "de saúde e de educação"}


def render(f) -> None:
    c, rot = cor(f.entidade), D.ESCOPO[f.entidade]
    p = {e: D.mercado(f.entidade, e, f.ano) for e in rot}

    with gt.cartao("intro_regra"):
        _doze_meses(c) if f.doze else _ano_civil(c)
    with gt.cartao("intro_cpf"):
        _o_que_conta(f, c)
    with gt.cartao("intro_anos"):
        gt.cabecalho("Os anos da análise", "A análise considera de 2023 em diante", "A meta de 2027 parte da projeção de 2026")
        I.quadros([
            ("De 2023 a 2026", I.anos_usados(c, "Linha com os anos 2023, 2024, 2025 e 2026, que levam à meta de 2027."),
             "Os anos de 2023 a 2026 mostram o crescimento. Dele sai a meta de 2027."),
            ("Quais unidades servem de referência", I.maturidade(c, "Três unidades com 5 anos ou mais entram na conta; uma com menos de 5 anos fica fora."),
             f"Para medir o crescimento de referência entram só as unidades com pelo menos 5 anos de inauguração em 2023, pela maturidade do mercado. A meta vale para todas as {num(len(p[1]['metas']))} unidades."),
            ("2026 é uma projeção", I.projecao(c, "Barras de janeiro a outubro cheias e de novembro e dezembro tracejadas."),
             "O ano ainda não terminou. O número de 2026 é uma projeção com base histórica.")])
    with gt.cartao("intro_termos"):
        _termos(f, c, p)
    with gt.cartao("intro_proposta"):
        _resumo(f, c, p, rot)


def _doze_meses(c: str) -> None:
    gt.cabecalho("A regra dos 12 meses", "A pessoa conta na 1ª vez na unidade ou quando volta depois de 12 meses ou mais",
                 "O que vale é a data do último atendimento dela na unidade")
    I.quadros([
        ("1ª vez na unidade", I.visitas([(160, "10/02/2025", True)], c, "Uma pessoa atendida pela primeira vez em 10/02/2025: novo CPF."),
         "A pessoa nunca tinha sido atendida ali. <strong>Novo CPF.</strong>"),
        ("Voltou antes de 12 meses", I.visitas([(60, "10/02/2025", True), (256, "05/02/2026", False)], c, "Atendida em 10/02/2025 e de novo em 05/02/2026: a segunda vez não conta.", (60, 256, "menos de 12 meses")),
         "Ainda não completou 12 meses desde o último atendimento. <strong>Não conta.</strong>"),
        ("Voltou depois de 12 meses", I.visitas([(60, "10/02/2025", True), (256, "10/02/2026", True)], c, "Atendida em 10/02/2025 e de novo em 10/02/2026: novo CPF.", (60, 256, "12 meses")),
         "Completou 12 meses sem vir. <strong>Novo CPF.</strong>"),
        ("Veio no meio do caminho", I.visitas([(46, "10/02/2025", True), (154, "15/08/2025", False), (268, "15/08/2026", True)], c,
                                              "Atendida em 10/02/2025, 15/08/2025 e 15/08/2026: novo CPF na primeira e na terceira.", (154, 268, "12 meses")),
         "Cada atendimento recomeça o prazo. Depois de 15/08/2025, só é novo CPF a partir de <strong>15/08/2026</strong>.")])


def _ano_civil(c: str) -> None:
    gt.cabecalho("A regra do exercício anual", "Cada pessoa conta uma vez por ano em cada unidade", "O exercício vai de janeiro a dezembro")
    I.quadros([
        ("Veio várias vezes no ano", I.anos_civis(c, [("2025", [0, 35, 70], "conta 1"), ("2026", [10, 60], "conta 1")], "Três visitas em 2025 contam 1; duas visitas em 2026 contam 1."),
         "Todas as visitas do mesmo ano valem <strong>1</strong>."),
        ("Virou o ano", I.anos_civis(c, [("2025", [92], "conta 1"), ("2026", [2], "conta 1")], "Uma visita em dezembro de 2025 e outra em janeiro de 2026: conta nos dois anos."),
         "A contagem recomeça em janeiro: quem veio em dezembro e voltou em janeiro conta <strong>nos dois anos</strong>.")])


def _o_que_conta(f, c: str) -> None:
    gt.cabecalho("O que é contado", "A meta conta pessoas, uma por CPF. Não conta atendimentos", "Só valem as especialidades escolhidas")
    continuo = {"SEST": "tratamento contínuo", "SENAT": "um curso longo"}.get(f.entidade, "tratamento ou curso longo")
    grupos = ["Odontologia", "Fisioterapia", "Psicologia"] if f.entidade != "SENAT" else ["Curso de 8 horas", "Curso de 40 horas", "Curso técnico"]
    itens = [("Vários atendimentos", I.varios_para_um(["1º atendimento", "2º atendimento", "10º atendimento"], c, "Dez atendimentos da mesma pessoa contam 1."),
              f"A mesma pessoa, em {continuo}, conta <strong>1</strong>" + (", no começo." if f.doze else ", por mais vezes que venha.")),
             ("Vários cursos" if f.entidade == "SENAT" else "Várias especialidades", I.varios_para_um(grupos, c, "Três serviços na mesma unidade contam 1 pessoa."),
              "Usou mais de um serviço na mesma unidade: conta <strong>1</strong>."),
             ("Duas unidades", I.duas_unidades(c, "A mesma pessoa atendida em duas unidades conta 1 em cada."), "Foi atendida em duas unidades: conta <strong>1 em cada</strong>.")]
    if f.entidade == D.COMBINADA:
        itens.append(("SEST e SENAT na mesma unidade", I.varios_para_um(["SEST", "SENAT"], c, "A mesma pessoa no SEST e no SENAT da mesma unidade conta 1."),
                      "Foi atendida nos dois, na mesma unidade: conta <strong>1</strong>."))
    I.quadros(itens)


def _termos(f, c: str, p: dict) -> None:
    esforcos = [pct(e, 0) for e in M.ESFORCOS]
    gt.cabecalho("As palavras da meta", "O que significa cada termo usado na proposta", "Números inventados, só para ilustrar")
    I.quadros([
        ("Mercado potencial", I.multidao(c, "Uma unidade e as muitas pessoas que ela poderia atender."),
         f"Quantas pessoas a unidade poderia atender. É o mercado {AREA[f.entidade]} na área dela."),
        ("Penetração e lacuna", I.pontos100(c, 2, "De um potencial de mercado de 100 pessoas, 2 foram atendidas e 98 não."),
         "<strong>Penetração</strong> é a parte do mercado que a unidade atendeu no ano. <strong>Lacuna</strong> é a parte que falta. Aqui, a unidade atendeu 2 pessoas de um potencial de mercado de 100."),
        ("Esforço padrão", I.mesmo_passo(c, "Três unidades de tamanhos diferentes crescem os mesmos 7%."),
         "É o valor encontrado na análise: o crescimento médio por ano das unidades de referência (delta Nacional). A porcentagem é a mesma para todas as unidades."
         + (" Quando a média é negativa, ela entra sem o sinal." if any(x["nacional"] < 0 for x in p.values()) else "")),
        ("Esforço de mercado", I.termometro(c, esforcos, M.POTENCIAL, .62, "Régua de 0 a 1 com quatro faixas de esforço: 5%, 10%, 15% e 20%."),
         "Um acréscimo sobre o esforço padrão. O <strong>fator de mercado (FM)</strong> junta o mercado potencial e a lacuna: quanto mais espaço para crescer, maior o potencial e o esforço.")])


def _resumo(f, c: str, p: dict, rot: dict) -> None:
    gt.cabecalho("A proposta", "Meta = base + [esforço padrão × (1 + esforço de mercado)]", f"{f.entidade} · {num(len(p[1]['metas']))} unidades · {contados(f)} · exemplo com 1.000 pessoas em 2026")
    I.quadros([
        ("1. Some o esforço padrão", I.barra_meta(c, "1.070", [("+ 70", "esforço padrão (7%)", .5)], "1.000 pessoas em 2026 mais 70 do esforço padrão: 1.070."),
         "É igual para todas: 7% de 1.000 pessoas são 70."),
        ("2. Some o esforço de mercado", I.barra_meta(c, "1.081", [("+ 70", "esforço padrão (7%)", .5), ("", "+ 11: esforço de mercado", 1)], "1.000 pessoas em 2026, mais 70 do esforço padrão e 11 do esforço de mercado: 1.081."),
         "Muda de uma unidade para outra: com 15%, são 15% das 70 pessoas, 10,5, arredondado para cima. A meta é <strong>1.081</strong>.")])
    gt.tabela(pd.DataFrame([{
        "Especialidades": rot[e], "2026 (projeção)": mil(x["resumo"]["base"]), "Esforço padrão¹": esforco_padrao(x),
        "Meta 2027": mil(x["resumo"]["meta"]), "Sobre 2026": pct(x["resumo"]["nacional_pct"], 1, sinal=True),
        "Por unidade": f"{pct(x['resumo']['minimo'], 1, sinal=True)} a {pct(x['resumo']['maximo'], 1, sinal=True)}"} for e, x in p.items()]))
    st.caption("¹ Delta Nacional: crescimento médio² por ano, de 2023 a 2026, das unidades com pelo menos 5 anos de inauguração em 2023, somadas. A conta está na aba Proposta.")
    if any(x["nacional"] < 0 for x in p.values()):
        st.caption(NOTA_MODULO.replace("*", r"\*", 1))
    st.caption(nota_media("²"))
    st.caption("  \n".join(f"**{rot[e]}**: {t}." for e, t in ENTRA[f.entidade].items()))
