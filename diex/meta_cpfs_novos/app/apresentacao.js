/* Apresentação curta em tela cheia sobre o painel. Abre sozinha uma vez por aba do navegador e pelo botão da barra lateral.
   Sem texto parecido com tag HTML aqui: o st.html descartaria o script inteiro. Fica fora do React (document.body), então trocar filtro não a fecha nem reabre. Se o arquivo não carregar, o painel aparece normalmente. */
(() => {
  const ARQUIVO = 'app/static/apresentacao.bin?v=__VERSAO__', VISTA = 'meta_cpfs_apresentacao';
  const ler = () => { try { return sessionStorage.getItem(VISTA); } catch (e) { return window.__metaCpfsVista; } };
  const marcar = () => { window.__metaCpfsVista = '1'; try { sessionStorage.setItem(VISTA, '1'); } catch (e) { /* aba privada */ } };
  let antes = null;

  function fechar() {
    const el = document.getElementById('apresentacao-painel');
    if (!el) return;
    el.remove(); document.documentElement.style.overflow = '';
    if (antes && antes.focus) antes.focus();
  }
  async function abrir() {
    if (document.getElementById('apresentacao-painel')) return;
    antes = document.activeElement; marcar();
    const el = document.createElement('div');
    el.id = 'apresentacao-painel'; el.setAttribute('role', 'dialog'); el.setAttribute('aria-modal', 'true'); el.setAttribute('aria-label', 'Explicação da meta');
    const espera = Object.assign(document.createElement('p'), { className: 'ap-espera', textContent: 'Carregando a explicação…' });
    const sair = Object.assign(document.createElement('button'), { type: 'button', className: 'ap-sair', textContent: 'Ir para o painel', onclick: fechar });
    el.append(espera, sair);
    document.body.append(el); document.documentElement.style.overflow = 'hidden';
    const limite = new AbortController(), tempo = setTimeout(() => limite.abort(), 20000);
    try {
      const r = await fetch(ARQUIVO, { signal: limite.signal });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const html = await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
      clearTimeout(tempo);
      if (!el.isConnected) return;
      const f = document.createElement('iframe');
      f.title = 'Explicação da meta'; f.srcdoc = html; f.onload = () => f.contentWindow && f.contentWindow.focus();
      el.prepend(f);
    } catch (e) { clearTimeout(tempo); console.error('Apresentação não carregou:', e); if (el.isConnected) fechar(); }
  }
  if (!window.__metaCpfsOuvindo) {
    window.__metaCpfsOuvindo = true;
    document.addEventListener('click', e => { if (e.target.closest && e.target.closest('#apresentacao-btn')) window.__metaCpfsAbrir(); });
    addEventListener('keydown', e => { if (e.key === 'Escape') window.__metaCpfsFechar(); });
    addEventListener('message', e => {
      const f = document.querySelector('#apresentacao-painel iframe');
      if (!f || e.source !== f.contentWindow || !e.data) return;
      if (e.data.meta_cpfs === 'fechar') window.__metaCpfsFechar();
      if (e.data.meta_cpfs === 'pronta') { const p = document.querySelector('#apresentacao-painel .ap-espera'); if (p) p.remove(); }
    });
  }
  window.__metaCpfsAbrir = abrir; window.__metaCpfsFechar = fechar;
  if (!ler()) abrir();
})();
