<template>
  <div class="flex h-full">
    <aside
      ref="sidebarRef"
      class="border-r border-outline-gray-2 flex flex-col bg-surface-gray-1 relative flex-shrink-0"
      :style="{ width: `${sidebarWidth}px` }"
    >
      <!-- Header -->
      <div class="p-4 border-b border-outline-gray-2">
        <div class="flex items-center justify-between mb-3">
          <Button
            variant="ghost"
            icon-left="arrow-left"
            :route="{ name: 'SpaceList' }"
          >
            {{ __("Back to Spaces") }}
          </Button>
          <Button
            variant="ghost"
            icon="settings"
            :title="__('Settings')"
            @click="showSettingsDialog = true"
          />
        </div>
        <div class="flex items-center gap-2">
          <h1 class="text-lg font-semibold text-ink-gray-9">
            {{ space.doc?.space_name || spaceId }}
          </h1>
          <Button
            v-if="space.doc?.route"
            variant="ghost"
            icon="external-link"
            :title="__('View Space')"
            :link="'/' + space.doc?.route"
          />
        </div>
        <p class="text-sm text-ink-gray-5 mt-0.5">{{ space.doc?.route }}</p>
      </div>

      <div v-if="space.doc && treeData" class="flex-1 overflow-auto p-2">
        <WikiDocumentList
          :tree-data="treeData"
          :change-type-map="changeTypeMap"
          :space-id="spaceId"
          :root-node="treeData.root_group || space.doc.root_group"
          :selected-page-id="currentPageId"
          :selected-draft-key="currentDraftKey"
          @refresh="refreshTree"
          @reorder-state-change="handleReorderStateChange"
        />
      </div>
      <div v-else class="flex-1 overflow-auto p-2">
        <!-- Sidebar tree skeleton -->
        <div class="space-y-1 animate-pulse">
          <div
            v-for="i in 8"
            :key="i"
            class="flex items-center gap-2 px-2 py-1.5 rounded"
          >
            <div class="size-4 rounded bg-surface-gray-3 shrink-0" />
            <div
              class="h-3.5 rounded bg-surface-gray-3"
              :style="{ width: `${60 + (i % 3) * 25}%` }"
            />
          </div>
          <div
            v-for="i in 4"
            :key="'nested-' + i"
            class="flex items-center gap-2 px-2 py-1.5 rounded ml-6"
          >
            <div class="size-4 rounded bg-surface-gray-3 shrink-0" />
            <div
              class="h-3.5 rounded bg-surface-gray-3"
              :style="{ width: `${50 + (i % 2) * 30}%` }"
            />
          </div>
        </div>
      </div>

      <div
        class="absolute top-0 right-0 w-1 h-full cursor-col-resize z-10"
        :class="
          sidebarResizing ? 'bg-surface-gray-4' : 'hover:bg-surface-gray-4'
        "
        @mousedown="startResize"
      />
    </aside>

    <main class="flex-1 flex flex-col bg-surface-white min-w-0">
      <ContributionBanner
        :mergeDisabled="isTreeReordering"
        @submit="handleSubmitChangeRequest"
        @withdraw="handleArchiveChangeRequest"
        @merge="handleMergeChangeRequest"
      />
      <div class="flex-1 overflow-auto">
        <router-view :space-id="spaceId" @refresh="refreshTree" />
      </div>
    </main>

    <Dialog v-model="showSettingsDialog">
      <template #body-title>
        <h3 class="text-xl font-semibold text-ink-gray-9">
          {{ __("Space Settings") }}
        </h3>
      </template>
      <template #body-content>
        <div class="space-y-4 py-2">
          <div
            class="flex items-center justify-between p-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1"
          >
            <div class="flex-1 mr-4">
              <p class="text-sm font-medium text-ink-gray-9">
                {{ __("Published") }}
              </p>
              <p class="text-xs text-ink-gray-5 mt-0.5">
                {{ __("Make this wiki space publicly accessible") }}
              </p>
            </div>
            <Switch
              v-model="isPublished"
              :disabled="updatingPublishSetting"
              @update:modelValue="updatePublishSetting"
            />
          </div>
          <div
            class="flex items-center justify-between p-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1"
          >
            <div class="flex-1 mr-4">
              <p class="text-sm font-medium text-ink-gray-9">
                {{ __("Enable Feedback Collection") }}
              </p>
              <p class="text-xs text-ink-gray-5 mt-0.5">
                {{
                  __(
                    "Show a feedback widget on wiki pages to collect user reactions",
                  )
                }}
              </p>
            </div>
            <Switch
              v-model="enableFeedbackCollection"
              :disabled="updatingFeedbackSetting"
              @update:modelValue="updateFeedbackSetting"
            />
          </div>
          <div
            class="flex items-center justify-between p-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1"
          >
            <div class="flex-1 mr-4">
              <p class="text-sm font-medium text-ink-gray-9">
                {{ __("Bulk Update Routes") }}
              </p>
              <p class="text-xs text-ink-gray-5 mt-0.5">
                {{
                  __("Change the base route for this space and all its pages")
                }}
              </p>
            </div>
            <Button variant="outline" size="sm" @click="openUpdateRoutesDialog">
              {{ __("Update") }}
            </Button>
          </div>
          <div
            class="flex items-center justify-between p-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1"
          >
            <div class="flex-1 mr-4">
              <p class="text-sm font-medium text-ink-gray-9">
                {{ __("Clone Space") }}
              </p>
              <p class="text-xs text-ink-gray-5 mt-0.5">
                {{ __("Create a new space with the same structure") }}
              </p>
            </div>
            <Button variant="outline" size="sm" @click="openCloneSpaceDialog">
              {{ __("Clone") }}
            </Button>
          </div>
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end">
          <Button variant="outline" @click="close">{{ __("Close") }}</Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showUpdateRoutesDialog">
      <template #body-title>
        <h3 class="text-xl font-semibold text-ink-gray-9">
          {{ __("Update Wiki Space Routes") }}
        </h3>
      </template>
      <template #body-content>
        <div class="space-y-4 py-2">
          <FormControl
            type="text"
            :label="__('Current Base Route')"
            :modelValue="space.doc?.route"
            :disabled="true"
          />
          <FormControl
            type="text"
            :label="__('New Base Route')"
            v-model="newRoute"
            :placeholder="__('Enter new route (without leading slash)')"
          />
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="outline" @click="close">{{ __("Cancel") }}</Button>
          <Button
            variant="solid"
            :loading="updatingRoutes"
            @click="updateRoutes(close)"
          >
            {{ __("Update Routes") }}
          </Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showCloneSpaceDialog">
      <template #body-title>
        <h3 class="text-xl font-semibold text-ink-gray-9">
          {{ __("Clone Wiki Space") }}
        </h3>
      </template>
      <template #body-content>
        <div class="space-y-4 py-2">
          <FormControl
            type="text"
            :label="__('New Space Route')"
            v-model="cloneRoute"
            :placeholder="__('Enter new route (without leading slash)')"
          />
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="outline" @click="close">{{ __("Cancel") }}</Button>
          <Button
            variant="solid"
            :loading="cloningSpace"
            @click="cloneSpace(close)"
          >
            {{ __("Start Cloning") }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  createDocumentResource,
  Button,
  Dialog,
  Switch,
  FormControl,
} from "frappe-ui";
import WikiDocumentList from "../components/WikiDocumentList.vue";
import ContributionBanner from "../components/ContributionBanner.vue";
import { useSidebarResize } from "../composables/useSidebarResize";
import { useSpaceSettings } from "@/composables/useSpaceSettings";
import { useSpaceChangeRequestFlow } from "@/composables/useSpaceChangeRequestFlow";

const props = defineProps({
  spaceId: {
    type: String,
    required: true,
  },
});

const route = useRoute();
const router = useRouter();

const sidebarRef = ref(null);
const { sidebarWidth, sidebarResizing, startResize } =
  useSidebarResize(sidebarRef);

const space = createDocumentResource({
  doctype: "Wiki Space",
  name: props.spaceId,
  auto: true,
  whitelistedMethods: {
    updateRoutes: "update_routes",
    cloneWikiSpace: "clone_wiki_space_in_background",
  },
});

const {
  crStore,
  isTreeReordering,
  currentPageId,
  currentDraftKey,
  treeData,
  changeTypeMap,
  refreshTree,
  handleReorderStateChange,
  handleSubmitChangeRequest,
  handleArchiveChangeRequest,
  handleMergeChangeRequest,
} = useSpaceChangeRequestFlow({ props, route, router, space });

const {
  showSettingsDialog,
  showUpdateRoutesDialog,
  showCloneSpaceDialog,
  newRoute,
  updatingRoutes,
  cloneRoute,
  cloningSpace,
  enableFeedbackCollection,
  updatingFeedbackSetting,
  isPublished,
  updatingPublishSetting,
  updateFeedbackSetting,
  updatePublishSetting,
  openUpdateRoutesDialog,
  openCloneSpaceDialog,
  updateRoutes,
  cloneSpace,
} = useSpaceSettings(space, refreshTree);
</script>
