(() => {
  const show = (message, type = "success") => {
    let container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.className = "toast-container";
      container.setAttribute("aria-live", "polite");
      container.setAttribute("aria-atomic", "false");
      document.body.append(container);
    }

    const toast = document.createElement("div");
    toast.className = `app-toast toast-${type}`;
    toast.setAttribute("role", type === "error" ? "alert" : "status");
    const icon = document.createElement("span");
    icon.className = "toast-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = type === "error" ? "!" : "✓";
    const text = document.createElement("span");
    text.className = "toast-text";
    text.textContent = message;
    const close = document.createElement("button");
    close.className = "toast-close";
    close.type = "button";
    close.setAttribute("aria-label", "Dismiss notification");
    close.textContent = "×";
    close.addEventListener("click", () => toast.remove());
    toast.append(icon, text, close);
    container.append(toast);
    window.setTimeout(() => toast.remove(), 5000);
  };

  window.HireSenseToast = { show };
})();
