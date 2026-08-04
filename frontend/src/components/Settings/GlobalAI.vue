<template>
	<div class="flex flex-col gap-5">
		<!-- Managed install: the host runs the models for its customers, so there
		     is nothing to choose. No endpoint, no model name — which
		     infrastructure a host runs is its business, not a line to publish in
		     a customer's settings screen. -->
		<div v-if="managed" class="flex flex-col gap-2 rounded-lg bg-surface-gray-1 p-4">
			<span class="text-base font-medium text-ink-gray-9">
				{{ __("AI comes with your hosting") }}
			</span>
			<p class="text-sm text-ink-gray-6">
				{{ __("Your provider runs the models for you — there is nothing to configure here.") }}
			</p>
		</div>

		<template v-else>
		<FormControl
			type="select"
			:label="__('Provider')"
			:options="providerOptions"
			:modelValue="preset"
			@update:modelValue="setPreset" />

		<div v-if="usesApiKey" class="flex flex-col gap-2">
			<label class="text-sm text-ink-gray-9">{{ __("API Key") }}</label>
			<div class="flex items-center gap-2">
				<FormControl
					type="password"
					:modelValue="apiKey"
					@update:modelValue="updateApiKey"
					:placeholder="preset === 'ollama' ? __('optional') : __('sk-…')"
					class="flex-1" />
				<Button variant="subtle" @click="testConnection" :disabled="testing">
					{{ testing ? __("Testing...") : __("Test connection") }}
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

		<p v-if="!usesApiKey" class="text-xs text-ink-gray-6">{{ keyHint }}</p>

		<!-- site_config wins over anything chosen here; saying nothing about it
		     would make this tab show a provider that is not the one in use -->
		<div
			v-if="pinnedFields.length"
			class="rounded-lg bg-surface-amber-1 p-3 text-sm text-ink-amber-9">
			{{
				__("This server pins {0} in site_config.json — what you choose here is ignored for those.").format(
					pinnedFields.join(", "),
				)
			}}
		</div>

		<div v-if="statusMessage" class="rounded-lg p-3 text-sm" :class="statusClass">
			{{ statusMessage }}
		</div>

		<!-- only when the ChatGPT subscription is the chosen provider: pairing a
		     personal plan has nothing to do with a Moonshot or OpenRouter key -->
		<CodexPairing v-if="preset === 'codex'" />

		<Switch
			:label="__('Generate images with AI')"
			:description="__('Replace placeholders with generated images after a site is built')"
			:modelValue="!!imagesEnabled"
			@update:modelValue="setImagesEnabled" />
		<FormControl
			v-if="imagesEnabled"
			type="select"
			size="sm"
			:label="__('Image backend')"
			:options="imageBackendOptions"
			:modelValue="imageProvider"
			@update:modelValue="setImageProvider" />

		<!-- A subscription still lets you name the model and how hard it thinks:
		     both change the result and the wait, so both belong here rather
		     than in site_config where only an operator can reach them. -->
		<div class="flex flex-col gap-3">
			<button
				class="flex w-fit items-center gap-1 text-sm text-ink-gray-7 hover:text-ink-gray-9"
				@click="advancedOpen = !advancedOpen">
				<span
					class="inline-block size-4"
					:class="advancedOpen ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				{{ __("Advanced") }}
			</button>
			<template v-if="advancedOpen">
				<FormControl
					type="text"
					size="sm"
					:label="__('Brief model')"
					:description="modelHint"
					:modelValue="briefModel"
					@update:modelValue="(v: string) => (briefModel = v)"
					:placeholder="defaultBriefModel" />
				<FormControl
					type="text"
					size="sm"
					:label="__('Page model')"
					:description="modelHint"
					:modelValue="pageModel"
					@update:modelValue="(v: string) => (pageModel = v)"
					:placeholder="defaultPageModel" />
				<FormControl
					type="select"
					size="sm"
					:label="__('Reasoning effort')"
					:description="__('How long the model thinks before answering. More is slower and usually better.')"
					:options="reasoningOptions"
					:modelValue="reasoningEffort"
					@update:modelValue="(v: string) => (reasoningEffort = v)" />
				<FormControl
					v-if="imagesEnabled && imageProvider === 'codex'"
					type="text"
					size="sm"
					:label="__('Image model')"
					:description="__('Drawing and writing are different jobs; a plan may expose a different model for each. Empty = the same as above.')"
					:modelValue="imageModel"
					@update:modelValue="(v: string) => (imageModel = v)" />
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
		</template>
	</div>
</template>
<script setup lang="ts">
import CodexPairing from "@/components/Settings/CodexPairing.vue";
import { builderSettings } from "@/data/builderSettings";
import useBuilderStore from "@/stores/builderStore";
import { watchDebounced } from "@vueuse/core";
import { createResource, FormControl, Switch } from "frappe-ui";
import { computed, onMounted, ref } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const builderStore = useBuilderStore();

// Presets are UI sugar over two stored fields (unpress_ai_provider +
// unpress_ai_base_url); empty stored values mean "engine defaults" (Moonshot).
const PRESETS: Record<string, { provider: string; base_url: string }> = {
	moonshot: { provider: "", base_url: "" },
	// drives a ChatGPT subscription through the Codex CLI — no API key, no
	// endpoint, so it clears both rather than pointing anywhere
	codex: { provider: "codex", base_url: "" },
	openai: { provider: "", base_url: "https://api.openai.com/v1" },
	openrouter: { provider: "", base_url: "https://openrouter.ai/api/v1" },
	ollama: { provider: "ollama", base_url: "http://localhost:11434" },
};

// Labels are translatable and live here; WHICH of them to offer comes from the
// server (describe_resolution). That is what lets one component serve every
// edition: Codex only appears where the CLI is usable, and a fork adds a
// provider once, server-side, instead of patching this file.
const PROVIDER_LABELS: Record<string, string> = {
	moonshot: __("Moonshot AI (recommended)"),
	codex: __("OpenAI — ChatGPT subscription"),
	openai: __("OpenAI — API key"),
	openrouter: __("OpenRouter"),
	ollama: __("Ollama (local)"),
	custom: __("Custom (OpenAI-compatible)"),
};

const allowedProviders = ref<string[]>(Object.keys(PROVIDER_LABELS));
const providerOptions = computed(() =>
	allowedProviders.value
		.filter((v) => PROVIDER_LABELS[v])
		.map((v) => ({ label: PROVIDER_LABELS[v], value: v })),
);

// a subscription is not a key: the whole API-key block is meaningless here
const usesApiKey = computed(() => preset.value !== "codex");

// What "empty" resolves to depends on the provider: suggesting kimi while
// OpenRouter is selected is just wrong information.
const MODEL_DEFAULTS: Record<string, [string, string]> = {
	moonshot: ["kimi-k3", "kimi-k2.7-code"],
	openai: ["gpt-5.5", "gpt-5.5"],
	openrouter: ["moonshotai/kimi-k3", "moonshotai/kimi-k2.7-code"],
	ollama: ["", ""],
	custom: ["", ""],
};
const defaultBriefModel = computed(() => MODEL_DEFAULTS[preset.value]?.[0] || "");
const defaultPageModel = computed(() => MODEL_DEFAULTS[preset.value]?.[1] || "");
const modelHint = computed(() =>
	defaultBriefModel.value
		? __("Leave empty to use this provider's default.")
		: __("Required for this provider — no default is assumed."),
);

const KEY_HINTS: Record<string, { hint: string; link?: string; linkLabel?: string }> = {
	moonshot: {
		hint: __("Powers the built-in site generation (kimi models). Get an API key from"),
		link: "https://platform.moonshot.ai/console/api-keys",
		linkLabel: "platform.moonshot.ai",
	},
	openai: {
		hint: __("Get an API key from"),
		link: "https://platform.openai.com/api-keys",
		linkLabel: "platform.openai.com",
	},
	openrouter: {
		hint: __("Claude, Gemini, GPT and more under one key. Get it from"),
		link: "https://openrouter.ai/keys",
		linkLabel: "openrouter.ai/keys",
	},
	codex: { hint: __("Uses your ChatGPT Plus/Pro plan through the Codex CLI — no API key, no metered billing.") },
	ollama: { hint: __("A local Ollama server needs no API key; cloud endpoints may require one.") },
	custom: { hint: __("Any OpenAI-compatible endpoint (must serve /chat/completions).") },
};

const testing = ref(false);
const statusMessage = ref("");
const statusClass = ref("");

// what the server says this install allows
const managed = ref(false);
// the NAMES of the fields site_config decides — never their values, which can
// name private infrastructure
const pinnedFields = ref<string[]>([]);

const loadResolution = () => {
	createResource({ url: "builder.ai.config.describe_resolution" })
		.submit()
		.then((r: any) => {
			managed.value = !!r?.managed;
			pinnedFields.value = Array.isArray(r?.pinned) ? r.pinned : Object.keys(r?.pinned || {});
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const list = (r?.providers || []).map((p: any) => p.value).filter(Boolean);
			if (list.length) allowedProviders.value = list;
		})
		.catch(() => {
			managed.value = false;
			pinnedFields.value = [];
		});
};

const preset = ref("moonshot");
const apiKey = ref("");
const baseUrl = ref("");
const briefModel = ref("");
const pageModel = ref("");
const language = ref("");
const reasoningEffort = ref("");
const imageModel = ref("");

// Codex's own vocabulary. Empty leaves the choice to the provider, which is
// the right default: a plan may not expose every level.
const reasoningOptions = [
	{ label: __("Provider default"), value: "" },
	{ label: __("Minimal"), value: "minimal" },
	{ label: __("Low"), value: "low" },
	{ label: __("Medium"), value: "medium" },
	{ label: __("High"), value: "high" },
];

const keyHint = computed(() => KEY_HINTS[preset.value]?.hint || "");
const keyLink = computed(() => KEY_HINTS[preset.value]?.link || "");
const keyLinkLabel = computed(() => KEY_HINTS[preset.value]?.linkLabel || "");

const save = (values: Record<string, string>) => {
	(builderSettings.setValue as any).submit(values).then(() => builderSettings.reload());
};

const derivePreset = (provider: string, base_url: string): string => {
	if (provider === "codex") return "codex";
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
	if (value === "codex") {
		// The plan that writes the pages also draws the images, at no extra
		// cost. Leaving the user to find two more switches for something they
		// already paid for is just friction.
		imagesEnabled.value = 1;
		imageProvider.value = "codex";
		save({ unpress_ai_image_provider: "codex" });
		builderSettings.setValue.submit({ unpress_ai_image_enabled: 1 } as never);
	}
};

const updateApiKey = (value: string) => {
	apiKey.value = value;
};

// Debounced: the upstream pattern saved on every keystroke, which fired a
// frappe.client.set_value per character typed.
watchDebounced(
	apiKey,
	(value) => {
		if (value !== (builderSettings.doc as any)?.ai_api_key) {
			builderStore.updateBuilderSettings("ai_api_key", value);
		}
	},
	{ debounce: 600 },
);

const testConnection = async () => {
	testing.value = true;
	statusMessage.value = "";
	try {
		const result = (await createResource({
			url: "builder.api.test_ai_connection",
		}).submit()) as { success: boolean; message?: string };
		statusMessage.value = result.message || (result.success ? __("Connected!") : __("Connection failed"));
		statusClass.value = result.success
			? "text-ink-green-6 bg-surface-green-1"
			: "text-ink-red-6 bg-surface-red-1";
	} catch (error: unknown) {
		statusMessage.value = error instanceof Error ? error.message : __("Failed to test connection");
		statusClass.value = "text-ink-red-6 bg-surface-red-1";
	} finally {
		testing.value = false;
		setTimeout(() => {
			statusMessage.value = "";
		}, 8000);
	}
};

// Text inputs auto-save debounced, like the rest of the Settings dialog.
// Skip when the value already matches the doc (hydration on mount, preset
// writes) so opening the tab never fires spurious saves.
const saveIfChanged = (field: string, v: string) => {
	const current = (((builderSettings.doc as any) || {})[field] || "") as string;
	if (v !== current) save({ [field]: v });
};
watchDebounced(baseUrl, (v) => saveIfChanged("unpress_ai_base_url", v), { debounce: 500 });
watchDebounced(briefModel, (v) => saveIfChanged("unpress_ai_brief_model", v), { debounce: 500 });
watchDebounced(pageModel, (v) => saveIfChanged("unpress_ai_page_model", v), { debounce: 500 });
watchDebounced(language, (v) => saveIfChanged("unpress_ai_output_language", v), { debounce: 500 });
watchDebounced(reasoningEffort, (v) => saveIfChanged("unpress_ai_reasoning_effort", v), { debounce: 500 });
watchDebounced(imageModel, (v) => saveIfChanged("unpress_ai_image_model", v), { debounce: 500 });

const advancedOpen = ref(false);

// images: on/off plus which backend fills the placeholders
const imagesEnabled = ref(0);
const imageProvider = ref("");
const imageBackendOptions = computed(() => [
	{ label: __("API endpoint (OpenAI-compatible)"), value: "API" },
	{ label: __("Codex CLI (ChatGPT plan)"), value: "codex" },
]);

const setImagesEnabled = (value: boolean) => {
	imagesEnabled.value = value ? 1 : 0;
	save({ unpress_ai_image_enabled: imagesEnabled.value } as never);
};

const setImageProvider = (value: string) => {
	imageProvider.value = value;
	save({ unpress_ai_image_provider: value });
};

onMounted(() => {
	loadResolution();
	const doc = builderSettings.doc as any;
	if (!doc) return;
	imagesEnabled.value = doc.unpress_ai_image_enabled || 0;
	imageProvider.value = doc.unpress_ai_image_provider || "API";
	apiKey.value = doc.ai_api_key || "";
	baseUrl.value = doc.unpress_ai_base_url || "";
	briefModel.value = doc.unpress_ai_brief_model || "";
	pageModel.value = doc.unpress_ai_page_model || "";
	language.value = doc.unpress_ai_output_language || "";
	reasoningEffort.value = doc.unpress_ai_reasoning_effort || "";
	imageModel.value = doc.unpress_ai_image_model || "";
	preset.value = derivePreset(doc.unpress_ai_provider || "", doc.unpress_ai_base_url || "");
	advancedOpen.value = !!(
		briefModel.value ||
		pageModel.value ||
		language.value ||
		reasoningEffort.value ||
		imageModel.value
	);
});
</script>
