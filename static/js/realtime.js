document.addEventListener('DOMContentLoaded', () => {
    const alertBox = document.getElementById('realtime-alert-box');
    const source = new EventSource('/stream/orders');

    function showVisualAlert(message) {
        if (!alertBox) return;
        const toast = document.createElement('div');
        toast.className = 'flash-message success';
        toast.style.cssText = 'padding: 0.9rem 1.2rem; margin-bottom: 1rem; border: 2px solid var(--black-ink); background: var(--sand-bg); font-weight: bold;';
        toast.textContent = message;
        alertBox.prepend(toast);
        setTimeout(() => toast.remove(), 7000);
    }

    source.onmessage = (event) => {
        const orders = JSON.parse(event.data);
        let enCola = 0;
        let imprimiendo = 0;
        let terminados = 0;

        orders.forEach((o) => {
            if (o.status === 'Pendiente' || o.status === 'En Cola') enCola++;
            if (o.status === 'Imprimiendo') imprimiendo++;
            if (o.status === 'Terminado') terminados++;

            const card = document.querySelector(`[data-order-id="${o.id}"]`);
            if (!card) return;

            const prevStatus = card.getAttribute('data-status');
            const prevTime = card.getAttribute('data-time');
            const newTimeStr = o.print_time_est !== null ? String(o.print_time_est) : '';

            if (prevStatus !== o.status || prevTime !== newTimeStr) {
                card.setAttribute('data-status', o.status);
                card.setAttribute('data-time', newTimeStr);

                const badge = card.querySelector('.js-status-badge');
                if (badge) {
                    badge.textContent = o.status.toUpperCase();
                    badge.className = 'status-indicator js-status-badge ' +
                        (o.status === 'Imprimiendo' ? 'printing' : (o.status === 'Terminado' ? '' : 'pending'));
                }

                const timeEl = card.querySelector('.js-time-est');
                if (timeEl && o.print_time_est) {
                    timeEl.textContent = `Tiempo Est: ${o.print_time_est} hrs`;
                }

                showVisualAlert(`Actualización en tiempo real: Pedido #${o.id} (${o.filename}) → ${o.status}`);
            }
        });

        const elCola = document.getElementById('stat-cola');
        const elImp = document.getElementById('stat-imprimiendo');
        const elTerm = document.getElementById('stat-terminados');
        if (elCola) elCola.textContent = enCola;
        if (elImp) elImp.textContent = imprimiendo;
        if (elTerm) elTerm.textContent = terminados;
    };
});