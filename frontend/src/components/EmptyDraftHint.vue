<!-- //// Neoffice — added file (no upstream equivalent): says what an empty page is, and offers to design it with Nora. -->
<!-- The editor showed a blank page, and a person who does not know the Builder could not tell what to do with it
     (neoffice-maintenance#2614). This lies over the canvas, never in it: an empty page stays exactly empty (its root
     block alone, what the site pipeline expects of site_creation_page). Jérémy, 13.11: « si on édite une page ou qu'on
     crée une page qui est vide, elle doit s'afficher vide dans le builder, mais qu'on ait un CTA en disant designer avec
     Nora ». The button opens Nora's tab and starts the conversation: the site's (as ?nora=site) while no page of the
     site is built, else this page's. It is gone once the conversation has begun; the words stay while the page is
     empty. -->
<template>
	<div
		v-if="visible"
		class="pointer-events-none absolute bottom-0 z-[5] grid place-items-center p-10"
		:style="{
			top: 'var(--toolbar-height)',
			left: `${builderStore.showLeftPanel ? builderStore.builderLayout.leftPanelWidth + builderStore.builderLayout.optionsPanelWidth : 0}px`,
			right: `${builderStore.showRightPanel ? builderStore.builderLayout.rightPanelWidth : 0}px`,
		}">
		<div
			class="pointer-events-auto max-w-sm rounded-6 border border-outline-gray-2 bg-surface-base/95 px-7 py-6 text-center shadow-sm">
			<NoraOrb class="mx-auto" />
			<p class="empty-draft-hint-title mt-3 text-ink-gray-9">{{ title }}</p>
			<p class="mt-2 text-p-sm leading-snug text-ink-gray-6">{{ text }}</p>
			<!-- the one action, in ink (the editor's solid button follows its dark theme too) -->
			<Button v-if="offered" variant="solid" size="md" class="mt-4" @click="design">
				{{ __("Design with {0}", named) }}
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import NoraOrb from "@/components/Icons/NoraOrb.vue";
import { isSiteCreationRoute } from "@/composables/useSiteCreation";
import { noraKickoff, noraStartedPages } from "@/composables/useNoraKickoff";
import { __ } from "@/translation";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { assistantName } from "@/utils/neofficeBoot";
import { hasNoraChat } from "@/utils/noraChatHost";
import { Button, call } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();
const route = useRoute();
const name = assistantName("Bob AI");
// the POT's extractor loses a call whose list of values opens on its line and closes on another (`__("…", [`)
const named = [name];

const pageId = computed(() => String(route.params.pageId || ""));
const empty = computed(
	() => canvasStore.editingMode === "page" && (pageStore.pageBlocks[0]?.children?.length ?? 1) === 0,
);
// a page that has content, or an editor without the assistant, shows no word of it
const visible = computed(() => builderStore.isAIEnabled && empty.value);

// what the server says of this page: whether its site has a built page yet, whether its conversation has begun
const site = ref(false);
const startedHere = ref(false);
watch(
	[pageId, empty],
	async ([id, isEmpty]) => {
		site.value = false;
		startedHere.value = false;
		if (!id || id === "new" || !isEmpty) return;
		try {
			const r = (await call("builder.site_ai.nora.api.page_kickoff", { page_id: id })) as {
				site: boolean;
				started: boolean;
			};
			if (id !== pageId.value) return;
			site.value = Boolean(r?.site);
			startedHere.value = Boolean(r?.started);
		} catch {
			/* the words stay; the button follows what this tab knows */
		}
	},
	{ immediate: true },
);

const started = computed(
	() =>
		startedHere.value ||
		noraStartedPages.value.includes(pageId.value) ||
		noraKickoff.value?.pageId === pageId.value ||
		isSiteCreationRoute(route),
);
// Nora's conversation draws in the tab (nora installed); upstream's panel does not take the request
const offered = computed(() => hasNoraChat() && !started.value);

const title = computed(() => (site.value ? __("Your site is built here") : __("This page is empty")));
const text = computed(() => {
	if (site.value)
		return started.value
			? __(
					"This is the first page, still empty. Answer {0}'s questions on the left: she writes this page, then creates the other pages and the menu.",
					named,
				)
			: __(
					"This is the first page of your site, still empty. {0} builds it with you, then creates the other pages and the menu.",
					named,
				);
	return started.value
		? __("Answer {0}'s questions on the left: she draws this page in the style of your site.", named)
		: __(
				"{0} can design it with you: she asks what the page is for, then draws it in the style of your site.",
				named,
			);
});

function design() {
	noraKickoff.value = { kind: site.value ? "site" : "page", pageId: pageId.value };
	builderStore.showLeftPanel = true;
	builderStore.leftPanelActiveTab = "Chat";
}
</script>

<style scoped>
/* the design system's titles are in Forum (§ 6.12) */
.empty-draft-hint-title {
	font-family: "Forum", serif;
	font-size: 22px;
	line-height: 1.2;
}
</style>
