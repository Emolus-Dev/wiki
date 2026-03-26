<template>
  <Sidebar
    v-model:collapsed="isSidebarCollapsed"
    :header="{
      title: __('Frappe Wiki'),
      logo: '/assets/wiki/images/wiki-logo.png',
      menuItems: [
        { label: __('Toggle Theme'), icon: themeIcon, onClick: toggleTheme },
      ],
    }"
    :sections="sections"
  />
</template>

<script setup>
import { Sidebar } from "frappe-ui";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useStorage } from "@vueuse/core";
import LucideRocket from "~icons/lucide/rocket";
import LucideGitBranch from "~icons/lucide/git-branch";
import { useTheme } from "@/composables/useTheme";

const route = useRoute();
const router = useRouter();

const { themeIcon, toggleTheme } = useTheme();

const isSidebarCollapsed = useStorage("is-sidebar-collapsed", false);

const navItems = [
  { label: __("Spaces"), icon: LucideRocket, to: { name: "SpaceList" } },
  {
    label: __("Change Requests"),
    icon: LucideGitBranch,
    to: { name: "ChangeRequests" },
  },
];

const sections = computed(() => [
  {
    label: "",
    items: navItems.map((item) => ({
      ...item,
      isActive: route.path.startsWith(router.resolve(item.to).path),
    })),
  },
]);
</script>
