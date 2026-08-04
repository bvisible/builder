<template>
	<div v-if="!loaded" class="text-base text-ink-gray-5">{{ __("Loading...") }}</div>
	<div v-else class="flex flex-col gap-4">
		<p class="text-sm text-ink-gray-6">
			{{
				__(
					"The accounts this business has. Set them once here; the footer and anywhere else that shows them only decides whether to display them.",
				)
			}}
		</p>

		<div class="grid grid-cols-2 gap-3">
			<FormControl
				v-for="network in networks"
				:key="network.field"
				size="sm"
				:label="network.label"
				:placeholder="network.placeholder"
				:modelValue="state[network.field]"
				@update:modelValue="(v: string) => (state[network.field] = v)" />
		</div>

		<div class="flex items-center gap-2 text-xs">
			<span v-if="saving" class="flex items-center gap-1.5 text-ink-gray-5">
				<span
					class="size-3 animate-spin rounded-full border-2 border-outline-gray-2 border-t-ink-gray-6" />
				{{ __("Saving...") }}
			</span>
			<span v-else-if="justSaved" class="flex items-center gap-1.5 text-ink-green-3">
				<span class="lucide-check size-3.5" aria-hidden="true" />
				{{ __("Saved") }}
			</span>
			<span v-else class="text-ink-gray-5">
				{{ __("Changes save automatically.") }}
			</span>
		</div>
	</div>
</template>
<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import { createResource, FormControl, toast } from "frappe-ui";
import { reactive, ref, watch } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const API = "builder.hf_utils.chrome_api";

const networks = [
	{ field: "facebook_url", label: __("Facebook"), placeholder: "https://facebook.com/…" },
	{ field: "instagram_url", label: __("Instagram"), placeholder: "https://instagram.com/…" },
	{ field: "linkedin_url", label: __("LinkedIn"), placeholder: "https://linkedin.com/company/…" },
	{ field: "twitter_url", label: __("Twitter"), placeholder: "https://x.com/…" },
	{ field: "youtube_url", label: __("YouTube"), placeholder: "https://youtube.com/@…" },
];

const FIELDS = networks.map((n) => n.field);

const loaded = ref(false);
const saving = ref(false);
const savedAt = ref(0);
const justSaved = ref(false);
watch(savedAt, (at) => {
	if (!at) return;
	justSaved.value = true;
	setTimeout(() => (justSaved.value = false), 2200);
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const state = reactive<Record<string, any>>({});
let snapshot = "";

const payload = () => Object.fromEntries(FIELDS.map((f) => [f, state[f] ?? ""]));

createResource({
	url: `${API}.get_chrome_settings`,
	auto: true,
	onSuccess(data: Record<string, unknown>) {
		FIELDS.forEach((f) => (state[f] = data[f] ?? ""));
		snapshot = JSON.stringify(payload());
		loaded.value = true;
	},
});

watchDebounced(
	state,
	async () => {
		if (!loaded.value) return;
		const current = payload();
		const serialized = JSON.stringify(current);
		if (serialized === snapshot) return;
		saving.value = true;
		try {
			await createResource({ url: `${API}.update_chrome_settings` }).submit({ settings: current });
			snapshot = serialized;
			savedAt.value = Date.now();
		} catch (error) {
			toast.error(error instanceof Error ? error.message : String(error));
		} finally {
			saving.value = false;
		}
	},
	{ debounce: 700, deep: true },
);
</script>
