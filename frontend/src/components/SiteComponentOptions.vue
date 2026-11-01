<!-- //// Neoffice — added file (no upstream equivalent): the options of the selected component, applied as they are changed.

	 The form is the one of the Site blocks panel (SiteComponentFields), in the block's own properties: click a component
	 and its options are there, and each change writes the block's tag, which the canvas draws again from the server
	 (ComponentTagBlock.vue). The tag is built and held to what the component declares on the server, as everywhere
	 (builder.api.render_component_tag): a value it refuses says why here and leaves the block as it was. -->
<template>
	<div v-if="editing" class="flex w-full flex-col gap-2" data-testid="site-component-options">
		<p v-if="editing.values === null" class="text-p-sm text-ink-gray-5">
			{{ __("This block's tag was written by hand: it cannot be changed from here.") }}
		</p>
		<template v-else>
			<p v-if="editing.component.help" class="text-p-sm text-ink-gray-5">{{ editing.component.help }}</p>
			<SiteComponentFields v-model:form="form" :component="editing.component" />
			<p v-if="problem" class="text-p-sm text-ink-red-3">{{ problem }}</p>
		</template>
	</div>
</template>

<script setup lang="ts">
import type Block from "@/block";
import SiteComponentFields from "@/components/SiteComponentFields.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { __ } from "@/translation";
import { getErrorMessage } from "@/utils/helpers";
import {
	chosenOptions,
	ensureSiteComponents,
	formFromValues,
	readComponentTag,
	siteComponents,
	type OptionsForm,
	type SiteComponent,
} from "@/utils/siteComponents";
import { useDebounceFn } from "@vueuse/core";
import { createResource } from "frappe-ui";
import { computed, ref, watch } from "vue";

type Editing = { block: Block; component: SiteComponent; values: Record<string, unknown> | null };

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const editing = ref<Editing | null>(null);
const form = ref<OptionsForm>({ typed: {}, flags: {} });
const problem = ref("");

const readTag = createResource({ url: "builder.api.read_component_tag" });
const tagFor = createResource({ url: "builder.api.render_component_tag" });

const selected = computed<Block | null>(() => {
	const blocks = canvasStore.activeCanvas?.selectedBlocks;
	return blocks && blocks.length === 1 ? (blocks[0] as Block) : null;
});

// what this form wrote last: the block's text changing to it is not a reason to read the block again, which would
// put back a form the person is still typing in
let written = "";
// the options as they stand on the block: selecting a block must not rewrite it, only a change does
let applied = "";
let reading = 0;

watch(
	() => [selected.value?.blockId, selected.value?.getInnerHTML?.()] as const,
	async ([, html]) => {
		const block = selected.value;
		const text = html ?? "";
		if (block && text === written && editing.value?.block === block) return;
		const mine = ++reading;
		problem.value = "";
		if (!block || !readComponentTag(text)) {
			editing.value = null;
			return;
		}
		try {
			await ensureSiteComponents();
			const read = await readTag.submit({ text });
			if (mine !== reading) return;
			const component = read && siteComponents.value.find((c) => c.path === read.path);
			if (!component) {
				editing.value = null;
				return;
			}
			written = text;
			form.value = formFromValues(component, read.values);
			applied = JSON.stringify(chosenOptions(component, form.value));
			editing.value = { block, component, values: read.values };
		} catch {
			if (mine === reading) editing.value = null;
		}
	},
	{ immediate: true },
);

const apply = useDebounceFn(async () => {
	const current = editing.value;
	if (!current || current.values === null || builderStore.readOnlyMode) return;
	try {
		const values = JSON.stringify(chosenOptions(current.component, form.value));
		if (values === applied) return;
		const tag: string = await tagFor.submit({ path: current.component.path, values });
		problem.value = "";
		applied = values;
		written = tag;
		current.block.setInnerHTML(tag);
	} catch (e) {
		problem.value = getErrorMessage(e, __("The block could not be updated."));
	}
}, 350);

watch(form, () => void apply(), { deep: true });
</script>
