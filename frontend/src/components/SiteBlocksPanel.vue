<!-- //// Neoffice — added file (no upstream equivalent): the site's live blocks, for a person.

	 The generator learned what a page can carry from a catalogue (builder/site_ai/components.py)
	 on 2026-09-15. This is the other half of that promise: the same catalogue, in the editor, so
	 the client can drop their products carousel or their blog listing themselves and set what it
	 takes — instead of only the assistant being able to.

	 These are not the saved components of the Components tab: those are blocks a user designed.
	 These are blocks an APP provides, and they draw the site's own live data. -->
<template>
	<div class="flex flex-col gap-3 px-3 pb-3">
		<p class="text-p-sm text-ink-gray-5">
			{{ __("Blocks that show this site's own data. Pick one, set what it needs, and it lands on the page.") }}
		</p>

		<div v-if="loading" class="text-p-sm text-ink-gray-4">{{ __("Loading…") }}</div>
		<div v-else-if="error" class="text-p-sm text-ink-red-3">{{ error }}</div>
		<div v-else-if="!components.length" class="text-p-sm text-ink-gray-4">
			{{ __("No block is available on this site yet.") }}
		</div>

		<div v-for="component in components" :key="component.path" class="rounded border border-outline-gray-1">
			<button
				class="flex w-full items-start gap-2 p-2 text-left hover:bg-surface-gray-1"
				@click="toggle(component)">
				<div class="flex-1">
					<div class="flex items-center gap-2">
						<span class="text-base font-medium text-ink-gray-8">{{ component.label }}</span>
						<span
							v-if="component.has_data === false"
							class="rounded bg-surface-gray-2 px-1 text-xs text-ink-gray-5">
							{{ __("nothing to show yet") }}
						</span>
					</div>
					<p class="mt-0.5 text-p-sm text-ink-gray-5">{{ component.shows }}</p>
				</div>
			</button>

			<div v-if="open === component.path" class="border-t border-outline-gray-1 p-2">
				<p v-if="component.has_data === false" class="mb-2 text-p-sm text-ink-gray-5">
					{{ __("This block has nothing to show on this site yet — it will stay empty until it does.") }}
				</p>
				<p v-if="component.note" class="mb-2 text-p-sm text-ink-gray-5">{{ component.note }}</p>

				<div v-for="param in component.params" :key="param.name" class="mb-2">
					<!-- //// BuilderInput emits update:modelValue on `change` — that is, on blur — and
						 debounced by 100ms, while it emits `input` on every keystroke. Clicking "Add to
						 the page" right after typing fired the click handler BEFORE the debounce, so the
						 value was still unset and the block landed without it (found on screen,
						 2026-09-16). Listening to both closes that race: `input` for typing, and
						 update:modelValue for the number arrows, which emit only that one. -->
					<BuilderInput
						v-if="param.type !== 'bool'"
						:type="param.type === 'int' ? 'number' : 'text'"
						:label="param.name"
						:description="param.about"
						:placeholder="String(param.default ?? '')"
						:modelValue="typed[param.name] ?? ''"
						@input="(v: string) => (typed[param.name] = v)"
						@update:modelValue="(v: string) => (typed[param.name] = String(v ?? ''))" />
					<label v-else class="flex items-center gap-2 text-p-sm text-ink-gray-7">
						<input
							type="checkbox"
							:checked="Boolean(flags[param.name] ?? param.default)"
							@change="(e) => (flags[param.name] = (e.target as HTMLInputElement).checked)" />
						<span>{{ param.name }} — {{ param.about }}</span>
					</label>
				</div>

				<Button variant="solid" class="w-full" :loading="inserting" @click="insert(component)">
					{{ __("Add to the page") }}
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import useCanvasStore from "@/stores/canvasStore";
import { getBlockInstance } from "@/utils/helpers";
import { __ } from "@/translation";
// BuilderInput is registered globally in main.ts; Button and toast come from frappe-ui
import { Button, createResource, toast } from "frappe-ui";
import { onMounted, ref } from "vue";

type Param = { name: string; type: string; default: unknown; about: string };
type SiteComponent = {
	label: string;
	path: string;
	app: string;
	shows: string;
	pages: string[];
	params: Param[];
	tag: string;
	note: string;
	has_data: boolean | null;
};

const canvasStore = useCanvasStore();
const components = ref<SiteComponent[]>([]);
// what was typed, exactly as typed: coercing while someone is still typing fights their cursor
// (an int field would turn "1." back into "1"), so the coercion happens once, on insert.
const typed = ref<Record<string, string>>({});
const flags = ref<Record<string, boolean>>({});
const open = ref<string | null>(null);
const loading = ref(true);
const inserting = ref(false);
const error = ref("");

const listing = createResource({
	url: "builder.api.get_site_components",
	onSuccess: (data: SiteComponent[]) => {
		components.value = data || [];
		loading.value = false;
	},
	onError: (e: Error) => {
		error.value = e?.message || __("The components could not be loaded.");
		loading.value = false;
	},
});

const tagFor = createResource({ url: "builder.api.render_component_tag" });

onMounted(() => listing.fetch());

const toggle = (component: SiteComponent) => {
	// one open at a time, and its fields start empty: a blank field means "use the default",
	// which is what the catalogue's default column already says
	open.value = open.value === component.path ? null : component.path;
	typed.value = {};
	flags.value = {};
};

const chosen = (component: SiteComponent) => {
	// only what the person actually set: a blank field is not "" for that parameter, it is
	// silence, and the component's own default then applies
	const out: Record<string, unknown> = {};
	for (const param of component.params) {
		if (param.type === "bool") {
			if (param.name in flags.value) out[param.name] = flags.value[param.name];
			continue;
		}
		const value = (typed.value[param.name] ?? "").trim();
		if (!value) continue;
		if (param.type === "int") {
			const number = Number(value);
			if (Number.isFinite(number)) out[param.name] = number;
			continue;
		}
		out[param.name] = value;
	}
	return out;
};

const insert = async (component: SiteComponent) => {
	inserting.value = true;
	try {
		// the tag is built on the server, from the catalogue: a value for a parameter the
		// component does not declare is dropped there, exactly as it is for a generated page
		const tag = await tagFor.submit({ path: component.path, values: JSON.stringify(chosen(component)) });
		const root = canvasStore.getRootBlock();
		if (!root) {
			toast.error(__("Open a page first."));
			return;
		}
		root.addChild(getBlockInstance({ element: "div", innerHTML: tag, baseStyles: {} }));
		toast.success(__("{0} added to the page.").replace("{0}", component.label));
		open.value = null;
	} catch (e) {
		toast.error((e as Error)?.message || __("The block could not be added."));
	} finally {
		inserting.value = false;
	}
};
</script>
