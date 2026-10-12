<template>
	<div class="flex h-full flex-col" data-testid="home-page">
		<PageHeaderMobile v-if="isMobile" :title="__('Home')">
			<template #suffix><MobileAppMenu /></template>
		</PageHeaderMobile>

		<ScrollArea class="min-h-0 flex-1">
			<div class="mx-auto flex w-full max-w-5xl flex-col gap-14 px-5 pb-16 pt-12 sm:px-8 sm:pt-16">
				<section class="flex flex-col items-center text-center">
					<h1
						class="font-display text-[2.5rem] font-medium leading-[1.1] tracking-tight text-ink-gray-9 sm:text-[3.25rem]"
						data-testid="home-greeting"
					>
						{{ greeting }}
					</h1>
					<p class="mt-3 text-base text-ink-gray-6">
						{{ __('What do you need to pick up today?') }}
					</p>

					<button
						type="button"
						class="mt-8 flex h-12 w-full max-w-2xl items-center gap-3 rounded-5 border border-outline-gray-2 bg-surface-base px-4 text-left shadow-sm transition-colors hover:border-outline-gray-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-4"
						data-testid="home-search"
						@click="openCommandPalette('home')"
					>
						<span class="lucide-search size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
						<span class="flex-1 truncate text-base text-ink-gray-5">
							{{ __('Search pages, snippets and attachments…') }}
						</span>
						<KeyboardShortcut combo="Mod+K" class="text-ink-gray-4" />
					</button>

					<div
						v-if="recentPages.length"
						class="mt-4 flex flex-wrap justify-center gap-2"
						data-testid="home-chips"
					>
						<router-link
							v-for="page in recentPages"
							:key="page.name"
							:to="{ name: 'SpacePage', params: { spaceId: page.space, pageId: page.name } }"
							class="rounded-full border border-outline-gray-2 bg-surface-base px-3 py-1 text-sm text-ink-gray-7 transition-colors hover:bg-surface-gray-2"
						>
							{{ page.title }}
						</router-link>
					</div>
				</section>

				<section v-if="homeSpaces.length || spaces.loading" data-testid="home-spaces">
					<div class="mb-5 flex items-baseline justify-between">
						<h2 class="font-display text-[1.625rem] font-medium leading-tight text-ink-gray-9">
							{{ __('Spaces') }}
						</h2>
						<router-link
							:to="{ name: 'AllSpaces' }"
							class="text-sm text-ink-green-7 hover:underline"
						>
							{{ __('View all') }}
						</router-link>
					</div>
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
						<template v-if="!homeSpaces.length">
							<Skeleton v-for="i in 4" :key="i" class="h-40 rounded-6" />
						</template>
						<router-link
							v-for="space in homeSpaces"
							v-else
							:key="space.name"
							:to="{ name: 'SpaceDetails', params: { spaceId: space.name } }"
							class="group flex flex-col rounded-6 border border-outline-gray-2 bg-surface-base p-5 transition-all hover:-translate-y-0.5 hover:border-outline-gray-3 hover:shadow-md"
							data-testid="home-space-card"
						>
							<SpaceAvatar
								:space="space"
								:label="space.space_name || space.name"
								size="xl"
							/>
							<span class="mt-4 truncate text-lg-medium text-ink-gray-9">
								{{ space.space_name || space.name }}
							</span>
							<span class="mt-0.5 truncate font-mono text-xs text-ink-gray-5">
								/{{ space.route }}
							</span>
							<span class="mt-3 text-sm text-ink-gray-6">
								{{ pageCount(space.name) }}
							</span>
						</router-link>
					</div>
				</section>

				<div class="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
					<section data-testid="home-recent">
						<h2 class="mb-5 font-display text-[1.625rem] font-medium leading-tight text-ink-gray-9">
							{{ __('Recently edited') }}
						</h2>
						<div class="overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-base">
							<template v-if="!recentDocs.data">
								<Skeleton v-for="i in 4" :key="i" class="m-3 h-10 rounded-4" />
							</template>
							<p
								v-else-if="!recentDocs.data.length"
								class="p-6 text-center text-sm text-ink-gray-5"
							>
								{{ __('No pages yet') }}
							</p>
							<router-link
								v-for="doc in recentDocs.data || []"
								v-else
								:key="doc.name"
								:to="{ name: 'SpacePage', params: { spaceId: doc.wiki_space, pageId: doc.name } }"
								class="flex items-center gap-3 border-b border-outline-gray-1 px-4 py-3 last:border-b-0 hover:bg-surface-gray-1"
							>
								<span class="lucide-file-text size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
								<span class="min-w-0 flex-1">
									<span class="block truncate text-base text-ink-gray-9">{{ doc.title }}</span>
									<span class="block truncate text-sm text-ink-gray-5">
										{{ spaceLabel(doc.wiki_space) }}
									</span>
								</span>
								<span class="shrink-0 text-sm text-ink-gray-5">
									{{ dayjsLocal(doc.modified).fromNow() }}
								</span>
							</router-link>
						</div>
					</section>

					<section data-testid="home-snippets">
						<div class="mb-5 flex items-center justify-between">
							<h2 class="font-display text-[1.625rem] font-medium leading-tight text-ink-gray-9">
								{{ __('Pinned snippets') }}
							</h2>
							<Button
								variant="ghost"
								size="sm"
								:label="__('Add')"
								data-testid="home-snippet-add"
								@click="showAddSnippet = true"
							>
								<template #prefix>
									<span class="lucide-plus size-4" aria-hidden="true" />
								</template>
							</Button>
						</div>
						<div class="flex flex-col gap-3">
							<p
								v-if="!pinnedSnippets.length"
								class="rounded-6 border border-dashed border-outline-gray-3 p-6 text-center text-sm text-ink-gray-5"
							>
								{{ __('Pin the commands you reach for most. They stay in this browser.') }}
							</p>
							<div
								v-for="snippet in pinnedSnippets"
								:key="snippet.id"
								class="wiki-code-card group"
								data-testid="home-snippet"
							>
								<div class="wiki-code-card__bar">
									<span class="min-w-0 flex-1 truncate">{{ snippet.title }}</span>
									<button
										type="button"
										class="wiki-code-card__btn opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
										:aria-label="__('Remove snippet')"
										@click="removeSnippet(snippet.id)"
									>
										<span class="lucide-x size-3.5" aria-hidden="true" />
									</button>
									<button
										type="button"
										class="wiki-code-card__btn"
										:aria-label="__('Copy code')"
										@click="copySnippet(snippet)"
									>
										<span
											:class="copiedId === snippet.id ? 'lucide-check' : 'lucide-copy'"
											class="size-3.5"
											aria-hidden="true"
										/>
									</button>
								</div>
								<pre class="wiki-code-card__body"><code>{{ snippet.code }}</code></pre>
							</div>
						</div>
					</section>
				</div>
			</div>
		</ScrollArea>

		<Dialog
			v-model:open="showAddSnippet"
			:title="__('Pin a snippet')"
			:actions="[{ label: __('Pin'), variant: 'solid', onClick: saveSnippet }]"
		>
			<template #default>
				<div class="flex flex-col gap-4">
					<FormControl
						v-model="draft.title"
						type="text"
						:label="__('Title')"
						:placeholder="__('Restart bench')"
					/>
					<FormControl
						v-model="draft.code"
						type="textarea"
						:rows="5"
						:label="__('Code')"
						:placeholder="__('bench restart')"
						input-class="font-mono"
					/>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import MobileAppMenu from '@/components/MobileAppMenu.vue';
import SpaceAvatar from '@/components/SpaceAvatar.vue';
import { useCommandPalette } from '@/composables/useCommandPalette';
import { useMobile } from '@/composables/useMobile';
import { usePinnedSnippets } from '@/composables/usePinnedSnippets';
import { useRecentPages } from '@/composables/useRecentPages';
import { useSpaceLibrary } from '@/composables/useSpaceLibrary';
import { useUserStore } from '@/stores/user';
import {
	Button,
	Dialog,
	FormControl,
	KeyboardShortcut,
	PageHeaderMobile,
	ScrollArea,
	Skeleton,
	createListResource,
	dayjsLocal,
	toast,
	usePageMeta,
} from 'frappe-ui';
import { computed, reactive, ref } from 'vue';

const userStore = useUserStore();
const { isMobile } = useMobile();
const { open: openCommandPalette } = useCommandPalette();
const { recentPages } = useRecentPages();
const { pinnedSnippets, addSnippet, removeSnippet } = usePinnedSnippets();

const CARD_COUNT = 4;

// The same query the sidebar runs, so the cards agree with it on order, pins
// and which spaces a non-manager may see. A wide page doubles as the lookup
// that turns a recent page's `wiki_space` into a name.
const { spaces, orderedSpaces, spaceStats } = useSpaceLibrary({
	limit: 100,
	withStats: true,
	publishedOnly: computed(() => !userStore.isWikiManager),
});
const homeSpaces = computed(() => orderedSpaces.value.slice(0, CARD_COUNT));

const recentDocs = createListResource({
	doctype: 'Wiki Document',
	fields: ['name', 'title', 'wiki_space', 'modified'],
	filters: { is_group: 0 },
	orderBy: 'modified desc',
	pageLength: 5,
	auto: true,
});

const greeting = computed(() => {
	const name = userStore.data?.first_name;
	return name ? __('Hello, {0}', [name]) : __('Hello');
});

function spaceLabel(name) {
	const space = (spaces.data || []).find((row) => row.name === name);
	return space?.space_name || name;
}

function pageCount(space) {
	const count = spaceStats.value[space]?.pages;
	if (count === undefined) return '';
	return count === 1 ? __('1 page') : __('{0} pages', [count]);
}

const showAddSnippet = ref(false);
const draft = reactive({ title: '', code: '' });

function saveSnippet({ close }) {
	if (!addSnippet(draft)) {
		toast.error(__('Add some code to pin'));
		return;
	}
	draft.title = '';
	draft.code = '';
	close();
}

const copiedId = ref(null);
async function copySnippet(snippet) {
	await navigator.clipboard.writeText(snippet.code);
	copiedId.value = snippet.id;
	setTimeout(() => {
		if (copiedId.value === snippet.id) copiedId.value = null;
	}, 2000);
}

usePageMeta(() => ({ title: `${__('Home')} | Frappe Wiki` }));
</script>
