# Wiki Contribution & Merge Flow — Refactor Plan

## Executive Summary

The wiki app's contribution and merge system is overengineered for what it does. A git-style full-tree-snapshot revision model was built, but without the optimizations that make git fast. The result:

- **Data integrity bug**: Desk edits bypass the revision system entirely — changes made from Frappe's admin UI are silently lost when CRs are created or merged.
- **O(N) operations that should be O(1)**: Creating a Change Request clones every revision item in the space (500 pages → 500 DB inserts for a 1-page edit). Every CR mutation recomputes hashes over the entire tree.
- **O(N) merge for O(1) changes**: Merging loads all content blobs for 3 full revisions and iterates every doc_key, even when only 1 page changed. Then `apply_merge_revision` does individual `get_doc()` + `save()` for every document in the tree.
- **4 overlapping merge strategies** tried in sequence with a duplicated retry block — hard to reason about, hard to test.
- **Dead code** from the old `WikiPagePatch` system still ships.

This document proposes 6 independently-shippable phases to fix all of the above.

---

## Current Architecture

### Data Model

```
Wiki Space
  ├── root_group → Wiki Document (NestedSet root)
  ├── main_revision → Wiki Revision (current published state)
  └── route

Wiki Document (NestedSet)
  ├── doc_key (immutable identifier)
  ├── title, slug, route
  ├── content (live markdown)
  ├── parent_wiki_document, lft, rgt, sort_order
  └── is_group, is_published

Wiki Revision (full tree snapshot)
  ├── wiki_space, change_request
  ├── parent_revision
  ├── tree_hash, content_hash
  ├── is_working, is_merge
  └── has N → Wiki Revision Items

Wiki Revision Item (one per doc per revision)
  ├── revision (link to Wiki Revision)
  ├── doc_key, title, slug
  ├── parent_key, order_index
  ├── content_blob → Wiki Content Blob
  └── is_deleted, is_group, is_published

Wiki Content Blob (content-addressed storage)
  ├── hash (SHA256)
  └── content (markdown text)

Wiki Change Request
  ├── base_revision (snapshot when CR was created)
  ├── head_revision (working revision with edits)
  ├── merge_revision (created on merge)
  └── status: Draft → In Review → Approved → Merged
```

### Edit Flows

**Editor UI (Change Request flow):**
```
User types → WikiEditor.vue auto-save → update_cr_page() API
  → updates Wiki Revision Item in head_revision
  → updates Wiki Content Blob
  → recompute_revision_hashes() over entire tree
```

**Desk (direct save — NO revision tracking):**
```
User edits Wiki Document in Frappe admin → doc.save()
  → WikiDocument.validate() runs (slug, route, etc.)
  → saves directly to tabWiki Document
  → revision system is NEVER notified
```

**Merge flow:**
```
merge_change_request()
  → load ALL items for base_revision, main_revision, head_revision
  → load ALL content blobs for all 3 revisions
  → iterate every doc_key across all 3 sets
  → for each: try 4 merge strategies in sequence
  → create merge_revision with ALL items
  → apply_merge_revision: load + save EVERY Wiki Document individually
```

### Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `frappe_wiki/doctype/wiki_change_request/wiki_change_request.py` | 1341 | CR CRUD, diff, 3-way merge, 4 content-merge strategies, apply to live tree |
| `frappe_wiki/doctype/wiki_revision/wiki_revision.py` | 278 | Revision creation, cloning, hash computation, content blobs |
| `frappe_wiki/doctype/wiki_document/wiki_document.py` | 594 | Wiki Document model, validation, rendering, tree building |
| `api/wiki_space.py` | 225 | Live tree reorder, sync to revision system |
| `frappe_wiki/doctype/wiki_change_request/test_wiki_change_request.py` | 580 | 20 test cases covering CR lifecycle |

---

## Findings

### P1: Desk Edits Bypass Revision System (Critical — Data Integrity)

**The problem**: Wiki Document can be edited directly from Frappe Desk. There is no `doc_events` hook for `Wiki Document` in `hooks.py:111-113` — only `User` has a hook. The only place that syncs desk edits to the revision system is `_sync_main_revision_for_space()` in `api/wiki_space.py:155-170`, which is called **only** from `reorder_wiki_documents()` — never from normal content edits.

**Impact**: Team members edit Wiki Documents from Desk. The Editor UI builds its tree from `Wiki Revision Item` records (`get_cr_tree()` at `wiki_change_request.py:268-360`). These items are cloned from `main_revision`, which was never updated after the Desk edit. The desk changes are invisible to CRs and are overwritten on the next merge.

**Root cause**: No `on_update` / `on_trash` doc_event for `Wiki Document`.

### P2: Full-Tree Clone on CR Creation (Performance)

**The problem**: `create_change_request()` at `wiki_change_request.py:410-430` calls `clone_revision()` at `wiki_revision.py:97-150`. This copies **every** `Wiki Revision Item` from the base revision to a new working revision.

**Impact**: For a wiki space with 500 pages, creating a CR inserts 500 `Wiki Revision Item` records even though the user may only edit 1 page. Each insert is an individual `frappe.new_doc().insert()` call — no bulk operations.

**Compounding factor**: Every subsequent CR operation (`update_cr_page`, `create_cr_page`, `move_cr_page`, `delete_cr_page`, `reorder_cr_children`) calls `recompute_revision_hashes()` at `wiki_revision.py:171-217`, which queries ALL items in the revision plus ALL their content blobs, every single time.

### P3: Full-Tree Merge Processing (Performance)

**The problem**: `merge_change_request()` at `wiki_change_request.py:785-887`:

1. Loads ALL items for 3 revisions via `get_revision_item_map()` — 3 queries returning N rows each
2. Loads ALL content blobs for all 3 via `get_contents_for_items()` at lines 795-797 — 3 bulk queries returning N content strings each
3. Iterates `set(base_items) | set(ours_items) | set(theirs_items)` — processes every doc_key
4. For every doc_key, runs normalization + comparison + merge logic

Then `apply_merge_revision()` at lines 1267-1341:
1. Creates a new merge revision with ALL items (N inserts)
2. Gets all space docs (1 query)
3. For each of N doc_keys: `frappe.get_doc()` + set fields + `doc.save()` — that's N doc loads + N validates + N saves

**Impact**: Merging a 1-page content change on a 500-page wiki loads ~1500 revision items, ~1500 content blobs, creates 500 new revision items, and individually loads + saves 500 Wiki Documents. This is where the "merge is slow" complaints come from.

### P4: Redundant Content Merge Strategies (Complexity)

**The problem**: There are 4 content-merge functions at `wiki_change_request.py:1034-1131`:

1. `line_merge_fallback()` — same-length only, rstrip comparison
2. `merge_content_linewise()` — diff-based, `splitlines()` (strips endings)
3. `merge_content_disjoint()` — diff-based, `splitlines(keepends=True)`
4. `merge_content()` — tries same-length first, then diff-based

They are called in a waterfall at `wiki_change_request.py:966-977`:
```python
merged_content, line_ok = line_merge_fallback(...)
if not line_ok:
    merged_content, conflict = merge_content_linewise(...)
    if conflict:
        merged_content = merge_content_disjoint(...)
        if merged_content is None:
            merged_content, conflict = merge_content(...)
```

Then there's a **duplicated retry** of the exact same waterfall at lines 813-848 inside `merge_change_request()` — if `merge_items()` returns a `"content"` conflict, the same 4 strategies are tried again.

**Impact**: `merge_content()` already subsumes the logic of the other 3. The duplication makes the code ~100 lines longer than needed and very hard to follow. When someone needs to fix a merge bug, they have to understand all 4 strategies plus the retry block.

### P5: N+1 Query Pattern in apply_merge_revision (Performance)

**The problem**: `apply_merge_revision()` at `wiki_change_request.py:1267-1341` processes every doc_key individually:

```python
for doc_key in ordered_keys:
    # ...
    if doc_key in key_to_name:
        doc = frappe.get_doc("Wiki Document", key_to_name[doc_key])  # DB read
    else:
        doc = frappe.new_doc("Wiki Document")
    doc.title = item.get("title")
    # ... set fields ...
    content = frappe.get_value("Wiki Content Blob", content_blob, "content")  # DB read
    doc.content = content
    doc.save()  # DB write + validate
```

For N documents: N `get_doc` calls + N `get_value` calls for content + N `save()` calls (each triggering `validate()` with route computation, unique-route checks, etc.).

**Impact**: This is the main bottleneck in merge. Content blobs could be batch-loaded in 1 query. Documents that haven't changed don't need to be loaded or saved at all.

### P6: Dead Code — WikiPagePatch (Tech Debt)

**The problem**: `wiki/wiki/doctype/wiki_page_patch/wiki_page_patch.py` (116 lines) references a `"Wiki Page"` doctype that no longer exists (replaced by `Wiki Document` in the v3 architecture). It imports `apply_changes`, `apply_markdown_diff`, `highlight_changes` from `wiki.utils` — these are dead utility functions.

**Impact**: Confusing for new contributors. The old merge logic in `update_old_page()` at line 62 uses a completely different approach from the current 3-way merge, creating a false impression of how the system works.

### P7: Overcomplicated Draft CR Logic (Complexity)

**The problem**: `get_or_create_draft_change_request()` at `wiki_change_request.py:157-216` is 60 lines with:
- Loop through all user's drafts checking hash equality for each
- Inline hash comparison (duplicates `has_revision_changes()` logic)
- Auto-archive logic for stale drafts with no changes
- Creates new CR inside the stale-draft branch

This function is called **every time the editor opens**.

**Impact**: Hard to follow, hard to test. The inline hash comparison at lines 198-201 duplicates the logic already in `has_revision_changes()` at lines 129-153.

---

## Refactor Plan

### Phase 1: Desk-to-Revision Sync ✅ DONE

**Goal**: Any edit to a Wiki Document through Desk automatically updates `main_revision`.

**Priority**: Critical — this is the only data-integrity bug.

**Status**: Completed. Added `Wiki Document` doc_events (`on_update`, `on_trash`) in `hooks.py`. Hook handlers in `wiki_document.py` sync desk edits to the revision system via `_sync_main_revision_for_space()`. Guard flags in `apply_merge_revision()` and `reorder_wiki_documents()` prevent infinite loops. Three new tests added and all 28 tests pass.

**Changes**:

1. **`hooks.py`** — Add `Wiki Document` to `doc_events`:
   ```python
   doc_events = {
       "User": {"after_insert": "wiki.utils.add_wiki_user_role"},
       "Wiki Document": {
           "on_update": "wiki.frappe_wiki.doctype.wiki_document.wiki_document.on_wiki_document_update",
           "on_trash": "wiki.frappe_wiki.doctype.wiki_document.wiki_document.on_wiki_document_trash",
       },
   }
   ```

2. **`wiki_document.py`** — Add hook handlers:
   - `on_wiki_document_update(doc, method)`: Skip if `frappe.flags.in_apply_merge_revision` is set (avoid infinite loop during merge). Otherwise, find the owning Wiki Space and call `_sync_main_revision_for_space()`.
   - `on_wiki_document_trash(doc, method)`: Same logic.
   - Use a per-request debounce via `frappe.flags` so bulk operations only trigger 1 revision sync per space.

3. **`wiki_change_request.py`** — Set `frappe.flags.in_apply_merge_revision = True` around the loop in `apply_merge_revision()` (wrap in try/finally).

4. **`api/wiki_space.py`** — Set `frappe.flags.in_reorder_wiki_documents = True` around `reorder_wiki_documents()` to avoid double-sync.

**Tests to add**:
- `test_desk_edit_syncs_to_revision_system`: Edit Wiki Document directly, verify `main_revision` updates.
- `test_desk_edit_visible_in_new_cr`: Edit via desk, create CR, verify CR's head_revision includes the desk edit.
- `test_merge_does_not_double_sync`: Merge a CR, verify the `on_update` hook doesn't re-trigger revision creation.

**Risk**: Low. Guard flags are a well-understood pattern. The `_sync_main_revision_for_space` function already exists and is tested (it's used by reorder).

---

### Phase 2: Consolidate Merge Strategies ✅ DONE

**Goal**: Replace 4 overlapping merge functions + duplicated retry block with 1 clean function.

**Priority**: High — simplifies the hardest-to-understand part of the codebase, makes Phase 5 easier.

**Status**: Completed. Replaced `line_merge_fallback`, `merge_content_linewise`, `merge_content_disjoint`, and `merge_content` with a single `merge_content_three_way()` function. Deleted the duplicated retry block in `merge_change_request()`. Removed unused helpers `edits_conflict` and `ranges_overlap`. Five new unit tests added and all 33 tests pass.

**Changes**:

1. **`wiki_change_request.py`** — New function `merge_content_three_way(base, ours, theirs) -> (str, bool)`:
   ```
   Strategy (in order):
   1. Trivial: ours == theirs, or one side == base
   2. Normalize whitespace, re-check trivials
   3. Same-length line-by-line (rstrip comparison for whitespace tolerance)
   4. Diff-based with SequenceMatcher + disjoint-edit detection
   5. If edits overlap → conflict
   ```

2. **Delete**: `line_merge_fallback`, `merge_content_linewise`, `merge_content_disjoint`, `merge_content` (the old 4 functions).

3. **Delete**: The duplicated retry block at lines 813-848 of `merge_change_request()`.

4. **Update `merge_items()`**: Replace the waterfall chain with a single call to `merge_content_three_way()`.

5. **Delete unused helpers**: `edits_conflict`, `ranges_overlap` — after consolidation, only `edits_disjoint` is needed for the conflict check.

**Net result**: ~150 lines removed, 1 function to understand instead of 4.

**Tests to add**:
- `test_merge_content_three_way_trivial_cases`
- `test_merge_content_three_way_same_length_lines`
- `test_merge_content_three_way_different_length_disjoint`
- `test_merge_content_three_way_overlapping_conflict`
- `test_merge_content_three_way_whitespace_tolerance`

All existing merge tests must continue to pass (they test the end-to-end flow, not the internal functions).

**Risk**: Low. Pure refactor with no schema or API changes. Existing test coverage validates correctness.

---

### Phase 3: Dead Code Removal ✅ DONE

**Goal**: Remove `WikiPagePatch` active code and dead utility functions.

**Priority**: Low effort, low risk, reduces confusion.

**Status**: Completed. WikiPagePatch replaced with stub class. Removed `apply_changes`, `apply_markdown_diff`, `highlight_changes` from `wiki/utils.py`. Cleaned up `wiki_page_patch.js`.

**Changes**:

1. **`wiki/wiki/doctype/wiki_page_patch/wiki_page_patch.py`** — Replace with stub:
   ```python
   from frappe.model.document import Document

   class WikiPagePatch(Document):
       pass
   ```
   Keep the doctype JSON and `__init__.py` for backward compatibility (existing databases may have old records).

2. **`wiki/utils.py`** — Remove `apply_changes`, `apply_markdown_diff`, `highlight_changes` if they have no other callers (verify with grep first).

**Tests**: Existing tests should pass unchanged. No new tests needed.

**Risk**: Very low. The old code references `"Wiki Page"` which doesn't exist in the current schema.

---

### Phase 4: Delta-Based "Overlay" Revisions

**Goal**: CR working revisions only store items that differ from the base. CR creation goes from O(N) to O(1).

**Priority**: High impact on performance, but larger change — do after Phases 1-3 are stable.

**Design: Overlay Revisions**

Instead of `clone_revision()` copying all N items, a CR's `head_revision` starts empty and only accumulates items as they're edited. Reading the full tree = base items + overlay items (overlay wins).

**Schema change**:

Add to `Wiki Revision`:
```
is_overlay (Check, default 0) — if set, this revision inherits from parent_revision
hashes_stale (Check, default 0, hidden) — if set, tree_hash/content_hash need recomputation
```

**Changes**:

1. **`wiki_revision.py`** — New function `create_overlay_revision(base_revision)`:
   - Creates a Wiki Revision with `is_overlay=1`, zero items
   - Copies `tree_hash`, `content_hash`, `doc_count` from base (initially identical)

2. **`wiki_revision.py`** — New function `get_effective_revision_item_map(revision)`:
   - If `is_overlay`: return `base_items | overlay_items` (overlay wins)
   - If not overlay: return `get_revision_item_map(revision)` as before

3. **`wiki_change_request.py`** — Update `create_change_request()`:
   - Replace `clone_revision(base_revision, is_working=1)` with `create_overlay_revision(base_revision, is_working=1)`

4. **`wiki_change_request.py`** — New helper `_ensure_overlay_item(head_revision, doc_key)`:
   - If item exists in overlay → return it
   - If not → copy from base revision to overlay → return it
   - Used by `update_cr_page`, `delete_cr_page`, `move_cr_page`

5. **Update all CR read functions** (`get_cr_tree`, `get_cr_page`, `diff_change_request`) to use `get_effective_revision_item_map()`.

6. **Lazy hash computation**: Replace per-mutation `recompute_revision_hashes()` calls with `frappe.db.set_value(revision, "hashes_stale", 1)`. Add `ensure_revision_hashes()` that recomputes only when needed (before merge, before `has_revision_changes()` check).

**Data migration**:

For existing open CRs (Draft / In Review / Changes Requested):
1. Compare head_revision items against base_revision items
2. Delete identical items from head_revision
3. Set `is_overlay = 1` on head_revision

Add patch to `patches.txt`.

**Tests to add**:
- `test_create_cr_creates_empty_overlay`: Verify 0 items in head_revision after CR creation
- `test_editing_promotes_item_to_overlay`: Edit 1 page, verify only 1 item in overlay
- `test_overlay_tree_shows_all_pages`: `get_cr_tree()` returns full tree despite empty overlay
- `test_overlay_diff_shows_only_changes`: `diff_change_request()` only shows edited pages
- `test_overlay_merge_works`: Full merge lifecycle with overlay revisions
- All existing tests must pass (they test the same public API)

**Risk**: Medium. Schema change + migration. The overlay model is well-understood (it's how Docker layers work). The migration only affects open CRs.

---

### Phase 5: Optimized Merge

**Goal**: Merge only processes changed doc_keys. `apply_merge_revision` only touches changed documents.

**Depends on**: Phase 4 (overlay revisions make changed-key detection trivial).

**Changes**:

1. **`wiki_change_request.py`** — Add fast-forward path to `merge_change_request()`:
   ```python
   if cr.base_revision == space.main_revision:
       # No concurrent changes — fast-forward merge
       return _fast_forward_merge(cr, space)
   else:
       return _three_way_merge(cr, space)
   ```

2. **Fast-forward merge** (`_fast_forward_merge`):
   - Materialize effective tree from overlay
   - Create merge revision (full snapshot for main_revision)
   - Only apply changes to live tree (not the entire tree)

3. **Optimized 3-way merge** (`_three_way_merge`):
   - Find changed doc_keys: `main_changed = _find_changed_keys(base, main)`
   - Head overlay items are already only the changed keys
   - Only load content blobs for `main_changed | head_changed` keys
   - Only run merge logic for those keys
   - Start with base items, apply merge results

4. **New function `_find_changed_keys(base_items, other_items)`**:
   - Compare `content_blob`, `title`, `slug`, `parent_key`, `order_index`, `is_group`, `is_published` without loading content
   - Content blob comparison is a simple string compare (the blob name includes the hash)

5. **Optimized `apply_merge_revision`** → rename to `_apply_merge_changes_only(space, merge_revision, base_revision)`:
   - Find changed keys between merge_revision and base_revision
   - Batch-load content blobs for changed items (1 query instead of N)
   - Only `get_doc()` + `save()` for changed documents
   - Unchanged documents are not touched at all

6. **Content-only fast path**: For documents where only `content` changed (no title/slug/parent changes), use `frappe.db.set_value()` instead of `doc.save()` to skip validation. Content changes don't affect routes or tree structure.

**Impact on a 500-page wiki with 1 changed page**:
- Before: Load 1500 items + 1500 blobs, process 500 keys, create 500 items, load+save 500 docs
- After: Load ~2 items + 1 blob, process 1 key, create 500 items (merge revision is still full), load+save 1 doc

Note: The merge revision still needs to be a full snapshot (it becomes `main_revision`). But items can be bulk-inserted from base with the delta applied, rather than individually created.

**Tests to add**:
- `test_fast_forward_merge_only_updates_changed_docs`: Create 10 pages, edit 1 via CR, merge, verify only 1 doc's `modified` timestamp changed
- `test_three_way_merge_only_loads_changed_content`: Mock/count DB queries during merge to verify content isn't loaded for unchanged docs
- `test_content_only_change_skips_validation`: Edit only content (no title/slug), verify route is untouched

**Risk**: Medium. The fast-forward path is safe (it's just applying a diff). The 3-way optimization needs careful testing to ensure unchanged documents truly aren't affected.

---

### Phase 6: Simplify Draft CR Logic ✅ DONE

**Goal**: Make `get_or_create_draft_change_request()` readable.

**Priority**: Low — UX improvement, not a bug.

**Status**: Completed. Extracted the 60-line `get_or_create_draft_change_request()` into 3 focused helpers: `_find_existing_draft()`, `_is_stale_empty_draft()`, `_archive_stale_draft()`. Replaced duplicated inline hash comparison with a call to `has_revision_changes()`. Two new tests added and all 35 tests pass.

**Changes**:

Extract the 60-line function into 3 small functions:

```python
@frappe.whitelist()
def get_or_create_draft_change_request(wiki_space, title=None):
    cr = _find_existing_draft(wiki_space)
    if cr:
        if _should_replace_stale_draft(cr, wiki_space):
            _archive_stale_draft(cr)
        else:
            return cr.as_dict()

    space = frappe.get_doc("Wiki Space", wiki_space)
    default_title = title or f"Draft Changes - {space.space_name}"
    return create_change_request(wiki_space, default_title).as_dict()


def _find_existing_draft(wiki_space):
    """Find user's most relevant draft: prefer one with actual changes."""
    ...

def _should_replace_stale_draft(cr, wiki_space):
    """True if the draft is outdated AND has no changes."""
    ...

def _archive_stale_draft(cr):
    """Archive a stale empty draft."""
    ...
```

**Tests**: Existing tests cover `get_or_create_draft_change_request` indirectly. Add:
- `test_stale_empty_draft_is_auto_archived`
- `test_stale_draft_with_changes_is_kept`

**Risk**: Very low. Pure refactor with no behavior change.

---

## Execution Order

```
Phase 1 (Desk sync)          ← Do first: data integrity fix
  ↓
Phase 3 (Dead code removal)  ← Quick win, no dependencies
  ↓
Phase 2 (Merge consolidation) ← Simplifies code for Phase 5
  ↓
Phase 6 (Draft CR cleanup)   ← Quick win, no dependencies
  ↓
Phase 4 (Overlay revisions)  ← Biggest architectural change
  ↓
Phase 5 (Optimized merge)    ← Builds on Phase 4
```

Phases 1, 2, 3, 6 are independent of each other and can be done in any order.
Phase 5 depends on Phase 4.
Phase 2 should be done before Phase 5 (cleaner code to optimize).

## Dependency Graph

```
Phase 1 ──┐
Phase 3 ──┤
Phase 2 ──┼──→ Phase 4 ──→ Phase 5
Phase 6 ──┘
```

## Summary Table

| Phase | Problem | Risk | Effort | Lines Changed (est.) |
|-------|---------|------|--------|---------------------|
| 1 | Desk sync (data integrity) | Low | Medium | +60, ~10 modified |
| 2 | 4 merge strategies → 1 | Low | Low | -150, +50 |
| 3 | Dead code removal | Very Low | Very Low | -100 |
| 4 | O(N) → O(1) CR creation | Medium | High | +120, ~80 modified |
| 5 | O(N) → O(changed) merge | Medium | Medium | +100, ~60 modified |
| 6 | Draft CR cleanup | Very Low | Low | ~40 modified |

## Test Strategy

All phases add tests to `test_wiki_change_request.py`. The existing 20 tests serve as regression guards — they must pass after every phase.

Run tests with:
```bash
bench --site <site> run-tests --app wiki --module wiki.frappe_wiki.doctype.wiki_change_request.test_wiki_change_request
```

Manual verification checklist:
- [ ] Edit a Wiki Document from Desk → open Editor UI → changes visible (Phase 1)
- [ ] Create a CR on a wiki with 100+ pages → should be near-instant (Phase 4)
- [ ] Merge a CR with 1 changed page → should not take noticeably longer than creating the CR (Phase 5)
- [ ] Merge with concurrent changes (main advanced while CR was open) → 3-way merge resolves cleanly or reports conflict correctly (Phase 2 + 5)
