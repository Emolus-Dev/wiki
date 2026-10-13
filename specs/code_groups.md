# Code Groups

Date: 2026-10-12
Status: **Implemented.** Round-trip, reader HTML, reader tabs and editor tabs checked in a browser harness; e2e written, **not run** (no bench).

## Goal

Show consecutive code blocks as one block with tabs (`bash` | `site_config.json`),
in the editor and on the published page.

## Syntax

````
:::code-group
```bash
bench restart
```
```json site_config.json
{}
```
:::
````

Words after the language on a fence are the block's **label** (the tab title);
without one the tab is named by its language. A labelled fence outside a group
still highlights by its language.

## Decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Container | Same `:::` family as callouts, so it stays plain markdown for the git-synced spaces and for agents reading `text/markdown`. |
| 2 | Editor | `codeGroup` node (`codeBlock+`) with a Vue node view: tabs, double-click to rename, add and remove. `WikiCodeBlock` is frappe-ui's block plus a `label` attribute; fences with no label serialize exactly as before. Slash command **Code Group**. |
| 3 | Reader | `markdown.py` wraps the rendered fences in `.wiki-code-group` (`<pre data-label>`); `code-blocks.js` builds the tab bar, so with no JS the blocks simply stack. |
| 4 | Nesting | A group cannot be inserted inside a group or a callout. |

## Not done

- ~~Reordering tabs~~ Done (move left/right on the active tab). Tab titles are the language or the author's label, so there is nothing to translate; more than 12 tabs in the editor is untested.
