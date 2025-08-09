function showMessage(message) {
  const box = document.getElementById('messageBox');
  const text = document.getElementById('messageText');
  if (!box || !text) return;
  text.textContent = message;
  box.classList.remove('hidden');
}

function toggleMenu() {
  const panel = document.getElementById('menu-panel');
  if (panel) panel.classList.toggle('open');
}

document.addEventListener('DOMContentLoaded', () => {
  const menuBtn = document.getElementById('menu-button');
  if (menuBtn) menuBtn.addEventListener('click', toggleMenu);

  const closeBtn = document.querySelector('[data-close-menu]');
  if (closeBtn) closeBtn.addEventListener('click', toggleMenu);

  const dismissBtn = document.querySelector('[data-dismiss-message]');
  if (dismissBtn) dismissBtn.addEventListener('click', () => {
    const box = document.getElementById('messageBox');
    if (box) box.classList.add('hidden');
  });

  // Any button with data-action + data-input will redirect to ?url=<value>
  document.querySelectorAll('button[data-action][data-input]').forEach(btn => {
    btn.addEventListener('click', () => {
      const inputId = btn.getAttribute('data-input');
      const action = btn.getAttribute('data-action');
      const input = document.getElementById(inputId);
      if (!input || !input.value) {
        showMessage('Please enter a URL.');
        return;
      }
      window.location.href = `${action}?url=${encodeURIComponent(input.value)}`;
    });
  });
});
