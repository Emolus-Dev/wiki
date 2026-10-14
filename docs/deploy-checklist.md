# Deploy checklist (private wiki, signed-in users only)

Do it on a copy of the site first. Nothing below is destructive, but this branch changes how every page is
rendered, adds two fields to Wiki Space and rewrites how attachments work.

## 1. Before

- [ ] Backup: `bench --site <site> backup --with-files`.
- [ ] Restore that backup on a staging site and deploy there first.

## 2. Deploy

```
git pull                      # the branch
bench --site <site> migrate   # Wiki Space: version_group, version_label
bench build --app wiki
bench restart
bench --site <site> clear-cache
bench --site <site> clear-website-cache
```

Hard-reload the browser (Ctrl+Shift+R): the frontend, fonts and reader CSS are new.

## 3. Run the tests that could not run while this was written

```
bench --site <staging> run-tests --app wiki
```

Python tests that need Frappe (permissions, feedback, presence, page history, analytics feedback, file sizes,
private uploads, related pages) were written but never executed.

## 4. What the HTML filter would change

```
bench --site <site> execute wiki.wiki.html_audit.run
```

Lists each page whose raw HTML loses a tag or attribute (inline SVG, `id` anchors, iframes from hosts the editor
does not offer). Fix those pages, or tell me what to allow. Pages written only in markdown are unaffected.

## 5. It really is private

Open a private window (no session) and check each of these answers 404 or sends you to login, never content:

- [ ] a page URL, and the same URL with `.md` or `Accept: text/markdown`
- [ ] `/api/method/wiki.frappe_wiki.doctype.wiki_document.wiki_document.get_page_data` with a real `route`
- [ ] `/api/method/wiki.frappe_wiki.doctype.wiki_document.wiki_document.download_pdf?route=<route>`
- [ ] the search box
- [ ] `sitemap.xml` and `llms.txt` list no page of a restricted space

And in Space Settings > Access: **Public (read only)** is off on every space and no space has the `Guest` role.

## 6. Files

A public file (`/files/...`) opens for anyone who has the link, signed in or not. For a private wiki, attach
sensitive files with **Attach file > Private file**.

- [ ] With two users who can read the space: user A attaches a private file; user B opens the page and downloads
      it. (A private file is attached to the space so every reader can open it; if user B gets 403, tell me.)
- [ ] A visitor with no session gets 403 on the same URL.

Images pasted or uploaded in the editor are public files. If images are sensitive, say so: they can default to
private.

## 7. Smoke test, as an editor

- [ ] Open a long page; type; the tab does not freeze; "Saved" appears.
- [ ] Copy button on a code block copies (also over plain HTTP).
- [ ] Submit for review, merge, open the published page: text, tables, callouts, `:::details`, code groups.
- [ ] Page history shows the merge; compare and restore work.
- [ ] Files list above the page; breadcrumbs; "Linked from"; version switcher if you use versions.
- [ ] Search finds a word in Spanish with accents and another form of the word.

## 8. Roll back

Nothing is deleted by the migration. To go back: check out the previous commit, `bench build --app wiki`,
`bench restart`. The two new Wiki Space fields stay in the table, unused.
