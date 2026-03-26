import { computed, watch } from 'vue';
import { useStorage } from '@vueuse/core';
import LucideMoon from '~icons/lucide/moon';
import LucideSun from '~icons/lucide/sun';

const THEME_STORAGE_KEY = 'wiki-theme';

export function useTheme() {
	const theme = useStorage(THEME_STORAGE_KEY, 'dark');

	const themeIcon = computed(() =>
		theme.value === 'dark' ? LucideSun : LucideMoon,
	);

	function applyTheme(value) {
		document.documentElement.setAttribute('data-theme', value);
	}

	function toggleTheme() {
		theme.value = theme.value === 'dark' ? 'light' : 'dark';
	}

	watch(
		theme,
		(value) => {
			applyTheme(value);
		},
		{ immediate: true },
	);

	return {
		theme,
		themeIcon,
		toggleTheme,
		applyTheme,
	};
}
