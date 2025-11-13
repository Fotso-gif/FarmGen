(() => {
  // Utility: read cookie for csrftoken
  function getCookie(name) {
    const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }

  // Formats cents or euro decimal to display string
  function formatPriceFromCents(cents) {
    const c = Number(cents || 0);
    return (c / 100).toFixed(2).replace('.', ',') + ' €';
  }

  function formatPriceFromEurosString(eurosStr) {
    // accept "4.50" or "4,50"
    const normalized = ('' + eurosStr).replace(',', '.').trim();
    const val = parseFloat(normalized) || 0;
    return Math.round(val * 100);
  }

  // DOM refs
  const cartToggleBtn = document.getElementById('cart-toggle-btn');
  const cartCount = document.getElementById('cart-count');
  const cartDrawer = document.getElementById('cart-drawer');
  const drawerBackdrop = document.getElementById('drawer-backdrop');
  const cartDrawerClose = document.getElementById('cart-drawer-close');
  const cartItemsContainer = document.getElementById('cart-items');
  const drawerTotal = document.getElementById('drawer-total');
  const summaryTotal = document.getElementById('summary-total');
  const summaryCount = document.getElementById('summary-count');
  const payNowBtn = document.getElementById('pay-now');
  const payNowSmall = document.getElementById('pay-now-small');
  const quickAddForm = document.getElementById('quick-add-form');

  // Show toast using Toastify
  function showToast(message) {
    if (window.Toastify) {
      Toastify({ text: message, duration: 2200, gravity: "bottom", position: "center", backgroundColor: "#16a34a" }).showToast();
    } else {
      // fallback minimal toast
      const d = document.createElement('div');
      d.style = 'position:fixed;left:50%;transform:translateX(-50%);bottom:24px;background:#16a34a;color:#fff;padding:8px 12px;border-radius:8px;z-index:1200';
      d.textContent = message;
      document.body.appendChild(d);
      setTimeout(()=> document.body.removeChild(d),2200);
    }
  }

  // Update UI elements with summary
  function updateSummary(total_cents, item_count) {
    if (cartCount) {
      if (!item_count || item_count === 0) cartCount.classList.add('hidden');
      else cartCount.classList.remove('hidden');
      cartCount.innerText = item_count || 0;
    }
    if (drawerTotal) drawerTotal.innerText = formatPriceFromCents(total_cents);
    if (summaryTotal) summaryTotal.innerText = formatPriceFromCents(total_cents);
    if (summaryCount) summaryCount.innerText = item_count || 0;

    const visible = (item_count && item_count > 0);
    if (payNowBtn) { payNowBtn.style.display = visible ? 'block' : 'none'; }
    if (payNowSmall) { payNowSmall.style.display = visible ? 'block' : 'none'; }
  }

  // Escape HTML to avoid injection
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (m) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]); });
  }

  // Render drawer items from cart data (cart is dict)
  function renderDrawer(cart) {
    if (!cartItemsContainer) return;
    cartItemsContainer.innerHTML = '';
    const keys = Object.keys(cart || {});
    if (keys.length === 0) {
      cartItemsContainer.innerHTML = '<div class="p-4 text-sm text-gray-500">Votre panier est vide.</div>';
      return;
    }
    keys.forEach(pid => {
      const it = cart[pid];
      const row = document.createElement('div');
      row.className = 'cart-item flex items-center justify-between p-3 border-b';
      row.innerHTML = `
        <div class="min-w-0">
          <div class="font-medium truncate">${escapeHtml(it.name)}</div>
          <div class="text-sm text-gray-500">Prix: ${formatPriceFromCents(it.price)} × ${it.quantity}</div>
        </div>
        <div class="ml-3 flex items-center space-x-2">
          <button class="remove-btn text-sm px-2 py-1 bg-red-500 text-white rounded" data-product-id="${escapeHtml(pid)}">Supprimer</button>
        </div>
      `;
      cartItemsContainer.appendChild(row);
    });

    // attach remove handlers
    cartItemsContainer.querySelectorAll('.remove-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        await removeFromCart(btn.dataset.productId);
      });
    });
  }

  // Fetch cart summary from server
  async function loadCart() {
    try {
      const res = await fetch('/payments/api/cart/');
      if (!res.ok) return;
      const j = await res.json();
      renderDrawer(j.cart || {});
      updateSummary(j.total_cents || 0, j.item_count || 0);
    } catch (err) {
      console.error('loadCart error', err);
    }
  }

  // Add to cart via POST JSON
  async function addToCart(payload) {
    try {
      const csrftoken = getCookie('csrftoken');
      const res = await fetch('/payments/api/cart/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify(payload)
      });
      const j = await res.json();
      if (res.ok && j.success) {
        showToast('✅ Produit ajouté au panier');
        await loadCart();
        openDrawerTemporary();
      } else {
        showToast(j.detail || j.error || 'Erreur ajout panier');
        console.error('addToCart error', j);
      }
    } catch (err) {
      console.error('addToCart network', err);
      showToast('Erreur réseau');
    }
  }

  // Remove item via DELETE JSON
  async function removeFromCart(product_id) {
    try {
      const csrftoken = getCookie('csrftoken');
      const res = await fetch('/payments/api/cart/', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ product_id })
      });
      const j = await res.json();
      if (res.ok) {
        showToast('Produit supprimé');
        await loadCart();
      } else {
        showToast(j.detail || 'Erreur suppression');
        console.error('remove error', j);
      }
    } catch (err) {
      console.error('removeFromCart', err);
      showToast('Erreur réseau');
    }
  }

  // Drawer open/close logic
  function openDrawer() {
    if (!cartDrawer) return;
    cartDrawer.classList.add('open');
    if (drawerBackdrop) drawerBackdrop.classList.remove('hidden');
    cartDrawer.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }
  function closeDrawer() {
    if (!cartDrawer) return;
    cartDrawer.classList.remove('open');
    if (drawerBackdrop) drawerBackdrop.classList.add('hidden');
    cartDrawer.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  function openDrawerTemporary() {
    openDrawer();
    setTimeout(closeDrawer, 1600);
  }

  // Wire UI events
  if (cartToggleBtn) cartToggleBtn.addEventListener('click', () => { loadCart(); openDrawer(); });
  if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeDrawer);
  if (cartDrawerClose) cartDrawerClose.addEventListener('click', closeDrawer);

  if (quickAddForm) {
    quickAddForm.addEventListener('submit', (ev) => {
      ev.preventDefault();
      const fd = new FormData(quickAddForm);
      const pid = fd.get('product_id');
      const name = fd.get('name');
      const priceEur = fd.get('price');
      const qty = Number(fd.get('quantity') || 1);
      const price_cents = formatPriceFromEurosString(priceEur);
      addToCart({ product_id: pid, name, price: price_cents, quantity: qty });
      quickAddForm.reset();
    });
  }

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', loadCart);

  // Expose for debugging
  window.FarmGenCart = { loadCart, addToCart, removeFromCart, openDrawer, closeDrawer };
})();
