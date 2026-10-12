<template>
	<div class="divide-y divide-outline-gray-1">
		<SettingsRow
			:title="__('Public Pages Language')"
			:description="
				__(
					'Language of published pages for visitors who are not logged in. Logged-in users see their own language.',
				)
			"
		>
			<Select
				class="w-48"
				:model-value="publicLanguage"
				:options="languageOptions"
				:disabled="savingLanguage"
				data-testid="setting-public-language"
				@update:model-value="saveLanguage"
			/>
		</SettingsRow>

		<SettingToggle
			:settings="settings"
			fieldname="enable_table_of_contents"
			:title="__('Enable Table of Contents')"
			:description="__('Show an auto-generated table of contents on wiki pages')"
		/>

		<SettingToggle
			:settings="settings"
			fieldname="auto_convert_images_to_webp"
			:title="__('Auto Convert Image to WebP')"
			:description="
				__('Automatically convert uploaded PNG/JPEG images to WebP to reduce page size')
			"
		/>

		<SettingToggle
			v-if="metaImagesSupported"
			:settings="settings"
			fieldname="auto_generate_meta_images"
			:title="__('Auto Generate Meta Images')"
			:description="
				__(
					'Generate a branded social preview image for pages that have no Meta Image uploaded',
				)
			"
		/>

		<ViewTrackingToggle />
	</div>
</template>

<script setup>
import { Select, SettingsRow, createListResource } from 'frappe-ui';
import { computed, ref } from 'vue';
import SettingToggle from './SettingToggle.vue';
import ViewTrackingToggle from './ViewTrackingToggle.vue';

// A site with neither Chromium nor Node and satori has no card renderer.
const metaImagesSupported = window.meta_images_supported;

const props = defineProps({
	settings: {
		type: Object,
		required: true,
	},
});

const languages = createListResource({
	doctype: 'Language',
	fields: ['name', 'language_name'],
	filters: { enabled: 1 },
	orderBy: 'language_name asc',
	pageLength: 200,
	auto: true,
});

const publicLanguage = computed(
	() => props.settings.doc?.public_language || 'es',
);

// The saved code stays selectable even if its Language row is disabled.
const languageOptions = computed(() => {
	const options = (languages.data || []).map((row) => ({
		label: row.language_name || row.name,
		value: row.name,
	}));
	if (!options.some((option) => option.value === publicLanguage.value)) {
		options.unshift({
			label: publicLanguage.value,
			value: publicLanguage.value,
		});
	}
	return options;
});

const savingLanguage = ref(false);
async function saveLanguage(value) {
	savingLanguage.value = true;
	try {
		await props.settings.setValue.submit({ public_language: value });
	} finally {
		savingLanguage.value = false;
	}
}
</script>
