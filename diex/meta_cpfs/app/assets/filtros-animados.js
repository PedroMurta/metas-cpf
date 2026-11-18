/* Filtros animados: st.pills / st.segmented_control viram uma trilha com indicador branco que desliza até a opção
 * escolhida (mesmo movimento do seletor de período do guia interativo).
 * Não insere nós no DOM do React: só grava a posição da opção ativa em variáveis CSS da trilha
 * (--seg-x, --seg-y, --seg-w, --seg-h, --seg-o); o desenho e a animação ficam no CSS (style_estudo.css, .streamlit-seg-trilha).
 * Copiado da Matriz; aqui injetado inline por meta_cpfs.py; um MutationObserver acompanha as re-renderizações do Streamlit. */
(function () {
  if (window.__filtrosAnimados) { window.__filtrosAnimados(); return; }
  const SEL = '[data-testid="stButtonGroup"] [role="radiogroup"]';

  // última posição de cada filtro (pelo rótulo): o Streamlit pode recriar a trilha a cada clique; a nova
  // nasce na posição antiga e desliza até a opção escolhida, em vez de aparecer pronta
  const ultima = new Map();
  const aplicar = (grupo, v) => {
    for (const [k, val] of Object.entries(v)) grupo.style.setProperty('--seg-' + k, val);
  };

  function posicionar(grupo) {
    const novo = !grupo.classList.contains('streamlit-seg-trilha');
    if (novo) grupo.classList.add('streamlit-seg-trilha', 'streamlit-seg-sem-transicao'); // classe antes de medir (muda o layout)
    const chave = grupo.getAttribute('aria-label') || '';
    const ativo = grupo.querySelector('[role="radio"][aria-checked="true"]');
    const g = grupo.getBoundingClientRect();
    if (!g.width) return; // escondido (aba fechada, sidebar recolhida)
    let alvo = { o: '0' };
    if (ativo) {
      const a = ativo.getBoundingClientRect();
      alvo = { x: (a.left - g.left - grupo.clientLeft) + 'px', y: (a.top - g.top - grupo.clientTop) + 'px',
               w: a.width + 'px', h: a.height + 'px', o: '1' };
    }
    if (novo) {
      const antes = ultima.get(chave);
      aplicar(grupo, antes && antes.o === '1' ? antes : alvo);  // começa onde estava (ou já no lugar, na 1ª vez)
      grupo.getBoundingClientRect();                             // fixa o estado inicial antes de animar
      requestAnimationFrame(() => requestAnimationFrame(() => {
        grupo.classList.remove('streamlit-seg-sem-transicao');
        aplicar(grupo, alvo);
      }));
    } else {
      aplicar(grupo, alvo);
    }
    ultima.set(chave, alvo);
  }

  let agendado = false;
  function atualizar() {
    if (agendado) return;
    agendado = true;
    requestAnimationFrame(() => { agendado = false; document.querySelectorAll(SEL).forEach(posicionar); });
  }

  new MutationObserver(atualizar).observe(document.body, {
    // sem 'style'/'class': o próprio script mexe neles e entraria em ciclo
    childList: true, subtree: true, attributes: true, attributeFilter: ['aria-checked', 'aria-expanded'],
  });
  addEventListener('resize', atualizar);
  document.addEventListener('transitionend', e => { if (e.target.closest && e.target.closest('[data-testid="stSidebar"]')) atualizar(); });
  window.__filtrosAnimados = atualizar;
  atualizar();
})();
