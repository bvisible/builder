<template>
	<div v-if="!loaded" class="text-base text-ink-gray-5">Loading...</div>
	<div v-else class="flex flex-col gap-4">
		<!-- Theme -->
		<div class="flex flex-col gap-3">
			<button
				class="flex w-fit items-center gap-1 text-sm font-medium text-ink-gray-8"
				@click="open.theme = !open.theme">
				<span
					class="inline-block size-4"
					:class="open.theme ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				Colors & typography
			</button>
			<template v-if="open.theme">
				<div class="grid grid-cols-2 gap-3">
					<div v-for="color in themeColors" :key="color.field" class="flex items-end gap-2">
						<FormControl
							size="sm"
							:label="color.label"
							:modelValue="state[color.field]"
							@update:modelValue="(v: string) => (state[color.field] = v)"
							placeholder="#000000"
							class="flex-1" />
						<input
							type="color"
							class="h-7 w-9 shrink-0 cursor-pointer rounded border border-outline-gray-2 bg-transparent"
							:value="state[color.field] || '#000000'"
							@input="(e: Event) => (state[color.field] = (e.target as HTMLInputElement).value)" />
					</div>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						type="select"
						size="sm"
						label="Heading font"
						:options="options.heading_font"
						:modelValue="state.heading_font"
						@update:modelValue="(v: string) => (state.heading_font = v)" />
					<FormControl
						type="select"
						size="sm"
						label="Body font"
						:options="options.body_font"
						:modelValue="state.body_font"
						@update:modelValue="(v: string) => (state.body_font = v)" />
				</div>
			</template>
		</div>

		<!-- Header -->
		<div class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4">
			<button
				class="flex w-fit items-center gap-1 text-sm font-medium text-ink-gray-8"
				@click="open.header = !open.header">
				<span
					class="inline-block size-4"
					:class="open.header ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				Header
			</button>
			<template v-if="open.header">
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						type="select"
						size="sm"
						label="Layout"
						:options="options.header_layout"
						:modelValue="state.header_layout"
						@update:modelValue="(v: string) => (state.header_layout = v)" />
					<FormControl
						type="select"
						size="sm"
						label="Height"
						:options="options.header_height"
						:modelValue="state.header_height"
						@update:modelValue="(v: string) => (state.header_height = v)" />
					<FormControl
						type="select"
						size="sm"
						label="Logo type"
						:options="options.logo_type"
						:modelValue="state.logo_type"
						@update:modelValue="(v: string) => (state.logo_type = v)" />
					<FormControl
						v-if="state.logo_type === 'Text'"
						size="sm"
						label="Logo text"
						:modelValue="state.logo_text"
						@update:modelValue="(v: string) => (state.logo_text = v)" />
					<FormControl
						v-else
						size="sm"
						label="Logo image URL"
						:modelValue="state.logo_image"
						@update:modelValue="(v: string) => (state.logo_image = v)"
						placeholder="/files/logo.png" />
					<FormControl
						type="select"
						size="sm"
						label="Search"
						:options="options.search_type"
						:modelValue="state.search_type"
						@update:modelValue="(v: string) => (state.search_type = v)" />
				</div>
				<div class="flex items-center gap-5">
					<Switch
						size="sm"
						label="Sticky header"
						:modelValue="!!state.sticky_header"
						@update:modelValue="(v: boolean) => (state.sticky_header = v ? 1 : 0)" />
					<Switch
						size="sm"
						label="CTA button"
						:modelValue="!!state.show_cta"
						@update:modelValue="(v: boolean) => (state.show_cta = v ? 1 : 0)" />
				</div>
				<div v-if="state.show_cta" class="grid grid-cols-3 gap-3">
					<FormControl
						size="sm"
						label="CTA text"
						:modelValue="state.cta_text"
						@update:modelValue="(v: string) => (state.cta_text = v)" />
					<FormControl
						size="sm"
						label="CTA URL"
						:modelValue="state.cta_url"
						@update:modelValue="(v: string) => (state.cta_url = v)" />
					<FormControl
						type="select"
						size="sm"
						label="CTA style"
						:options="options.cta_style"
						:modelValue="state.cta_style"
						@update:modelValue="(v: string) => (state.cta_style = v)" />
				</div>
			</template>
		</div>

		<!-- Menu -->
		<div class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4">
			<button
				class="flex w-fit items-center gap-1 text-sm font-medium text-ink-gray-8"
				@click="open.menu = !open.menu">
				<span
					class="inline-block size-4"
					:class="open.menu ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				Menu
			</button>
			<template v-if="open.menu">
				<div
					v-for="(item, index) in state.menu_items"
					:key="index"
					class="flex items-center gap-2">
					<FormControl
						size="sm"
						placeholder="Label"
						:modelValue="item.label"
						@update:modelValue="(v: string) => (item.label = v)"
						class="flex-1" />
					<FormControl
						size="sm"
						placeholder="/route"
						:modelValue="item.url"
						@update:modelValue="(v: string) => (item.url = v)"
						class="flex-1" />
					<Button
						variant="ghost"
						icon="lucide-trash-2"
						@click="state.menu_items.splice(index, 1)" />
				</div>
				<Button
					variant="subtle"
					class="w-fit"
					icon-left="lucide-plus"
					@click="state.menu_items.push({ label: '', url: '', open_in_new_tab: 0 })">
					Add menu item
				</Button>
			</template>
		</div>

		<!-- Footer -->
		<div class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4">
			<button
				class="flex w-fit items-center gap-1 text-sm font-medium text-ink-gray-8"
				@click="open.footer = !open.footer">
				<span
					class="inline-block size-4"
					:class="open.footer ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				Footer
			</button>
			<template v-if="open.footer">
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						type="select"
						size="sm"
						label="Template"
						:options="options.footer_template"
						:modelValue="state.footer_template"
						@update:modelValue="(v: string) => (state.footer_template = v)" />
					<FormControl
						size="sm"
						label="Copyright"
						:modelValue="state.copyright_text"
						@update:modelValue="(v: string) => (state.copyright_text = v)" />
				</div>
				<FormControl
					type="textarea"
					size="sm"
					label="Description"
					:modelValue="state.footer_description"
					@update:modelValue="(v: string) => (state.footer_description = v)" />
				<Switch
					size="sm"
					label="Social links"
					:modelValue="!!state.show_social_links"
					@update:modelValue="(v: boolean) => (state.show_social_links = v ? 1 : 0)" />
				<div v-if="state.show_social_links" class="grid grid-cols-2 gap-3">
					<FormControl
						v-for="social in socials"
						:key="social.field"
						size="sm"
						:label="social.label"
						:modelValue="state[social.field]"
						@update:modelValue="(v: string) => (state[social.field] = v)"
						placeholder="https://" />
				</div>
			</template>
		</div>

		<p class="text-xs text-ink-gray-5">
			{{ saving ? "Saving..." : "Changes save automatically and apply to the whole site." }}
		</p>
	</div>
</template>
<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import { createResource, FormControl, Switch, toast } from "frappe-ui";
import { computed, reactive, ref } from "vue";

const API = "builder.hf_utils.chrome_api";

const themeColors = [
	{ field: "primary_color", label: "Primary" },
	{ field: "secondary_color", label: "Secondary" },
	{ field: "background_color", label: "Background" },
	{ field: "text_color", label: "Text" },
];

const socials = [
	{ field: "facebook_url", label: "Facebook" },
	{ field: "instagram_url", label: "Instagram" },
	{ field: "linkedin_url", label: "LinkedIn" },
	{ field: "youtube_url", label: "YouTube" },
];

const loaded = ref(false);
const saving = ref(false);
const open = reactive({ theme: true, header: false, menu: false, footer: false });
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const state = reactive<Record<string, any>>({ menu_items: [] });
let snapshot = "";

const payload = () => {
	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	const { _options, _profile, ...rest } = state;
	return JSON.parse(JSON.stringify(rest));
};

createResource({
	url: `${API}.get_chrome_settings`,
	auto: true,
	onSuccess(data: Record<string, unknown>) {
		Object.assign(state, data);
		state.menu_items = data.menu_items || [];
		snapshot = JSON.stringify(payload());
		loaded.value = true;
	},
});

const options = computed<Record<string, string[]>>(() => state._options || {});

watchDebounced(
	state,
	async () => {
		if (!loaded.value) return;
		const current = payload();
		const serialized = JSON.stringify(current);
		if (serialized === snapshot) return;
		saving.value = true;
		try {
			// echo the resolved Website Profile back so the write lands on the
			// same doc the read came from (variant vs global single)
			await createResource({ url: `${API}.update_chrome_settings` }).submit({
				settings: current,
				profile: state._profile || undefined,
			});
			snapshot = serialized;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : String(error));
		} finally {
			saving.value = false;
		}
	},
	{ debounce: 700, deep: true },
);
</script>
