# Reader: TOC Flash, Search Focus and Wider Search

Date: 2026-10-12
Status: **Implemented.** Front end verified on a static page with the real CSS and script; Python merge helper checked outside Frappe; Frappe-backed tests and e2e written but **not run** (no bench).

## Goal

1. Clicking an entry in "On this page" (or a heading's `#` anchor) briefly
   highlights the heading it jumps to.
2. Picking a search result opens the page **at the match**: the first hit is
   scrolled to the middle of the viewport and the matched words are lightly
   highlighted for a few seconds.
3. Search returns more useful results when the exact query matches little.

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Where the match is found | In the browser, on the rendered page, after it loads. No new endpoint and no extra server work: the server already returns the page, the client only walks its text nodes once. |
| 2 | How the query travels | SPA navigation passes it in memory; a new tab (Ctrl+Enter, middle click) or a full load gets `?q=`. The URL is cleaned by the nav store's `replaceState`. |
| 3 | Matching | Case- and accent-insensitive substring match per word (words of 2+ characters); all occurrences are marked up to a cap, the first in document order is scrolled to. Marks are unwrapped after 6 s so the DOM returns to normal. |
| 4 | DuckDB | Not used for search. It is in the app for analytics. Its FTS extension is a separate download, is rebuilt rather than updated per page and has no edge over the SQLite FTS5 index (BM25, diacritics-insensitive tokenizer) already incremental in this app. The thin results come from how the query is shaped, not from the engine. |
| 5 | Wider results | When the full query returns fewer than 5 hits and has several words, each word is searched alone with the same engine call and the hits are merged, ranking pages that matched more words first. Only plain single-word queries are issued, so it does not depend on the engine's query syntax. Capped at 5 words. |

## Test plan

- Python: merge/ranking helper (pure function) in `test_search_snippet.py`.
- Browser: verified on a static page with the real CSS and script.
- e2e (needs a bench): search -> click result -> `mark.wiki-hit` visible and in
  viewport; TOC click adds `wiki-flash` to the heading.

## Addendum: content search in the editor palette

`wiki.api.search.search_content` (authenticated) finds pages by title and body
text for the Cmd/Ctrl+K palette, drafts and unpublished pages included, with a
snippet around the first match. SQL narrows on the longest word, Python checks
every word case- and accent-insensitively; at most 100 candidates are read. The
palette shows the hits in an "In page content" group after the URL matches,
holding back rows that answer an earlier query. Requires 3+ characters.
Not done: scrolling the editor to the match (the reader already does this).
