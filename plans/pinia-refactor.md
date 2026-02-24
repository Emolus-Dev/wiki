# Pinia State Management Migration Plan (Tracer Bullet Approach)

## Context

The wiki frontend has no centralized state management. State is scattered across module-level refs (`currentChangeRequest`), reactive singletons (`session`), global resources (`userResource`), and role-checking functions (`isWikiManager`, `canAccessWiki`) awkwardly living in `useChangeRequest.js`. Pinia will provide a structured, discoverable, and maintainable state layer.

**Approach:** Tracer bullets — build the thinnest possible end-to-end slice first, prove the architecture works, then expand.

## Target Architecture

3 Setup stores: `useUserStore`, `useSessionStore`, `useChangeRequestStore`

```
src/stores/
  index.js              # createPinia() instance
  user.js               # useUserStore
  session.js            # useSessionStore
  changeRequest.js      # useChangeRequestStore
```

What stays outside Pinia: `socket.js`, `translation.js`, `useSidebarResize.js`, sidebar theme/collapsed, page document resources, dialog visibility refs.

---

## Phase 1: Tracer Bullet — One Store, One Consumer, Full Stack [DONE]

**Goal:** Prove Pinia works end-to-end with frappe-ui resources in this codebase. One store, one consuming component, build passes, app loads.

**The slice:** Install Pinia → Create `useUserStore` with _only_ `isWikiManager` → Wire it into `SpaceList.vue` (simplest consumer — just checks the role) → Build & verify.

| Step | File | What |
|---|---|---|
| 1 | `package.json` | `yarn add pinia` |
| 2 | `src/stores/index.js` | **Create** — `createPinia()` export |
| 3 | `src/main.js` | Add `app.use(pinia)` |
| 4 | `src/stores/user.js` | **Create** — minimal `useUserStore` with just `userResource` + `isWikiManager` computed |
| 5 | `src/components/SpaceList.vue` | Replace `import { isWikiManager } from "@/composables/useChangeRequest"` with `useUserStore()`, change `computed(() => isWikiManager())` → `userStore.isWikiManager` |

**Verify:** `yarn build` succeeds. App loads. SpaceList page shows/hides "Create Space" button correctly based on role. Old code still works everywhere else (untouched).

**What this proves:**
- Pinia initializes with the Frappe/Vite setup
- A Setup store can own a `createResource` from frappe-ui
- Store getters reactively derive from resource data
- A component can consume store state in templates
- Old imports and new store coexist

> **Completed:** 2026-02-24 — commit `a5ef57c` on `r/pinia`. Build passes, browser-tested (New Space button visible for Admin, sidebar loads, no console errors).

---

## Phase 2: Widen the User Store — All Consumers [DONE]

**Goal:** Now that the pattern works, migrate all remaining `isWikiManager` / `canAccessWiki` / `userResource` consumers.

| Step | File | What |
|---|---|---|
| 1 | `src/stores/user.js` | Add `canAccessWiki`, `shouldUseChangeRequestMode`, `data`, `roles`, `isLoading`, `fetch()`, `reload()`, `reset()` |
| 2 | `src/layouts/MainLayout.vue` | `canAccessWiki()` + `userResource` → `userStore` |
| 3 | `src/pages/Contributions.vue` | `isWikiManager()` → `userStore.isWikiManager` |
| 4 | `src/pages/ContributionReview.vue` | `isWikiManager()` + `userResource` → `userStore` |
| 5 | `src/router.js` | `userResource.fetch()` → `useUserStore().fetch()` (inside `beforeEach`, safe timing) |
| 6 | `src/composables/useChangeRequest.js` | Remove `isWikiManager`, `canAccessWiki`, `shouldUseChangeRequestMode` functions + `userResource` import |
| 7 | `src/data/user.js` | Deferred to Phase 3 — `session.js` still imports from it |

**Verify:** Build passes. Login redirects work. Role-gated UI (manager actions, access denied page) all behave correctly.

> **Completed:** 2026-02-24 — commit `95b4865` on `r/pinia`. Build passes, browser-tested (spaces list with New Space button, change-requests tabs with Pending Reviews visible for manager, contribution review page renders with correct role-gated UI).

---

## Phase 3: Session Store — Full Migration [DONE]

**Goal:** Prove cross-store communication works (session → user). Session is small enough to migrate fully in one shot.

| Step | File | What |
|---|---|---|
| 1 | `src/stores/session.js` | **Create** — `useSessionStore` with cookie user, `isLoggedIn`, login/logout resources. Login `onSuccess` calls `useUserStore().reload()` lazily. |
| 2 | `src/router.js` | Replace `import { session } from './data/session'` → `useSessionStore().isLoggedIn` inside `beforeEach` |
| 3 | `src/data/session.js` | **Delete** |

**Verify:** Build passes. Unauthenticated users get redirected to `/login`. Login/logout cycle works. Cross-store lazy call doesn't cause circular dep issues.

**What this proves:**
- Cross-store composition works (session store calling user store lazily)
- Store access inside `router.beforeEach` has correct timing (after `app.use(pinia)`)

> **Completed:** 2026-02-24 — commit `ac193d2` on `r/pinia`. Build passes, browser-tested (login redirect works, spaces list with New Space button, sidebar tree loads, no console errors post-auth). Also deleted `src/data/` directory (no remaining consumers).

---

## Phase 4: Change Request Store — Full Component Tree (Atomic)

**Why atomic:** `currentChangeRequest` is a singleton ref shared by 7 components. You can't bridge it — Vue's `watch()` requires a real reactive source, so a getter/setter proxy between old ref and new store breaks watchers. All readers and writers must move together.

**Goal:** Migrate the entire `currentChangeRequest` consumer tree at once.

| Step | File | What |
|---|---|---|
| 1 | `src/stores/changeRequest.js` | **Create** — full `useChangeRequestStore` merging `useChangeRequestMode` + `useChangeRequest` |
| 2 | `src/pages/SpaceDetails.vue` | `useChangeRequestMode` + `currentChangeRequest` + `isWikiManager` → `useChangeRequestStore()` + `useUserStore()` |
| 3 | `src/components/WikiDocumentPanel.vue` | `useChangeRequestMode` + `useChangeRequest` + `currentChangeRequest` → `useChangeRequestStore()` |
| 4 | `src/components/WikiDocumentList.vue` | Same pattern |
| 5 | `src/components/NestedDraggable.vue` | `useChangeRequest` + `currentChangeRequest` → `useChangeRequestStore()` |
| 6 | `src/components/DraftContributionPanel.vue` | Same pattern as WikiDocumentPanel |
| 7 | `src/pages/ContributionReview.vue` | `currentChangeRequest` → `crStore.currentChangeRequest` |
| 8 | `src/composables/useChangeRequest.js` | **Delete** |

**Verify:** Build passes. Full editing flow works: navigate to space → sidebar tree loads → click page → editor opens → edit content → save → changes count updates in banner → submit for review → merge.

> **Completed:** 2026-02-24 — commit `64752a2` on `r/pinia`. Build passes, browser-tested (spaces list with New Space button, sidebar tree loads, page editor opens with content, change-requests tabs render, CR draft banner visible, no Vue console errors).

---

## Phase 5: Cleanup [DONE]

| Step | What |
|---|---|
| 1 | **Delete** `src/data/` directory |
| 2 | Verify no remaining imports from deleted files |
| 3 | Final `yarn build` clean |

> **Completed:** 2026-02-24 — all cleanup already done in Phases 3-4 (`src/data/` deleted in Phase 3, `src/composables/useChangeRequest.js` deleted in Phase 4). No stale imports remain. Final `yarn build` passes clean. Browser-tested: spaces list with New Space button, sidebar tree loads, page editor opens with content, change-requests tabs render with both My Change Requests and Pending Reviews, no console errors.

---

## Key Design Decisions

1. **Setup stores** (Composition API style) — matches existing `<script setup>` patterns and wraps `createResource` naturally.
2. **`createResource` stays as-is inside stores.** Returns reactive proxies that work in Pinia with zero wrapping.
3. **Singleton resources.** Old composables created new resource instances per call. Store creates them once — shared `.loading` state is more correct.
4. **`spaceId` becomes an action argument.** `crStore.initChangeRequest(props.spaceId)` instead of `useChangeRequestMode(spaceId)`.
5. **Cross-store calls are lazy.** `useUserStore()` called inside actions/computeds, never at store top-level — avoids circular deps.
6. **CR store migrates as an atomic unit.** The `currentChangeRequest` singleton can't be partially migrated — all readers and writers must move together.

## Component Migration Cheatsheet

```js
// BEFORE (composable pattern)
import { useChangeRequestMode, useChangeRequest, currentChangeRequest } from '@/composables/useChangeRequest'
const spaceIdRef = toRef(props, 'spaceId')
const { isChangeRequestMode, changesResource, initChangeRequest, loadChanges } = useChangeRequestMode(spaceIdRef)
const { createPage, updatePage } = useChangeRequest()
watch(() => currentChangeRequest.value?.name, ...)

// AFTER (Pinia store)
import { useChangeRequestStore } from '@/stores/changeRequest'
const crStore = useChangeRequestStore()
// crStore.isChangeRequestMode, crStore.changesResource, etc.
// crStore.initChangeRequest(props.spaceId)  — spaceId as arg, not composable param
// crStore.createPage(...), crStore.updatePage(...)
// watch(() => crStore.currentChangeRequest?.name, ...)  — no .value needed
```

## Verification After Each Phase

1. `yarn build` — must succeed
2. **Automated browser testing** via `agent-browser` on `http://wiki.localhost:8000`
   - Credentials: `Administrator` / `admin`
   - Login at `http://wiki.localhost:8000/login` if needed
3. Check console for Vue reactivity warnings
4. Confirm old + new code coexist (during transitional phases)

### Phase-Specific Browser Tests

**After Phase 1 (Tracer Bullet):**
- Navigate to `http://wiki.localhost:8000/wiki/spaces`
- Verify "Create Space" button is visible (Administrator has Wiki Manager role)
- Click into a space, confirm sidebar tree loads without errors

**After Phase 2 (User Store Widened):**
- Navigate to spaces list — manager UI elements visible
- Navigate to `/wiki/change-requests` — tabs render correctly
- Open a change request review page — role-gated actions appear

**After Phase 3 (Session Store):**
- Open `http://wiki.localhost:8000/wiki` — should load (authenticated)
- Logout → should redirect to `/login`
- Login with `Administrator` / `admin` → should redirect back to wiki

**After Phase 4 (Change Request Store):**
- Navigate to a space → sidebar tree loads
- Click a page → editor opens with content
- Edit content → save → verify "unsaved changes" clears
- Check contribution banner shows change count
- Submit change request for review
- Navigate to `/wiki/change-requests` → verify it appears
- Open the CR → merge it
