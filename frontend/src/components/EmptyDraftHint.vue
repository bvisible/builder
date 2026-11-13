<!-- //// Neoffice — added file (no upstream equivalent): says what the empty first page of a site being built is. -->
<!-- The editor showed a blank page beside the assistant, and a person who does not know the Builder could not tell
     whether a page or a whole site was being made (neoffice-maintenance#2614). This lies over the canvas, never in it:
     the blank draft and its root block stay exactly what the site pipeline expects (site_creation_page). -->
<template>
	<div
		v-if="visible"
		class="pointer-events-none absolute bottom-0 z-[5] grid place-items-center p-10"
		:style="{
			top: 'var(--toolbar-height)',
			left: `${builderStore.builderLayout.leftPanelWidth + builderStore.builderLayout.optionsPanelWidth}px`,
			right: `${builderStore.showRightPanel ? builderStore.builderLayout.rightPanelWidth : 0}px`,
		}">
		<div
			class="max-w-sm rounded-6 border border-outline-gray-2 bg-surface-base/95 px-6 py-5 text-center shadow-sm">
			<p class="text-p-base font-semibold text-ink-gray-9">{{ __("Your site is built here") }}</p>
			<p class="mt-2 text-p-sm leading-snug text-ink-gray-6">
				{{
					__(
						"This is the first page, still empty. Answer {0}'s questions on the left: she writes this page, then creates the other pages and the menu.",
						[name],
					)
				}}
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { assistantName } from "@/utils/neofficeBoot";
import { computed } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();
const name = assistantName("Bob AI");

// only while the assistant's tab is open over a page with nothing in it: a page that has content, or an editor
// without the assistant, shows no word of it
const visible = computed(
	() =>
		builderStore.isAIEnabled &&
		builderStore.showLeftPanel &&
		builderStore.leftPanelActiveTab === "Chat" &&
		canvasStore.editingMode === "page" &&
		(pageStore.pageBlocks[0]?.children?.length ?? 1) === 0,
);
</script>
