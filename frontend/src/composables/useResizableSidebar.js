import { clampSidebarWidth } from '@/lib/sidebarWidth';
import { useStorage } from '@vueuse/core';
import { ref } from 'vue';

// The width is stored, so it is the same the next time the editor opens.
export function useResizableSidebar(storageKey, defaultWidth) {
	const stored = useStorage(storageKey, defaultWidth);
	const width = ref(clampSidebarWidth(stored.value, window.innerWidth));
	const dragging = ref(false);

	function set(px, save = true) {
		width.value = clampSidebarWidth(px, window.innerWidth);
		if (save) stored.value = width.value;
	}

	function startDrag(event) {
		const startX = event.clientX;
		const startWidth = width.value;
		const handle = event.currentTarget;
		handle.setPointerCapture?.(event.pointerId);
		dragging.value = true;
		const move = (e) => set(startWidth + e.clientX - startX, false);
		const stop = () => {
			handle.removeEventListener('pointermove', move);
			handle.removeEventListener('pointerup', stop);
			handle.removeEventListener('pointercancel', stop);
			dragging.value = false;
			set(width.value);
		};
		handle.addEventListener('pointermove', move);
		handle.addEventListener('pointerup', stop);
		handle.addEventListener('pointercancel', stop);
	}

	return {
		width,
		dragging,
		startDrag,
		nudge: (delta) => set(width.value + delta),
		reset: () => set(defaultWidth),
	};
}
