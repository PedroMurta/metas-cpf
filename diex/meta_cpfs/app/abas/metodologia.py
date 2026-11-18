"""Aba 4 · Como a meta é calculada. Linguagem da apresentação "Meta de CPFs Distintos 2027" (CPF distinto, atendimentos
por CPF, grupo de porte, referência do grupo, ritmo da unidade, gap), sem contagem de unidades com meta, sem "ponto
percentual" e sem "caminho 1/2" (pedidos do usuário em 17/11). Acima da referência: fórmula; na referência ou abaixo:
mediana; fora do cálculo: mediana do próprio crescimento (como na apresentação; 18/11).

Passo 1 com os totais reais de 2026 projetado do filtro; passos 2 a 7 com uma unidade de exemplo de números redondos e
os grupos e referências reais; passo 8 com a conta da unidade escolhida. Os pesos do gap (10%, 15% e 20%) são todos
cenários e aparecem lado a lado."""
from math import ceil, log2

from common import painel as gt
import modelo as M
import pandas as pd
import streamlit as st
from scripts import dados as D

from abas.comum import (CONTEXTO_CLARO, DESTAQUE, MES_CORTE, inicio, mil, nome_cidade, num, onde, pagina, pct,
                        titulo_nivel)

BASE, FECHADO, INI = str(M.ANO_BASE), M.ANO_BASE - 1, M.JANELA[0]
PESOS = list(D.pesos().values())                         # 10, 15, 20: cenários

# Unidade de exemplo (números redondos, coerentes entre os passos)
EX_CPFS = 1_000                                          # CPFs distintos no ano-base
EX_CRESC = [0.08, 0.10, 0.12]                            # crescimento de 2024, 2025 e 2026 → média de 10% ao ano
EX_ATEND = 8_000                                         # atendimentos no ano-base → 8 por CPF
EX_APC, EX_REF = EX_ATEND / EX_CPFS, 6.0
EX_GAP = (EX_APC - EX_REF) / EX_APC                      # 25%
EX_GRUPO = [("Unidade 1", 9.0), ("Unidade de exemplo", EX_APC), ("Unidade 3", 7.0), ("Unidade 4", 6.0),
            ("Unidade 5", 5.0)]                         # P25 de 5, 6, 7, 8, 9 = 6
EX_RITMO, EX_MEDIANA = 0.10, 0.10

PECAS = [
    ("Grupo de porte", "Unidades com volume de atendimentos parecido."),
    ("Referência do grupo", "Para cada grupo, um valor de referência para o indicador de atendimentos por CPF."),
    ("Ritmo da unidade", f"Média do crescimento anual de CPFs distintos, de {INI} a {M.ANO_BASE}."),
    ("Gap", "Quanto o indicador de atendimentos por CPF da unidade está acima da referência do seu grupo."),
]


def _cpfs(base: float, meta: float) -> int:
    return ceil(round(base * (1 + meta), 6))              # arredonda para cima, sem erro de ponto flutuante


def _lista(valores) -> str:
    """[7, 1, 1] → "7, 1 e 1"."""
    v = [num(x) for x in valores]
    return v[0] if len(v) == 1 else ", ".join(v[:-1]) + " e " + v[-1]


def _conta(linhas: list[tuple[str, str]], final: int | None = None) -> None:
    """Conta passo a passo: (rótulo, expressão em HTML confiável); `final` destaca uma linha."""
    classe = " class='streamlit-conta-final'"
    html = "".join(f"<div{classe if i == final else ''}><span>{r}</span><p>{t}</p></div>"
                   for i, (r, t) in enumerate(linhas))
    st.html(f"<div class='streamlit-conta'>{html}</div>")


def _lista_pct(valores) -> str:
    v = [pct(x, 0) for x in valores]
    return ", ".join(v[:-1]) + " e " + v[-1]


def _cenarios(itens: list[tuple[str, str]]) -> None:
    """Os três cenários lado a lado: (valor, nota) na ordem de PESOS."""
    gt.kpis([(f"Cenário {p}%", v, n, "") for p, (v, n) in zip(PESOS, itens)], colunas=3)


def _pecas() -> None:
    for i, (col, (titulo, texto)) in enumerate(zip(st.columns(4, gap="small"), PECAS), 1):
        with col, gt.cartao(f"met_peca_{i}", compacto=True):
            gt.cabecalho(f"0{i}", titulo, "")
            gt.frase(texto)


def _regra(mediana: float) -> None:
    st.subheader("Como a meta é definida")
    c1, c2, c3 = st.columns(3, gap="small")
    with c1, gt.cartao("met_regra_formula", compacto=True):
        gt.cabecalho("Acima da referência", "Fórmula")
        gt.frase("A unidade recebe a meta <b>de acordo com o seu desempenho</b>: o ritmo da unidade mais uma parte "
                 "do gap. Há três cenários para essa parte: 10%, 15% e 20% do gap.")
    with c2, gt.cartao("met_regra_mediana", compacto=True):
        gt.cabecalho("Na referência ou abaixo", "Mediana")
        gt.frase(f"Quem está na referência ou abaixo recebe <b>a mesma meta</b>: a mediana da taxa de crescimento "
                 f"({pct(mediana, 2)}).")
    with c3, gt.cartao("met_regra_propria", compacto=True):
        gt.cabecalho("Fora do cálculo", "Mediana própria")
        gt.frase(f"Quem não entra no cálculo recebe a <b>mediana do próprio crescimento</b> de {M.ANO_BASE - 2} a "
                 f"{M.ANO_BASE}.")
    with gt.cartao("met_formula", compacto=True):
        st.html("<div class='streamlit-formula'>"
                "<div><span>Acima da referência</span><code>meta = <b>ritmo</b> + 10%, 15% ou 20% do <b>gap</b>"
                "</code></div>"
                f"<div><span>Na referência ou abaixo</span><code>meta = <b>mediana</b> ({pct(mediana, 2)})</code></div>"
                f"<div><span>Fora do cálculo</span><code>meta = <b>mediana do próprio crescimento</b> de "
                f"{M.ANO_BASE - 2} a {M.ANO_BASE}</code></div>"
                f"<div><span>Meta em CPFs</span><code>CPFs distintos de {M.ANO_BASE} + meta · ex.: 1.000 CPFs com meta "
                "de 12,5% = <b>1.125 CPFs</b></code></div></div>")


def _passo_ano(f) -> None:
    st.subheader(f"1. {M.ANO_BASE}: realizado até {MES_CORTE} e projeção")
    a, mp = D.anual(f.nivel, f.esp), D.meta_producao(f.nivel, f.esp)
    if pd.isna(a.cpfs.get(M.ANO_BASE)):
        gt.vazio(f"Sem atendimentos em {M.ANO_BASE} para este recorte.")
        return
    cpfs, at = a.cpfs[M.ANO_BASE], a.atendimentos[M.ANO_BASE]
    cpfs_ytd, at_ytd = D.ate_corte(f.nivel, f.esp)
    meta_at = mp.get(M.ANO_BASE, float("nan"))
    tem_meta = pd.notna(meta_at) and meta_at > 0
    with gt.cartao("met_ano"):
        gt.cabecalho(f"{titulo_nivel(f)} · {BASE}",
                     f"{num(at)} atendimentos para {num(cpfs)} CPFs distintos" +
                     (f", {pct(at / meta_at, 0)} da meta de atendimentos" if tem_meta else ""),
                     f"{inicio(onde(f))}. "
                     + ("Só odontologia, fisioterapia, nutrição e psicologia, nos atendimentos, nos CPFs e na meta. "
                        if f.esp == D.TODAS else f"Só {f.esp.lower()}, nos atendimentos, nos CPFs e na meta. ")
                     + f"Realizado até {MES_CORTE} e projeção do resto do ano. Meta de atendimentos pactuada para "
                     f"{M.ANO_BASE}.")
        gt.kpis([("Meta de atendimentos", num(meta_at) if tem_meta else "—", f"pactuada para {M.ANO_BASE}", ""),
                 (f"Atendimentos {BASE}", num(at), f"{num(at_ytd)} até {MES_CORTE}", ""),
                 (f"CPFs distintos {BASE}", num(cpfs), f"{num(cpfs_ytd)} até {MES_CORTE}", ""),
                 ("Atendimentos por CPF", num(at / cpfs, 2), f"em {BASE}", "")])
    quem = "o país" if f.nivel == D.NACIONAL else "a unidade"
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1:
        st.markdown(f"{M.ANO_BASE} ainda não fechou. Para ter o ano inteiro, dividimos o realizado até {MES_CORTE} "
                    f"pela parte do ano que {quem} costuma alcançar até {MES_CORTE} (média de "
                    f"{M.ANOS_FRACAO[0]} a {M.ANOS_FRACAO[-1]}). Na unidade típica, até outubro já foram atendidos "
                    "91% dos CPFs do ano e feitos 84% dos atendimentos.")
        st.caption(f"Em janeiro de {M.ANO_META}, com {M.ANO_BASE} fechado, entra o realizado no lugar da projeção.")
    with c2, gt.cartao("met_ano_conta", compacto=True):
        gt.cabecalho("Conta", f"{num(cpfs)} CPFs distintos em {BASE}")
        _conta([("CPFs distintos", f"{num(cpfs_ytd)} ÷ {gt.br(cpfs_ytd / cpfs, 2)} = <b>{num(cpfs)}</b>"),
                ("Atendimentos", f"{num(at_ytd)} ÷ {gt.br(at_ytd / at, 2)} = <b>{num(at)}</b>")])
        st.caption(f"O divisor é a parte do ano alcançada até {MES_CORTE} (0,90 = 90%).")


def _passo_universo() -> None:
    st.subheader("2. Quem recebe meta")
    c1, c2 = st.columns(2, gap="medium")
    with c1, gt.cartao("met_universo", compacto=True):
        gt.cabecalho("", "Recebem meta")
        gt.frase(f"Unidades com <b>2 anos ou mais</b>, com atendimentos em {M.ANO_BASE} e meta de atendimentos "
                 f"pactuada para {M.ANO_META}. Elas também definem os grupos e as referências.")
    with c2, gt.cartao("met_com_meta", compacto=True):
        gt.cabecalho("", "Entram no cálculo")
        gt.frase(f"As que, em cada ano de {INI} a {FECHADO}, atenderam nas <b>quatro áreas e nos 12 meses</b>, e "
                 f"têm as quatro áreas em {M.ANO_BASE}. Só elas têm ritmo e entram na mediana. As demais recebem a "
                 f"mediana do próprio crescimento de {M.ANO_BASE - 2} a {M.ANO_BASE}.")


def _faixas_texto(maior) -> list[str]:
    """Faixas contínuas como na apresentação: "até 13,3 mil", "13,3 a 23,2 mil"."""
    out, ant = [], None
    for b in maior:
        out.append(f"até {mil(b)}" if ant is None else f"{gt.br(ant / 1e3, 1)} a {mil(b)}")
        ant = b
    return out


def _passo_grupos(f) -> str:
    st.subheader("3. Grupo de porte")
    r, fx, g = D.metas().query("universo"), D.faixas_sturges(), D.grupos()
    n, k = len(r), len(fx)
    juntas = fx[fx.grupo.str.contains("–")]
    grupo_u = r.grupo.get(f.nivel)
    grupo_u = None if pd.isna(grupo_u) else grupo_u          # fora do universo: sem grupo

    tab = pd.DataFrame({"Grupo": g.index, "Unidades": g.unidades.astype(str).values,
                        f"Atendimentos em {M.ANO_BASE}": _faixas_texto(g.maior),
                        "Referência (atend. por CPF)": [num(v, 2) for v in g.referencia]})
    _, meio, _ = st.columns([1, 4, 1])
    with meio, gt.cartao("met_grupos_tab"):
        gt.cabecalho("Grupos de porte e referência", f"{len(g)} grupos de unidades com volume de atendimentos parecido",
                     f"Com base em {M.ANO_BASE} (realizado até {MES_CORTE} e projeção), nas {n} unidades com 2 anos ou "
                     "mais. Grupos e referências são recalculados todo ano." +
                     (" Em destaque, o grupo da unidade escolhida." if grupo_u else ""))
        gt.tabela(tab, destaque=("Grupo", grupo_u) if grupo_u else None)

    with st.expander("Como os grupos são formados (regra de Sturges)"):
        c1, c2 = st.columns([2, 3], gap="medium")
        with c1:
            st.markdown(f"As {n} unidades são ordenadas pelos atendimentos de {M.ANO_BASE} e divididas em faixas de "
                        "mesma largura. A regra de Sturges diz quantas faixas usar:")
            _conta([("Faixas", f"1 + log₂ {n} = {gt.br(1 + log2(n), 1)} → <b>{k}</b>"),
                    ("Largura", f"({mil(r.at0.max())} − {mil(r.at0.min())}) ÷ {k} ≈ "
                                f"<b>{mil((r.at0.max() - r.at0.min()) / k)}</b>")])
            st.caption(f"log₂ {n} = {gt.br(log2(n), 1)} porque 2 elevado a {gt.br(log2(n), 1)} dá {n}. Faixa com menos "
                       f"de {M.GRUPO_MINIMO} unidades se junta à vizinha.")
        with c2, gt.cartao("met_faixas"):
            achado = (f"As {len(juntas)} maiores faixas têm {_lista(juntas.unidades)} unidades e viram o "
                      f"{juntas.grupo.iloc[0]}" if len(juntas) else f"{k} faixas com {M.GRUPO_MINIMO} unidades ou mais")
            gt.cabecalho("Unidades por faixa", achado, "Em azul, as faixas que se juntaram.")
            rot = [f"{mil(a, 0)}–{mil(b, 0)}" for a, b in zip(fx.menor, fx.maior)]
            gt.grafico("met_faixas", gt.colunas(rot, fx.unidades.tolist(),
                                                [DESTAQUE if "–" in x else CONTEXTO_CLARO for x in fx.grupo], casas=0),
                       240)
    return grupo_u or g.unidades.idxmax()


def _passo_referencia(f, grupo: str) -> None:
    st.subheader("4. Referência do grupo")
    c1, c2 = st.columns([2, 3], gap="medium")
    with c1:
        st.markdown("Em cada grupo, olhamos o indicador de atendimentos por CPF de todas as unidades. A referência "
                    "é o **P25**: o valor que separa o quarto do grupo que menos repete atendimentos na mesma pessoa.")
        st.markdown(f"Ex.: um grupo com 5 unidades, de 5, 6, 7, 8 e 9 atendimentos por CPF, tem referência "
                    f"**{gt.br(EX_REF, 0)}**. A unidade de exemplo fez {num(EX_ATEND)} atendimentos para "
                    f"{num(EX_CPFS)} CPFs, ou **{gt.br(EX_APC, 0)} por CPF**: está acima da referência.")
    with c2, gt.cartao("met_ref_ex"):
        gt.cabecalho("Exemplo", f"Referência do grupo: {gt.br(EX_REF, 0)} atendimentos por CPF",
                     "Azul: acima da referência. Cinza: na referência ou abaixo.")
        gt.grafico("met_ref_ex", gt.barras_h(
            [n for n, _ in EX_GRUPO], [v for _, v in EX_GRUPO],
            [gt.CIANO if n == "Unidade de exemplo" else DESTAQUE if v > EX_REF else CONTEXTO_CLARO for n, v in EX_GRUPO],
            casas=0, referencia=EX_REF, ref_texto=f"Referência {gt.br(EX_REF, 0)}", maximo=10.5), 230)

    r = D.metas()
    grupos = D.grupos().index.tolist()
    with st.expander("Ver as unidades de um grupo"):
        escolha = st.segmented_control("Grupo", grupos, default=grupo, key="met_grupo_real") or grupo
        u = r[r.grupo == escolha].sort_values("apc", ascending=False)
        ref = u.referencia.iloc[0]
        cor = [gt.CIANO if i == f.nivel else DESTAQUE if v > ref else CONTEXTO_CLARO for i, v in zip(u.index, u.apc)]
        with gt.cartao("met_ref_real"):
            gt.cabecalho(escolha, f"Referência do {escolha}: {num(ref, 2)} atendimentos por CPF",
                         f"Atendimentos por CPF em {M.ANO_BASE} (projeção). Azul: acima da referência. Ciano: a "
                         "unidade escolhida.")
            gt.grafico(f"met_ref_real_{escolha}", gt.barras_h(
                [nome_cidade(c) for c in u.cidade.fillna(u.unidade)], u.apc.tolist(), cor, casas=2,
                referencia=ref, ref_texto=f"Ref. {num(ref, 2)}"), 22 * len(u) + 60)


def _passo_ritmo() -> None:
    st.subheader("5. Ritmo da unidade")
    anos = [str(a) if a < M.ANO_BASE else BASE for a in range(INI + 1, M.ANO_BASE + 1)]
    c1, c2 = st.columns([2, 3], gap="medium")
    with c1:
        st.markdown(f"É a média do crescimento anual de CPFs distintos de {INI} a {M.ANO_BASE}.")
        _conta([("Crescimento", " · ".join(f"{a}: <b>+{pct(v, 0)}</b>" for a, v in zip(anos, EX_CRESC))),
                ("Ritmo", f"média de <b>{pct(EX_RITMO, 0)} ao ano</b>")], final=1)
        st.caption("A média considera que o crescimento de um ano se soma ao do ano seguinte (média geométrica).")
    with c2, gt.cartao("met_ritmo"):
        gt.cabecalho("Exemplo", f"Média do crescimento: {pct(EX_RITMO, 0)} ao ano",
                     f"Crescimento de CPFs distintos sobre o ano anterior. {BASE}: projetado.")
        gt.grafico("met_ritmo", gt.colunas(anos, [100 * v for v in EX_CRESC], DESTAQUE, casas=0, sufixo="%"), 240)


def _passo_gap() -> None:
    st.subheader("6. Gap")
    acima = int(EX_APC - EX_REF)
    c1, c2 = st.columns([3, 2], gap="medium")
    with c1, gt.cartao("met_blocos"):
        gt.cabecalho("Exemplo", f"Gap de {pct(EX_GAP, 0)}: {gt.br(EX_APC, 0)} atendimentos por CPF, com referência de "
                     f"{gt.br(EX_REF, 0)}",
                     f"Cada quadrado é um atendimento de uma pessoa típica da unidade de exemplo. Os {acima} acima da "
                     f"referência, divididos pelos {gt.br(EX_APC, 0)}, dão o gap.")
        blocos = "".join(f"<div class='{'streamlit-acima' if i >= EX_REF else ''}' style='animation-delay:{i * 70}ms'>{i + 1}"
                         "</div>" for i in range(int(EX_APC)))
        st.html(f"<div class='streamlit-blocos'>{blocos}</div><div class='streamlit-blocos-legenda'>"
                f"<span><i></i>até a referência do grupo ({gt.br(EX_REF, 0)})</span>"
                "<span><i class='streamlit-acima'></i>acima da referência (gap)</span></div>")
        st.caption("Se esses atendimentos fossem para pessoas novas, a unidade atenderia mais CPFs com a mesma "
                   "produção. A meta pede só uma parte disso.")
    with c2, gt.cartao("met_gap", compacto=True):
        gt.cabecalho("Conta", f"Gap de {pct(EX_GAP, 0)}")
        _conta([("Gap", f"({gt.br(EX_APC, 0)} − {gt.br(EX_REF, 0)}) ÷ {gt.br(EX_APC, 0)} = <b>{pct(EX_GAP, 0)}</b>"),
                ("Na referência ou abaixo", "não há gap")], final=0)
    with gt.cartao("met_gap_cenarios", compacto=True):
        gt.cabecalho("Quanto o gap acrescenta à meta", f"Gap de {pct(EX_GAP, 0)} nos três cenários")
        _cenarios([(f"+{pct(p / 100 * EX_GAP, 2)}", f"{p}% de {pct(EX_GAP, 0)}") for p in PESOS])


def _passo_meta(mediana: float) -> None:
    st.subheader("7. A meta")
    metas = [EX_RITMO + p / 100 * EX_GAP for p in PESOS]
    with gt.cartao("met_meta_1", compacto=True):
        gt.cabecalho("Acima da referência · fórmula", f"Ritmo de {pct(EX_RITMO, 0)} mais o acréscimo do gap",
                     f"Unidade de exemplo: {num(EX_CPFS)} CPFs distintos em {M.ANO_BASE}. Meta em CPFs arredondada "
                     "para cima.")
        _cenarios([(pct(m, 2), f"{pct(EX_RITMO, 0)} + {pct(m - EX_RITMO, 2)} · {num(_cpfs(EX_CPFS, m))} CPFs em "
                               f"{M.ANO_META}") for m in metas])
    with gt.cartao("met_meta_2", compacto=True):
        gt.cabecalho("Na referência ou abaixo · mediana", f"Mediana de {pct(mediana, 2)}, igual nos três cenários",
                     f"Ex.: {gt.br(5.5, 1)} atendimentos por CPF, abaixo da referência de {gt.br(EX_REF, 0)}. Com meta de "
                     f"{pct(mediana, 2)}, {num(EX_CPFS)} CPFs viram {num(_cpfs(EX_CPFS, mediana))} em {M.ANO_META}.")
        st.caption(f"Mediana é o valor do meio: aqui, dos crescimentos anuais de {INI + 1} a {M.ANO_BASE} das unidades "
                   "na referência ou abaixo que entram no cálculo.")
    ex = [0.05, 0.20, 0.15]
    with gt.cartao("met_meta_3", compacto=True):
        gt.cabecalho("Fora do cálculo · mediana própria",
                     f"Mediana de {pct(sorted(ex)[1], 0)}, igual nos três cenários",
                     f"Ex.: crescimento de {_lista_pct(ex)} de {M.ANO_BASE - 2} a {M.ANO_BASE}. O valor do meio é "
                     f"{pct(sorted(ex)[1], 0)}: {num(EX_CPFS)} CPFs viram {num(_cpfs(EX_CPFS, sorted(ex)[1]))} em "
                     f"{M.ANO_META}.")


def _na_unidade(f) -> None:
    st.subheader("8. A conta com os números reais")
    r = D.metas()
    com = r[r.meta_pct.notna()]
    if f.nivel == D.NACIONAL:
        base = com.cpf0.sum()
        with gt.cartao("met_nacional", compacto=True):
            gt.cabecalho("Nacional", f"{mil(base)} CPFs distintos em {BASE} nas unidades com meta",
                         "Soma dos CPFs distintos de cada unidade com meta: quem foi atendido em duas unidades conta "
                         "nas duas. Escolha uma unidade na barra lateral para ver a conta dela.")
            _cenarios([(mil(com[f"meta_pessoas_{p}"].sum()),
                        f"{pct(com[f'meta_pessoas_{p}'].sum() / base - 1, 2, sinal=True)} em {M.ANO_META}")
                       for p in PESOS])
        return
    nome = nome_cidade(f.cidade)
    if f.nivel not in r.index:
        gt.vazio(f"{nome} não recebe meta: tem menos de 2 anos, não teve atendimentos em {M.ANO_BASE} ou não tem "
                 f"meta de atendimentos pactuada para {M.ANO_META}.")
        return
    u = r.loc[f.nivel]
    acima = u.regra == "fórmula"
    sem_grupo = pd.isna(u.grupo)
    cres = [u.get(f"cresc_{a}") for a in range(INI + 1, M.ANO_BASE + 1)]
    anos = [str(a) if a < M.ANO_BASE else BASE for a in range(INI + 1, M.ANO_BASE + 1)]
    if not u.com_meta:
        situacao = "não entra no cálculo → mediana própria"
    else:
        situacao = "acima da referência → fórmula" if acima else "na referência ou abaixo → mediana"
    linhas = [(f"CPFs distintos {M.ANO_BASE}", f"{num(u.cpf_ytd)} até {MES_CORTE} → <b>{num(u.cpf0)}</b> no ano "
                                               "(projeção)"),
              ("Grupo de porte", "-" if sem_grupo else
               f"{u.grupo} · referência de <b>{num(u.referencia, 2)}</b> atendimentos por CPF"),
              ("Atendimentos por CPF", f"{num(u.at0)} ÷ {num(u.cpf0)} = <b>{num(u.apc, 2)}</b> → {situacao}")]
    if u.com_meta:
        linhas += [("Crescimento", " · ".join(f"{a}: {pct(v, 1, sinal=True)}" for a, v in zip(anos, cres))),
                   ("Ritmo da unidade", f"média de <b>{pct(u.ritmo, 2)}</b> ao ano")]
    else:
        linhas.append(("Fora do cálculo", f"faltou alguma das quatro áreas ou algum mês de atendimento entre {INI} e "
                                          f"{FECHADO}, ou alguma área em {M.ANO_BASE}"))
        linhas.append(("Crescimento", " · ".join(f"{a}: {pct(v, 1, sinal=True)}" for a, v in zip(anos, cres)
                                                 if int(a) >= M.ANO_BASE - 2)))
    if acima:
        linhas.append(("Gap", f"({num(u.apc, 2)} − {num(u.referencia, 2)}) ÷ {num(u.apc, 2)} = "
                              f"<b>{pct(u.distancia, 2)}</b>"))
    elif u.regra == "própria":
        linhas.append(("Meta", f"mediana do próprio crescimento = <b>{pct(u.meta_pct, 2)}</b>"))
    else:
        linhas.append(("Meta", f"mediana = <b>{pct(u.meta_pct, 2)}</b>"))
    with gt.cartao("met_unidade"):
        gt.cabecalho(nome, f"{num(u.cpf0)} CPFs distintos em {BASE}",
                     "A meta vale para as quatro áreas juntas; o filtro de especialidade não muda esta conta. Meta em "
                     "CPFs arredondada para cima.")
        _conta(linhas)
        if acima:
            _cenarios([(pct(u[f"meta_pct_{p}"], 2),
                        f"{pct(u.ritmo, 2)} + {pct(p / 100 * u.distancia, 2)} · {num(u[f'meta_pessoas_{p}'])} CPFs em "
                        f"{M.ANO_META}") for p in PESOS])
        else:
            gt.kpis([(f"Meta {M.ANO_META}", pct(u.meta_pct, 2, sinal=True), "igual nos três cenários", ""),
                     (f"CPFs em {M.ANO_META}", num(u.meta_pessoas), f"{num(u.meta_pessoas - ceil(u.cpf0))} a mais", "")],
                    colunas=2)


def render(f) -> None:
    mediana = D.metas().mediana_nacional.dropna().iloc[0]
    pagina("Metodologia", "Como a meta é calculada",
           "Quatro peças, calculadas a partir do indicador de atendimentos por CPF: atendimentos ÷ CPFs distintos da "
           "unidade no ano (ex.: 7.000 ÷ 1.000 = 7).")
    _pecas()
    _regra(mediana)
    _passo_ano(f)
    _passo_universo()
    grupo = _passo_grupos(f)
    _passo_referencia(f, grupo)
    _passo_ritmo()
    _passo_gap()
    _passo_meta(mediana)
    _na_unidade(f)
