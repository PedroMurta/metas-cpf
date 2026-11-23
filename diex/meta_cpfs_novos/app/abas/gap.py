"""Propostas 1 e 2 (mesma base, mesmo esperado e mesma regra: ritmo + parte do gap; muda de quais especialidades sai o gap), com a
regra passo a passo, exemplo de 1.000 pessoas, a conta real, a evolução e as metas por unidade. No SENAT, também horas-aula."""
import pandas as pd
import streamlit as st

from abas.comum import assunto, baixar_excel, conta, contados, cor, lx, mil, num, pct, regra_contagem, rotulos_anos
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import divergente
from scripts import dados as D

# Exemplo de números redondos: produção por CPF da unidade e referência do grupo (gap de 20% na P1 e de 40% na P2)
EXEMPLO = {(1, "SEST"): (10, 8), (1, "SENAT"): (50, 40), (2, "SEST"): (15, 9), (2, "SENAT"): (75, 45)}


def _opcoes(f, n: int) -> tuple[bool, bool]:
    """(meta em horas-aula?, campanhas?): botões da própria aba."""
    horas = campanhas = False
    if f.entidade == "SENAT":
        horas = st.pills("Meta do SENAT em", ["CPFs distintos", "Horas-aula"], default="CPFs distintos",
                         key=f"p{n}_medida") == "Horas-aula"
    elif n == 2:
        campanhas = st.pills("Campanhas", ["Sem campanhas", "Com campanhas"], default="Sem campanhas",
                             key="p2_campanhas") == "Com campanhas"
    return horas, campanhas


def _especialidades(f, n: int, campanhas: bool) -> str:
    if n == 1:
        return ("Odontologia, fisioterapia, psicologia e nutrição" if f.entidade == "SEST" else
                "Cursos presenciais, sem Palestras e sem Educação de Jovens e Adultos")
    if f.entidade == "SENAT":
        return "Todas as especialidades e modalidades"
    return "Todas as especialidades, " + ("com campanhas" if campanhas else "sem campanhas")


def render(f, n: int) -> None:
    horas, campanhas = _opcoes(f, n)
    esp = _especialidades(f, n, campanhas)
    if horas:
        _horas(f, n, esp)
    else:
        _cpfs(f, n, esp, campanhas)


# CPFs distintos ------------------------------------------------------------------------------------------------------
def _cpfs(f, n: int, esp: str, campanhas: bool) -> None:
    p = D.gap(n, f.entidade, campanhas, f.ano)
    m, k = p["metas"], f.peso
    chave = f"p{n}_{f.chave}_{campanhas}"
    uid = f.unidade
    tot, meta = m.cpf0.sum(), m[f"meta_pessoas_{k}"].sum()

    with gt.cartao(f"p{n}_resumo"):
        frase = "Esperado de 2027 + parte do gap" if n == 1 else "Esperado de 2027 + parte do gap, com todas as especialidades"
        onde = (f"{esp}." if n == 1 else f"{esp}: a pessoa conta uma vez na unidade, mesmo que passe por várias. A referência vem das unidades "
                "com 5 anos ou mais em 2023 e vale para todas.")
        gt.cabecalho(f"Proposta {n} · {f.entidade}", f"{frase}: {num(len(m))} unidades", f"{onde} Cenário de {k}% do gap.")
        gt.kpis([(f"{contados(f)} 2026", mil(tot), "estimativa", ""),
                 ("Esperado 2027", mil(m.sem_meta.sum()), f"{pct(m.sem_meta.sum() / tot - 1, 1, sinal=True)} · cada unidade no próprio ritmo", ""),
                 ("Meta 2027", mil(meta), f"{pct(meta / tot - 1, 1, sinal=True)} sobre a estimativa de 2026", ""),
                 ("Menor meta", pct(m[f"meta_pct_{k}"].min(), 1, sinal=True), f"{num(m[f'piso_{k}'].sum())} unidades estão nesse mínimo", "")
                 if p["nacional"] else ("Meta abaixo de 2026", num((m[f"meta_pct_{k}"] < 0).sum()), "unidade(s)", "")])

    with gt.cartao(f"p{n}_regra"):
        _exemplo(f, n, p, campanhas)

    with gt.cartao(f"p{n}_grupos"):
        g = D.grupos_porte(m)
        med = f.medida
        extra = "" if n == 1 else " A referência sai das unidades maduras do grupo (5 anos ou mais em 2023) e vale para todas."
        gt.cabecalho("Grupos de porte", f"Cada unidade se compara com as de porte parecido: {num(len(m))} unidades em {len(g)} grupos",
                     f"O porte é o volume de {med} em 2026 (estimativa), dividido em faixas de mesmo tamanho (regra de Sturges). "
                     f"Grupo com menos de 5 unidades se junta ao vizinho.{extra}")
        tab = pd.DataFrame({"Grupo": g.index, "Unidades": g.unidades.map(num)})
        if n == 2:
            tab["Unidades maduras"] = g.maduras.map(num).values
        tab[f"{med.capitalize()} em 2026 (estimativa)"] = [f"{mil(a)} a {mil(b)}" for a, b in zip(g.de, g.ate)]
        tab[f"Referência: {med} por pessoa atendida"] = g.referencia.map(lambda v: num(v, 1)).values
        tab["Acima da referência"] = g.acima.map(num).values
        gt.tabela(tab)

    with gt.cartao(f"p{n}_conta"):
        _conta_real(f, p, uid)

    with gt.cartao(f"p{n}_evolucao"):
        hist, obs = D.historico(p, f.entidade, uid)
        x = m.loc[uid] if uid in m.index else m[["sem_meta", *[f"meta_pessoas_{w}" for w in D.PESOS]]].sum()
        vals = [*hist.tolist(), x.sem_meta, *[x[f"meta_pessoas_{w}"] for w in D.PESOS]]
        rot = [*rotulos_anos(hist.index), "2027\nesperado", *[f"2027\nmeta {w}%" for w in D.PESOS]]
        i = len(hist) - 1
        neg, _, pos = divergente(assunto(f.entidade))
        gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}: meta de {pct(x[f'meta_pessoas_{k}'] / hist.iloc[-1] - 1, 1, sinal=True)} "
                                 f"em 2027 no cenário de {k}%",
                     f"{contados(f)} por ano; 2026 é estimativa. Os selos de 2027 comparam com 2026. Esperado: cada unidade "
                     f"continua no ritmo dela.{obs}")
        gt.grafico(f"evo_{chave}_{uid}", gt.evolucao(
            rot, vals, cor(f.entidade), textos=[mil(v) for v in vals], cores_var=(neg, pos), apagadas=[i, i + 1],
            comparar={j: i for j in range(i + 1, len(vals))}), 380)

    with gt.cartao(f"p{n}_unidades"):
        u = p["unidades"]
        mm = m.loc[u.index]
        gt.cabecalho("Metas por unidade", f"Meta de 2027 em {contados(f)} nos três cenários",
                     "Entre parênteses, quanto a meta representa sobre a estimativa de 2026")
        df = pd.DataFrame({"Unidade": u.rotulo, "Conselho": u.conselho_curto, "Regra": D.rotulo_regra(mm, k),
                           "CPFs 2026 (estimativa)": mm.cpf0.map(num), "Esperado 2027": mm.sem_meta.map(num)})
        for w in D.PESOS:
            df[f"Meta {w}%"] = [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in
                                zip(mm[f"meta_pessoas_{w}"], mm[f"meta_pct_{w}"])]
        gt.tabela(df, destaque=("Unidade", D.nome_unidade(p, uid)) if uid != D.NACIONAL else None, texto=3, altura=480)
        bruto = pd.DataFrame({"unidade": u.rotulo, "conselho": u.conselho_curto, "regra": mm.regra.map(D.REGRA), "grupo": mm.grupo,
                              "delta_nacional_minimo": p["nacional"],
                              "cpfs_2026_estimativa": mm.cpf0.round(0), "esperado_2027": mm.sem_meta, f"{f.medida}_por_cpf": mm.apc.round(2),
                              "referencia": mm.referencia.round(2), "ritmo": mm.ritmo.astype(float).round(4),
                              "gap": mm.distancia.astype(float).round(4)})
        for w in D.PESOS:
            bruto[f"meta_{w}"], bruto[f"meta_pct_{w}"] = mm[f"meta_pessoas_{w}"], mm[f"meta_pct_{w}"].round(4)
            bruto[f"no_minimo_{w}"] = mm[f"piso_{w}"].map({True: "sim", False: "não"})
        baixar_excel(bruto, f"meta_2027_proposta{n}_{f.chave.lower()}.xlsx", f"xls_{chave}")

    nota(regra_contagem(f) + " Já o gap usa todas as pessoas atendidas no ano. " + (
         f"Nenhuma unidade cresce menos que o delta Nacional, {pct(p['nacional'], 2)}. " if p["nacional"] else
         "Unidade em queda continua no ritmo dela e pode ficar com meta abaixo de 2026. ") + "Quem está na referência ou abaixo recebe a "
         "mediana nacional, que pode ser menor que o esperado da unidade. 2026 é o realizado até outubro mais a "
         "projeção de novembro e dezembro, e as metas mudam quando o ano fechar.")


def _exemplo(f, n: int, p: dict, campanhas: bool) -> None:
    m, oficial, g = p["metas"], p["oficial"], p["nacional"]
    a, r = EXEMPLO[n, f.entidade]
    med, gap = f.medida, (a - r) / a
    historico = ("as quatro áreas e os 12 meses de 2023 a 2025, e as quatro áreas em 2026" if oficial
                 else "produção nos 12 meses de 2023, 2024 e 2025")
    nac = m.mediana_nacional.iloc[0]
    onde = "" if n == 1 else (" em todas as especialidades" + (", com campanhas" if campanhas else
                                                              ", sem campanhas" if f.entidade == "SEST" else ""))
    gt.cabecalho("Como a meta é calculada", "Exemplo: uma unidade com 1.000 pessoas contadas em 2026 (estimativa)",
                 regra_contagem(f) + " Números inventados e arredondados.")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1, st.container(border=True):
        st.markdown("**Passo 1. Esperado de 2027**  \nA unidade continua no ritmo dos últimos anos.")
        st.latex(r"751 \rightarrow 1.000 = 10\%\ \text{ao ano}")
        st.latex(r"\boxed{1.000 + 10\% = 1.100\ \text{pessoas}}")
        st.caption(f"751 {contados(f)} em 2023 e 1.000 em 2026 (estimativa). O ritmo é o crescimento médio por ano (média geométrica): 10% em cada um dos três anos leva de 751 a 1.000.")
    with c2, st.container(border=True):
        st.markdown(f"**Passo 2. Gap do grupo**  \nQuanto a unidade faz acima da referência{onde}.")
        st.latex(rf"\text{{Unidade}} = {a} \quad \text{{Referência}} = {r}")
        st.latex(rf"\text{{Gap}} = \frac{{{a} - {r}}}{{{a}}} = {lx(100 * gap)}\%")
        st.caption(f"São {med} por pessoa atendida no ano. Na referência, 1 em cada 4 unidades do grupo de porte fica nesse valor ou abaixo (P25)"
                   + (". Na Proposta 2 ela sai das unidades com 5 anos ou mais em 2023." if n == 2 else "."))
    with c3, st.container(border=True):
        k = f.peso
        st.markdown(f"**Passo 3. Meta**  \nEsperado + {k}% do gap sobre as 1.000 pessoas.")
        st.latex(rf"{k}\% \times {lx(100 * gap)}\% \times 1.000 = {lx(1000 * k / 100 * gap)}")
        st.latex(rf"\boxed{{1.100 + {lx(1000 * k / 100 * gap)} = {lx(1100 + 1000 * k / 100 * gap)}\ \text{{pessoas}}}}")
        st.caption("Muda com o cenário escolhido na barra lateral.")
    st.markdown("**Os três cenários**")
    gt.tabela(pd.DataFrame([{"Cenário": f"{w}% do gap", "Esperado": "1.100", "Acréscimo": f"{w}% × {pct(gap, 0)} × 1.000 = {num(1000 * w / 100 * gap)}",
                             "Meta 2027": num(1100 + 1000 * w / 100 * gap), "Sobre 2026": pct(.1 + w / 100 * gap, 0, sinal=True)} for w in D.PESOS]),
              destaque=("Cenário", f"{f.peso}% do gap"))
    c = m.regra.value_counts()
    st.markdown(
        f"**Acima da referência ({num(c.get('fórmula', 0))} unidades):** é a conta do exemplo, para quem tem histórico completo.\n\n"
        f"**Na referência ou abaixo ({num(c.get('mediana', 0))} unidades):** não há gap. A meta é a mediana nacional: com os crescimentos em ordem, é o "
        f"da unidade do meio ({pct(nac, 1)}). Exemplo com 10%: 1.000 + 10% = 1.100.\n\n"
        f"**Sem histórico completo ({num(c.get('própria', 0))} unidades):** a meta é o esperado, calculado com o crescimento do meio entre os de "
        f"2024, 2025 e 2026. Exemplo: com 4%, 8% e 12%, o do meio é 8%, e 1.000 + 8% = 1.080. Histórico completo é ter {historico}."
        + (f"\n\n**Crescimento mínimo:** nenhuma unidade cresce menos que o delta Nacional, {pct(g, 2)} ao ano. É quanto as unidades com 5 anos ou mais "
           f"em 2023 cresceram, juntas, em média por ano, de 2023 a 2026. Exemplo com mínimo de 7%: se a conta der 1.040, vale 1.000 + 7% = **1.070**. "
           f"No cenário de {f.peso}%, {num(m[f'piso_{f.peso}'].sum())} unidades ficam no mínimo." if g else ""))


def _conta_real(f, p: dict, uid: int) -> None:
    m, k, med = p["metas"], f.peso, f.medida
    if uid == D.NACIONAL:
        tot, esp = m.cpf0.sum(), m.sem_meta.sum()
        gt.cabecalho("A conta real", "Nacional: a soma das metas das unidades", "Escolha uma unidade na barra lateral para ver a conta dela")
        conta([(f"{contados(f)} 2026", f"{num(tot)} (estimativa)"), ("Esperado 2027", f"{num(esp)} ({pct(esp / tot - 1, 1, sinal=True)})"),
               *[(f"Meta {w}%", f"{num(m[f'meta_pessoas_{w}'].sum())} ({pct(m[f'meta_pessoas_{w}'].sum() / tot - 1, 1, sinal=True)}): "
                  f"{num(m[f'meta_pessoas_{w}'].sum() - esp)} a mais que o esperado") for w in D.PESOS]])
        return
    u = m.loc[uid]
    q, meta = u[f"meta_pct_{k}"], u[f"meta_pessoas_{k}"]
    gt.cabecalho("A conta real", f"{D.nome_unidade(p, uid)}: meta de {num(meta)} CPFs em 2027 ({pct(q, 1, sinal=True)})",
                 f"{D.rotulo_regra(m, k)[uid]} · grupo {u.grupo} · cenário de {k}% do gap")
    linhas = [(f"{contados(f)} 2026", f"{num(u.cpf0)} (estimativa)"),
              ("Esperado 2027", f"{num(u.sem_meta)} ({pct(u.sem_meta / u.cpf0 - 1, 1, sinal=True)})"),
              (f"{med.capitalize()} por pessoa atendida no ano", f"{num(u.producao)} ÷ {num(u.pessoas)} = {num(u.apc, 1)} (estimativa)"),
              ("Referência do grupo", num(u.referencia, 1))]
    if u[f"piso_{k}"]:
        linhas.append(("Meta", f"crescimento mínimo, o delta Nacional: {num(u.cpf0)} + {pct(p['nacional'], 2)} = {num(meta)}"))
    elif u.regra == "fórmula":
        linhas += [("Gap", f"({num(u.apc, 1)} − {num(u.referencia, 1)}) ÷ {num(u.apc, 1)} = {pct(u.distancia, 1)}"),
                   ("Acréscimo", f"{k}% × {pct(u.distancia, 1)} × {num(u.cpf0)} = {num(k / 100 * u.distancia * u.cpf0)}"),
                   ("Meta", f"{num(u.sem_meta)} + {num(meta - u.sem_meta)} = {num(meta)}")]
    elif u.regra == "mediana":
        linhas.append(("Meta", f"na referência ou abaixo: mediana nacional de {pct(m.mediana_nacional.iloc[0], 1)} = {num(meta)}"))
    else:
        linhas.append(("Meta", f"sem histórico completo: o próprio esperado = {num(meta)}"))
    conta(linhas)


# Horas-aula (SENAT) ----------------------------------------------------------------------------------------------------
def _horas(f, n: int, esp: str) -> None:
    p = D.horas(n)
    m = p["metas"]
    uid = f.unidade
    tot, meta = m.cpf0.sum(), m.meta.sum()

    with gt.cartao(f"p{n}_resumo"):
        gt.cabecalho(f"Proposta {n} · SENAT em horas-aula", f"Horas de 2026 + ritmo das horas: {num(len(m))} unidades",
                     f"{esp}. Meta em horas-aula pelo ritmo das horas; sem cenários de 10%, 15% e 20%.")
        gt.kpis([("Horas-aula 2026", mil(tot), "estimativa", ""),
                 ("Meta 2027", mil(meta), f"{pct(meta / tot - 1, 1, sinal=True)} sobre a estimativa de 2026", ""),
                 ("8 em cada 10 unidades", f"{pct(m.meta_pct.quantile(.1), 0)} a {pct(m.meta_pct.quantile(.9), 0)}", "faixa da meta", ""),
                 ("Meta abaixo de 2026", num((m.meta_pct < 0).sum()), "unidade(s)", "")])

    with gt.cartao(f"p{n}_regra"):
        gt.cabecalho("Como a meta é calculada", "A meta segue o ritmo das horas-aula da própria unidade",
                     "Números inventados e arredondados, só para mostrar a conta")
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1, st.container(border=True):
            st.markdown("**1. Com histórico completo**  \nCrescimento constante das horas de 2023 a 2026.")
            st.latex(r"\text{Ritmo} = \left(\frac{1.000}{751}\right)^{1/3} - 1 = 10\%")
            st.latex(r"\boxed{1.000 \times 1{,}10 = 1.100\ \text{horas}}")
            st.caption("751 horas em 2023 e 1.000 em 2026 (estimativa).")
        with c2, st.container(border=True):
            st.markdown("**2. Sem histórico completo**  \nCrescimento Nacional das horas das unidades maduras.")
            st.latex(r"\text{Crescimento Nacional} = 12\%")
            st.latex(r"\boxed{1.000 \times 1{,}12 = 1.120\ \text{horas}}")
            st.caption(f"No exemplo, 12%. Neste recorte, o real é {pct(p['nacional'], 1)} ao ano. Histórico completo: produção nos 12 "
                       "meses de 2023, 2024 e 2025. O crescimento usa a estimativa de 2026.")
        with c3, st.container(border=True):
            st.markdown("**E o gap?**  \nFica só como informação.")
            st.latex(r"\frac{1.000\ \text{horas}}{20\ \text{CPFs}} = 50\ \text{horas por CPF}")
            st.latex(r"\text{Gap} = \frac{50 - 40}{50} = 20\%")
            st.caption("Gap alto quer dizer muitas horas para poucas pessoas. Ele pede mais pessoas com as mesmas horas, e por isso "
                       "não entra numa meta de horas. Para usar o gap, escolha a meta em CPFs distintos.")

    with gt.cartao(f"p{n}_conta"):
        if uid == D.NACIONAL:
            c = m.regra.value_counts()
            gt.cabecalho("A conta real", "Nacional: a soma das metas das unidades", "Escolha uma unidade na barra lateral para ver a conta dela")
            conta([("Horas-aula 2026", f"{num(tot)} (estimativa)"), ("Meta 2027", f"{num(meta)} ({pct(meta / tot - 1, 1, sinal=True)})"),
                   ("Pelo ritmo das horas", f"{num(c.get('ritmo', 0))} unidades"),
                   ("Pelo crescimento Nacional", f"{num(c.get('nacional', 0))} unidades sem histórico completo · {pct(p['nacional'], 1)} ao ano")])
        else:
            u = m.loc[uid]
            gt.cabecalho("A conta real", f"{D.nome_unidade(p, uid)}: meta de {num(u.meta)} horas em 2027 ({pct(u.meta_pct, 1, sinal=True)})",
                         D.REGRA[u.regra])
            conta([("Horas-aula 2026", f"{num(u.cpf0)} (estimativa)"),
                   ("Crescimento", f"{pct(u.meta_pct, 1, sinal=True)} " + ("ao ano, 2023→2026" if u.regra == "ritmo" else
                                                                          "ao ano (Nacional: sem histórico completo)")),
                   ("Meta", f"{num(u.cpf0)} com meta de {pct(u.meta_pct, 1)} = {num(u.meta)} horas"),
                   ("Horas por CPF (informação)", f"{num(u.cpf0)} ÷ {num(u.pessoas)} = {num(u.apc, 1)} · referência do grupo "
                    f"{num(u.referencia, 1)} · gap {pct(u.distancia, 1)}")])

    with gt.cartao(f"p{n}_evolucao"):
        hist = D.serie_de(p, uid, "producao")
        x = m.meta[uid] if uid in m.index else meta
        vals, i = [*hist.tolist(), x], len(hist) - 1
        neg, _, pos = divergente(assunto(f.entidade))
        gt.cabecalho("Evolução", f"{D.nome_unidade(p, uid)}: meta de {pct(x / hist.iloc[-1] - 1, 1, sinal=True)} em horas-aula em 2027",
                     "Horas-aula por ano; 2026 é estimativa. O selo de 2027 compara com 2026.")
        gt.grafico(f"evo_p{n}_horas_{uid}", gt.evolucao([*rotulos_anos(hist.index), "2027\nmeta"], vals, cor(f.entidade),
                   textos=[mil(v) for v in vals], cores_var=(neg, pos), apagadas=[i]), 360)

    with gt.cartao(f"p{n}_unidades"):
        u = p["unidades"]
        mm = m.loc[u.index]
        gt.cabecalho("Metas por unidade", "Meta de 2027 em horas-aula", "Entre parênteses, quanto a meta representa sobre a estimativa de 2026")
        gt.tabela(pd.DataFrame({
            "Unidade": u.rotulo, "Conselho": u.conselho_curto, "Regra": mm.regra.map(D.REGRA),
            "Horas 2026 (estimativa)": mm.cpf0.map(num),
            "Meta 2027": [f"{num(v)} ({pct(q, 1, sinal=True)})" for v, q in zip(mm.meta, mm.meta_pct)],
            "Horas por CPF (estimativa)": mm.apc.map(lambda v: num(v, 1)), "Gap": mm.distancia.map(lambda v: pct(v, 1))}),
            destaque=("Unidade", D.nome_unidade(p, uid)) if uid != D.NACIONAL else None, texto=3, altura=480)
        baixar_excel(pd.DataFrame({"unidade": u.rotulo, "conselho": u.conselho_curto, "regra": mm.regra.map(D.REGRA),
                                   "horas_2026_estimativa": mm.cpf0.round(0), "meta_2027_horas": mm.meta,
                                   "meta_pct": mm.meta_pct.round(4), "horas_por_cpf": mm.apc.round(2), "gap": mm.distancia.round(4)}),
                     f"meta_2027_proposta{n}_senat_horas.xlsx", f"xls_p{n}_horas")

    nota("Sem piso e sem teto: unidade com horas em queda fica com meta abaixo de 2026. 2026 é estimativa: realizado até outubro e projeção para novembro e dezembro.")
