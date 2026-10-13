# Page Attachments

Date: 2026-10-12
Status: **Implemented.** JS and the pure Python parser checked here; Frappe-backed tests and e2e written, **not run** (no bench).

## Goal

A page lists the files it offers for download as cards (type chip, name, size,
download), on the published page and under the editor, like the mockup's
"Archivos adjuntos".

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Where attachments live | In the content: an ordinary link to one of this site's uploads (`[name](/files/x.xlsx)`), or a PDF embed. No new DocType and no `File.attached_to_*`, so attachments move through change requests with the page and a direct edit of a published page is never needed. |
| 2 | What is excluded | Images and video (shown inline), links to other sites, anything inside a code fence, repeats. |
| 3 | Reader | `wiki/wiki/attachments.py` parses the markdown; sizes come from `File.file_size` in one query. Rendered by `includes/attachments.html`, redrawn on client-side navigation by `renderAttachments` in `includes/sidebar.html` (`get_page_data` now returns `attachments`). |
| 4 | Editor | `EditorAttachments.vue` reads the live document (`lib/attachments.js`, same rules as the Python parser). "Attach file" and the `/file` slash command upload through `upload_wiki_asset` and insert a link on its own line. Sizes via `wiki.api.get_file_sizes`, which returns sizes only. |
| 5 | Removing one | Delete its link in the text; the card follows. |

## Not done

- ~~A per-file remove button and drag-and-drop onto the list.~~ Done: each card has Remove (deletes the link or embed from the text) and PDFs have Preview; files dropped on the list are uploaded and linked.
- A file's size is blank when the upload has no `File` record.
