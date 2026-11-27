"""Aba Perfil dos CPFs: quem são todas as pessoas atendidas (CPFs distintos por unidade e ano civil), por unidade ou Nacional (soma das unidades com
meta): sexo, idade, escolaridade, público, frequência, atendimentos por pessoa e empresas. Cenário da aba; unidade e público da barra lateral."""
import pandas as pd
import streamlit as st

from abas.comum import CINZA, TODOS_PUBLICOS, assunto, baixar_excel, cenario, cor, do_publico, mil, num, pct
from common import painel as gt
from common.painel.casca import nota
from common.painel.classico import FORTE, sequencial
from recortes import ANO_CORRENTE, COMBINADA, CORTE
from scripts import dados as D

MIN_GRUPO = 20        # pessoas mínimas para mostrar atendimentos por pessoa de um grupo
TOP_EMPRESAS = 15
SEM_EMPRESA = "Sem empresa no cadastro"
INDIVIDUAIS = "Empresas individuais"
PUBLICOS = {"Transporte": "Trabalhadores do transporte", "Dependente": "Dependentes", "Comunidade": "Comunidade"}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _nome_ano(a: int) -> str:
    return f"{a} (janeiro a {MESES[CORTE - 1]})" if a == ANO_CORRENTE else str(a)


def _anos(faixa: str) -> str:
    """"30 a 39" → "de 30 a 39 anos"; "60 ou mais" → "com 60 anos ou mais"."""
    return "com 60 anos ou mais" if faixa == "60 ou mais" else f"de {faixa} anos"


def _escala(rotulos: list[str], f) -> dict[str, str]:
    """Faixas ordenadas em tons da cor da entidade (claro → escuro); "Não informado" em cinza."""
    ok = [r for r in rotulos if r != "Não informado"]
    return dict(zip(ok, sequencial(len(ok) + 1, assunto(f.entidade))[1:])) | {"Não informado": CINZA}


def _sexo(f) -> dict[str, str]:
    return {"Feminino": cor(f.entidade), "Masculino": FORTE, "Não informado": CINZA}


def _publico(p: pd.DataFrame) -> pd.Series:
    """Trabalhadores do transporte (titulares), dependentes deles e comunidade."""
    return p.publico.where(~((p.publico == "Transporte") & (p.vinculo == "Dependente")), "Dependente")


def _medida(f) -> str:
    return {"SEST": "Consultas da agenda e demais atendimentos do SEST.", "SENAT": "No SENAT, cada aula assistida conta como um atendimento; o curso a distância conta um.",
            COMBINADA: "Atendimentos do SEST e aulas do SENAT somados; quem vai aos dois na mesma unidade conta uma vez."}[f.entidade]


def _apc(g: pd.DataFrame) -> pd.Series:
    """Atendimentos por pessoa de cada grupo; grupo com menos de MIN_GRUPO pessoas fica vazio."""
    return (g.atendimentos / g.pessoas).where(g.pessoas >= MIN_GRUPO)


def _kpis(f, a: pd.DataFrame, ant: pd.DataFrame | None) -> None:
    pes, at = a.pessoas.sum(), a.atendimentos.sum()
    var = ("", "") if ant is None or not ant.pessoas.sum() else (
        f"{pct(pes / ant.pessoas.sum() - 1, 1, sinal=True)} sobre o ano anterior", "pos" if pes >= ant.pessoas.sum() else "neg")
    cartoes = [("Pessoas atendidas", mil(pes), *var),
               ("Atendimentos por pessoa", num(at / pes, 1) if pes else "—", "média no ano", ""),
               ("Vieram uma vez só", pct(a[a.faixa_freq == "1"].pessoas.sum() / pes) if pes else "—", "1 atendimento no ano", ""),
               ("Mulheres", pct(a[a.sexo == "Feminino"].pessoas.sum() / pes) if pes else "—", "das pessoas atendidas", "")]
    if f.entidade == "SENAT":
        cartoes[2] = ("Horas-aula por pessoa", num(a.horas.sum() / pes, 1) if pes else "—", "média no ano", "")
    with gt.cartao("pf_kpis", compacto=True):
        gt.kpis(cartoes)


def _composicao(f, a: pd.DataFrame, onde: str) -> None:
    total = a.pessoas.sum()
    c1, c2, c3 = st.columns([4, 5, 5], gap="small")
    with c1, gt.cartao("pf_sexo"):
        sx = a.groupby("sexo").pessoas.sum().reindex(D.SEXOS).dropna()
        sx = sx[sx / total >= .005]
        gt.cabecalho("Sexo", f"Mulheres são {pct(sx.get('Feminino', 0) / total)} das pessoas", onde)
        cores = _sexo(f)
        gt.grafico(f"pf_sexo_{hash(onde)}", gt.rosca(sx.index.tolist(), sx.tolist(), [cores[s] for s in sx.index], mil(total), "pessoas", "pessoas"), 260)
    with c2, gt.cartao("pf_publico"):
        pb = a.assign(grupo=_publico(a)).groupby("grupo").pessoas.sum().reindex(list(PUBLICOS)).dropna()
        maior = pb.idxmax()
        gt.cabecalho("Público", f"{PUBLICOS[maior]}: {pct(pb[maior] / total)} das pessoas",
                     f"{onde} Público pela classe do cliente no dia do atendimento; dependentes são a família dos trabalhadores.")
        cores = {"Transporte": cor(f.entidade), "Dependente": sequencial(3, assunto(f.entidade))[1], "Comunidade": CINZA}
        gt.grafico(f"pf_pub_{hash(onde)}", gt.barras_h([PUBLICOS[k] for k in pb.index], (100 * pb / total).tolist(),
                                                       [cores[k] for k in pb.index], casas=1, sufixo="%"), 260)
    with c3, gt.cartao("pf_freq"):
        fr = a.groupby("faixa_freq").pessoas.sum().reindex(D.FAIXAS_FREQ).fillna(0)
        gt.cabecalho("Quantas vezes a pessoa é atendida", f"{pct(fr['1'] / total)} vieram uma vez só no ano",
                     f"{onde} % das pessoas por número de atendimentos no ano. {_medida(f)}")
        esc = _escala(D.FAIXAS_FREQ, f)
        gt.grafico(f"pf_freq_{hash(onde)}", gt.barras_h([f"{k} atend." for k in fr.index], (100 * fr / total).tolist(),
                                                        [esc[k] for k in fr.index], casas=1, sufixo="%"), 260)


def _idade(f, a: pd.DataFrame, onde: str) -> None:
    faixas = D.FAIXAS_IDADE[:-1]
    x = a.pivot_table("pessoas", "faixa_etaria", "sexo", aggfunc="sum").reindex(index=faixas, columns=D.SEXOS).fillna(0)
    total = x[["Masculino", "Feminino"]].to_numpy().sum()   # só quem tem idade e sexo informados
    fora = 1 - total / a.pessoas.sum() if a.pessoas.sum() else 0
    if not total:
        gt.vazio("Nenhuma pessoa com data de nascimento e sexo no cadastro.")
        return
    c1, c2 = st.columns(2, gap="small")
    with c1, gt.cartao("pf_piramide"):
        g = (x[["Masculino", "Feminino"]] / total).stack()
        faixa, sexo = g.idxmax()
        gt.cabecalho("Idade e sexo", f"{'Homens' if sexo == 'Masculino' else 'Mulheres'} {_anos(faixa)} são o maior grupo: {pct(g.max())}", f"{onde} % das pessoas com idade e sexo informados; idade no ano. {pct(fora)} das pessoas não têm data de nascimento ou sexo no cadastro e ficam fora.")
        cores = _sexo(f)
        gt.grafico(f"pf_pir_{hash(onde)}", gt.piramide(faixas, (100 * x.Masculino / total).tolist(), (100 * x.Feminino / total).tolist(),
                                                       ("Masculino", "Feminino"), (cores["Masculino"], cores["Feminino"])), 330)
    with c2, gt.cartao("pf_apc_idade"):
        apc = _apc(a[a.faixa_etaria.isin(faixas)].groupby("faixa_etaria")[["pessoas", "atendimentos"]].sum()).reindex(faixas[::-1]).dropna()
        if apc.empty:
            gt.cabecalho("Idade e frequência", "Poucas pessoas por faixa de idade para comparar", onde)
            return
        gt.cabecalho("Idade e frequência", f"Pessoas {_anos(apc.idxmax())} voltam mais: {num(apc.max(), 1)} atendimentos por pessoa",
                     f"{onde} Atendimentos ÷ pessoas de cada faixa; faixa com menos de {MIN_GRUPO} pessoas não aparece.")
        esc = _escala(faixas, f)
        gt.grafico(f"pf_apc_idade_{hash(onde)}", gt.barras_h(apc.index.tolist(), apc.tolist(), [esc[k] for k in apc.index], casas=1), 330)


def _escolaridade(f, a: pd.DataFrame, onde: str) -> None:
    c1, c2 = st.columns(2, gap="small")
    with c1, gt.cartao("pf_instrucao"):
        ad = a[a.faixa_etaria.isin(D.ADULTOS)]
        inst = ad.groupby("instrucao").pessoas.sum().reindex(D.INSTRUCAO).fillna(0)
        if not inst.sum():
            gt.cabecalho("Escolaridade", "Sem pessoas de 18 anos ou mais neste recorte", onde)
        else:
            info = inst.drop("Não informado")
            maior = info.idxmax() if info.sum() else "Não informado"
            gt.cabecalho("Escolaridade", f"{maior} é o grau mais comum: {pct(info[maior] / info.sum()) if info.sum() else '—'} de quem informou",
                         f"{onde} Pessoas de 18 anos ou mais; {pct(inst['Não informado'] / inst.sum())} sem escolaridade no cadastro (barra cinza). "
                         "Mestrado e doutorado entram em pós-graduação.")
            esc = _escala(D.INSTRUCAO, f)
            gt.grafico(f"pf_inst_{hash(onde)}", gt.barras_h(inst.index.tolist(), (100 * inst / inst.sum()).tolist(),
                                                            [esc[k] for k in inst.index], casas=1, sufixo="%"), 330)
    with c2, gt.cartao("pf_apc_grupo"):
        g = pd.concat([a.assign(grupo=_publico(a).map(PUBLICOS)).groupby("grupo")[["pessoas", "atendimentos"]].sum(),
                       a[a.sexo != "Não informado"].assign(grupo=a.sexo.map({"Feminino": "Mulheres", "Masculino": "Homens"}))
                       .groupby("grupo")[["pessoas", "atendimentos"]].sum()])
        apc = _apc(g).dropna()
        media = a.atendimentos.sum() / a.pessoas.sum()
        if apc.empty:
            gt.cabecalho("Atendimentos por pessoa", "Poucas pessoas por grupo para comparar", onde)
            return
        gt.cabecalho("Atendimentos por pessoa", f"{apc.idxmax()} voltam mais: {num(apc.max(), 1)} atendimentos por pessoa",
                     f"{onde} Atendimentos ÷ pessoas do grupo. Linha tracejada: média de todos ({num(media, 1)}). {_medida(f)}")
        cores = [cor(f.entidade) if k == apc.idxmax() else CINZA for k in apc.index]
        gt.grafico(f"pf_apc_grupo_{hash(onde)}", gt.barras_h(apc.index.tolist(), apc.tolist(), cores, casas=1, referencia=round(media, 1),
                                                             ref_texto=f"média {num(media, 1)}", maximo=max(apc.max(), media) * 1.18), 330)


def _unidades(f, escopo: int, ano: int) -> None:
    d = D.perfil_unidades(f.entidade, escopo, ano, f.publico)
    u = D.mercado(f.entidade)["unidades"].loc[lambda x: x.index.isin(d.index)]
    d = d.loc[u.index]
    tab = pd.DataFrame({"Unidade": u.rotulo, "Conselho": u.conselho_curto, "Pessoas": d.pessoas,
                        "Atend. por pessoa": d.atendimentos / d.pessoas, "Uma vez só": d.uma_vez / d.pessoas,
                        "Mulheres": d.mulheres / d.pessoas, "40 anos ou mais": d.de_40 / d.com_idade.where(d.com_idade > 0),
                        "Médio completo ou mais¹": d.medio / d.com_instrucao.where(d.com_instrucao > 0),
                        "Transporte": d.transporte / d.pessoas, "Dependentes": d.dependentes / d.pessoas})
    if f.publico:
        tab = tab.drop(columns="Transporte")
    if f.entidade == "SENAT":
        tab.insert(4, "Horas-aula por pessoa", d.horas / d.pessoas)
    with gt.cartao("pf_unidades"):
        mais = tab["Atend. por pessoa"].where(tab.Pessoas >= MIN_GRUPO).idxmax()
        gt.cabecalho(f"Por unidade · {do_publico(f)}", f"{tab.Unidade[mais]} tem o maior número de atendimentos por pessoa: {num(tab['Atend. por pessoa'][mais], 1)}",
                     f"{_nome_ano(ano)} · {num(len(tab))} unidades com meta · ordem por tipologia e número. ¹ Entre as pessoas de 18 anos ou mais que informaram.")
        fmt = {"Pessoas": num, "Atend. por pessoa": lambda v: num(v, 1), "Horas-aula por pessoa": lambda v: num(v, 1)}
        vis = tab.copy()
        for c in vis.columns[2:]:
            vis[c] = vis[c].map(lambda v, c=c: "—" if pd.isna(v) else fmt.get(c, pct)(v))
        nome = u.rotulo.get(f.unidade) if f.unidade != D.NACIONAL else None
        gt.tabela(vis, destaque=("Unidade", nome) if nome else None, texto=2, altura=480)
        baixar_excel(tab.round(4), f"perfil_cpfs_{f.entidade.replace(' + ', '_')}_{ano}.xlsx", f"pf_excel_{f.entidade}_{escopo}_{ano}")


def _empresas(f, escopo: int, ano: int, onde: str) -> None:
    e = D.empresas(f.entidade, escopo, f.unidade, ano)
    if e.empty:
        return
    titulares, sem = e.pessoas.sum(), e[e.empresa == SEM_EMPRESA].pessoas.sum()
    demais = e[e.empresa.str.startswith("Demais empresas")]
    individuais = e[e.empresa == INDIVIDUAIS]
    nomeadas = e[~e.empresa.isin([SEM_EMPRESA, INDIVIDUAIS]) & ~e.empresa.str.startswith("Demais empresas")]
    top = nomeadas.head(TOP_EMPRESAS)
    com = titulares - sem
    with gt.cartao("pf_emp_kpis", compacto=True):
        gt.kpis([("Titulares com empresa", pct(com / titulares) if titulares else "—", "no cadastro", ""),
                 ("Empresas com 5+ pessoas", num(len(nomeadas)), _nome_ano(ano), ""),
                 ("Demais empresas", num(demais.empresas.sum()), "com até 4 pessoas cada", ""),
                 (f"{len(top)} maiores", pct(top.pessoas.sum() / com) if com else "—", "dos titulares com empresa", "")])
    if top.empty:
        gt.vazio("Nenhuma empresa com 5 ou mais pessoas atendidas.")
        return
    with gt.cartao("pf_empresas"):
        medida = st.segmented_control("Ver", ["Pessoas atendidas", "Atendimentos por pessoa"], default="Pessoas atendidas",
                                      key="pf_emp_medida") or "Pessoas atendidas"
        detalhe = (f"{onde.replace(do_publico(f), TODOS_PUBLICOS)} Titulares (sem os dependentes); empresa do cadastro atual, com matriz e filiais "
                   "juntas e a razão social da Receita Federal; nunca o CNPJ. MEI e empresário individual ficam em \"Empresas individuais\", sem "
                   "o nome. Empresas com menos de 5 pessoas ficam em \"Demais empresas\".")
        nomes, altura = top.empresa.str.title().tolist(), 36 + 26 * len(top)
        chave = f"pf_emp_{f.entidade}_{escopo}_{f.unidade}_{ano}"
        if medida == "Pessoas atendidas":
            gt.cabecalho("Empresas", f"As {len(top)} maiores somam {pct(top.pessoas.sum() / com)} dos titulares com empresa", detalhe)
            gt.grafico(chave, gt.barras_h(nomes, top.pessoas.tolist(), cor(f.entidade), casas=0), altura)
        else:
            media = e.atendimentos.sum() / titulares
            apc = top.atendimentos / top.pessoas
            gt.cabecalho("Empresas", f"Cada titular teve, em média, {num(media, 1)} atendimentos",
                         f"Atendimentos ÷ pessoas de cada empresa, nas mesmas empresas do ranking. Linha tracejada: média de todos os titulares. {detalhe}")
            gt.grafico(f"{chave}_apc", gt.barras_h(nomes, apc.tolist(), cor(f.entidade), casas=1, referencia=round(media, 1),
                                                    ref_texto=f"média {num(media, 1)}", maximo=max(apc.max(), media) * 1.18), altura)
        with st.expander("Ver a lista completa"):
            t = pd.concat([nomeadas, demais, individuais, e[e.empresa == SEM_EMPRESA]])
            gt.tabela(pd.DataFrame({"Empresa": t.empresa.str.title(), "Pessoas": t.pessoas.map(num), "Atendimentos": t.atendimentos.map(num),
                                    "Atend. por pessoa": (t.atendimentos / t.pessoas).map(lambda v: num(v, 1))}), altura=420)


def render(f) -> None:
    escopo = cenario(f, "pf")
    ano = st.pills("Ano", D.ANOS_PERFIL, default=ANO_CORRENTE - 1, key="pf_ano", format_func=_nome_ano) or ANO_CORRENTE - 1
    p = D.perfil(f.entidade, escopo, f.unidade)
    if f.publico:
        p = p[p.publico == f.publico]
    a = p[p.ano == ano]
    if a.empty:
        gt.vazio(f"Sem pessoas atendidas em {_nome_ano(ano)} neste recorte.")
        return
    ant = p[p.ano == ano - 1] if ano - 1 in D.ANOS_PERFIL and ano < ANO_CORRENTE else None
    unidade = D.nome_unidade(D.mercado(f.entidade), f.unidade)
    onde = f"{unidade} · {D.nome(f.entidade)} · {do_publico(f)} · {_nome_ano(ano)}."

    _kpis(f, a, ant)
    _composicao(f, a, onde)
    _idade(f, a, onde)
    _escolaridade(f, a, onde)
    _unidades(f, escopo, ano)
    st.subheader("Empresas dos trabalhadores atendidos")
    _empresas(f, escopo, ano, onde)

    nota("Todas as pessoas atendidas no ano: cada CPF conta uma vez por unidade, de janeiro a dezembro (não é a contagem de novos CPFs da meta). "
         f"Nacional: soma das unidades com meta; quem é atendido em duas unidades conta nas duas. Sexo, idade, escolaridade e empresa vêm do "
         f"cadastro atual da pessoa. {ANO_CORRENTE} vai só até {MESES[CORTE - 1]}, sem projeção: a frequência e os atendimentos por pessoa desse ano "
         "ainda vão subir. Nenhum CPF ou CNPJ aparece no painel.")
