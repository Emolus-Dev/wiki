// What deleting a group takes with it: every page and sub-group below it, except
// what the draft already marks as deleted.
export function countDeletion(node) {
	const counts = { pages: 0, groups: 0 };
	const walk = (children) => {
		for (const child of children || []) {
			if (child.is_deleted) continue;
			if (child.is_group) counts.groups += 1;
			else counts.pages += 1;
			walk(child.children);
		}
	};
	walk(node?.children);
	return counts;
}
