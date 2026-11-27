// Large Mermaid diagrams shrink to the text column until their labels are
// unreadable. Each rendered diagram gets a toolbar to open it full screen
// (zoom, pan, fit) or download it as SVG.
(function () {
  const t = (text) => (window.wikiT ? window.wikiT(text) : text);

  // Lucide paths, inline: the reader has no icon set at runtime.
  const ICONS = {
    maximize:
      '<path d="M15 3h6v6"/><path d="m21 3-7 7"/><path d="m3 21 7-7"/><path d="M9 21H3v-6"/>',
    download:
      '<path d="M12 15V3"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/>',
    zoomIn:
      '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/>',
    zoomOut:
      '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M8 11h6"/>',
    fit: '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/>',
    close: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  };

  const MIN_SCALE = 0.1;
  const MAX_SCALE = 8;
  const STEP = 1.25;

  function iconButton(icon, label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "wiki-mermaid-btn";
    button.title = label;
    button.setAttribute("aria-label", label);
    button.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[icon]}</svg>`;
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      onClick();
    });
    return button;
  }

  function diagramSvg(el) {
    return el.querySelector(":scope > svg");
  }

  // Natural size from the viewBox: mermaid renders width="100%" with a
  // max-width, which says nothing about how big the drawing really is.
  function naturalSize(svg) {
    const box = svg.viewBox?.baseVal;
    if (box && box.width && box.height) return { width: box.width, height: box.height };
    const rect = svg.getBoundingClientRect();
    return { width: rect.width || 800, height: rect.height || 600 };
  }

  function fileName() {
    return window.location.pathname.split("/").filter(Boolean).pop() || "diagram";
  }

  function downloadSvg(el) {
    const svg = diagramSvg(el);
    if (!svg) return;
    const clone = svg.cloneNode(true);
    const { width, height } = naturalSize(svg);
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("width", String(width));
    clone.setAttribute("height", String(height));
    clone.style.removeProperty("max-width");
    const markup = `<?xml version="1.0" encoding="UTF-8"?>\n${new XMLSerializer().serializeToString(clone)}`;
    const url = URL.createObjectURL(new Blob([markup], { type: "image/svg+xml" }));
    const link = document.createElement("a");
    const index = Array.from(document.querySelectorAll(".mermaid[data-processed]")).indexOf(el);
    link.href = url;
    link.download = `${fileName()}-diagram-${index + 1}.svg`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  // ---------- Full screen viewer ----------

  let viewer = null;

  function buildViewer() {
    const root = document.createElement("div");
    root.className = "wiki-mermaid-viewer";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", t("Diagram"));
    root.hidden = true;

    const bar = document.createElement("div");
    bar.className = "wiki-mermaid-viewer-bar";
    const zoomLabel = document.createElement("span");
    zoomLabel.className = "wiki-mermaid-viewer-zoom";

    const stage = document.createElement("div");
    stage.className = "wiki-mermaid-viewer-stage";
    const canvas = document.createElement("div");
    canvas.className = "wiki-mermaid-viewer-canvas";
    stage.appendChild(canvas);

    const state = { scale: 1, x: 0, y: 0, size: { width: 0, height: 0 }, source: null, lastFocus: null };

    function apply() {
      canvas.style.transform = `translate(${state.x}px, ${state.y}px) scale(${state.scale})`;
      zoomLabel.textContent = `${Math.round(state.scale * 100)}%`;
    }

    function fit() {
      const rect = stage.getBoundingClientRect();
      const pad = 48;
      const scale = Math.min(
        (rect.width - pad) / state.size.width,
        (rect.height - pad) / state.size.height,
      );
      state.scale = Math.min(Math.max(scale, MIN_SCALE), MAX_SCALE);
      state.x = (rect.width - state.size.width * state.scale) / 2;
      state.y = (rect.height - state.size.height * state.scale) / 2;
      apply();
    }

    // Zoom about a point of the stage, so what is under the cursor stays put.
    function zoomTo(scale, cx, cy) {
      const rect = stage.getBoundingClientRect();
      const px = cx ?? rect.width / 2;
      const py = cy ?? rect.height / 2;
      const next = Math.min(Math.max(scale, MIN_SCALE), MAX_SCALE);
      state.x = px - ((px - state.x) * next) / state.scale;
      state.y = py - ((py - state.y) * next) / state.scale;
      state.scale = next;
      apply();
    }

    stage.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        const rect = stage.getBoundingClientRect();
        const factor = Math.exp(-event.deltaY * 0.0015);
        zoomTo(state.scale * factor, event.clientX - rect.left, event.clientY - rect.top);
      },
      { passive: false },
    );

    let drag = null;
    stage.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      drag = { x: event.clientX - state.x, y: event.clientY - state.y };
      stage.setPointerCapture(event.pointerId);
      stage.classList.add("is-dragging");
    });
    stage.addEventListener("pointermove", (event) => {
      if (!drag) return;
      state.x = event.clientX - drag.x;
      state.y = event.clientY - drag.y;
      apply();
    });
    const endDrag = () => {
      drag = null;
      stage.classList.remove("is-dragging");
    };
    stage.addEventListener("pointerup", endDrag);
    stage.addEventListener("pointercancel", endDrag);

    function close() {
      root.hidden = true;
      canvas.innerHTML = "";
      document.body.classList.remove("wiki-mermaid-viewer-open");
      document.removeEventListener("keydown", onKey, true);
      state.lastFocus?.focus?.();
    }

    function onKey(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        close();
      } else if (event.key === "+" || event.key === "=") {
        zoomTo(state.scale * STEP);
      } else if (event.key === "-") {
        zoomTo(state.scale / STEP);
      } else if (event.key === "0") {
        fit();
      }
    }

    const closeButton = iconButton("close", t("Close"), close);
    bar.append(
      iconButton("zoomOut", t("Zoom out"), () => zoomTo(state.scale / STEP)),
      zoomLabel,
      iconButton("zoomIn", t("Zoom in"), () => zoomTo(state.scale * STEP)),
      iconButton("fit", t("Fit to screen"), fit),
      iconButton("download", t("Download SVG"), () => state.source && downloadSvg(state.source)),
      closeButton,
    );
    root.append(bar, stage);
    document.body.appendChild(root);

    function open(el) {
      const svg = diagramSvg(el);
      if (!svg) return;
      state.source = el;
      state.lastFocus = document.activeElement;
      state.size = naturalSize(svg);
      // The clone keeps its id: mermaid scopes the SVG's <style> to it.
      const clone = svg.cloneNode(true);
      clone.setAttribute("width", String(state.size.width));
      clone.setAttribute("height", String(state.size.height));
      clone.style.removeProperty("max-width");
      canvas.replaceChildren(clone);
      root.hidden = false;
      document.body.classList.add("wiki-mermaid-viewer-open");
      document.addEventListener("keydown", onKey, true);
      closeButton.focus();
      fit();
    }

    return { open };
  }

  function openFullScreen(el) {
    viewer ||= buildViewer();
    viewer.open(el);
  }

  function decorate(el) {
    if (!diagramSvg(el)) return;
    el.querySelector(":scope > .wiki-mermaid-toolbar")?.remove();
    const toolbar = document.createElement("div");
    toolbar.className = "wiki-mermaid-toolbar";
    toolbar.append(
      iconButton("maximize", t("Full screen"), () => openFullScreen(el)),
      iconButton("download", t("Download SVG"), () => downloadSvg(el)),
    );
    el.appendChild(toolbar);
    // The element outlives re-renders (theme flips); listen once.
    if (!el.hasAttribute("data-mermaid-viewer")) {
      el.setAttribute("data-mermaid-viewer", "");
      el.addEventListener("dblclick", () => openFullScreen(el));
    }
  }

  window.wikiMermaidViewer = { decorate, open: openFullScreen, download: downloadSvg };
})();
