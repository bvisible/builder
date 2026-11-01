<!-- //// Neoffice — added file (no upstream equivalent): what the canvas draws for a block that carries a component's tag.

	 A div whose text is `{% include "…/contact_form.html" %}` is a live block on the published page (the form, the map,
	 the carousel), but the editor cannot run Jinja: the block drew nothing, stood 0px tall, and a person who had just
	 added one could not see it, click it or find it again. The server draws it (builder.api.render_component_preview,
	 only for a lawful tag) and the canvas shows that, in a shadow root so that its stylesheets and the editor's keep
	 apart, and under the block so that a click selects the block. This card stands in while nothing has come back, when
	 the site has nothing for it to show, or when it could not be drawn. It is never published. -->
<template>
	<div ref="component" :style="live ? bare : card" data-component-tag="">
		<div v-show="live" ref="stage" style="pointer-events: none" />
		<template v-if="!live">
			<div style="display: flex; align-items: center; gap: 8px; font-weight: 600">
				<span class="lucide-layout-template" style="width: 16px; height: 16px; flex: none" />
				<span>{{ label }}</span>
			</div>
			<div v-if="options" style="margin-top: 4px; opacity: 0.8">{{ options }}</div>
			<div style="margin-top: 4px; opacity: 0.6; font-size: 12px">
				{{
					empty
						? __("This block has nothing to show on this site yet — it will stay empty until it does.")
						: __(
								"It draws this site's live data once published. Select it, then open Site blocks to change its options.",
							)
				}}
			</div>
		</template>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import usePageStore from "@/stores/pageStore";
import { __ } from "@/translation";
import {
	componentPreview,
	ensureSiteComponents,
	readComponentTag,
	shadowHtml,
	siteComponents,
	summarize,
} from "@/utils/siteComponents";
import { useDebounceFn } from "@vueuse/core";
import { computed, onMounted, ref, watch } from "vue";

const component = ref<HTMLElement | null>(null);
const stage = ref<HTMLElement | null>(null);
const live = ref(false);
const empty = ref(false);
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

// Drawn by the server, and drawn again when the block's text changes, as a person changes its options. What was on screen stays until the new one is
// here, and an answer that a later change overtook is dropped. A small canvas thumbnail (`preview`) keeps the card.
const pageStore = usePageStore();
let asked = 0;
const draw = useDebounceFn(async () => {
	const text = props.block.getInnerHTML() || "";
	const mine = ++asked;
	if (props.preview || !readComponentTag(text)) return;
	try {
		const drawn = await componentPreview(text, pageStore.activePage?.name ?? null);
		if (mine !== asked || !stage.value) return;
		empty.value = drawn.state === "empty";
		live.value = drawn.state === "ok";
		if (live.value) {
			const root = stage.value.shadowRoot ?? stage.value.attachShadow({ mode: "open" });
			root.innerHTML = shadowHtml(drawn.html);
		}
	} catch {
		if (mine === asked) live.value = false;
	}
}, 200);
onMounted(() => void draw());
watch(
	() => props.block.getInnerHTML(),
	() => void draw(),
);

const bare = { boxSizing: "border-box", width: "100%" } as const;

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
