<template>
  <div class="flex flex-col h-full">
    <div
      class="flex items-center justify-between p-4 border-b border-outline-gray-2 bg-surface-white shrink-0"
    >
      <div class="flex items-center gap-4">
        <Button
          variant="ghost"
          icon-left="arrow-left"
          :route="{ name: 'ChangeRequests' }"
        >
          {{ __("Back") }}
        </Button>
        <div v-if="changeRequest.doc">
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold text-ink-gray-9">
              {{ changeRequest.doc.title }}
            </h1>
            <Badge
              :variant="'subtle'"
              :theme="getStatusTheme(changeRequest.doc.status)"
              size="sm"
            >
              {{ changeRequest.doc.status }}
            </Badge>
          </div>
          <p class="text-sm text-ink-gray-5 mt-0.5">
            {{ changeRequest.doc.wiki_space }}
            <span v-if="changeRequest.doc.owner">
              &middot; {{ __("by") }} {{ changeRequest.doc.owner }}
            </span>
          </p>
        </div>
      </div>

      <div v-if="canReview" class="flex items-center gap-2">
        <Button @click="showRejectDialog = true">
          {{ __("Request Changes") }}
        </Button>
        <Button
          v-if="hasConflicts"
          variant="solid"
          :disabled="!allResolved"
          :loading="resolvingMerge"
          @click="handleResolveAndMerge"
        >
          {{ __("Resolve & Merge") }}
        </Button>
        <Button
          v-else
          variant="solid"
          :loading="mergeResource.loading"
          @click="handleApprove"
        >
          {{ __("Merge") }}
        </Button>
      </div>

      <div v-else-if="canWithdraw" class="flex items-center gap-2">
        <Button
          variant="outline"
          :loading="withdrawResource.loading"
          @click="handleWithdraw"
        >
          {{ __("Archive") }}
        </Button>
      </div>
    </div>

    <div class="flex-1 overflow-auto p-4">
      <div
        v-if="reviewNote"
        class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg"
      >
        <div class="flex items-start gap-3">
          <LucideAlertCircle class="size-5 text-red-500 shrink-0 mt-0.5" />
          <div>
            <p class="font-medium text-red-800">
              {{ __("Changes Requested") }}
            </p>
            <p class="text-sm text-red-700 mt-1">{{ reviewNote.comment }}</p>
            <p class="text-xs text-red-600 mt-2">
              {{ __("Reviewed by") }} {{ reviewNote.reviewer }} {{ __("on") }}
              {{ formatDate(reviewNote.reviewed_at) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Conflict resolution banner -->
      <div
        v-if="hasConflicts"
        class="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg"
      >
        <div class="flex items-start gap-3">
          <LucideAlertTriangle class="size-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p class="font-medium text-amber-800">
              {{ __("Merge Conflicts") }}
            </p>
            <p class="text-sm text-amber-700 mt-1">
              {{
                __(
                  "The following documents have conflicting changes. Choose which version to keep for each conflict.",
                )
              }}
            </p>
            <p class="text-sm text-amber-600 mt-2 font-medium">
              {{ resolvedCount }}/{{ conflicts.length }} {{ __("resolved") }}
            </p>
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <!-- Conflict list (replaces changes list when conflicts exist) -->
        <template v-if="hasConflicts">
          <h3 class="text-lg font-medium text-ink-gray-8">
            {{ __("Conflicts") }} ({{ conflicts.length }})
          </h3>

          <div class="space-y-3">
            <div
              v-for="conflict in conflicts"
              :key="conflict.name"
              class="border border-outline-gray-2 rounded-lg overflow-hidden"
              :class="{ 'border-amber-300': !resolutions[conflict.name] }"
            >
              <div
                class="flex items-center justify-between p-4 bg-surface-gray-1 cursor-pointer"
                @click="toggleConflict(conflict.name)"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="flex items-center justify-center size-8 rounded-full shrink-0 bg-amber-100 text-amber-600"
                  >
                    <LucideAlertTriangle class="size-4" />
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-ink-gray-9">
                        {{
                          conflict.ours_title ||
                          conflict.theirs_title ||
                          conflict.doc_key
                        }}
                      </span>
                      <Badge
                        variant="subtle"
                        :theme="getConflictTheme(conflict.conflict_type)"
                        size="sm"
                      >
                        {{ conflict.conflict_type }}
                      </Badge>
                      <Badge
                        v-if="resolutions[conflict.name]"
                        variant="subtle"
                        theme="green"
                        size="sm"
                      >
                        {{
                          resolutions[conflict.name] === "ours"
                            ? __("Keep Main")
                            : __("Keep Your Changes")
                        }}
                      </Badge>
                    </div>
                  </div>
                </div>
                <LucideChevronDown
                  class="size-5 text-ink-gray-4 transition-transform"
                  :class="{
                    'rotate-180': expandedConflicts.has(conflict.name),
                  }"
                />
              </div>

              <div
                v-if="expandedConflicts.has(conflict.name)"
                class="border-t border-outline-gray-2"
              >
                <div class="grid grid-cols-2 gap-4 px-4 pt-4">
                  <FormControl
                    type="checkbox"
                    :label="__('Keep Main')"
                    :modelValue="resolutions[conflict.name] === 'ours'"
                    @update:modelValue="setResolution(conflict.name, 'ours')"
                  />
                  <FormControl
                    type="checkbox"
                    :label="__('Keep Your Changes')"
                    :modelValue="resolutions[conflict.name] === 'theirs'"
                    @update:modelValue="setResolution(conflict.name, 'theirs')"
                  />
                </div>
                <div class="p-4 relative z-0 isolate">
                  <DiffViewer
                    :old-content="conflict.ours_content || ''"
                    :new-content="conflict.theirs_content || ''"
                    :file-name="
                      conflict.ours_title ||
                      conflict.theirs_title ||
                      conflict.doc_key
                    "
                    language="markdown"
                  />
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Normal changes list -->
        <template v-else>
          <h3 class="text-lg font-medium text-ink-gray-8">
            {{ __("Changes") }} ({{ changes.data?.length || 0 }})
          </h3>

          <div
            v-if="changes.loading"
            class="flex items-center justify-center py-8"
          >
            <LoadingIndicator class="size-8" />
          </div>

          <div v-else-if="changes.data?.length" class="space-y-3">
            <div
              v-for="change in changes.data"
              :key="change.doc_key"
              class="border border-outline-gray-2 rounded-lg overflow-hidden"
            >
              <div
                class="flex items-center justify-between p-4 bg-surface-gray-1 cursor-pointer"
                @click="toggleChange(change.doc_key)"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="flex items-center justify-center size-8 rounded-full shrink-0"
                    :class="getChangeIconClass(change.change_type)"
                  >
                    <component
                      :is="getChangeIcon(change.change_type)"
                      class="size-4"
                    />
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-ink-gray-9">
                        {{ change.title || __("Untitled") }}
                      </span>
                      <Badge
                        variant="subtle"
                        :theme="getChangeTheme(change.change_type)"
                        size="sm"
                      >
                        {{ getChangeLabel(change.change_type) }}
                      </Badge>
                    </div>
                    <p class="text-sm text-ink-gray-5">
                      {{
                        getChangeDescription(
                          change.change_type,
                          change.is_group,
                          change.is_external_link,
                        )
                      }}
                    </p>
                    <p
                      v-if="change.is_external_link && change.external_url"
                      class="text-sm text-ink-gray-5 mt-0.5"
                    >
                      <a
                        :href="change.external_url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="text-blue-600 hover:underline"
                      >
                        {{ change.external_url }}
                      </a>
                    </p>
                  </div>
                </div>
                <LucideChevronDown
                  class="size-5 text-ink-gray-4 transition-transform"
                  :class="{ 'rotate-180': expandedChanges.has(change.doc_key) }"
                />
              </div>

              <div
                v-if="expandedChanges.has(change.doc_key)"
                class="border-t border-outline-gray-2"
              >
                <div class="p-4 relative z-0 isolate">
                  <DiffViewer
                    v-if="diffsByDocKey[change.doc_key]"
                    :old-content="
                      diffsByDocKey[change.doc_key]?.base?.content || ''
                    "
                    :new-content="
                      diffsByDocKey[change.doc_key]?.head?.content || ''
                    "
                    :file-name="change.title || change.doc_key"
                    language="markdown"
                  />
                  <div v-else class="flex items-center justify-center py-8">
                    <LoadingIndicator class="size-6" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="text-center py-8 text-ink-gray-5">
            {{ __("No changes in this change request.") }}
          </div>
        </template>
      </div>
    </div>

    <Dialog v-model="showRejectDialog" :options="{ size: 'md' }">
      <template #body-title>
        <h3 class="text-xl font-semibold text-ink-gray-9">
          {{ __("Request Changes") }}
        </h3>
      </template>
      <template #body-content>
        <div class="space-y-4">
          <p class="text-ink-gray-7">
            {{ __("Please provide feedback explaining what needs to change.") }}
          </p>
          <FormControl
            v-model="rejectComment"
            type="textarea"
            :label="__('Feedback')"
            :placeholder="__('Enter your feedback...')"
            :rows="4"
          />
        </div>
      </template>
      <template #actions="{ close }">
        <div class="flex justify-end gap-2">
          <Button variant="outline" @click="close">{{ __("Cancel") }}</Button>
          <Button
            variant="solid"
            theme="red"
            :loading="rejectResource.loading"
            @click="handleReject(close)"
          >
            {{ __("Request Changes") }}
          </Button>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import {
  Button,
  Badge,
  Dialog,
  FormControl,
  LoadingIndicator,
} from "frappe-ui";
import DiffViewer from "@/components/DiffViewer.vue";
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import { useContributionReview } from "@/composables/useContributionReview";

const props = defineProps({
  changeRequestId: {
    type: String,
    required: true,
  },
});

const {
  getChangeIcon,
  getChangeIconClass,
  getChangeTheme,
  getChangeLabel,
  getChangeDescription,
  showRejectDialog,
  rejectComment,
  expandedChanges,
  diffsByDocKey,
  hasConflicts,
  conflicts,
  resolutions,
  expandedConflicts,
  resolvingMerge,
  resolvedCount,
  allResolved,
  changeRequest,
  changes,
  mergeResource,
  rejectResource,
  withdrawResource,
  canReview,
  canWithdraw,
  reviewNote,
  setResolution,
  toggleConflict,
  toggleChange,
  handleApprove,
  handleResolveAndMerge,
  handleReject,
  handleWithdraw,
  getStatusTheme,
  getConflictTheme,
  formatDate,
} = useContributionReview(props.changeRequestId);
</script>
