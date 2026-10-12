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

## Finding what still freezes: the activity log

The freeze could not be reproduced outside the user's machine (a pasted
1,100-line page loads, pastes and saves in under a second here, whatever mix of
tables, lists, code, callouts and links it holds), and it also happens on the
base branch, so it is not a regression. A frozen tab cannot be inspected, so the
app now logs its heavy steps to `localStorage['wiki:trace']` (`lib/freezeTrace.js`):
a `:start` is written before each step and an `:end` after, so the last `:start`
without an `:end` is the step that never finished. Steps covered: editor create /
mount, paste, markdown canonicalize, `getMarkdown`, autosave, save request,
draft persist, hydrate, page load, and any task over 500 ms (`longtask`).

To read it after a freeze, from another tab of the same site (localStorage is
shared): DevTools > Application > Local storage > `wiki:trace`, or in that tab's
console: `copy(localStorage.getItem('wiki:trace'))`.

Remove (or gate behind a flag) once the cause is fixed.

## The loop (found from the user's activity log)

The log showed `draft:persist` -> `markdown:canonicalize` (~80 ms, 84 KB) ->
`draft:persist` repeating without end: hundreds of thousands of entries. The
editor reports `content-ready` (its snapshot plus the *normalized* saved content);
the store rebases `page.content` onto the normalized text and persists the draft
to IndexedDB; `page.content` is the `savedContent` prop, whose watcher reports
again. It only stops when normalizing is a no-op, and for this page (raw saved
content 84 KB, normalized 81 KB, so it is not) it kept going.

Existing on the base branch, so inherited. Three changes:

- The editor does not report identical snapshots twice, and stops reporting after
  8 reports in 2 s (`editor:contentReady:loop-stopped`, with where the texts
  differ). A loop is not editing.
- The store skips a reconcile that would leave the page unchanged, so a no-op
  report no longer rewrites the whole page to IndexedDB.
- The first reports of an editor log fingerprints (`editor:contentReady`), so the
  inputs of a loop can be told apart.

Not yet known: which construct in the user's page makes the saved text change
shape on every pass. My round-trip checks over 64 constructs and every pair of
them (8,192 combinations, compared as text, six passes) found none that fails to
settle; `loop-stopped` carries the first difference, which names it.

## Data loss on submit (reported after the loop fix)

After "Submit for review" a long page had no content and was not in the wiki.
Two ways the editor could lose a page that exists only in this browser, both on
the base branch:

1. **Restoring drafts trusted the store's baseline.** `restorePersistedDrafts`
   deleted a persisted draft when it equalled the baseline stored with it
   (`draft.savedContent`). That baseline is the store's belief about the server;
   with the content-ready loop it could be rebased onto the local text, so the
   draft looked "already saved" and was deleted without the server having it.
   Now a draft is dropped only when the **server's own text** equals it
   (`shouldDropPersistedDraft`); with the server unreadable it is kept. A phantom
   draft restored this way saves the same text once and is dropped next time.
2. **Submit and merge trusted the buffer.** They judged "is there unsaved work"
   from the buffer's dirty flag alone. `verifyPagesSaved` now asks the server for
   each open page first and saves any page whose text differs
   (`serverNeedsContent`); if that save fails, nothing is submitted or merged.
   Logged as `draft:verify:resave`.
