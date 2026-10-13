/**
 * Move tab `from` of the code group at `groupPos` to index `to`. Returns false
 * when there is nothing to move.
 */
export function moveGroupTab(tr, groupPos, from, to) {
	const group = tr.doc.nodeAt(groupPos);
	if (!group || from === to) return false;
	if (from < 0 || to < 0 || from >= group.childCount || to >= group.childCount) {
		return false;
	}

	const starts = [];
	let pos = groupPos + 1;
	group.forEach((child) => {
		starts.push(pos);
		pos += child.nodeSize;
	});

	const moved = group.child(from);
	const fromStart = starts[from];
	const fromEnd = fromStart + moved.nodeSize;
	// Where the tab lands, in the document as it is before the delete.
	const target =
		to > from ? starts[to] + group.child(to).nodeSize : starts[to];

	tr.insert(target, moved);
	// Inserting after the tab shifts nothing before it; inserting before shifts it.
	const shift = target <= fromStart ? moved.nodeSize : 0;
	tr.delete(fromStart + shift, fromEnd + shift);
	return true;
}
