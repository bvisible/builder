<template>
	<div v-if="!loaded" class="text-base text-ink-gray-5">{{ __("Loading...") }}</div>
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
				{{ __("Colors & typography") }}
			</button>
			<template v-if="open.theme">
				<!-- The design system. Set here once; the header, the footer and
				     every generated block read it, so pages stay coherent
				     without anyone repeating a radius or a shadow. -->
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						type="select"
						size="sm"
						:label="__('Corners')"
						:options="options.radius_style"
						:modelValue="state.radius_style"
						@update:modelValue="(v: string) => (state.radius_style = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('Elevation')"
						:options="options.shadow_style"
						:modelValue="state.shadow_style"
						@update:modelValue="(v: string) => (state.shadow_style = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('Button hover')"
						:options="options.button_hover"
						:modelValue="state.button_hover"
						@update:modelValue="(v: string) => (state.button_hover = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('Motion')"
						:options="options.motion_style"
						:modelValue="state.motion_style"
						@update:modelValue="(v: string) => (state.motion_style = v)" />
				</div>
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
						:label="__('Heading font')"
						:options="options.heading_font"
						:modelValue="state.heading_font"
						@update:modelValue="(v: string) => (state.heading_font = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('Body font')"
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
				{{ __("Header") }}
			</button>
			<template v-if="open.header">
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						type="select"
						size="sm"
						:label="__('Layout')"
						:options="options.header_layout"
						:modelValue="state.header_layout"
						@update:modelValue="(v: string) => (state.header_layout = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('Height')"
						:options="options.header_height"
						:modelValue="state.header_height"
						@update:modelValue="(v: string) => (state.header_height = v)" />
					<!-- How the bar sits on the page — a complete prefab look, not
					     a switch to combine with three others. -->
					<FormControl
						type="select"
						size="sm"
						:label="__('Header style')"
						:options="options.header_style"
						:modelValue="state.header_style"
						@update:modelValue="(v: string) => (state.header_style = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('Logo type')"
						:options="options.logo_type"
						:modelValue="state.logo_type"
						@update:modelValue="(v: string) => (state.logo_type = v)" />
					<FormControl
						v-if="state.logo_type === 'Text'"
						size="sm"
						:label="__('Logo text')"
						:modelValue="state.logo_text"
						@update:modelValue="(v: string) => (state.logo_text = v)" />
					<!-- The logo is the one thing every client brings. It gets an
					     uploader and a preview, not a path to type. The address is
					     deliberately fixed: a hosted fleet points at it everywhere, so
					     a new logo replaces the file rather than minting a new URL. -->
					<div v-else class="col-span-2 flex flex-col gap-2">
						<span class="text-xs text-ink-gray-5">{{ __("Logo") }}</span>
						<div class="flex items-center gap-3">
							<div
								class="flex size-16 shrink-0 items-center justify-center rounded-lg border border-outline-gray-2 bg-surface-white p-1">
								<img v-if="logoPreview" :src="logoPreview" class="max-h-full max-w-full object-contain" alt="" />
								<span v-else class="lucide-image size-5 text-ink-gray-4" aria-hidden="true" />
							</div>
							<div class="flex flex-col items-start gap-1">
								<input
									ref="logoInput"
									type="file"
									accept="image/*"
									class="hidden"
									@change="onLogoPicked" />
								<Button
									size="sm"
									:loading="logoBusy"
									:label="logoPreview ? __('Replace the logo') : __('Upload a logo')"
									@click="logoInput?.click()" />
								<span class="text-xs text-ink-gray-5">
									{{ __("The address stays {0} — a new file replaces the old one.").format(LOGO_PATH) }}
								</span>
							</div>
						</div>
						<FormControl
							v-if="state.logo_image && state.logo_image !== LOGO_PATH"
							size="sm"
							:label="__('Logo image URL')"
							:modelValue="state.logo_image"
							@update:modelValue="(v: string) => (state.logo_image = v)"
							placeholder="/files/logo.png" />
					</div>
					<FormControl
						type="select"
						size="sm"
						:label="__('Search')"
						:options="options.search_type"
						:modelValue="state.search_type"
						@update:modelValue="(v: string) => (state.search_type = v)" />
				</div>
				<div class="flex items-center gap-5">
					<Switch
						size="sm"
						:label="__('Sticky header')"
						:modelValue="!!state.sticky_header"
						@update:modelValue="(v: boolean) => (state.sticky_header = v ? 1 : 0)" />
					<Switch
						size="sm"
						:label="__('CTA button')"
						:modelValue="!!state.show_cta"
						@update:modelValue="(v: boolean) => (state.show_cta = v ? 1 : 0)" />
				</div>
				<div v-if="state.show_cta" class="grid grid-cols-3 gap-3">
					<FormControl
						size="sm"
						:label="__('CTA text')"
						:modelValue="state.cta_text"
						@update:modelValue="(v: string) => (state.cta_text = v)" />
					<FormControl
						size="sm"
						:label="__('CTA URL')"
						:modelValue="state.cta_url"
						@update:modelValue="(v: string) => (state.cta_url = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('CTA style')"
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
				{{ __("Menu") }}
			</button>
			<template v-if="open.menu">
				<div
					v-for="(item, index) in state.menu_items"
					:key="index"
					class="flex items-center gap-2">
					<FormControl
						size="sm"
						:placeholder="__('Label')"
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
					{{ __("Add menu item") }}
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
				{{ __("Footer") }}
			</button>
			<template v-if="open.footer">
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						type="select"
						size="sm"
						:label="__('Template')"
						:options="options.footer_template"
						:modelValue="state.footer_template"
						@update:modelValue="(v: string) => (state.footer_template = v)" />
					<FormControl
						size="sm"
						:label="__('Copyright')"
						:modelValue="state.copyright_text"
						@update:modelValue="(v: string) => (state.copyright_text = v)" />
				</div>
				<FormControl
					type="textarea"
					size="sm"
					:label="__('Description')"
					:modelValue="state.footer_description"
					@update:modelValue="(v: string) => (state.footer_description = v)" />
				<Switch
					size="sm"
					:label="__('Social links')"
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
			{{ saving ? __("Saving...") : __("Changes save automatically and apply to the whole site.") }}
		</p>
	</div>
</template>
<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import { Button, createResource, FileUploadHandler, FormControl, Switch, toast } from "frappe-ui";
import { computed, reactive, ref } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const API = "builder.hf_utils.chrome_api";

const themeColors = [
	{ field: "primary_color", label: __("Primary") },
	{ field: "secondary_color", label: __("Secondary") },
	{ field: "background_color", label: __("Background") },
	{ field: "text_color", label: __("Text") },
];

const socials = [
	{ field: "facebook_url", label: __("Facebook") },
	{ field: "instagram_url", label: __("Instagram") },
	{ field: "linkedin_url", label: __("LinkedIn") },
	{ field: "youtube_url", label: __("YouTube") },
];

// Kept in step with builder.branding.LOGO_PATH — the one address the
// site logo ever has.
const LOGO_PATH = "/files/logo-default.png";
const BRANDING_API = "builder.branding";

const logoInput = ref<HTMLInputElement>();
const logoBusy = ref(false);
const logoPreview = ref("");

const loaded = ref(false);
const saving = ref(false);
const open = reactive({ theme: true, header: false, menu: false, footer: false });
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const state = reactive<Record<string, any>>({ menu_items: [] });
let snapshot = "";

const payload = () => {
	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	const { _options, ...rest } = state;
	return JSON.parse(JSON.stringify(rest));
};

createResource({
	url: `${BRANDING_API}.get_logo`,
	auto: true,
	onSuccess(data: { url?: string }) {
		logoPreview.value = data?.url || "";
	},
});

// The upload goes through the server so the file lands on the stable path and
// the chrome is pointed at it in one move — the chat does exactly the same.
const onLogoPicked = async (event: Event) => {
	const input = event.target as HTMLInputElement;
	const file = (input.files || [])[0];
	input.value = "";
	if (!file) return;
	logoBusy.value = true;
	try {
		const doc = await new FileUploadHandler().upload(file, {
			private: false,
			folder: "Home/Builder Uploads",
		});
		if (!doc?.file_url) throw new Error(__("The file could not be uploaded."));
		const r = await createResource({ url: `${BRANDING_API}.set_logo` }).submit({
			file_url: doc.file_url,
		});
		logoPreview.value = r?.url || "";
		// keep the form in step, or the next debounced save would push the old
		// value back over what the server just wrote
		state.logo_image = LOGO_PATH;
		state.logo_type = "Image";
		toast.success(__("Logo updated"));
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	} finally {
		logoBusy.value = false;
	}
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
			await createResource({ url: `${API}.update_chrome_settings` }).submit({ settings: current });
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
