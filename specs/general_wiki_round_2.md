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

## Type scale (follow-up)

Text sizes disagreed between the editor and the reader, and compounded inside tables
(code at 11px beside 15px prose). Both now import `wiki/public/css/wiki-type-scale.css`.

Faces: **Inter** for headings (same family, weight 600) and text; **JetBrains Mono**
(bundled, SIL OFL, Latin and Latin-Extended) for inline and block code, with ligatures
on. The earlier serif display face (Newsreader) was removed.

Sizes from a 16px body: page title and h1 36px, h2 27, h3 21, h4 18, body 16 at line-height
1.6, tables and callouts 15, code 14.4 at 1.55 (inline code 0.9em of its context), headings
at line-height 1.2 to 1.35. Measured in the editor and in the reader: the same numbers in both.

To tune it, change that one file. `--wiki-title-size`, `--wiki-text-code`,
`--wiki-text-small` and `--prose-font-size` are variables; set `--wiki-code-ligatures: none`
to turn ligatures off.

## Copy button, attachments on the published page, inline code colour (follow-up)

- **Copy buttons did nothing on a wiki served over plain HTTP.** `navigator.clipboard` exists only
  on HTTPS or localhost, and the reader called it without a fallback. The reader
  (`window.wikiCopyText` in `code-blocks.js`, also used by "Copy page" and heading links) and the
  editor (`lib/clipboard.js`, used by code blocks, link popup, sidebar, settings) now fall back to a
  hidden textarea and `execCommand('copy')`. The button shows a check only when the copy worked, and
  a cross when it did not. Verified in a browser with and without `navigator.clipboard`.
- **Uploaded files with a space in their name never became attachments.** Frappe keeps the name as
  uploaded; a space ends a markdown link destination, so the link was saved as plain text. Images
  were already handled (`_encode_image_url_spaces`), other files were not. Now the editor writes
  `%20` into the url on upload (`lib/fileUrl.js`), the renderer repairs existing content
  (`wiki/wiki/upload_links.py`), and the attachments list reads names with spaces, accents and
  parentheses (`attachments.py`), looking sizes up by the stored, decoded name.
- **Inline code colour** is two variables, `--wiki-inline-code-bg` and `--wiki-inline-code-fg`
  (`wiki-type-scale.css`); the default is unchanged.

## Files above the text, private files, content width (follow-up)

- **Files list moved to the top** of both the published page and the editor, as a collapsible
  "Files" box (open when there are three or fewer, closed with more). A thousand-line page no
  longer hides it. In the reader it is rendered on the server like breadcrumbs and backlinks
  (`wiki/related.py`, `includes/attachments.html`), so the first load and client-side navigation
  share one template; the old JS copy was removed. The payload key `attachments` became
  `attachments_html`.
- **What counts as a file:** any *link* to one of the site's uploads, of any type (a PNG linked
  from the text is a file the author chose to offer); embedded images and video (`![..](..)`)
  are already on the page and are not listed. This is why linked images used to be missing.
- **Public or private:** "Attach file" is a menu with *Public file* and *Private file (signed-in
  users only)*; the last choice is remembered and used for files dropped on the list. Private files
  show a lock in both lists; guests are asked to sign in by Frappe when they download one.
- **Content width:** `--wiki-content-width` (56rem, 896px, about 100 characters a line at 16px)
  drives the text column in the reader and in the editor; with the sidebar collapsed the reader
  adds 10rem. Change it in `wiki-type-scale.css`.
- **Inline code** now defaults to soft violet (`--surface-violet-2` / `--ink-violet-8`).
