# Editor troubleshooting

## The activity log (`wiki:debug`)

The editor keeps a small log in `localStorage['wiki:trace']` so a freeze can be
diagnosed from another tab (a frozen tab cannot open its own DevTools).

- On: `localStorage.setItem('wiki:debug', '1')` in DevTools on any tab of the site.
- Off: `localStorage.removeItem('wiki:debug')`.
- Read: DevTools > Application > Local storage > `wiki:trace`. The last
  `...:start` without a matching `...:end` is the step that never finished.

It is off by default. Two events are always recorded because they mean
something already went wrong: `editor:contentReady:loop-stopped` and
`draft:verify:resave`.

## Finding a page that does not survive the editor

With `wiki:debug` on, opening a page logs `editor:canonicalize:unstable` when
the page's text changes every time it goes through the editor, with the first
place it differs (`a` is the text, `b` the text after another pass). Send that
entry with the page's markdown around `at`.

## Manual check: no draft is lost on submit

1. Create a page, paste 1000+ lines, wait for "Saved".
2. Reload: the text must be intact and the page must not read as edited.
3. Edit one line, submit for review, reload: the edit must be in the change request.
4. Withdraw, edit again, submit, merge: the published page must show the edit.
5. Open DevTools > Application > IndexedDB > `wiki-drafts`: drafts of a merged
   or rejected change request are removed a few seconds after the next page load.
