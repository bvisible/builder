<!-- //// Neoffice — added file (no upstream equivalent): the dialog that edits a form of the website.

	 A form is a record of the theme (`Site Form`), written here, in the desk, by the editor's assistant and by the
	 site generator, all through the same checks (neoffice_theme/site_forms.py). The dialog edits a copy and shows it
	 as the visitor will meet it, live, on the right. Nothing is written until "Save": the server holds the form to
	 its rules (exactly one e-mail question, no empty step...) and a refusal comes back as the sentence to show. -->
<template>
	<Dialog
		v-model="open"
		:title="definition ? definition.title || __('New form') : __('Form')"
		size="5xl"
		:isDirty="dirty"
		:actions="[
			{
				label: __('Save the form'),
				variant: 'solid',
				disabled: !definition || saving || builderStore.readOnlyMode,
				loading: saving,
				onClick: save,
			},
		]">
		<template #default>
			<p v-if="loadError" class="text-p-sm text-ink-red-3">{{ loadError }}</p>
			<p v-else-if="!definition" class="text-p-sm text-ink-gray-5">{{ __("Loading…") }}</p>
			<div
				v-else
				class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]"
				data-testid="site-form-dialog">
				<div class="flex max-h-[68vh] flex-col gap-5 overflow-y-auto pr-2">
					<!-- the form -->
					<section class="flex flex-col gap-3">
						<BuilderInput
							type="text"
							:label="__('Name of the form')"
							:modelValue="definition.title"
							:hideClearButton="true"
							@input="(v: string) => (definition!.title = String(v ?? ''))"
							@update:modelValue="(v: string) => (definition!.title = String(v ?? ''))" />
						<label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
							<input v-model="definition.enabled" type="checkbox" />
							{{ __("Shown on the website") }}
						</label>
					</section>

					<!-- the steps -->
					<section class="flex flex-col gap-2">
						<h4 class="text-base font-semibold text-ink-gray-8">{{ __("Steps of the form") }}</h4>
						<p class="text-p-sm text-ink-gray-5">
							{{
								__(
									"Leave a single page, or split the questions into steps the visitor goes through one at a time.",
								)
							}}
						</p>
						<div v-for="(title, index) in definition.steps" :key="index" class="flex items-center gap-2">
							<span class="w-14 shrink-0 text-p-sm text-ink-gray-5">{{ __("Step {0}", [index + 1]) }}</span>
							<BuilderInput
								class="flex-1"
								type="text"
								:modelValue="title"
								:hideClearButton="true"
								@input="(v: string) => (definition!.steps[index] = String(v ?? ''))"
								@update:modelValue="(v: string) => (definition!.steps[index] = String(v ?? ''))" />
							<Button variant="ghost" :title="__('Remove this step')" @click="dropStep(index + 1)">
								<template #icon><span class="lucide-trash-2 size-3.5" /></template>
							</Button>
						</div>
						<div>
							<Button variant="subtle" size="sm" :disabled="!canAddStep" @click="addAStep">
								{{ __("Add a step") }}
							</Button>
						</div>
					</section>

					<!-- the questions -->
					<section class="flex flex-col gap-2">
						<h4 class="text-base font-semibold text-ink-gray-8">{{ __("Questions") }}</h4>
						<draggable
							v-model="definition.fields"
							item-key="key"
							handle=".drag-handle"
							class="flex flex-col gap-2">
							<template #item="{ element: question, index }">
								<div
									class="rounded border border-outline-gray-2 bg-surface-white p-2"
									:data-question="question.fieldname || question.key">
									<div class="flex items-center gap-1.5">
										<span
											class="drag-handle lucide-grip-vertical size-4 shrink-0 cursor-grab text-ink-gray-4"
											:title="__('Drag to reorder')" />
										<span class="w-6 shrink-0 text-p-sm text-ink-gray-5">{{ index + 1 }}</span>
										<BuilderInput
											class="flex-1"
											type="text"
											:modelValue="question.label"
											:placeholder="__('Your question')"
											:hideClearButton="true"
											@input="(v: string) => (question.label = String(v ?? ''))"
											@update:modelValue="(v: string) => (question.label = String(v ?? ''))" />
										<Button
											variant="ghost"
											size="sm"
											:disabled="index === 0"
											:title="__('Move up')"
											@click="move(index, -1)">
											<template #icon><span class="lucide-arrow-up size-3.5" /></template>
										</Button>
										<Button
											variant="ghost"
											size="sm"
											:disabled="index === definition.fields.length - 1"
											:title="__('Move down')"
											@click="move(index, 1)">
											<template #icon><span class="lucide-arrow-down size-3.5" /></template>
										</Button>
										<Button
											variant="ghost"
											size="sm"
											:disabled="question.role === 'Email'"
											:title="
												question.role === 'Email'
													? __('The e-mail question stays: a message needs someone to answer')
													: __('Remove this question')
											"
											@click="remove(index)">
											<template #icon><span class="lucide-trash-2 size-3.5" /></template>
										</Button>
									</div>

									<div class="mt-2 grid grid-cols-2 gap-2 pl-7">
										<BuilderInput
											type="select"
											:label="__('Type')"
											:options="typeOptions(question)"
											:modelValue="question.type"
											:disabled="Boolean(question.role)"
											@update:modelValue="(v: string) => changeType(question, v as QuestionType)" />
										<BuilderInput
											v-if="stepCount > 1"
											type="select"
											:label="__('Asked in')"
											:options="stepOptions"
											:modelValue="String(question.step)"
											@update:modelValue="(v: string) => (question.step = Number(v))" />
									</div>
									<div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 pl-7">
										<label class="flex items-center gap-2 text-p-sm text-ink-gray-7">
											<input
												v-model="question.required"
												type="checkbox"
												:disabled="question.role === 'Email'" />
											{{ __("Required") }}
										</label>
										<span v-if="question.role" class="text-p-xs text-ink-gray-5">
											{{ __("Used as {0} of the message.", [roleLabel(question.role)]) }}
										</span>
									</div>
									<div v-if="isChoice(question.type)" class="mt-2 pl-7">
										<BuilderInput
											type="textarea"
											:label="__('Choices, one per line')"
											:rows="4"
											:modelValue="question.options.join('\n')"
											:hideClearButton="true"
											@input="(v: string) => (question.options = String(v ?? '').split('\n'))"
											@update:modelValue="(v: string) => (question.options = String(v ?? '').split('\n'))" />
									</div>
									<div v-if="question.type !== 'Consent'" class="mt-2 pl-7">
										<BuilderInput
											type="text"
											:label="__('Hint')"
											:modelValue="question.help"
											:hideClearButton="true"
											@input="(v: string) => (question.help = String(v ?? ''))"
											@update:modelValue="(v: string) => (question.help = String(v ?? ''))" />
									</div>
								</div>
							</template>
						</draggable>
						<div class="flex items-center gap-2">
							<BuilderInput
								class="w-48"
								type="select"
								:options="newTypeOptions"
								:modelValue="nextType"
								@update:modelValue="(v: string) => (nextType = v as QuestionType)" />
							<Button variant="subtle" size="sm" :disabled="!canAddQuestion" @click="addAQuestion">
								{{ __("Add a question") }}
							</Button>
						</div>
					</section>

					<!-- what happens next -->
					<section class="flex flex-col gap-3">
						<h4 class="text-base font-semibold text-ink-gray-8">{{ __("How it is shown") }}</h4>
						<label class="flex items-start gap-2 text-p-sm text-ink-gray-7">
							<input v-model="definition.dialog" type="checkbox" class="mt-0.5" />
							<span>
								<span class="font-medium">{{ __("Open in a window") }}</span>
								<span class="block text-ink-gray-5">
									{{ __("The form waits behind a button, and any link to #contact opens it.") }}
								</span>
							</span>
						</label>
						<BuilderInput
							v-if="definition.dialog"
							type="text"
							:label="__('Button text')"
							:description="__('Empty: no button, the page has its own link to #contact.')"
							:modelValue="definition.button_text"
							:hideClearButton="true"
							@input="(v: string) => (definition!.button_text = String(v ?? ''))"
							@update:modelValue="(v: string) => (definition!.button_text = String(v ?? ''))" />
						<BuilderInput
							type="text"
							:label="__('Send button text')"
							:placeholder="__('Send Message')"
							:modelValue="definition.submit_text"
							:hideClearButton="true"
							@input="(v: string) => (definition!.submit_text = String(v ?? ''))"
							@update:modelValue="(v: string) => (definition!.submit_text = String(v ?? ''))" />
						<BuilderInput
							type="textarea"
							:label="__('Message once sent')"
							:placeholder="__('Thank you, your message has been sent.')"
							:rows="2"
							:modelValue="definition.success_message"
							:hideClearButton="true"
							@input="(v: string) => (definition!.success_message = String(v ?? ''))"
							@update:modelValue="(v: string) => (definition!.success_message = String(v ?? ''))" />
					</section>

					<section class="flex flex-col gap-3">
						<h4 class="text-base font-semibold text-ink-gray-8">{{ __("Who is told") }}</h4>
						<BuilderInput
							type="text"
							:label="__('Messages go to')"
							:description="
								__(
									'E-mail addresses separated by commas. Empty: the address of the company, as for every message.',
								)
							"
							:modelValue="definition.recipients"
							:hideClearButton="true"
							@input="(v: string) => (definition!.recipients = String(v ?? ''))"
							@update:modelValue="(v: string) => (definition!.recipients = String(v ?? ''))" />
						<BuilderInput
							type="select"
							:label="__('What the visitor receives')"
							:options="visitorCopyOptions"
							:modelValue="definition.visitor_copy"
							@update:modelValue="(v: string) => (definition!.visitor_copy = String(v ?? ''))" />
					</section>

					<ul
						v-if="issues.length"
						class="rounded border border-outline-amber-2 bg-surface-amber-1 p-2 text-p-sm text-ink-gray-8"
						data-testid="site-form-problems">
						<li v-for="issue in issues" :key="issue">{{ issue }}</li>
					</ul>
				</div>

				<!-- what the visitor will meet -->
				<div class="flex flex-col gap-2">
					<h4 class="text-base font-semibold text-ink-gray-8">{{ __("What the visitor sees") }}</h4>
					<SiteFormPreview :definition="definition" />
					<p class="text-p-xs text-ink-gray-5">
						{{ __("The page draws the saved form in the style of the site. This is its shape.") }}
					</p>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import SiteFormPreview from "@/components/SiteFormPreview.vue";
import useBuilderStore from "@/stores/builderStore";
import { __ } from "@/translation";
import { getErrorMessage } from "@/utils/helpers";
import {
	addStep,
	fetchSiteForm,
	isChoice,
	moveQuestion,
	newQuestion,
	problems,
	removeQuestion,
	removeStep,
	roleLabel,
	saveSiteForm,
	siteFormsState,
	stepCount as stepsOf,
	typeLabel,
	type Question,
	type QuestionType,
	type SiteFormDefinition,
} from "@/utils/siteForms";
import { Button, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";
import draggable from "vuedraggable";

const props = defineProps<{ modelValue: boolean; formName: string | null }>();
const emit = defineEmits<{
	"update:modelValue": [value: boolean];
	saved: [definition: SiteFormDefinition];
}>();

const builderStore = useBuilderStore();
const open = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit("update:modelValue", value),
});

const definition = ref<SiteFormDefinition | null>(null);
const saved = ref("");
const loadError = ref("");
const saving = ref(false);
const nextType = ref<QuestionType>("Text");

// what was loaded, to know whether anything changed since (the dialog asks before it throws a change away)
const snapshot = (value: SiteFormDefinition | null) => JSON.stringify(value);
const dirty = computed(() => Boolean(definition.value) && snapshot(definition.value) !== saved.value);

watch(
	() => [props.modelValue, props.formName] as const,
	async ([isOpen, name]) => {
		if (!isOpen || !name) return;
		definition.value = null;
		loadError.value = "";
		try {
			const loaded = await fetchSiteForm(name);
			definition.value = loaded;
			saved.value = snapshot(loaded);
		} catch (error) {
			loadError.value = getErrorMessage(error, __("The form could not be loaded."));
		}
	},
	{ immediate: true },
);

const limits = computed(() =>
	siteFormsState.value.available ? siteFormsState.value.limits : { fields: 30, steps: 5, choices: 20 },
);
const fieldTypes = computed<QuestionType[]>(() =>
	siteFormsState.value.available
		? siteFormsState.value.field_types
		: ["Text", "Long text", "Email", "Phone", "Single choice", "Checkboxes", "Date", "Consent"],
);

const stepCount = computed(() => (definition.value ? stepsOf(definition.value) : 1));
const stepOptions = computed(() =>
	Array.from({ length: stepCount.value }, (_, index) => ({
		value: String(index + 1),
		label: definition.value?.steps[index]?.trim() || __("Step {0}", [index + 1]),
	})),
);
const canAddStep = computed(() => stepCount.value < limits.value.steps);
const canAddQuestion = computed(() => (definition.value?.fields.length ?? 0) < limits.value.fields);
const issues = computed(() => (definition.value ? problems(definition.value, limits.value) : []));

// the type of a question that is the name, the e-mail, the phone or the message is fixed: the message is read from it
const typeOptions = (question: Question) =>
	(question.role ? [question.type] : fieldTypes.value).map((type) => ({
		value: type,
		label: typeLabel(type),
	}));
const newTypeOptions = computed(() =>
	fieldTypes.value.map((type) => ({ value: type, label: typeLabel(type) })),
);
const visitorCopyOptions = computed(() => [
	{ value: "", label: __("As chosen in the settings of the contact form") },
	{ value: "Acknowledgement", label: __("An acknowledgement, without their words") },
	{ value: "Copy of the message", label: __("A copy of their message") },
	{ value: "None", label: __("Nothing") },
]);

const changeType = (question: Question, type: QuestionType) => {
	question.type = type;
	if (isChoice(type) && question.options.filter((option) => option.trim()).length < 2)
		question.options = ["", ""];
	if (!isChoice(type)) question.options = [];
	if (type === "Consent") question.required = true;
};

const move = (index: number, direction: -1 | 1) =>
	definition.value && moveQuestion(definition.value, index, direction);
const remove = (index: number) => definition.value && removeQuestion(definition.value, index);
const addAStep = () => definition.value && addStep(definition.value, limits.value.steps);
const dropStep = (step: number) => definition.value && removeStep(definition.value, step);

const addAQuestion = () => {
	if (!definition.value) return;
	// a new question goes before the one used as the message (the visitor writes it last), in its step
	const fields = definition.value.fields;
	const messageAt = fields.findIndex((field) => field.role === "Message");
	if (messageAt === -1) {
		fields.push(newQuestion(nextType.value, stepCount.value));
		return;
	}
	fields.splice(messageAt, 0, newQuestion(nextType.value, fields[messageAt].step));
};

const save = async () => {
	const current = definition.value;
	if (!current || saving.value) return;
	if (issues.value.length) {
		toast.error(issues.value[0]);
		return;
	}
	saving.value = true;
	try {
		const result = await saveSiteForm(current);
		definition.value = result;
		saved.value = snapshot(result);
		toast.success(__("{0} saved.", [result.title]));
		emit("saved", result);
		emit("update:modelValue", false);
	} catch (error) {
		// the server holds the form to its rules and says which one it broke
		toast.error(getErrorMessage(error, __("The form could not be saved.")));
	} finally {
		saving.value = false;
	}
};
</script>
