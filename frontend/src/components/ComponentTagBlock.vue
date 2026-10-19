<!-- //// Neoffice — added file (no upstream equivalent): what the canvas draws for a block that carries a component's tag.

	 A div whose text is `{% include "…/contact_form.html" %}` is a live block on the published page (the form, the map,
	 the carousel), but the editor cannot run Jinja: the block drew nothing, stood 0px tall, and a person who had just
	 added one could not see it, click it or find it again. This card stands in for it: the component's name, the
	 options it carries, and where to change them. It is never published, only the editor's canvas shows it. -->
<template>
	<div ref="component" :style="card" data-component-tag="">
		<div style="display: flex; align-items: center; gap: 8px; font-weight: 600">
			<span class="lucide-layout-template" style="width: 16px; height: 16px; flex: none" />
			<span>{{ label }}</span>
		</div>
		<div v-if="options" style="margin-top: 4px; opacity: 0.8">{{ options }}</div>
		<div style="margin-top: 4px; opacity: 0.6; font-size: 12px">
			{{
				__(
					"It draws this site's live data once published. Select it, then open Site blocks to change its options.",
				)
			}}
		</div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import { __ } from "@/translation";
import { ensureSiteComponents, readComponentTag, siteComponents, summarize } from "@/utils/siteComponents";
import { computed, ref } from "vue";

const component = ref<HTMLElement | null>(null);
const props = defineProps<{
	block: Block;
	// BuilderBlock hands these to every block it draws with its own component; none is used here
	data?: Record<string, unknown> | null;
	componentData?: Record<string, unknown> | null;
	defaultProps?: Record<string, unknown> | null;
	breakpoint?: string;
	preview?: boolean;
	repeaterIndex?: string | number | null;
}>();

// the names come from the catalogue; until it is here the card says what it can from the tag itself
void ensureSiteComponents();

const read = computed(() => readComponentTag(props.block.getInnerHTML()));
const known = computed(() => siteComponents.value.find((c) => c.path === read.value?.path));
const label = computed(
	() =>
		known.value?.label ||
		read.value?.path
			.split("/")
			.pop()
			?.replace(/\.html$/, "") ||
		__("Component"),
);
const options = computed(() => (read.value ? summarize(read.value, known.value) : ""));

// inline, because a page's own stylesheet is what is loaded in the canvas: a class of the editor could be reset
const card = {
	boxSizing: "border-box",
	width: "100%",
	minHeight: "64px",
	padding: "14px 16px",
	border: "1px dashed #9ca3af",
	borderRadius: "8px",
	background: "#f3f4f6",
	color: "#374151",
	font: "14px/1.4 system-ui, sans-serif",
	textAlign: "left",
} as const;

defineExpose({ component });
</script>
