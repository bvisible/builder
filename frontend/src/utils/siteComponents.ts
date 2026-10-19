//// Neoffice — added file (no upstream equivalent): what the editor knows of the component catalogue.
//
// The catalogue lives on the server (builder/site_ai/components.py): the generator reads it as its prompt, the
// assistant places a component through it, and this is the human half — the Site blocks panel lists it, a canvas
// block that carries a component's tag draws a card instead of nothing. Everything that WRITES a tag stays on the
// server (builder.api.render_component_tag, which holds the options to what the component declares and to
// `lawful_tag`); what is here only reads, to show.
import { __ } from "@/translation";
import { createResource } from "frappe-ui";
import { ref } from "vue";

export type ParamChoice = { value: string; label: string };

export type Param = {
	name: string;
	label: string;
	type: "str" | "int" | "bool" | string;
	default: unknown;
	about: string;
	choices?: ParamChoice[];
	min?: number;
	max?: number;
	/** an empty text is a choice (no button), not "leave it to the default" */
	blank?: boolean;
};

export type SiteComponent = {
	label: string;
	path: string;
	app: string;
	shows: string;
	pages: string[];
	params: Param[];
	tag: string;
	help: string;
	has_data: boolean | null;
	/** true / false when the open page's type is known, null when nothing is recommended */
	suited: boolean | null;
};

/** What the person typed or ticked, exactly as it was: the options are coerced once, on send. */
export type OptionsForm = { typed: Record<string, string>; flags: Record<string, boolean> };

export const siteComponents = ref<SiteComponent[]>([]);
export const siteComponentsLoaded = ref(false);
export const siteComponentsError = ref("");

// made on first use: a module that only reads tags should not need the resource layer to be imported
let listing: ReturnType<typeof createResource> | null = null;
let inflight: Promise<void> | null = null;
let sequence = 0;

/** Ask the server for the catalogue, as it stands for `page` (the suited ones are flagged). The last answer wins. */
export function loadSiteComponents(page: string | null = null): Promise<void> {
	const mine = ++sequence;
	listing ??= createResource({ url: "builder.api.get_site_components" });
	inflight = listing
		.submit(page ? { page } : {})
		.then((data) => {
			if (mine !== sequence) return;
			siteComponents.value = (data as SiteComponent[]) || [];
			siteComponentsError.value = "";
			siteComponentsLoaded.value = true;
		})
		.catch((error: { messages?: string[]; message?: string }) => {
			if (mine !== sequence) return;
			siteComponentsError.value =
				error?.messages?.[0] || error?.message || __("The components could not be loaded.");
			siteComponentsLoaded.value = true;
		});
	return inflight;
}

/** The catalogue, loaded once for whoever needs the labels (the canvas card); the panel reloads it per page. */
export function ensureSiteComponents(): Promise<void> {
	if (siteComponentsLoaded.value) return Promise.resolve();
	return inflight ?? loadSiteComponents();
}

const SET = /\{%-?\s*set\s+([a-z_][a-z0-9_]*)\s*=\s*(.+?)\s*-?%\}/g;
// the shape a component's tag has: `set` statements, then ONE include of a template of an app's includes folder
const TAG =
	/^\s*(?:\{%-?\s*set\s+[a-z_][a-z0-9_]*\s*=\s*[^%]*?-?%\}\s*)*\{%-?\s*include\s+["']([^"']+\/includes\/[^"']+)["']\s*-?%\}\s*$/;

export type ReadTag = { path: string; values: Record<string, string> };

/**
 * The component a block's text names and the values written on it, for DISPLAY. This is a reading by shape; whether
 * the text is a lawful tag of a catalogued component is the server's answer (builder.api.read_component_tag), asked
 * when a block is selected to be edited.
 */
export function readComponentTag(html: string | null | undefined): ReadTag | null {
	const text = html || "";
	if (!text.includes("{%")) return null;
	const found = TAG.exec(text);
	if (!found) return null;
	const values: Record<string, string> = {};
	for (const [, name, raw] of text.matchAll(SET)) {
		values[name] = raw.replace(/^["']|["']$/g, "");
	}
	return { path: found[1], values };
}

/** "Form: Quote request · Open in a window: yes", the options a tag carries, in the words of the catalogue. */
export function summarize(read: ReadTag, component: SiteComponent | undefined): string {
	const parts: string[] = [];
	for (const [name, value] of Object.entries(read.values)) {
		const param = component?.params.find((p) => p.name === name);
		const label = param?.label || name;
		const shown = param?.choices?.find((c) => c.value === value)?.label ?? readable(param, value);
		parts.push(shown === "" ? `${label}: ∅` : `${label}: ${shown}`);
	}
	return parts.join(" · ");
}

function readable(param: Param | undefined, value: string): string {
	if (param?.type === "bool") return /^true$/i.test(value) ? __("yes") : __("no");
	return value;
}

/** What a tag carries, as a form: text and numbers as typed, booleans as ticked. */
export function formFromValues(
	component: SiteComponent,
	values: Record<string, unknown> | null,
): OptionsForm {
	const form: OptionsForm = { typed: {}, flags: {} };
	for (const param of component.params) {
		if (!values || !(param.name in values)) continue;
		const value = values[param.name];
		if (param.type === "bool") form.flags[param.name] = Boolean(value);
		else form.typed[param.name] = String(value ?? "");
	}
	return form;
}

/**
 * The options to send: only what the person actually set. A blank field is silence (the component's default then
 * applies), except where the component says an empty text means something (`blank`). A number that is not one is sent
 * as typed, so the server refuses it with its own sentence.
 */
export function chosenOptions(component: SiteComponent, form: OptionsForm): Record<string, unknown> {
	const out: Record<string, unknown> = {};
	for (const param of component.params) {
		if (param.type === "bool") {
			if (param.name in form.flags) out[param.name] = form.flags[param.name];
			continue;
		}
		if (!(param.name in form.typed)) continue;
		const value = (form.typed[param.name] ?? "").trim();
		if (!value && !param.blank) continue;
		const number = Number(value);
		out[param.name] = param.type === "int" && value && Number.isFinite(number) ? number : value;
	}
	return out;
}
