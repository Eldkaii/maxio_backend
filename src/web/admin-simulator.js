// Initialized only after admin.js has verified the signed-in administrator.
window.initSimulatorLog = function () {
  const panel = document.querySelector('#simulator-panel');
  if (!panel || panel.dataset.initialized) return;
  panel.dataset.initialized = 'true';
  panel.hidden = false;
  const log = panel.querySelector('#simulator-log');
  const status = panel.querySelector('#simulator-status');
  const refresh = panel.querySelector('#simulator-refresh');
  const limit = panel.querySelector('#simulator-limit');
  const auto = panel.querySelector('#simulator-auto');
  let busy = false, timer, controller, stopped = false, loaded = false;

  function schedule() {
    clearTimeout(timer);
    if (!stopped && auto.checked && !document.hidden) timer = setTimeout(load, 15000);
  }

  async function load() {
    if (busy || stopped) return;
    clearTimeout(timer);
    busy = true;
    refresh.disabled = true;
    limit.disabled = true;
    controller = new AbortController();
    try {
      const data = await adminApi(`/maxio/users/admin/simulator/log?limit=${limit.value}`, {
        signal: controller.signal, cache: 'no-store'
      });
      const follow = !loaded || log.scrollHeight - log.scrollTop - log.clientHeight < 40;
      const scrollTop = log.scrollTop;
      const fragment = document.createDocumentFragment();
      for (const line of data.lines) {
        const row = document.createElement('span');
        row.className = 'simulator-line';
        if (line.includes(' | ERROR | ') || line.includes(' | CRITICAL | ')) row.classList.add('error');
        else if (line.includes(' | WARNING | ')) row.classList.add('warning');
        row.textContent = line;
        fragment.append(row);
      }
      log.replaceChildren(fragment);
      loaded = true;
      status.dataset.error = 'false';
      if (!data.lines.length) {
        log.textContent = 'Todavía no hay acciones registradas.';
        status.textContent = data.available ? 'El archivo de actividad está vacío.' : 'El simulador aún no generó un log.';
      } else {
        const time = new Date().toLocaleTimeString('es-UY');
        status.textContent = `${data.lines.length} registros${data.truncated ? ' más recientes' : ''} · Actualizado ${time} · Últimos al final`;
      }
      log.scrollTop = follow ? log.scrollHeight : scrollTop;
    } catch (error) {
      if (error.name === 'AbortError') return;
      status.dataset.error = 'true';
      status.textContent = 'No se pudo actualizar la actividad. ' + error.message;
      if (error.status === 401 || error.status === 403) {
        stopped = true;
        auto.checked = false;
        log.replaceChildren();
      }
    } finally {
      busy = false;
      refresh.disabled = stopped;
      limit.disabled = stopped;
      schedule();
    }
  }

  refresh.addEventListener('click', load);
  limit.addEventListener('change', load);
  auto.addEventListener('change', schedule);
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && auto.checked) load();
    else clearTimeout(timer);
  });
  window.addEventListener('pagehide', () => { stopped = true; clearTimeout(timer); controller?.abort(); });
  window.addEventListener('pageshow', event => {
    if (event.persisted) { stopped = false; load(); }
  });
  load();
};
