export const SIDEBAR_MIN = 240;
export const SIDEBAR_MAX = 640;

// Never more than half the window, so the content always keeps room to read.
export function clampSidebarWidth(px, viewport = Infinity) {
	const value = Number(px);
	if (!Number.isFinite(value)) return SIDEBAR_MIN;
	const max = Math.max(SIDEBAR_MIN, Math.min(SIDEBAR_MAX, Math.round(viewport * 0.5)));
	return Math.round(Math.max(SIDEBAR_MIN, Math.min(value, max)));
}
