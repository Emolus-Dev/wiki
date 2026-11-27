import { ref } from 'vue';

const showCommandPalette = ref(false);

function show() {
	showCommandPalette.value = true;
}

export function useCommandPalette() {
	function open() {
		show();
	}

	function close() {
		showCommandPalette.value = false;
	}

	function toggle() {
		if (showCommandPalette.value) close();
		else show();
	}

	return { showCommandPalette, open, close, toggle };
}
