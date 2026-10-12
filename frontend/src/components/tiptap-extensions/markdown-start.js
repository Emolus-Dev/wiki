/**
 * Where a custom block tokenizer's `start()` looks for its marker.
 *
 * marked calls every `start()` at the head of each paragraph, to know where to
 * cut the paragraph short. The text it receives is *everything left in the
 * document*, so a `start()` that searches all of it costs O(document) per
 * paragraph: O(n^2) for a page, and seconds of frozen UI when a long guide is
 * saved (parse 47 KB: 0.2 s, 95 KB: 1 s, 190 KB: 5 s).
 *
 * A paragraph cannot run past a blank line, so a marker beyond the next one can
 * never cut it. Searching only up to there gives the same answer for the same
 * parse, in time proportional to the paragraph.
 */
export function startInParagraph(src, find) {
	const blank = src.indexOf('\n\n');
	return find(blank === -1 ? src : src.slice(0, blank));
}

// A line can only start an ordered list item if it opens with an alphanumeric
// marker and a `.` or `)` followed by whitespace. Looser than TipTap's own
// pattern on purpose: it only has to be a fast way to say "certainly not".
const ORDERED_ITEM_OPENING = /^\s*[0-9A-Za-z]+[.)]\s/;

/**
 * TipTap's ordered list tokenizer splits the whole remaining document into
 * lines every time marked tries it, which is at every block, so a long page
 * parsed in O(n^2): about two thirds of the time to save a 190 KB guide.
 *
 * This runs the same tokenizer on a window instead: not at all when the next
 * line cannot open a list, otherwise on a window that grows until the list ends
 * inside it. The token is the one the tokenizer returns for the whole text.
 */
export function boundedListTokenize(tokenize, opening = ORDERED_ITEM_OPENING) {
	function boundedTokenize(src, tokens, lexer) {
		const newline = src.indexOf('\n');
		if (!opening.test(newline === -1 ? src : src.slice(0, newline))) {
			return undefined;
		}

		let size = 4096;
		for (;;) {
			const whole = size >= src.length;
			const text = whole ? src : src.slice(0, size);
			const token = tokenize.call(this, text, tokens, lexer);
			if (whole || !token) return token;

			// The window's last line may be cut short, so the list must have
			// stopped before it for the token to be final.
			const consumed = token.raw.split('\n').length;
			if (consumed < text.split('\n').length - 1) return token;
			size *= 4;
		}
	}

	// Kept so tests can compare against the tokenizer it wraps.
	boundedTokenize.original = tokenize;
	return boundedTokenize;
}
