# Page-Level Access (proposal, not implemented)

Date: 2026-10-13
Status: **Proposal.** Nothing here is built. See "Why not yet".

## What works today

Access is granted **per space** (`Wiki Space.roles`, Read or Write), enforced on the
reader, markdown, PDF, search, the SPA lists and change requests
(`specs/role_based_space_access_control.md`).

- To make a space **public and read only**: add the built-in `Guest` role with
  Read. Space Settings > Access now has a **Public (read only)** switch that does it.
- To keep some pages for some people: put them in their own space and give that
  space the roles. Pages move between spaces with the tree's move action.

## What is missing

Restricting **one page or folder inside a space** to some roles, for example an
"Internal" folder in a customer-facing space.

## Design

- New child table `Wiki Document Role` (`role`) on `Wiki Document`, edited from
  Page Settings by space writers and managers. Saved directly, like the meta
  fields, so it does not travel through change requests.
- A page is readable when the user can read the space **and**, for every
  ancestor-or-self that has role rows, holds at least one of those roles
  (intersection: a child can only narrow). Managers and space writers bypass it.
- The restricted nodes and their `lft`/`rgt` ranges are cached in one small
  structure and cleared with `clear_wiki_tree_cache`; with no restricted page the
  check costs one cache read.

## Every place that has to enforce it

A page-level rule that misses one of these leaks the page, so all of them ship together:

| Exit | Where |
|------|-------|
| Reader HTML, `.md`, PDF, `get_page_data` | `check_space_access` in `wiki_document.py` |
| Reader sidebar tree and prev/next | tree is cached for everyone: filter after the cache, per user |
| Reader search | `_filter_hits_by_space_visibility` |
| `sitemap.xml`, `llms.txt`, crawler cache | public caches: omit restricted pages entirely |
| OG image endpoint | would reveal a restricted title |
| Backlinks, `wiki:` link resolution | omit restricted targets |
| SPA lists and search | `wiki_document_query_conditions` / `has_permission` |
| SPA tree (`get_wiki_tree`) | uses `ignore_permissions`: filter |
| Change request page overlay | `get_cr_page` and friends take a `doc_key` directly |

Uploaded files under `/files/` are not covered: a restricted page that links a
public file does not protect that file.

## Why not yet

It touches nine exits plus the change-request API, and it is a security feature:
a partial version gives a false sense of safety. It needs a bench to run the
permission matrix (as `role_based_space_access_control.md` did) before it can be
trusted, which the environment this was written in does not have.
