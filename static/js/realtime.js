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
            if (o.status === 'Pendiente' || o.status === 'Cotizado' || o.status === 'En Cola') enCola++;
            if (o.status === 'Imprimiendo') imprimiendo++;
            if (o.status === 'Terminado') terminados++;

            const card = document.querySelector(`[data-order-id="${o.id}"]`);
            if (!card) return;

            const prevStatus = card.getAttribute('data-status');
            const prevTime = card.getAttribute('data-time');
            const prevPrice = card.getAttribute('data-price');

            const newTimeStr = o.print_time_est !== null ? String(o.print_time_est) : '';
            const newPriceStr = o.price !== null ? String(o.price) : '';

            if (prevStatus !== o.status || prevTime !== newTimeStr || prevPrice !== newPriceStr) {
                card.setAttribute('data-status', o.status);
                card.setAttribute('data-time', newTimeStr);
                card.setAttribute('data-price', newPriceStr);

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

                const priceEl = card.querySelector('.js-price-est');
                if (priceEl && o.price) {
                    priceEl.textContent = `Cotización: $${Number(o.price).toFixed(2)} MXN`;
                }

                const quoteBox = card.querySelector('.js-quote-actions');
                if (quoteBox) {
                    if (o.status === 'Cotizado') {
                        quoteBox.innerHTML = `
                            <form action="/order/${o.id}/respond" method="POST" style="display: flex; gap: 0.5rem;">
                                <button type="submit" name="action" value="accept" class="btn-primary" style="flex: 1; padding: 0.5rem; font-size: 0.8rem;">
                                    Aceptar Oferta
                                </button>
                                <button type="submit" name="action" value="decline" class="btn-secondary" style="flex: 1; padding: 0.5rem; font-size: 0.8rem;">
                                    Declinar
                                </button>
                            </form>`;
                    } else {
                        quoteBox.innerHTML = '';
                    }
                }

                const priceNotice = (o.status === 'Cotizado' && o.price) ? ` ($${Number(o.price).toFixed(2)} MXN)` : '';
                showVisualAlert(`Actualización en tiempo real: Pedido #${o.id} (${o.filename}) → ${o.status}${priceNotice}`);
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