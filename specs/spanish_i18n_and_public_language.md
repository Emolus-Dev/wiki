# Spanish Catalogue and Public-Page Language

Date: 2026-10-12
Status: **Implemented.** Catalogue checked for placeholders; Frappe-backed tests written, **not run** (no bench).

## Goal

The app and the published reader speak Spanish. Logged-in users see the
language they configured on their User; visitors who are not logged in see the
language set for public pages.

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Catalogue | `wiki/translations/es.csv`, every `__()` (frontend) and `_()` (python, templates) string, 665 rows. Placeholders (`{0}`) verified to match the source. Frappe reads it as the app's Spanish catalogue. |
| 2 | Logged-in users | Unchanged: Frappe puts the User's language on the request, and `wiki.api.get_translations` serves the SPA the same catalogue. It now falls back to the System Settings language when the User has none. |
| 3 | Guests | New `Wiki Settings.public_language` (Link to Language, default `es`). `apply_public_language()` runs at the top of the reader's `render()` and sets `frappe.local.lang` for Guests only. `get_translations` uses it for Guests too. |
| 4 | `<html lang>` | Follows the request language through `reader_lang()` instead of a hard-coded `en`. |
| 5 | Settings UI | A language select on the General panel of the SPA's Wiki Settings dialog, kept in sync with the DocType field. |

## Out of scope

- Strings hard-coded in JS (e.g. the code block's "Copy code" tooltip).
- Other languages: add `<lang>.csv` the same way.
