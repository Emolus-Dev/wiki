# Home Page and Editor/Reader Redesign

Date: 2026-10-12
Status: **In progress**

## Goal

Make the app feel like a team knowledge base: a welcoming Home page as the
landing screen, and a page view/editor whose code blocks look like the mockups
(dark, with a header bar, always-visible language + copy, good syntax colours).
Keep the Frappe v16 / frappe-ui tokens; the mockups only add layout, a serif
display face and the dark code surface.

## Phase 1 -- Home page

Route `/` renders a new `Home` page for every user. The analytics Overview moves
to `/overview` (Wiki Manager only; non-managers are redirected to `/`).

Sections, top to bottom:

1. **Greeting**: `Hola, <first name>` (translated) and a prompt line.
2. **Search box**: opens the existing command palette (click / focus / `Ctrl K`).
   Below it, quick-link chips for the user's recently visited pages.
3. **Spaces** (the mockup's "Apps"): up to 4 spaces as cards -- avatar, name,
   `/route`, page count. "View all" links to All Spaces.
4. **Recently edited**: the 5 most recently modified published-or-visible
   pages (`Wiki Document`, `is_group = 0`, `modified desc`) with their space and
   relative time.
5. **Pinned snippets**: small dark code cards with a copy button. Snippets are
   **per-user, per-browser** (localStorage), like pinned spaces, until a shared
   Snippet DocType is wanted. Users add (title + code) and remove them inline.

Sidebar gets a **Home** item (first). Mobile bottom nav gets a Home tab.

## Phase 2 -- Code blocks and page surface

- Code blocks are dark in both themes, with a header bar (language label left,
  copy right, always visible) instead of the hover-only corner controls.
  Applies to the editor, the in-app preview and change-request previews (they
  share `wiki-editor-content.css`) and to the reader (`.wiki-rendered`).
- Syntax palette: GitHub-dark tokens already shipped by frappe-ui, on a warm
  near-black surface.
- Page title / H1-H2 use the serif display face; page meta line unchanged.

## Out of scope

- Shared (server-side) snippets, attachments cards, favourites, version
  history -- visible in the mockup but need backend work.

## Test plan

- Unit: snippets composable (add / remove / cap / storage shape).
- e2e: Home renders for manager and Wiki User; `/overview` is manager-only;
  search box opens the palette; adding and copying a snippet.
- Existing e2e that assumed `/` is the Overview are updated.
