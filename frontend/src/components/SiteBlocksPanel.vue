<!-- //// Neoffice — added file (no upstream equivalent): the site's live blocks, for a person.

	 The generator learned what a page can carry from a catalogue (builder/site_ai/components.py) on 2026-09-15, and
	 the assistant learned to place and change a component on 2026-10-19. This is the human half: the same
	 catalogue, in the editor. A person picks a component, sets its options in a form made from what the
	 component declares, and the editor places — or, when the selected block is already a component, updates —
	 the div whose text is the canonical include tag. The tag is built on the server and goes through the same
	 gate the assistant's tools do (builder.api.render_component_tag, components.lawful_tag).

	 These are not the saved components of the Components tab: those are blocks a user designed.
	 These are blocks an APP provides, and they draw the site's own live data. -->
<template>
	<div class="flex flex-col gap-3 px-3 pb-3">
		<p class="text-p-sm text-ink-gray-5">
			{{
				__("Blocks that show this site's own data. Pick one, set what it needs, and it lands on the page.")
			}}
		</p>

		<!-- the selected block is already one of them: change it rather than add another -->
		<section
			v-if="editing"
			class="rounded border border-outline-gray-3 bg-surface-gray-1 p-2"
			data-testid="site-blocks-edit">
			<div class="flex items-center gap-2">
				<span class="lucide-pencil size-3.5 text-ink-gray-5" />
				<span class="text-base font-medium text-ink-gray-8">{{ editing.component.label }}</span>
			</div>
			<p v-if="editing.values === null" class="mt-1 text-p-sm text-ink-gray-5">
				{{ __("This block's tag was written by hand: it cannot be changed from here.") }}
			</p>
			<template v-else>
				<p class="mt-0.5 mb-2 text-p-sm text-ink-gray-5">
					{{ __("This block is selected: change its options and update it.") }}
				</p>
				<p v-if="editing.component.help" class="mb-2 text-p-sm text-ink-gray-5">
					{{ editing.component.help }}
				</p>
				<SiteComponentFields v-model:form="editForm" :component="editing.component" />
				<Button
					variant="solid"
					class="mt-2 w-full"
					:loading="saving"
					:disabled="builderStore.readOnlyMode"
					@click="update">
					{{ __("Update the block") }}
				</Button>
				<!-- the block draws a form: its questions are written in a dialog of their own -->
				<Button
					v-if="editing.component.path === FORM_INCLUDE && selectedFormName"
					variant="subtle"
					class="mt-2 w-full"
					data-testid="edit-this-form"
					@click="openFormDialog(selectedFormName)">
					{{ __("Edit the questions of this form") }}
				</Button>
			</template>
		</section>

		<!-- the forms of this site: where the questions of a form are written (the form itself is a record of the theme) -->
		<section
			v-if="formsState.available"
			class="rounded border border-outline-gray-3 p-2"
			data-testid="site-forms">
			<div class="flex items-center justify-between gap-2">
				<span class="text-base font-medium text-ink-gray-8">{{ __("Forms") }}</span>
				<Button
					variant="subtle"
					size="sm"
					:disabled="builderStore.readOnlyMode"
					@click="startNewForm = !startNewForm">
					{{ __("New form") }}
				</Button>
			</div>
			<p class="mt-0.5 text-p-sm text-ink-gray-5">
				{{
					__(
						"A form keeps its questions and its answers in the site's inbox. Write it here, then add it to a page.",
					)
				}}
			</p>

			<!-- a new form starts from one of three shapes -->
			<div v-if="startNewForm" class="mt-2 flex flex-col gap-1" data-testid="site-form-presets">
				<button
					v-for="preset in formsState.presets"
					:key="preset.key"
					class="rounded border border-outline-gray-2 p-2 text-left hover:bg-surface-gray-1"
					:disabled="creating"
					:data-preset="preset.key"
					@click="createForm(preset.key)">
					<span class="text-base font-medium text-ink-gray-8">{{ preset.label }}</span>
					<span class="block text-p-sm text-ink-gray-5">{{ preset.about }}</span>
				</button>
			</div>

			<ul class="mt-2 flex flex-col gap-1">
				<li
					v-for="form in formsState.forms"
					:key="form.name"
					class="flex items-center gap-2 rounded bg-surface-gray-1 p-1.5"
					:data-form="form.name">
					<div class="min-w-0 flex-1">
						<span class="block truncate text-p-sm font-medium text-ink-gray-8">{{ form.title }}</span>
						<span v-if="!form.enabled" class="text-p-xs text-ink-gray-5">{{ __("switched off") }}</span>
					</div>
					<Button size="sm" variant="ghost" @click="openFormDialog(form.name)">{{ __("Edit") }}</Button>
					<Button
						size="sm"
						variant="subtle"
						:disabled="builderStore.readOnlyMode || !form.enabled"
						:loading="saving"
						@click="placeForm(form.name)">
						{{ __("Add to the page") }}
					</Button>
				</li>
			</ul>
		</section>
		<SiteFormDialog v-model="showFormDialog" :formName="formBeingEdited" @saved="formSaved" />

		<div v-if="!siteComponentsLoaded" class="text-p-sm text-ink-gray-4">{{ __("Loading…") }}</div>
		<div v-else-if="siteComponentsError" class="text-p-sm text-ink-red-3">{{ siteComponentsError }}</div>
		<div v-else-if="!siteComponents.length" class="text-p-sm text-ink-gray-4">
			{{ __("No block is available on this site yet.") }}
		</div>

		<template v-for="group in groups" :key="group.name">
			<h4 v-if="group.title" class="mt-1 text-p-sm font-medium text-ink-gray-6">{{ group.title }}</h4>
			<div
				v-for="component in group.components"
				:key="component.path"
				class="rounded border border-outline-gray-1"
				:data-component="component.path">
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
					<p v-if="component.help" class="mb-2 text-p-sm text-ink-gray-5">{{ component.help }}</p>

					<SiteComponentFields v-model:form="addForm" :component="component" />

					<p class="mt-2 mb-1 text-p-sm text-ink-gray-5">
						{{ __("It will be placed {0}.", [placement.where]) }}
					</p>
					<Button
						variant="solid"
						class="w-full"
						:loading="saving"
						:disabled="builderStore.readOnlyMode"
						@click="insert(component)">
						{{ __("Add to the page") }}
					</Button>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type Block from "@/block";
import SiteComponentFields from "@/components/SiteComponentFields.vue";
import SiteFormDialog from "@/components/Modals/SiteFormDialog.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { getErrorMessage } from "@/utils/helpers";
import {
	chosenOptions,
	formFromValues,
	loadSiteComponents,
	readComponentTag,
	siteComponents,
	siteComponentsError,
	siteComponentsLoaded,
	type OptionsForm,
	type SiteComponent,
} from "@/utils/siteComponents";
import { createSiteForm, loadSiteForms, siteFormsState, type SiteFormDefinition } from "@/utils/siteForms";
import { __ } from "@/translation";
// BuilderInput is registered globally in main.ts; Button and toast come from frappe-ui
import { Button, createResource, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

// what was typed, exactly as typed: coercing while someone is still typing fights their cursor (an int field would
// turn "1." back into "1"), so the coercion happens once, on send.
const addForm = ref<OptionsForm>({ typed: {}, flags: {} });
const editForm = ref<OptionsForm>({ typed: {}, flags: {} });
const open = ref<string | null>(null);
const saving = ref(false);

// the catalogue is asked for the open page, so the components that suit it come first
watch(
	() => pageStore.activePage?.name ?? null,
	(page) => {
		void loadSiteComponents(page);
		void loadSiteForms(page);
	},
	{ immediate: true },
);

// ---- the forms of the site ----------------------------------------------------------------------------------------

// the include that draws a form kept as data (builder/templates/includes/site_form.html)
const FORM_INCLUDE = "builder/templates/includes/site_form.html";
const formsState = siteFormsState;
const startNewForm = ref(false);
const creating = ref(false);
const showFormDialog = ref(false);
const formBeingEdited = ref<string | null>(null);

const openFormDialog = (name: string) => {
	formBeingEdited.value = name;
	showFormDialog.value = true;
};

// a form is written in its website's language, so the person who clicks only chooses its shape
const createForm = async (preset: string) => {
	if (builderStore.readOnlyMode || creating.value) return;
	creating.value = true;
	try {
		const made: SiteFormDefinition = await createSiteForm(
			preset,
			"",
			formsState.value.available ? formsState.value.website_profile : "",
		);
		startNewForm.value = false;
		await reloadForms();
		openFormDialog(made.name);
	} catch (e) {
		toast.error(getErrorMessage(e, __("The form could not be created.")));
	} finally {
		creating.value = false;
	}
};

// the options of the include list the forms that exist, so the catalogue is read again when they change
const reloadForms = async () => {
	const page = pageStore.activePage?.name ?? null;
	await Promise.all([loadSiteForms(page), loadSiteComponents(page)]);
};
const formSaved = () => void reloadForms();

// the form a selected block draws: the one its option names, else the contact form of the site
const selectedFormName = computed<string | null>(() => {
	const named = editing.value?.values?.site_form;
	if (typeof named === "string" && named) return named;
	if (!formsState.value.available) return null;
	const profile = formsState.value.website_profile;
	const contact = formsState.value.forms.filter((f) => f.kind === "Contact" && f.enabled);
	return (contact.find((f) => f.profile === profile) ?? contact[0])?.name ?? null;
});

// put a form on the page: the include with the form named, through the same door as any other component
const placeForm = async (name: string) => {
	const component = siteComponents.value.find((c) => c.path === FORM_INCLUDE);
	if (!component) {
		toast.error(__("The form block is not available on this site."));
		return;
	}
	await insert(component, { site_form: name }, false);
};

const selected = computed<Block | null>(() => {
	const blocks = canvasStore.activeCanvas?.selectedBlocks;
	return blocks && blocks.length === 1 ? (blocks[0] as Block) : null;
});

// ---- change the selected block ------------------------------------------------------------------------------------

type Editing = { block: Block; component: SiteComponent; values: Record<string, unknown> | null };
const editing = ref<Editing | null>(null);
const readTag = createResource({ url: "builder.api.read_component_tag" });
let reading = 0;

// A block is read when it is selected, and again when its text changes (the update below, an undo). The shape is
// checked here first so an ordinary block costs no request; the server decides whether it is a lawful tag.
watch(
	() => [selected.value?.blockId, selected.value?.getInnerHTML?.()] as const,
	async () => {
		const block = selected.value;
		const text = block?.getInnerHTML?.() ?? "";
		const mine = ++reading;
		if (!block || !readComponentTag(text)) {
			editing.value = null;
			return;
		}
		try {
			const read = await readTag.submit({ text });
			if (mine !== reading) return;
			const component = read && siteComponents.value.find((c) => c.path === read.path);
			if (!component) {
				editing.value = null;
				return;
			}
			editing.value = { block, component, values: read.values };
			editForm.value = formFromValues(component, read.values);
		} catch {
			if (mine === reading) editing.value = null;
		}
	},
	{ immediate: true },
);

const tagFor = createResource({ url: "builder.api.render_component_tag" });

// the tag is built on the server, from the catalogue: a value the component does not declare is dropped, one it
// would refuse comes back with its sentence, and nothing but a lawful tag is written
const tagOf = (component: SiteComponent, form: OptionsForm): Promise<string> =>
	tagFor.submit({ path: component.path, values: JSON.stringify(chosenOptions(component, form)) });

const update = async () => {
	const current = editing.value;
	if (!current || builderStore.readOnlyMode) return;
	saving.value = true;
	try {
		current.block.setInnerHTML(await tagOf(current.component, editForm.value));
		toast.success(__("{0} updated.", [current.component.label]));
	} catch (e) {
		toast.error(getErrorMessage(e, __("The block could not be updated.")));
	} finally {
		saving.value = false;
	}
};

// ---- add a block --------------------------------------------------------------------------------------------------

const toggle = (component: SiteComponent) => {
	// one open at a time, and its fields start empty: a blank field means "use the default",
	// which is what the catalogue's default column already says
	open.value = open.value === component.path ? null : component.path;
	addForm.value = { typed: {}, flags: {} };
};

// What the person calls a block: a component by its name, else the name the block was given, else its element
const nameOf = (block: Block) => {
	const read = readComponentTag(block.getInnerHTML());
	const component = read && siteComponents.value.find((c) => c.path === read.path);
	return component?.label || block.blockName || block.getElement() || "";
};

// Where a block lands: after the selected one, but never inside a row or a grid (a component is a block of its own,
// full width); with nothing selected, at the end of the page.
const placement = computed<{ parent: Block | null; after: Block | null; where: string }>(() => {
	const root = canvasStore.getRootBlock() as Block | undefined;
	const anchor = (canvasStore.activeCanvas?.selectedBlocks?.[0] as Block | undefined) ?? null;
	if (!root || !anchor || anchor.isRoot()) {
		return { parent: root ?? null, after: null, where: __("at the end of the page") };
	}
	let target = anchor;
	let parent = target.getParentBlock();
	while (parent && !parent.isRoot() && (parent.isRow() || parent.isGrid())) {
		target = parent;
		parent = target.getParentBlock();
	}
	if (!parent) return { parent: root, after: null, where: __("at the end of the page") };
	return { parent, after: target, where: __("after “{0}”", [nameOf(target)]) };
});

const insert = async (component: SiteComponent, values?: Record<string, unknown>, fromList = true) => {
	if (builderStore.readOnlyMode) return;
	saving.value = true;
	try {
		const tag = values
			? await tagFor.submit({ path: component.path, values: JSON.stringify(values) })
			: await tagOf(component, addForm.value);
		const { parent, after } = placement.value;
		if (!parent) {
			toast.error(__("Open a page first."));
			return;
		}
		const options = {
			element: "div",
			blockName: component.path
				.split("/")
				.pop()
				?.replace(/\.html$/, "")
				.replace(/_/g, "-"),
			innerHTML: tag,
			baseStyles: { width: "100%" },
		};
		if (after) parent.addChildAfter(options, after);
		else parent.addChild(options);
		toast.success(__("{0} added to the page.", [component.label]));
		if (fromList) open.value = null;
	} catch (e) {
		toast.error(getErrorMessage(e, __("The block could not be added.")));
	} finally {
		saving.value = false;
	}
};

// ---- the list -----------------------------------------------------------------------------------------------------

// Suited to the open page first, the rest after it. When the page's type is not known nothing is recommended, and
// the list is one list.
const groups = computed(() => {
	// what the site turned off is not offered (a block that carries it is still found above, in the whole list)
	const all = siteComponents.value.filter((c) => c.enabled !== false);
	if (!all.some((c) => c.suited !== null)) return [{ name: "all", title: "", components: all }];
	return [
		{ name: "suited", title: __("Suited to this page"), components: all.filter((c) => c.suited) },
		{ name: "others", title: __("Other blocks"), components: all.filter((c) => !c.suited) },
	].filter((group) => group.components.length);
});
</script>
