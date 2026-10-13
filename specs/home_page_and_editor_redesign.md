# Home Page and Editor/Reader Redesign

Date: 2026-10-12
Status: **Implemented** (frontend). Verified by building the app and by
screenshots against a mocked API; the e2e specs are written but were **not run**
(no bench in the authoring environment).

## Goal

Make the app feel like a team knowledge base: a page view/editor whose code blocks look like the mockups
(dark, with a header bar, always-visible language + copy, good syntax colours).
Keep the Frappe v16 / frappe-ui tokens; the mockups only add layout, a serif
display face and the dark code surface.

## Phase 1 -- Home page (dropped)

A Home page (greeting, search, spaces, recent pages, pinned snippets) was built
and then removed: the focus is a general-purpose wiki, not a dashboard. `/` is
the analytics Overview again for managers; everyone else lands on All Spaces.

## Phase 2 -- Code blocks and page surface

- Code blocks are dark in both themes, with a header bar (language label left,
  copy right, always visible) instead of the hover-only corner controls.
  Applies to the editor, the in-app preview and change-request previews (they
  all render through `.wiki-editor-content`).
- Syntax palette: GitHub-dark tokens already shipped by frappe-ui, on a warm
  near-black surface.
- Page title / H1-H2 use the serif display face; page meta line unchanged.

## Phase 3 -- Published reader

The public reader gets the same code block (dark surface, header bar with
language + copy, GitHub-dark tokens) and serif page title / h1 / h2. It is pure
CSS in `wiki/public/css/main.css`, layered over the generated
`frappe-ui-code.css` with doubled `.code-block-enhanced` selectors; the existing
`code-blocks.js` markup (gutter, toolbar) is unchanged. Verified on a static page
built with the real `tailwind.css`, `wiki-highlight.bundle.js` and `code-blocks.js`.

## Out of scope

- Shared (server-side) snippets, favourites, version history.

## Test plan

- Visual check of code blocks in the editor, preview and published reader.

## Progress log

- Phase 1: Home page built, then reverted (see above).
- Phase 2: `wiki-editor-content.css` restyles frappe-ui's code-block node view
  (the same element, so language picker, copy and Tab keep working); serif
  display face on page title and h1/h2. The editor root *is* `.ProseMirror`, so
  selectors are `.wiki-editor-content ...`, not `.wiki-editor-content .ProseMirror ...`.
- Copy is Spanish-agnostic: strings go through `__()`; Spanish text needs the
  translation catalogue (Crowdin) to be filled.
- Phase 3: reader CSS in `wiki/public/css/main.css` (requires `yarn build` / `tailwind:build` on deploy).
