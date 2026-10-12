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

## Not fixed

Typing in a ~100 KB page costs ~55 ms per key (editor view update), with or
without these changes. Separate from saving, and worth profiling next.
