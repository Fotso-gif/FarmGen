// Minimal cart frontend helper using fetch()
// Requires elements:
// - data-add-button on product buttons, with data attributes data-product-id, data-name, data-price (cents)
// - a container with id="cart-toast-root" will be created dynamically
(function(){
  function el(html){ const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstChild; }

  // Create toast/root and sticky checkout button containers
  function ensureUI() {
    if (!document.getElementById('cart-toast-root')) {
      document.body.appendChild(el('<div id="cart-toast-root"></div>'));
    }
    if (!document.getElementById('cart-checkout-btn')) {
      const btn = document.createElement('div');
      btn.id = 'cart-checkout-btn';
      btn.className = 'cart-checkout-hidden';
      btn.innerHTML = '<a href="/payments/checkout/" class="cart-checkout-link">🛒 Passer au paiement — <span id="cart-total-display">0,00 €</span></a>';
      document.body.appendChild(btn);
    }
  }

  function showToast(message){
    ensureUI();
    const root = document.getElementById('cart-toast-root');
    const t = document.createElement('div');
    t.className = 'cart-toast';
    t.innerHTML = '<div class="cart-toast-inner">✅ ' + (message || 'Produit ajouté au panier') + '</div>';
    root.appendChild(t);
    setTimeout(()=> t.classList.add('cart-toast-show'), 20);
    setTimeout(()=> { t.classList.remove('cart-toast-show'); setTimeout(()=> root.removeChild(t), 300); }, 2400);
  }

  function updateCheckoutVisibility(total_display, item_count){
    ensureUI();
    const btn = document.getElementById('cart-checkout-btn');
    const span = document.getElementById('cart-total-display');
    if (span) span.textContent = total_display;
    if (item_count && item_count > 0) {
      btn.classList.remove('cart-checkout-hidden');
      btn.classList.add('cart-checkout-visible');
    } else {
      btn.classList.remove('cart-checkout-visible');
      btn.classList.add('cart-checkout-hidden');
    }
  }

  async function addToCart(product_id, name, price_cents, quantity){
    try {
      const res = await fetch('/cart/add/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({product_id: product_id, name: name, price: price_cents, quantity: quantity})
      });
      const j = await res.json();
      if (j && j.success) {
        showToast('Produit ajouté au panier');
        updateCheckoutVisibility(j.total_display, j.item_count);
      } else {
        showToast('Erreur ajout panier');
        console.error('addToCart error', j);
      }
    } catch (e) {
      console.error(e);
      showToast('Erreur réseau');
    }
  }

  // Attach to buttons with data-add-button attribute
  function bindButtons() {
    document.querySelectorAll('[data-add-button]').forEach(btn => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', (ev) => {
        ev.preventDefault();
        const pid = btn.dataset.productId || btn.getAttribute('data-product-id');
        const name = btn.dataset.name || btn.getAttribute('data-name') || 'Produit';
        const price = parseInt(btn.dataset.price || btn.getAttribute('data-price') || '0', 10);
        const qty = parseInt(btn.dataset.quantity || btn.getAttribute('data-quantity') || '1', 10) || 1;
        addToCart(pid, name, price, qty);
      });
    });
  }

  // initialize: bind buttons and fetch current summary to set checkout visibility
  async function init() {
    ensureUI();
    bindButtons();
    try {
      const res = await fetch('/cart/summary/');
      if (res.ok) {
        const j = await res.json();
        updateCheckoutVisibility(j.total_display || (j.total_cents ? (j.total_cents/100).toFixed(2)+' €' : '0,00 €'), j.item_count || 0);
      }
    } catch(e){}
  }

  // Expose global initializer
  window.CartUI = { init: init, addToCart: addToCart };
  // auto init on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', init);
})();
