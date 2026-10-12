# Long Page Save Performance

Date: 2026-10-12
Status: **Fixed.** Measured in node; the editor itself was not run in a browser against a real long page.

## Problem

Saving a long page froze the tab ("Saving…", then the browser's "page not
responding"). Documentation pages are long by design, so this is the normal case.

## Cause

Every save re-parses the page's markdown in the browser (`canonicalizeMarkdown`).
That parse was O(n^2):

| Page size | Parse time before | after |
|-----------|------------------:|------:|
| 47 KB | 0.2 s | -- |
| 95 KB | 1.1 s | 0.11 s |
| 190 KB | 5.2 s | 0.11 s |
| 380 KB | ~13 s | 0.18 s |

- TipTap's ordered list tokenizer splits the **whole remaining document** into
  lines each time marked tries it (every block): ~65% of the time.
- Each custom tokenizer's `start()` (callouts, images, iframes, mermaid, PDF,
  video, code groups) searched the whole remaining document per paragraph.

## Fix

- `startInParagraph`: a paragraph cannot pass a blank line, so `start()` searches
  only up to the next one.
- `boundedListTokenize`: the ordered list tokenizer is skipped when the next line
  cannot open a list, and otherwise runs on a window that grows until the list
  ends inside it. Tests prove it returns the same token as the original, across
  windows, nested lists and non-lists.

## Second pass: loading and typing in a long page

Measured in a production build with a realistic 1,600-line page (80 code blocks,
40 tables, nested lists), the real `WikiEditor`:

- Load is linear, about 2 ms per line (1,600 lines: ~3.9 s; 6,400 lines: ~14 s).
- Code blocks dominate it: ~22 ms each, because frappe-ui's node view mounts a
  Combobox, a tooltip and a button per block and listens to every transaction.
  `CodeBlockView.vue` keeps the same markup and classes but uses plain buttons,
  builds the language list only while it is open, and subscribes to nothing:
  load 3.9 s -> 3.0 s.
- Typing costs ~90 ms per key at that size, from the editor's per-transaction
  work (toolbar `can()` checks, Vue re-renders, `getMarkdown` re-serialization),
  not from code blocks.

## Not fixed

Typing in a ~100 KB page costs ~55 ms per key (editor view update), with or
without these changes. Separate from saving, and worth profiling next.
