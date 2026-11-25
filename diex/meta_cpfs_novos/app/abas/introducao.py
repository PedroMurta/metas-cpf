"""Aba Introdução, ilustrada: o que conta como CPF, os anos da análise, a projeção de 2026, as palavras da meta e o resumo."""
import pandas as pd
import streamlit as st

import modelo as M
from abas.comum import ENTRA, TODOS_PUBLICOS, contados, cor, mil, nota_media, num, pct, regra_contagem
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
        gt.cabecalho("Os anos da análise", "A análise considera de 2023 em diante", "A meta de 2027 partirá da projeção de 2026")
        I.quadros([
            ("De 2023 a 2026", I.anos_usados(c, "Linha com os anos 2023, 2024, 2025 e 2026, que levam à meta de 2027."),
             "Os anos de 2023 a 2026 mostram o crescimento. Dele sairá a meta de 2027."),
            ("Unidades analisadas", I.maturidade(c, "Três unidades com 5 anos ou mais entram na conta; uma com menos de 5 anos fica fora."),
             f"Para medir o crescimento entram só as unidades com pelo menos 5 anos de inauguração em 2023, pela estabilidade do mercado. A meta será atribuída a {num(len(p[1]['metas']))} unidades, as que não são novas: com pelo menos 2 anos de inauguração."),
            ("2026 é uma projeção", I.projecao(c, "Barras de janeiro a outubro cheias e de novembro e dezembro tracejadas."),
             "O ano ainda não terminou. O número de 2026 é uma projeção com base histórica.")])
    with gt.cartao("intro_termos"):
        _termos(f, c, p)
    with gt.cartao("intro_proposta"):
        _resumo(f, c, p, rot)


def _doze_meses(c: str) -> None:
    gt.cabecalho("A regra dos 12 meses", "A pessoa contará na 1ª vez na unidade ou quando voltar depois de 12 meses ou mais",
                 "Valerá a data do último atendimento dela na unidade")
    I.quadros([
        ("1ª vez na unidade", I.visitas([(160, "10/02/2025", True)], c, "Uma pessoa atendida pela primeira vez em 10/02/2025: novo CPF."),
         "A pessoa nunca tinha sido atendida ali. <strong>Novo CPF.</strong>"),
        ("Voltou antes de 12 meses", I.visitas([(60, "10/02/2025", True), (256, "05/02/2026", False)], c, "Atendida em 10/02/2025 e de novo em 05/02/2026: a segunda vez não contará.", (60, 256, "menos de 12 meses")),
         "Ainda não completou 12 meses desde o último atendimento. <strong>Não contará.</strong>"),
        ("Voltou depois de 12 meses", I.visitas([(60, "10/02/2025", True), (256, "10/02/2026", True)], c, "Atendida em 10/02/2025 e de novo em 10/02/2026: novo CPF.", (60, 256, "12 meses")),
         "Completou 12 meses sem vir. <strong>Novo CPF.</strong>"),
        ("Veio no meio do caminho", I.visitas([(46, "10/02/2025", True), (154, "15/08/2025", False), (268, "15/08/2026", True)], c,
                                              "Atendida em 10/02/2025, 15/08/2025 e 15/08/2026: novo CPF na primeira e na terceira.", (154, 268, "12 meses")),
         "Cada atendimento recomeçará o prazo. Depois de 15/08/2025, só será novo CPF a partir de <strong>15/08/2026</strong>.")])


def _ano_civil(c: str) -> None:
    gt.cabecalho("A regra do exercício anual", "Cada pessoa contará uma vez por ano em cada unidade", "O exercício irá de janeiro a dezembro")
    I.quadros([
        ("Veio várias vezes no ano", I.anos_civis(c, [("2025", [0, 35, 70], "contará 1"), ("2026", [10, 60], "contará 1")], "Três visitas em 2025 contarão 1; duas visitas em 2026 contarão 1."),
         "Todas as visitas do mesmo ano valerão <strong>1</strong>."),
        ("Virou o ano", I.anos_civis(c, [("2025", [92], "contará 1"), ("2026", [2], "contará 1")], "Uma visita em dezembro de 2025 e outra em janeiro de 2026: contará nos dois anos."),
         "A contagem recomeçará em janeiro: quem vier em dezembro e voltar em janeiro contará <strong>nos dois anos</strong>.")])


def _o_que_conta(f, c: str) -> None:
    gt.cabecalho("O que será contado", "A meta contará pessoas, uma por CPF. Não contará atendimentos", "Só valerão os serviços do cenário")
    continuo = {"SEST": "tratamento contínuo", "SENAT": "um curso longo"}.get(f.entidade, "tratamento ou curso longo")
    grupos = ["Odontologia", "Fisioterapia", "Psicologia"] if f.entidade != "SENAT" else ["Curso de 8 horas", "Curso de 40 horas", "Curso técnico"]
    itens = [("Vários atendimentos", I.varios_para_um(["1º atendimento", "2º atendimento", "10º atendimento"], c, "Dez atendimentos da mesma pessoa contarão 1."),
              f"A mesma pessoa, em {continuo}, contará <strong>1</strong>" + (", no começo." if f.doze else ", por mais vezes que venha.")),
             ("Vários cursos" if f.entidade == "SENAT" else "Várias especialidades", I.varios_para_um(grupos, c, "Três serviços na mesma unidade contarão 1 pessoa."),
              "Usou mais de um serviço na mesma unidade: contará <strong>1</strong>."),
             ("Duas unidades", I.duas_unidades(c, "A mesma pessoa atendida em duas unidades contará 1 em cada."), "Foi atendida em duas unidades: contará <strong>1 em cada</strong>.")]
    if f.entidade == D.COMBINADA:
        itens.append(("SEST e SENAT na mesma unidade", I.varios_para_um(["SEST", "SENAT"], c, "A mesma pessoa no SEST e no SENAT da mesma unidade contará 1."),
                      "Foi atendida nos dois, na mesma unidade: contará <strong>1</strong>."))
    I.quadros(itens)


def _termos(f, c: str, p: dict) -> None:
    esforcos = [pct(e, 0) for e in M.ESFORCOS]
    gt.cabecalho("As palavras da meta", "O que significa cada termo usado na proposta", "Desenhos e números ilustrativos, com o crescimento padrão real")
    I.quadros([
        ("Mercado potencial", I.multidao(c, "Uma unidade e as muitas pessoas que ela poderia atender."),
         f"Quantas pessoas a unidade poderia atender. É o mercado {AREA[f.entidade]} na área dela, de um estudo da ESPM."),
        ("Penetração e lacuna", I.pontos100(c, 2, "De um potencial de mercado de 100 pessoas, 2 foram atendidas e 98 não."),
         "<strong>Penetração</strong> é a parte do mercado que a unidade atendeu no ano. <strong>Lacuna</strong> é a parte que falta. Aqui, a unidade atendeu 2 pessoas de um potencial de mercado de 100."),
        ("Crescimento padrão", I.mesmo_passo(c, f"Três unidades de tamanhos diferentes crescem os mesmos {pct(p[1]['delta'], 2)}.", pct(p[1]["delta"], 2)),
         "É o crescimento médio Nacional: a média por ano das unidades analisadas, de 2023 a 2026. A porcentagem será a mesma para todas as unidades e será aplicada sobre a base."),
        ("Esforço de mercado", I.termometro(c, esforcos, M.POTENCIAL, None, "Quatro faixas de esforço de mercado: 5%, 10%, 15% e 20%."),
         "Será um acréscimo sobre o crescimento padrão, de 5% a 20%. Quanto mais espaço a unidade tiver para crescer, maior será. O espaço vem do mercado potencial e da lacuna.")])


def _resumo(f, c: str, p: dict, rot: dict) -> None:
    x, b = M.exemplo(p[1]["delta"]), num(M.BASE_EX)
    v = lambda q, casas: num(q, 0 if x["inteiro"] else casas)     # inteiro quando o crescimento padrão é inteiro
    g, sp, sm, meio, meta = pct(x["g"], 2), v(x["padrao"], 1), v(x["mercado"], 2), v(M.BASE_EX + x["padrao"], 1), num(x["meta"])
    gt.cabecalho(f"A proposta · {TODOS_PUBLICOS}", "Meta = base + [crescimento padrão × (1 + esforço de mercado)]", f"{D.nome(f.entidade)} · {num(len(p[1]['metas']))} unidades · {contados(f)} · exemplo com {b} pessoas em 2026 e o crescimento padrão do {rot[1]}")
    I.quadros([
        ("1. Some o crescimento padrão", I.barra_meta(c, b, meio, [(f"+ {sp}", f"crescimento padrão ({g})", .5)], f"{b} pessoas em 2026 mais {sp} do crescimento padrão: {meio}."),
         f"A porcentagem será igual para todas: {g} de {b} pessoas são {sp}."),
        ("2. Some o esforço de mercado", I.barra_meta(c, b, meta, [(f"+ {sp}", f"crescimento padrão ({g})", .5), ("", f"+ {sm}: esforço de mercado", 1)], f"{b} pessoas em 2026, mais {sp} do crescimento padrão e {sm} do esforço de mercado: {meta}."),
         f"Mudará de uma unidade para outra: com {pct(M.FE_EX, 0)}, são {pct(M.FE_EX, 0)} de {sp} = {num(x['mercado'], 2)}. A meta, arredondada para cima, será <strong>{meta}</strong>.")])
    gt.tabela(pd.DataFrame([{
        "Cenário": rot[e], "2026 (projeção)": mil(x["resumo"]["base"]), "Crescimento padrão¹": pct(x["delta"], 2),
        "Meta 2027": mil(x["resumo"]["meta"]), "Sobre 2026": pct(x["resumo"]["nacional_pct"], 1, sinal=True),
        "Por unidade": f"{pct(x['resumo']['minimo'], 1, sinal=True)} a {pct(x['resumo']['maximo'], 1, sinal=True)}"} for e, x in p.items()]))
    st.caption("¹ Crescimento médio Nacional² por ano, de 2023 a 2026, das unidades com pelo menos 5 anos de inauguração em 2023, somadas. A conta está na aba Proposta.")
    st.caption(nota_media("²"))
    st.caption("  \n".join(f"**{rot[e]}**: {t}." for e, t in ENTRA[f.entidade].items()))
