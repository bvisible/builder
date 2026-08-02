<template>
	<div class="flex flex-col gap-5">
		<FormControl
			type="select"
			:label="__('Provider')"
			:options="providerOptions"
			:modelValue="preset"
			@update:modelValue="setPreset" />

		<div class="flex flex-col gap-2">
			<label class="text-sm text-ink-gray-9">{{ __("API Key") }}</label>
			<div class="flex items-center gap-2">
				<FormControl
					type="password"
					:modelValue="apiKey"
					@update:modelValue="updateApiKey"
					:placeholder="preset === 'ollama' ? __('optional') : __('sk-…')"
					class="flex-1" />
				<Button variant="subtle" @click="testApiKey" :disabled="testing || !apiKey">
					{{ testing ? __("Testing...") : __("Test key") }}
				</Button>
			</div>
			<p class="text-xs text-ink-gray-6">
				{{ keyHint }}
				<a
					v-if="keyLink"
					:href="keyLink"
					target="_blank"
					rel="noopener noreferrer"
					class="text-ink-blue-8 underline">
					{{ keyLinkLabel }}
				</a>
			</p>
		</div>

		<FormControl
			v-if="preset === 'custom' || preset === 'ollama'"
			type="text"
			:label="__('API Base URL')"
			:modelValue="baseUrl"
			@update:modelValue="(v: string) => (baseUrl = v)"
			:placeholder="preset === 'ollama' ? 'http://localhost:11434' : 'https://api.example.com/v1'" />

		<!-- Neoffice instances are fleet-managed, so most of them ARE pinned.
		     Saying nothing would leave this tab showing a provider the engine
		     is not using — which is exactly what it did before. -->
		<div
			v-if="pinnedFields.length"
			class="rounded-lg bg-surface-amber-1 p-3 text-sm text-ink-amber-9">
			{{
				__("This server pins {0} in site_config.json — what you choose here is ignored for those.").format(
					pinnedFields.join(", "),
				)
			}}
			<span class="mt-1 block text-xs">
				{{ __("In effect: {0}").format(effectiveSummary) }}
			</span>
		</div>

		<div v-if="statusMessage" class="rounded-lg p-3 text-sm" :class="statusClass">
			{{ statusMessage }}
		</div>

		<div class="flex flex-col gap-3">
			<button
				class="flex w-fit items-center gap-1 text-sm text-ink-gray-7 hover:text-ink-gray-9"
				@click="advancedOpen = !advancedOpen">
				<span :class="advancedOpen ? 'lucide-chevron-down' : 'lucide-chevron-right'" class="size-4" />
				{{ __("Advanced") }}
			</button>
			<template v-if="advancedOpen">
				<FormControl
					type="text"
					size="sm"
					:label="__('Brief model')"
					:description="__('Creative brief + design system. Empty = the code default')"
					:modelValue="briefModel"
					@update:modelValue="(v: string) => (briefModel = v)"
					placeholder="kimi-k3" />
				<FormControl
					type="text"
					size="sm"
					:label="__('Page model')"
					:description="__('Page generation (code). Empty = the code default')"
					:modelValue="pageModel"
					@update:modelValue="(v: string) => (pageModel = v)"
					placeholder="kimi-k2.7-code" />
				<FormControl
					type="text"
					size="sm"
					:label="__('Content language')"
					:description="__('Language of the generated content. Empty = French')"
					:modelValue="language"
					@update:modelValue="(v: string) => (language = v)"
					:placeholder="__('French')" />
			</template>
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { watchDebounced } from "@vueuse/core";
import { createResource, FormControl } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
// The cast keeps the `{0}` placeholder contract (`__("..").format(x)`) visible to TS.
const __ = window.__ as (message: string) => string & { format: (...args: unknown[]) => string };

const builderStore = useBuilderStore();

// Presets are UI sugar over two stored fields (unpress_ai_provider +
// unpress_ai_base_url). No Codex here on purpose: driving a personal ChatGPT
// plan is a self-host feature, it has no place on a fleet-managed instance.
const PRESETS: Record<string, { provider: string; base_url: string }> = {
	moonshot: { provider: "", base_url: "" },
	openai: { provider: "", base_url: "https://api.openai.com/v1" },
	openrouter: { provider: "", base_url: "https://openrouter.ai/api/v1" },
	ollama: { provider: "ollama", base_url: "http://localhost:11434" },
};

const providerOptions = [
	{ label: __("Moonshot AI (recommended)"), value: "moonshot" },
	{ label: __("OpenRouter"), value: "openrouter" },
	{ label: __("OpenAI — API key"), value: "openai" },
	{ label: __("Ollama (local)"), value: "ollama" },
	{ label: __("Custom (OpenAI-compatible)"), value: "custom" },
];

const KEY_HINTS: Record<string, { hint: string; link?: string; linkLabel?: string }> = {
	moonshot: {
		hint: __("Powers the built-in site generation (kimi models). Get an API key from"),
		link: "https://platform.moonshot.ai/console/api-keys",
		linkLabel: "platform.moonshot.ai",
	},
	openrouter: {
		hint: __("Claude, Gemini, GPT and more under one key. Get it from"),
		link: "https://openrouter.ai/keys",
		linkLabel: "openrouter.ai/keys",
	},
	openai: {
		hint: __("Get an API key from"),
		link: "https://platform.openai.com/api-keys",
		linkLabel: "platform.openai.com",
	},
	ollama: { hint: __("A local Ollama server needs no API key; cloud endpoints may require one.") },
	custom: { hint: __("Any OpenAI-compatible endpoint (must serve /chat/completions).") },
};

const testing = ref(false);
const statusMessage = ref("");
const statusClass = ref("");
const advancedOpen = ref(false);

// what site_config pins, so the tab can admit when it is not in charge
const pinnedFields = ref<string[]>([]);
const effectiveSummary = ref("");

const preset = ref("moonshot");
const apiKey = ref("");
const baseUrl = ref("");
const briefModel = ref("");
const pageModel = ref("");
const language = ref("");

const keyHint = computed(() => KEY_HINTS[preset.value]?.hint || "");
const keyLink = computed(() => KEY_HINTS[preset.value]?.link || "");
const keyLinkLabel = computed(() => KEY_HINTS[preset.value]?.linkLabel || "");

const loadResolution = () => {
	createResource({ url: "builder.ai.config.describe_resolution" })
		.submit()
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		.then((r: any) => {
			pinnedFields.value = Object.keys(r?.pinned || {});
			const e = r?.effective || {};
			effectiveSummary.value = [e.provider, e.base_url, e.model].filter(Boolean).join(" · ");
		})
		.catch(() => {
			pinnedFields.value = [];
		});
};

const save = (values: Record<string, string>) => {
	Object.entries(values).forEach(([field, value]) => {
		builderStore.updateBuilderSettings(field, value);
	});
};

const derivePreset = (provider: string, base_url: string): string => {
	if (provider === "ollama") return "ollama";
	if (!base_url) return "moonshot";
	if (base_url.includes("openai.com")) return "openai";
	if (base_url.includes("openrouter.ai")) return "openrouter";
	return "custom";
};

const setPreset = (value: string) => {
	preset.value = value;
	const p = PRESETS[value];
	if (p) {
		baseUrl.value = p.base_url;
		save({ unpress_ai_provider: p.provider, unpress_ai_base_url: p.base_url });
	} else {
		// custom: keep whatever URL is typed, just clear the ollama flag
		save({ unpress_ai_provider: "" });
	}
};

const updateApiKey = (value: string) => {
	apiKey.value = value;
	builderStore.updateBuilderSettings("ai_api_key", value);
};

watchDebounced(
	[baseUrl, briefModel, pageModel, language],
	() => {
		save({
			unpress_ai_base_url: baseUrl.value,
			unpress_ai_brief_model: briefModel.value,
			unpress_ai_page_model: pageModel.value,
			unpress_ai_output_language: language.value,
		});
	},
	{ debounce: 600 },
);

const testApiKey = async () => {
	if (!apiKey.value) return;
	testing.value = true;
	statusMessage.value = "";
	try {
		const result = (await createResource({
			url: "builder.ai_page_generator.test_api_key",
		}).submit()) as { success: boolean; message?: string };

		if (result.success) {
			statusMessage.value = __("API key is valid");
			statusClass.value = "text-ink-green-6 bg-surface-green-1";
		} else {
			statusMessage.value = result.message || __("API key test failed");
			statusClass.value = "text-ink-red-6 bg-surface-red-1";
		}
	} catch (error: unknown) {
		statusMessage.value = error instanceof Error ? error.message : __("Failed to test the API key");
		statusClass.value = "text-ink-red-6 bg-surface-red-1";
	} finally {
		testing.value = false;
		setTimeout(() => {
			statusMessage.value = "";
		}, 5000);
	}
};

onMounted(() => {
	loadResolution();
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const doc = builderSettings.doc as any;
	if (!doc) return;
	apiKey.value = doc.ai_api_key || "";
	baseUrl.value = doc.unpress_ai_base_url || "";
	briefModel.value = doc.unpress_ai_brief_model || "";
	pageModel.value = doc.unpress_ai_page_model || "";
	language.value = doc.unpress_ai_output_language || "";
	preset.value = derivePreset(doc.unpress_ai_provider || "", doc.unpress_ai_base_url || "");
	advancedOpen.value = !!(briefModel.value || pageModel.value || language.value);
});
</script>
