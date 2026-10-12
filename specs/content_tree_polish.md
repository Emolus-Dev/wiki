# Content Tree Polish

Date: 2026-10-12
Status: **Implemented** (markup and CSS; verified by build and template render, not in a live site).

## Proposal and what was applied

A navigation tree is read far more than it is edited, so the changes make "where
am I" and "what is in there" answerable at a glance, without adding chrome.

| # | Change | Reader (`sidebar_tree.html`) | Editor (`WikiTree.vue`) |
|---|--------|------------------------------|-------------------------|
| 1 | Where am I | Current page gets medium weight, darker text and a green dot at the row's end | Selected row gets a 2px accent edge and medium weight |
| 2 | What is inside | Each group shows its child count, muted | Same, hidden while searching (flat results) |
| 3 | Following a level | The hovered branch lights its guide rail | (guides are off in the draggable tree) |
| 4 | Keyboard | Visible focus ring on every row | unchanged (frappe-ui Tree owns it) |
| 5 | Density | unchanged (h-7 rows) | Rows 40px -> 36px; two-line search rows still grow |

## Not done

- Expand/collapse all, per-group "contains the open page" emphasis, and
  arrow-key tree navigation in the reader. Each is self-contained if wanted.
