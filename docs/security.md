# Security notes

Written for a wiki with public pages. What the code defends, what it does not, and what to set on the server.

## What published pages trust

Anything an author writes is served to every visitor on the site's own origin, so it is treated as untrusted
at the point it is shown, not only when it is saved. Merges write page content with `frappe.db.set_value`,
which skips the framework's save-time sanitising, so the renderer is the control that holds.

- **Raw HTML in markdown** goes through an allow-list (`wiki/wiki/html_sanitizer.py`): no scripts, styles,
  forms or SVG; no `on*` handlers; no Alpine attributes (`x-*`, `@`, `:`), because the reader runs Alpine
  over the page text; urls are http(s), mailto, tel or relative; an `<iframe>` only for the embed providers
  the editor offers, over https; `style` keeps text and box properties only; positioning classes are dropped.
  `IFRAME_HOSTS` must match `IFRAME_PROVIDERS` in `iframe-embed.js` (a test checks it).
- **Text the renderer inserts into HTML** (callout titles, image alt and title, video and PDF names and urls)
  is escaped, and a `javascript:` url with a media extension is not embedded.
- **Search results** are shown with `x-html` so their `<mark>` works; the snippet's text is escaped first.
- **Pages with unclosed fences or long runs** cannot tie up a worker: the patterns are bounded and past 1,000
  `:::` fences callouts and code groups are left as text.

## Endpoints open to visitors

`get_page_data`, `download_pdf`, `search`, `og_image`, `get_translations`, the GitHub webhook (HMAC
verified) and `submit_feedback`. Each checks that the page is published and the space readable, and answers
"not found" for both a missing and a forbidden page. Feedback is also limited to 2,000 characters and, as
before, rate limited per IP.

## Files

- Uploads of HTML, scripts, XML and SVG with script are refused (`wiki/upload_guard.py`).
- A **private** file is served only to signed-in users with access; a published page lists it with a lock.
  Its size is not shown to visitors.
- This guard covers the editor's upload only. Frappe's own `/api/method/upload_file` is separate: set
  **System Settings > Allowed File Extensions** to the types you want (leave out html, svg, js, xml).

## Set on the server

- `developer_mode` off in production (`get_context_for_dev` and other helpers assume it).
- Serve over HTTPS. The copy buttons work without it, but cookies and the clipboard API need it.
- Response headers from nginx: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
  and `X-Frame-Options: SAMEORIGIN` (or CSP `frame-ancestors 'self'`). A strict CSP is not practical: the
  reader's Alpine build needs `unsafe-eval`.
- Keep **Accept Contributions** off on a public space unless an approver reads what they merge.

## Known gaps

- PDF export (`download_pdf`) renders the page server-side; an `<img src="http://internal/...">` makes the
  server fetch that address. Same-site and public images are the intent; consider a firewall rule for the
  worker's outbound requests.
- Page and folder titles are printed without extra escaping in a few reader templates, relying on Frappe's
  save-time sanitising of Data fields. Titles do not take the merge fast path that content does.
- `@tiptap/core` has a ReDoS advisory fixed in 3.30.5 (a hostile page could slow the editor of whoever opens
  it). It is pinned at 3.29.2 across the whole editor, so it was not bumped here; plan an upgrade with a full
  editor test pass.
- Page-level access is not built (see `specs/page_level_access.md`); use a space per audience.
