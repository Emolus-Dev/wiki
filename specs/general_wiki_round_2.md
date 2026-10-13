# General-Purpose Wiki: Round 2

Date: 2026-10-13
Status: **Implemented; backend not run.** JS, pure-Python helpers, templates and the CSS were
exercised here (node tests, a production build, a browser harness and static reader pages). The
Frappe-backed tests written for this round **were not run** (no bench in the authoring
environment); run them with `bench --site <site> run-tests --app wiki`.

The Home page was dropped (see `home_page_and_editor_redesign.md`); this round is the
list the product owner approved item by item.

## What was built

| # | Item | Where |
|---|------|-------|
| 2 | Typing/loading profile on a 1,700-line page | `long_page_save_performance.md` (no cheap win left) |
| 3 | Drafts of merged, rejected, archived or deleted change requests are pruned after load | `lib/draftJanitor.js`, `lib/pruneDrafts.js`, `stores/draftPersistence.js` |
| 6 | Editor strings go through `__()` (slash menu, link, image, PDF, mermaid, embed) | `components/tiptap-extensions/*`, `translations/es.csv` |
| 7 | Page history: versions from merged change requests, line diff, restore | `api/page_history.py`, `PageHistoryDialog.vue`, `lib/lineDiff.js` |
| 9 | Attachments: remove, PDF preview, drop files on the list | `EditorAttachments.vue`, `lib/attachmentRemoval.js` |
| 10 | Code group tabs can be reordered | `lib/codeGroupOps.js`, `CodeGroupView.vue` |
| 11 | Heading links copy their URL | `templates/wiki/document.html` (anchors and TOC already existed) |
| 13 | "Linked from" backlinks | `wiki/related.py`, `includes/backlinks.html` |
| 14 | Collapsible `:::details[Title]`; sortable, scrollable reader tables | `callout-markdown.js`, `markdown.py`, `code-blocks.js` |
| 15 | Spanish word forms find each other | `wiki/search_text.py`, `api/search.py`, `wiki_document/search.py` |
| 16 | Expand/collapse all and arrow keys in the content tree | `sidebar.html`, `WikiTree.vue` |
| 18 | Visible breadcrumbs (prev/next already existed) | `wiki/related.py`, `includes/breadcrumbs.html` |
| 22 | "Someone is editing this page" | `api/presence.py`, `usePagePresence.js` |
| 24 | Public (read only) switch per space; page-level access is a proposal | `AccessPanel.vue`, `page_level_access.md` |
| 25 | Dark mode and the theme toggle already existed; print forces the light theme | `main.css`, `code-blocks.js` |
| 26 | Print stylesheet | `main.css` |
| 28 | Feedback widget already existed; managers now see counts and comments | `api/analytics.get_feedback`, `AnalyticsDashboard.vue` |
| 29 | Documentation versions: a version group and label per space, a switcher in the reader | `wiki_space.json`, `versions_logic.py`, `includes/version_switcher.html` |
| 36 | `wiki:debug` documented | `docs/editor-troubleshooting.md` |

## Decisions worth knowing

- **Backlinks and breadcrumbs share one template per block** and are rendered on the
  server for both the first load and client-side navigation, so the two cannot drift
  (attachments still have the older duplicated JS/Jinja pair).
- **Backlinks are cached per page** and cleared with the tree cache, which every wiki
  edit already clears. Same space only, published pages only.
- **Search stemming** is applied to the editor's content search directly. The reader's
  FTS search can only use it where the framework's engine matches prefixes; where it does
  not, the extra query returns nothing and the result is the old one.
- **Restoring a version** puts its text in the editor as an undoable edit; it then goes
  through autosave and review like anything else. Nothing is written on the server.
- **Page history** reads the newest 300 merges of a space and lists the ones where the
  page changed. A page never merged has no history.

## Deploy

- `bench migrate` (new `Wiki Space` fields `version_group`, `version_label`).
- `bench build --app wiki` (frontend, and the reader CSS in `public/css/main.css`).
- Translations: `wiki/translations/es.csv` was extended; no action.

## Not done

- Page-level access (proposal only).
- Highlighting the match inside the editor's command-palette snippets (the palette
  component takes plain text).
- Reader-side PDF preview for attachments.
