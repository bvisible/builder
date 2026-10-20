//// Neoffice — added file (no upstream equivalent): what the editor knows of the forms of the website.
//
// A form is a record of the theme (`Site Form`): its questions, how it is shown, who is told. Every rule about it
// lives on the server (neoffice_theme/site_forms.py) and is applied there at save; what is here only edits a copy
// in the dialog, keeps the questions and the steps consistent while a person works, and says early what the server
// would refuse. The Builder reaches the record through four endpoints (builder/api.py) that answer
// `{available: false}` where the site keeps no forms (Unpress): the editor then shows nothing about forms.
import { __ } from "@/translation";
import { createResource } from "frappe-ui";
import { ref } from "vue";

export type QuestionType =
	| "Text"
	| "Long text"
	| "Email"
	| "Phone"
	| "Single choice"
	| "Checkboxes"
	| "Date"
	| "Consent";
export type QuestionRole = "" | "Name" | "Email" | "Phone" | "Message";

export type Question = {
	/** a handle for the list while it is edited (a new question has no identifier yet); never sent */
	key?: string;
	/** set by the server from the label when the question is first saved, and kept when the label changes */
	fieldname: string;
	label: string;
	type: QuestionType;
	required: number | boolean;
	step: number;
	/** one choice per element */
	options: string[];
	help: string;
	/** what the answer is used for in the message: who wrote, how to reach them, the text itself */
	role: QuestionRole;
	/** the free zone of a question beyond its type; nothing reads it yet (the file question to come will) */
	settings?: Record<string, unknown>;
};

export type SiteFormDefinition = {
	name: string;
	title: string;
	kind: string;
	profile: string;
	enabled: number | boolean;
	/** one title per step; empty for a form on a single page */
	steps: string[];
	dialog: number | boolean;
	button_text: string;
	submit_text: string;
	success_message: string;
	recipients: string;
	visitor_copy: string;
	fields: Question[];
};

export type FormSummary = { name: string; title: string; kind: string; profile: string; enabled: number };
export type Preset = { key: string; label: string; about: string; steps: number; questions: number };

export type FormsState =
	| { available: false }
	| {
			available: true;
			website_profile: string;
			forms: FormSummary[];
			presets: Preset[];
			kinds: string[];
			field_types: QuestionType[];
			limits: { fields: number; steps: number; choices: number };
	  };

/** The roles a question can hold, and the type each needs: the message is read from these. */
export const ROLE_TYPES: Record<Exclude<QuestionRole, "">, QuestionType> = {
	Name: "Text",
	Email: "Email",
	Phone: "Phone",
	Message: "Long text",
};

export function typeLabel(type: QuestionType): string {
	const labels: Record<QuestionType, string> = {
		Text: __("Short text"),
		"Long text": __("Long text"),
		Email: __("E-mail"),
		Phone: __("Phone"),
		"Single choice": __("One choice"),
		Checkboxes: __("Several choices"),
		Date: __("Date"),
		Consent: __("Consent box"),
	};
	return labels[type] ?? type;
}

export function roleLabel(role: QuestionRole): string {
	const labels: Record<QuestionRole, string> = {
		"": "",
		Name: __("the name"),
		Email: __("the e-mail"),
		Phone: __("the phone"),
		Message: __("the message"),
	};
	return labels[role] ?? role;
}

export const isChoice = (type: QuestionType) => type === "Single choice" || type === "Checkboxes";

// ---- state, shared by the panel and its dialogs -------------------------------------------------------------------

export const siteFormsState = ref<FormsState>({ available: false });
export const siteFormsLoaded = ref(false);

let listing: ReturnType<typeof createResource> | null = null;
let sequence = 0;

/** Ask the server for the forms of the open page's website. The last answer wins. */
export async function loadSiteForms(page: string | null = null): Promise<void> {
	const mine = ++sequence;
	listing ??= createResource({ url: "builder.api.get_site_forms" });
	try {
		const state = (await listing.submit(page ? { page } : {})) as FormsState;
		if (mine === sequence) siteFormsState.value = state?.available ? state : { available: false };
	} catch {
		// the panel works without forms: a failed list is the same as a site that keeps none
		if (mine === sequence) siteFormsState.value = { available: false };
	} finally {
		if (mine === sequence) siteFormsLoaded.value = true;
	}
}

export async function fetchSiteForm(name: string): Promise<SiteFormDefinition> {
	const resource = createResource({ url: "builder.api.get_site_form" });
	return normalised((await resource.submit({ name })) as SiteFormDefinition);
}

export async function createSiteForm(
	preset: string,
	title: string,
	websiteProfile: string,
): Promise<SiteFormDefinition> {
	const resource = createResource({ url: "builder.api.create_site_form" });
	return normalised(
		(await resource.submit({
			preset,
			title: title.trim() || undefined,
			website_profile: websiteProfile || undefined,
		})) as SiteFormDefinition,
	);
}

export async function saveSiteForm(definition: SiteFormDefinition): Promise<SiteFormDefinition> {
	const resource = createResource({ url: "builder.api.save_site_form" });
	return normalised(
		(await resource.submit({
			name: definition.name,
			data: JSON.stringify(payload(definition)),
		})) as SiteFormDefinition,
	);
}

let counter = 0;
const nextKey = () => `q${++counter}`;

/** A definition as the dialog edits it: switches are booleans, every list is a list, each question has a handle. */
export function normalised(definition: SiteFormDefinition): SiteFormDefinition {
	return {
		...definition,
		enabled: Boolean(definition.enabled),
		dialog: Boolean(definition.dialog),
		steps: [...(definition.steps || [])],
		fields: (definition.fields || []).map((field) => ({
			...field,
			key: field.key || nextKey(),
			required: Boolean(field.required),
			options: [...(field.options || [])],
			step: field.step || 1,
		})),
	};
}

/** What is sent on save: the editable parts, nothing the server decides (the identifier, the website). */
export function payload(definition: SiteFormDefinition) {
	return {
		title: definition.title,
		kind: definition.kind,
		enabled: definition.enabled ? 1 : 0,
		steps: definition.steps.map((step) => step.trim()).filter(Boolean),
		dialog: definition.dialog ? 1 : 0,
		button_text: definition.button_text,
		submit_text: definition.submit_text,
		success_message: definition.success_message,
		recipients: definition.recipients,
		visitor_copy: definition.visitor_copy,
		fields: definition.fields.map((field) => ({
			fieldname: field.fieldname,
			label: field.label,
			type: field.type,
			required: field.required ? 1 : 0,
			step: field.step,
			options: field.options.map((option) => option.trim()).filter(Boolean),
			help: field.help,
			role: field.role,
			// kept as the server gave it: this editor has nothing to say about it
			settings: field.settings && Object.keys(field.settings).length ? JSON.stringify(field.settings) : "",
		})),
	};
}

// ---- editing a copy ----------------------------------------------------------------------------------------------

/** How many steps the form has: its titles, at least one (a form on a single page). */
export const stepCount = (definition: SiteFormDefinition) => Math.max(1, definition.steps.length);

/** A new, empty question of `type`, in step `step`. */
export function newQuestion(type: QuestionType, step = 1): Question {
	return {
		key: nextKey(),
		fieldname: "",
		label: "",
		type,
		required: type === "Consent",
		step,
		options: isChoice(type) ? ["", ""] : [],
		help: "",
		role: "",
	};
}

/** Move the question at `index` one place up (-1) or down (+1) within the form. Returns whether it moved. */
export function moveQuestion(definition: SiteFormDefinition, index: number, direction: -1 | 1): boolean {
	const target = index + direction;
	if (index < 0 || target < 0 || index >= definition.fields.length || target >= definition.fields.length) {
		return false;
	}
	const fields = definition.fields;
	[fields[index], fields[target]] = [fields[target], fields[index]];
	return true;
}

/** Remove a question. The question that carries the e-mail cannot go: a message needs someone to answer. */
export function removeQuestion(definition: SiteFormDefinition, index: number): boolean {
	const field = definition.fields[index];
	if (!field || field.role === "Email") return false;
	definition.fields.splice(index, 1);
	return true;
}

/** Add a step at the end. A form on a single page becomes two steps: its questions stay in the first. */
export function addStep(definition: SiteFormDefinition, limit: number): boolean {
	if (stepCount(definition) >= limit) return false;
	if (!definition.steps.length) definition.steps.push(__("Step {0}", [1]));
	definition.steps.push(__("Step {0}", [definition.steps.length + 1]));
	return true;
}

/**
 * Remove a step: its questions join the step before it (the first step joins the one after), and the questions of
 * the steps beyond move up. Removing the second step of two leaves a form on a single page.
 */
export function removeStep(definition: SiteFormDefinition, step: number): boolean {
	const count = stepCount(definition);
	if (count <= 1 || step < 1 || step > count) return false;
	const into = step === 1 ? 1 : step - 1;
	for (const field of definition.fields) {
		if (field.step === step) field.step = into;
		else if (field.step > step) field.step -= 1;
	}
	definition.steps.splice(step - 1, 1);
	if (definition.steps.length === 1) definition.steps = [];
	return true;
}

/** Put a question in a step that exists. */
export function setStep(definition: SiteFormDefinition, index: number, step: number) {
	const field = definition.fields[index];
	if (field) field.step = Math.min(Math.max(1, step), stepCount(definition));
}

/** The questions of a step, in the order they are asked. */
export function questionsOfStep(definition: SiteFormDefinition, step: number): Question[] {
	return definition.fields.filter((field) => field.step === step);
}

/** What the server would refuse, said before it is asked: one sentence for each problem, in the order of the form. */
export function problems(
	definition: SiteFormDefinition,
	limits = { fields: 30, steps: 5, choices: 20 },
): string[] {
	const out: string[] = [];
	if (!definition.title.trim()) out.push(__("Give the form a name."));
	if (!definition.fields.length) out.push(__("A form needs at least one question."));
	if (definition.fields.length > limits.fields) {
		out.push(__("A form has {0} questions at most.", [limits.fields]));
	}
	if (definition.steps.length > limits.steps) {
		out.push(__("A form has {0} steps at most.", [limits.steps]));
	}
	definition.fields.forEach((field, index) => {
		const where = __("Question {0}", [index + 1]);
		if (!field.label.trim()) out.push(`${where}: ${__("write the question.")}`);
		if (isChoice(field.type)) {
			const choices = field.options.map((option) => option.trim()).filter(Boolean);
			if (choices.length < 2) out.push(`${where}: ${__("give at least two choices.")}`);
			if (choices.length > limits.choices) {
				out.push(`${where}: ${__("{0} choices at most.", [limits.choices])}`);
			}
		}
	});
	if (definition.fields.filter((field) => field.role === "Email").length !== 1) {
		out.push(__("A form needs exactly one e-mail question, so that the visitor can be answered."));
	}
	for (let step = 1; step <= stepCount(definition); step++) {
		if (!questionsOfStep(definition, step).length) {
			out.push(__("Step {0} has no question: add one or remove the step.", [step]));
		}
	}
	return out;
}
