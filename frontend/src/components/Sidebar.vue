<template>
<Sidebar
	v-model:collapsed="isSidebarCollapsed"
	:header="{
		title: __('Frappe Wiki'),
		logo: '/assets/wiki/images/wiki-logo.png',
		menuItems: [{ label: __('Toggle Theme'), icon: themeIcon, onClick: toggleTheme }]
	}"
	:sections="[
		{
			label: '',
			items: [
				{ label: __('Spaces'), icon: LucideRocket, to: { name: 'SpaceList' }, isActive: isSpacesActive },
				{ label: __('Change Requests'), icon: LucideGitBranch, to: { name: 'ChangeRequests' }, isActive: isChangeRequestsActive },
			]
		}
	]"
/>
</template>

<script setup>
import { Sidebar } from "frappe-ui";

import { onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { useStorage } from "@vueuse/core";
import LucideMoon from "~icons/lucide/moon";
import LucideSun from "~icons/lucide/sun";
import LucideRocket from "~icons/lucide/rocket";
import LucideGitBranch from "~icons/lucide/git-branch";

const route = useRoute();

const userTheme = useStorage("wiki-theme", "dark");

const themeIcon = computed(() => {
	return userTheme.value === "dark" ? LucideSun : LucideMoon;
});

const isSidebarCollapsed  = useStorage("is-sidebar-collapsed", false);

const isSpacesActive = computed(() => route.path.startsWith("/spaces"));
const isChangeRequestsActive = computed(() => route.path.startsWith("/change-requests"));

onMounted(() => {
	document.documentElement.setAttribute("data-theme", userTheme.value);
});

function toggleTheme() {
	const currentTheme = userTheme.value;
	const newTheme = currentTheme === "dark" ? "light" : "dark";
	document.documentElement.setAttribute("data-theme", newTheme);
	userTheme.value = newTheme;
}
</script>
