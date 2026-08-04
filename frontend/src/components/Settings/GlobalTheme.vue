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
						:label="__('On scroll')"
						:options="options.header_scroll"
						:modelValue="state.header_scroll"
						@update:modelValue="(v: string) => (state.header_scroll = v)" />
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

				<!-- The footer menu. "Same as header" is the cheap answer, but a
				     footer is where a site puts what the header has no room for —
				     legal pages, a second product line — so it can have its own. -->
				<FormControl
					type="select"
					size="sm"
					:label="__('Menu')"
					:options="options.footer_menu_source"
					:modelValue="state.footer_menu_source"
					@update:modelValue="(v: string) => (state.footer_menu_source = v)" />

				<template v-if="state.footer_menu_source === 'Custom links'">
					<!-- Grouped by column heading: one group is one column in the
					     rendered footer. Extended shows them side by side; the other
					     templates flatten them into a single row. -->
					<div
						v-for="(column, columnIndex) in footerColumns"
						:key="columnIndex"
						class="flex flex-col gap-2 rounded border border-outline-gray-1 p-3">
						<div class="flex items-center gap-2">
							<FormControl
								size="sm"
								:placeholder="__('Column heading')"
								:modelValue="column.name"
								@update:modelValue="(v: string) => renameColumn(column.name, v)"
								class="flex-1" />
							<Button
								variant="ghost"
								icon="lucide-trash-2"
								:title="__('Remove this column')"
								@click="removeColumn(column.name)" />
						</div>
						<div
							v-for="link in column.links"
							:key="link._key"
							class="flex items-center gap-2 pl-2">
							<FormControl
								size="sm"
								:placeholder="__('Label')"
								:modelValue="link.label"
								@update:modelValue="(v: string) => (link.label = v)"
								class="flex-1" />
							<FormControl
								size="sm"
								placeholder="/route"
								:modelValue="link.url"
								@update:modelValue="(v: string) => (link.url = v)"
								class="flex-1" />
							<Button
								variant="ghost"
								icon="lucide-trash-2"
								@click="removeLink(link)" />
						</div>
						<Button
							variant="ghost"
							class="w-fit"
							icon-left="lucide-plus"
							@click="addLink(column.name)">
							{{ __("Add link") }}
						</Button>
					</div>
					<Button
						variant="subtle"
						class="w-fit"
						icon-left="lucide-plus"
						@click="addColumn()">
						{{ __("Add column") }}
					</Button>
				</template>

				<!-- The accounts themselves live in Settings; here we only decide
				     whether the footer shows them. -->
				<Switch
					size="sm"
					:label="__('Social links')"
					:description="__('Set the accounts in Settings → Social')"
					:modelValue="!!state.show_social_links"
					@update:modelValue="(v: boolean) => (state.show_social_links = v ? 1 : 0)" />

				<!-- Somewhere to drop a newsletter embed until we ship our own. -->
				<Switch
					size="sm"
					:label="__('Custom block')"
					:description="__('Your own HTML — a newsletter form, a badge, a widget')"
					:modelValue="!!state.show_footer_html"
					@update:modelValue="(v: boolean) => (state.show_footer_html = v ? 1 : 0)" />
				<FormControl
					v-if="state.show_footer_html"
					type="textarea"
					size="sm"
					:rows="6"
					class="font-mono text-xs"
					placeholder="&lt;form action=&quot;...&quot;&gt;…&lt;/form&gt;"
					:modelValue="state.footer_html"
					@update:modelValue="(v: string) => (state.footer_html = v)" />
			</template>
		</div>

		<!-- The band above the content on pages the editor does not build. It
		     sits between the header and the footer settings because that is what
		     it is: the third piece of the site chrome. -->
		<div class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4">
			<button
				class="flex w-fit items-center gap-1 text-sm font-medium text-ink-gray-8"
				@click="open.pageHeader = !open.pageHeader">
				<span
					class="inline-block size-4"
					:class="open.pageHeader ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				{{ __("Page header") }}
			</button>
			<template v-if="open.pageHeader">
				<p class="text-xs text-ink-gray-5">
					{{ __("Shown above the content of pages the editor does not build — the blog, a section that is coming. Pages that open on a hero of their own keep it.") }}
				</p>
				<FormControl
					type="select"
					size="sm"
					:label="__('Style')"
					:options="options.page_header_style"
					:modelValue="state.page_header_style"
					@update:modelValue="(v: string) => (state.page_header_style = v)" />
				<Switch
					size="sm"
					:label="__('Breadcrumbs')"
					:modelValue="!!state.show_breadcrumbs"
					@update:modelValue="(v: boolean) => (state.show_breadcrumbs = v ? 1 : 0)" />
			</template>
		</div>

		<!-- Blog. Only there when the site has one — the plugin decides. -->
		<div v-if="capabilities.blog !== false" class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4">
			<button
				class="flex w-fit items-center gap-1 text-sm font-medium text-ink-gray-8"
				@click="open.blog = !open.blog">
				<span
					class="inline-block size-4"
					:class="open.blog ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				{{ __("Blog") }}
			</button>
			<template v-if="open.blog">
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						type="select"
						size="sm"
						:label="__('Article list')"
						:options="options.blog_layout"
						:modelValue="state.blog_layout"
						@update:modelValue="(v: string) => (state.blog_layout = v)" />
					<FormControl
						type="select"
						size="sm"
						:label="__('Article page')"
						:options="options.blog_post_layout"
						:modelValue="state.blog_post_layout"
						@update:modelValue="(v: string) => (state.blog_post_layout = v)" />
				</div>
				<Switch
					size="sm"
					:label="__('Show the author')"
					:modelValue="!!state.blog_show_author"
					@update:modelValue="(v: boolean) => (state.blog_show_author = v ? 1 : 0)" />
				<Switch
					size="sm"
					:label="__('Allow comments')"
					:description="__('Off by default. A comment box nobody watches fills with spam.')"
					:modelValue="!!state.blog_allow_comments"
					@update:modelValue="(v: boolean) => (state.blog_allow_comments = v ? 1 : 0)" />
			</template>
		</div>

		<!-- Where these settings came from. The generator already saved its brief
		     on the session and read it back to finish the site; nobody could read
		     it. The Theme is the durable home for it — the chat opens a fresh
		     session every time, so a panel living only there is unreachable the
		     day after. -->
		<div v-if="briefGroups.length" class="flex flex-col gap-3 border-t border-outline-gray-1 pt-4">
			<button
				class="flex w-fit items-center gap-1 text-sm font-medium text-ink-gray-8"
				@click="open.brief = !open.brief">
				<span
					class="inline-block size-4"
					:class="open.brief ? 'lucide-chevron-down' : 'lucide-chevron-right'"
					aria-hidden="true" />
				{{ __("What the AI decided") }}
			</button>
			<template v-if="open.brief">
				<p class="text-xs text-ink-gray-5">
					{{ __("The brief every page was generated from. Changing a setting above overrides it; the brief itself does not change.") }}
				</p>
				<div v-for="group in briefGroups" :key="group.title" class="flex flex-col gap-1">
					<span class="text-xs font-medium uppercase text-ink-gray-5">{{ group.title }}</span>
					<div v-for="row in group.rows" :key="row.label" class="flex items-start gap-2 text-sm">
						<span class="w-40 shrink-0 text-ink-gray-5">{{ row.label }}</span>
						<span class="flex items-center gap-1.5 text-ink-gray-8">
							<span
								v-if="row.is_color"
								class="size-3 shrink-0 rounded-sm border border-outline-gray-2"
								:style="{ background: row.value }" />
							{{ row.value }}
						</span>
					</div>
				</div>
			</template>
		</div>

		<!-- "Saving..." flashes for a few hundred milliseconds and is gone before
		     anyone reads it. The confirmation is what tells a user their change
		     was taken; it lingers a couple of seconds, then steps out of the way. -->
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
				{{ __("Changes save automatically and apply to the whole site.") }}
			</span>
		</div>
	</div>
</template>
<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import { Button, createResource, FileUploadHandler, FormControl, Switch, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const API = "builder.hf_utils.chrome_api";

const themeColors = [
	{ field: "primary_color", label: __("Primary") },
	{ field: "secondary_color", label: __("Secondary") },
	{ field: "background_color", label: __("Background") },
	{ field: "text_color", label: __("Text") },
];

// The footer links are stored flat, each row carrying the heading of the column
// it belongs to. The editor groups them; the renderer groups them again. A row
// needs an identity that survives regrouping, hence `_key` — it is stripped
// before the payload goes out.
type FooterLink = { _key: number; column_name: string; label: string; url: string };
let linkKey = 0;

const footerColumns = computed(() => {
	const groups: { name: string; links: FooterLink[] }[] = [];
	for (const link of (state.footer_links || []) as FooterLink[]) {
		const name = link.column_name || "";
		let group = groups.find((g) => g.name === name);
		if (!group) {
			group = { name, links: [] };
			groups.push(group);
		}
		group.links.push(link);
	}
	return groups;
});

const newLink = (columnName: string): FooterLink => ({
	_key: ++linkKey,
	column_name: columnName,
	label: "",
	url: "",
});

function addColumn() {
	// A column exists because rows point at it, so a new one starts with a row.
	let name = __("Links");
	let n = 2;
	while (footerColumns.value.some((g) => g.name === name)) name = `${__("Links")} ${n++}`;
	state.footer_links.push(newLink(name));
}

function addLink(columnName: string) {
	state.footer_links.push(newLink(columnName));
}

function removeLink(link: FooterLink) {
	const index = state.footer_links.indexOf(link);
	if (index >= 0) state.footer_links.splice(index, 1);
}

function removeColumn(name: string) {
	state.footer_links = (state.footer_links as FooterLink[]).filter(
		(link) => (link.column_name || "") !== name,
	);
}

function renameColumn(oldName: string, newName: string) {
	for (const link of state.footer_links as FooterLink[]) {
		if ((link.column_name || "") === oldName) link.column_name = newName;
	}
}

// Kept in step with builder.branding.LOGO_PATH — the one address the
// site logo ever has.
const LOGO_PATH = "/files/logo-default.png";
const BRANDING_API = "builder.branding";

const logoInput = ref<HTMLInputElement>();
const logoBusy = ref(false);
const logoPreview = ref("");

const loaded = ref(false);
const saving = ref(false);
// Everything here saves on its own. Without a mark that says so, a user
// changes a colour, sees nothing happen, and changes it again.
const savedAt = ref(0);
const justSaved = ref(false);
watch(savedAt, (at) => {
	if (!at) return;
	justSaved.value = true;
	setTimeout(() => (justSaved.value = false), 2200);
});
const open = reactive({
	theme: true,
	header: false,
	menu: false,
	footer: false,
	pageHeader: false,
	blog: false,
	brief: false,
});

// The blog section is only worth showing on a site that has a blog.
const capabilities = ref<Record<string, boolean>>({});
createResource({
	url: "builder.plugins.get_capabilities",
	auto: true,
	onSuccess(data: Record<string, boolean>) {
		capabilities.value = data || {};
	},
	onError() {
		capabilities.value = {};
	},
});

// The brief behind the site as it stands. Absent on a site nobody generated,
// in which case the whole section stays hidden.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const briefGroups = ref<any[]>([]);
createResource({
	url: "builder.brief_view.get_latest_brief",
	auto: true,
	onSuccess(data: { exists?: boolean; groups?: unknown[] }) {
		briefGroups.value = data?.exists ? (data.groups as never[]) || [] : [];
	},
	onError() {
		briefGroups.value = [];
	},
});
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const state = reactive<Record<string, any>>({ menu_items: [], footer_links: [] });
let snapshot = "";

const payload = () => {
	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	const { _options, ...rest } = state;
	const clone = JSON.parse(JSON.stringify(rest));
	// `_key` only exists to keep the editor's v-for stable
	clone.footer_links = (clone.footer_links || []).map(
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		({ _key, ...link }: Record<string, unknown>) => link,
	);
	return clone;
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
		state.footer_links = ((data.footer_links || []) as Record<string, unknown>[]).map((link) => ({
			...link,
			_key: ++linkKey,
		}));
		snapshot = JSON.stringify(payload());
		loaded.value = true;
	},
});

// The server sends the canonical option tokens ("Rounded", "Darken"): those are
// what gets stored, and they must not change with the reader's language. Only
// the label is translated, so a French screen reads French while the document
// keeps the same value it has always had.
const options = computed<Record<string, { label: string; value: string }[]>>(() => {
	const raw = (state._options || {}) as Record<string, string[]>;
	return Object.fromEntries(
		Object.entries(raw).map(([key, values]) => [
			key,
			(values || []).map((value) => ({ label: __(value), value })),
		]),
	);
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
