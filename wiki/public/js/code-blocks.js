// Initialize syntax highlighting and code block enhancements
function initCodeBlocks() {
    // Record the authored language before highlight.js auto-detection adds its
    // own language-* class, so the label mirrors the editor ("auto" when unset).
    document.querySelectorAll('pre > code').forEach(function(codeBlock) {
        if (codeBlock.dataset.language !== undefined) return;
        const match = codeBlock.className.match(/language-(\S+)/);
        codeBlock.dataset.language = match ? match[1] : '';
    });

    // First run syntax highlighting
    if (typeof hljs !== 'undefined') {
        hljs.highlightAll();
    }

    // Then enhance code blocks to match the editor's code block node view:
    // line-number gutter + hover-revealed toolbar (language label, copy button)
    document.querySelectorAll('pre code.hljs').forEach(function(codeBlock) {
        const pre = codeBlock.parentElement;

        // Skip if already processed
        if (pre.classList.contains('code-block-enhanced')) return;
        pre.classList.add('code-block-enhanced');

        // Strip trailing whitespace so it doesn't render as empty rows.
        const lastChild = codeBlock.lastChild;
        if (lastChild && lastChild.nodeType === Node.TEXT_NODE) {
            lastChild.nodeValue = lastChild.nodeValue.replace(/\s+$/, '\n');
        }

        // Line-number gutter (one number per line, like the editor)
        const lineCount = codeBlock.textContent.replace(/\n$/, '').split('\n').length;
        const gutter = document.createElement('span');
        gutter.className = 'code-block-gutter';
        gutter.setAttribute('aria-hidden', 'true');
        for (let n = 1; n <= lineCount; n++) {
            const line = document.createElement('span');
            line.textContent = n;
            gutter.appendChild(line);
        }
        pre.insertBefore(gutter, codeBlock);

        // Toolbar (positioned top-right inside pre, revealed on hover)
        const toolbar = document.createElement('div');
        toolbar.className = 'code-block-toolbar';

        // Language label ("auto" when the block has no explicit language)
        const langLabel = document.createElement('span');
        langLabel.className = 'code-block-lang';
        langLabel.textContent = codeBlock.dataset.language || 'auto';
        toolbar.appendChild(langLabel);

        // Copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'code-block-copy';
        copyBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>';
        copyBtn.title = window.wikiT ? wikiT('Copy code') : 'Copy code';
        const copyIcon = copyBtn.innerHTML;
        const checkIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>';
        const failIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>';
        let resetTimer;
        copyBtn.addEventListener('click', function() {
            window.wikiCopyText(codeBlock.textContent).then(function(ok) {
                copyBtn.innerHTML = ok ? checkIcon : failIcon;
                clearTimeout(resetTimer);
                resetTimer = setTimeout(function() { copyBtn.innerHTML = copyIcon; }, 2000);
            });
        });
        toolbar.appendChild(copyBtn);

        // Insert toolbar inside pre element
        pre.appendChild(toolbar);
    });

    initCodeGroups();
    initTables();
}

// Consecutive fences wrapped in `.wiki-code-group` become one block with tabs.
// A tab is named by the fence's label (```json site_config.json), else by its
// language. The blocks stay in the page; only the active one is shown.
function initCodeGroups() {
    document.querySelectorAll('.wiki-code-group').forEach(function(group) {
        if (group.dataset.tabsReady) return;
        const blocks = Array.from(group.children).filter(function(el) {
            return el.tagName === 'PRE';
        });
        if (blocks.length < 2) return;
        group.dataset.tabsReady = '1';

        const bar = document.createElement('div');
        bar.className = 'wiki-code-group-tabs';
        bar.setAttribute('role', 'tablist');

        const tabs = blocks.map(function(pre, index) {
            const code = pre.querySelector('code');
            const tab = document.createElement('button');
            tab.type = 'button';
            tab.className = 'wiki-code-group-tab';
            tab.setAttribute('role', 'tab');
            tab.textContent = pre.dataset.label || (code && code.dataset.language) || 'auto';
            tab.addEventListener('click', function() { select(index); });
            bar.appendChild(tab);
            return tab;
        });

        function select(active) {
            blocks.forEach(function(pre, index) {
                pre.classList.toggle('is-active-tab', index === active);
            });
            tabs.forEach(function(tab, index) {
                tab.classList.toggle('is-active', index === active);
                tab.setAttribute('aria-selected', index === active ? 'true' : 'false');
            });
        }

        group.insertBefore(bar, group.firstChild);
        select(0);
    });
}

// Copy text to the clipboard; resolves true when it worked. `navigator.clipboard`
// exists only on a secure origin (HTTPS or localhost), so a wiki served over
// plain HTTP, or inside a frame that forbids it, would fail without a sound.
// The fallback is a hidden textarea and execCommand('copy'), which works wherever
// a click does.
window.wikiCopyText = function(text) {
    function viaSelection() {
        const area = document.createElement('textarea');
        area.value = text;
        area.setAttribute('readonly', '');
        area.style.position = 'fixed';
        area.style.top = '0';
        area.style.opacity = '0';
        const previous = document.activeElement;
        document.body.appendChild(area);
        area.select();
        area.setSelectionRange(0, text.length);
        let ok = false;
        try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
        document.body.removeChild(area);
        if (previous && previous.focus) previous.focus();
        return ok;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text).then(function() { return true; }, function() { return viaSelection(); });
    }
    return Promise.resolve(viaSelection());
};

// Tables scroll sideways instead of overflowing the column, and a header cell
// sorts its column. A table with fewer than three body rows has nothing to sort.
function initTables() {
    const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

    document.querySelectorAll('#wiki-content table').forEach(function(table) {
        if (table.dataset.enhanced) return;
        table.dataset.enhanced = '1';

        const wrap = document.createElement('div');
        wrap.className = 'wiki-table-wrap';
        table.parentNode.insertBefore(wrap, table);
        wrap.appendChild(table);

        const tbody = table.tBodies[0];
        const headRow = table.tHead && table.tHead.rows[0];
        if (!tbody || !headRow || tbody.rows.length < 3) return;

        Array.from(headRow.cells).forEach(function(th, column) {
            th.classList.add('sortable');
            th.tabIndex = 0;
            th.setAttribute('role', 'columnheader');
            const sort = function() {
                const ascending = th.getAttribute('aria-sort') !== 'ascending';
                Array.from(headRow.cells).forEach(function(other) { other.removeAttribute('aria-sort'); });
                th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
                const rows = Array.from(tbody.rows);
                rows.sort(function(a, b) {
                    const left = (a.cells[column] || {}).textContent || '';
                    const right = (b.cells[column] || {}).textContent || '';
                    return (ascending ? 1 : -1) * collator.compare(left.trim(), right.trim());
                });
                rows.forEach(function(row) { tbody.appendChild(row); });
            };
            th.addEventListener('click', sort);
            th.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    sort();
                }
            });
        });
    });
}

// Printing: open every collapsible section (a closed one prints as a bare
// heading) and use the light theme whatever the reader chose, then put both back.
(function () {
    let restore = null;

    window.addEventListener('beforeprint', function() {
        const closed = Array.from(document.querySelectorAll('#wiki-content details:not([open])'));
        closed.forEach(function(el) { el.setAttribute('open', ''); });
        const root = document.documentElement;
        const theme = root.getAttribute('data-theme');
        if (theme && theme !== 'light') root.setAttribute('data-theme', 'light');
        restore = function() {
            closed.forEach(function(el) { el.removeAttribute('open'); });
            if (theme) root.setAttribute('data-theme', theme);
        };
    });

    window.addEventListener('afterprint', function() {
        if (restore) restore();
        restore = null;
    });
})();

// Initialize on page load
document.addEventListener('DOMContentLoaded', initCodeBlocks);

// Expose globally for SPA navigation
window.initCodeBlocks = initCodeBlocks;
