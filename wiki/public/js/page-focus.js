// Reader helpers that move the eye to where a click or a search sent you:
// a brief flash on the heading a TOC link jumps to, and the first search match
// scrolled into view with the matched words lightly marked. All client side,
// on the page already rendered: no extra request.
(function () {
    const HIT_CAP = 100;
    const HIT_LIFETIME_MS = 6000;
    const MIN_TERM = 2;

    function fold(text) {
        // One output char per input char, so offsets in the folded string map
        // straight back onto the original text node.
        let out = '';
        for (const ch of text) {
            const folded = ch.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
            out += folded.length === ch.length ? folded : ch.toLowerCase();
        }
        return out;
    }

    function termsOf(query) {
        const seen = new Set();
        return (query || '')
            .split(/\s+/)
            .map(fold)
            .filter((t) => t.length >= MIN_TERM && !seen.has(t) && seen.add(t));
    }

    function clearHits(root) {
        root.querySelectorAll('mark.wiki-hit').forEach((mark) => {
            const parent = mark.parentNode;
            if (!parent) return;
            parent.replaceChild(document.createTextNode(mark.textContent), mark);
            parent.normalize();
        });
    }

    function textNodes(root) {
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                if (!node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
                const parent = node.parentElement;
                if (!parent || parent.closest('script, style, svg, .heading-anchor, .code-block-gutter, .code-block-toolbar')) {
                    return NodeFilter.FILTER_REJECT;
                }
                return NodeFilter.FILTER_ACCEPT;
            },
        });
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        return nodes;
    }

    // Longest term first so "config" never claims the start of "configuración"
    // before the full word gets its turn.
    function rangesIn(folded, terms) {
        const ranges = [];
        for (const term of terms) {
            let from = 0;
            for (;;) {
                const at = folded.indexOf(term, from);
                if (at === -1) break;
                ranges.push([at, at + term.length]);
                from = at + term.length;
            }
        }
        ranges.sort((a, b) => a[0] - b[0] || b[1] - a[1]);
        const merged = [];
        for (const range of ranges) {
            const last = merged[merged.length - 1];
            if (last && range[0] < last[1]) last[1] = Math.max(last[1], range[1]);
            else merged.push(range);
        }
        return merged;
    }

    function markNode(node, ranges) {
        const text = node.nodeValue;
        const frag = document.createDocumentFragment();
        const marks = [];
        let cursor = 0;
        for (const [start, end] of ranges) {
            if (start > cursor) frag.appendChild(document.createTextNode(text.slice(cursor, start)));
            const mark = document.createElement('mark');
            mark.className = 'wiki-hit';
            mark.textContent = text.slice(start, end);
            frag.appendChild(mark);
            marks.push(mark);
            cursor = end;
        }
        if (cursor < text.length) frag.appendChild(document.createTextNode(text.slice(cursor)));
        node.parentNode.replaceChild(frag, node);
        return marks;
    }

    let hitTimer = null;

    window.wikiFocusMatch = function (query) {
        const root = document.getElementById('wiki-content');
        const terms = termsOf(query);
        if (!root || terms.length === 0) return false;

        clearTimeout(hitTimer);
        clearHits(root);

        const marks = [];
        for (const node of textNodes(root)) {
            if (marks.length >= HIT_CAP) break;
            const ranges = rangesIn(fold(node.nodeValue), terms);
            if (ranges.length) marks.push(...markNode(node, ranges));
        }
        if (marks.length === 0) return false;

        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        marks[0].scrollIntoView({ block: 'center', behavior: reduceMotion ? 'auto' : 'smooth' });
        hitTimer = setTimeout(() => clearHits(root), HIT_LIFETIME_MS);
        return true;
    };

    function flashHeading(id) {
        const heading = id && document.getElementById(id);
        if (!heading) return;
        heading.classList.remove('wiki-flash');
        // Reflow so a second click on the same entry replays the animation.
        void heading.offsetWidth;
        heading.classList.add('wiki-flash');
        heading.addEventListener('animationend', () => heading.classList.remove('wiki-flash'), { once: true });
    }
    window.wikiFlashHeading = flashHeading;

    document.addEventListener('click', (event) => {
        const link = event.target.closest('[data-toc-link], .heading-anchor');
        if (!link) return;
        flashHeading(link.dataset.tocLink || link.getAttribute('href')?.slice(1));
    });

    window.addEventListener('hashchange', () => flashHeading(decodeURIComponent(location.hash.slice(1))));

    // Opened from a search result in a new tab or a full load: `?q=` carries the
    // query. Read it now, before the navigation store rewrites the URL.
    const params = new URLSearchParams(location.search);
    const initialQuery = params.get('q');
    document.addEventListener('DOMContentLoaded', () => {
        // Defer past Alpine's own first render and code-block enhancement.
        if (initialQuery) setTimeout(() => window.wikiFocusMatch(initialQuery), 150);
        else if (location.hash) setTimeout(() => flashHeading(decodeURIComponent(location.hash.slice(1))), 150);
    });
})();
