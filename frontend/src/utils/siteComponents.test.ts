//// Neoffice — added file (no upstream equivalent): the readers of the editor's component picker.
import { beforeAll, describe, expect, it, vi } from "vitest";
import {
	chosenOptions,
	formFromValues,
	readComponentTag,
	summarize,
	type Param,
	type SiteComponent,
} from "@/utils/siteComponents";

// the translation function reads the catalogue the server booted the page with
beforeAll(() => vi.stubGlobal("window", { translated_messages: {} }));

const FORM = "builder/templates/includes/contact_form.html";

const params: Param[] = [
	{
		name: "contact_model",
		label: "Form",
		type: "str",
		default: "steps",
		about: "",
		choices: [
			{ value: "simple", label: "Simple" },
			{ value: "questions", label: "Quote request" },
		],
	},
	{ name: "contact_dialog", label: "Open in a window", type: "bool", default: false, about: "" },
	{
		name: "contact_button_text",
		label: "Button text",
		type: "str",
		default: "Contact us",
		about: "",
		blank: true,
	},
	{ name: "consent_text", label: "Consent sentence", type: "str", default: "", about: "" },
	{ name: "zoom", label: "Zoom", type: "int", default: 16, about: "", min: 1, max: 20 },
];

const component = { label: "Contact form", path: FORM, params } as SiteComponent;

describe("readComponentTag", () => {
	it("reads the shape the generator writes, newline and Python's True included", () => {
		const read = readComponentTag(
			`{%- set contact_model = "simple" -%}\n{%- set phone_required = True -%}\n{% include "${FORM}" %}`,
		);
		expect(read).toEqual({ path: FORM, values: { contact_model: "simple", phone_required: "True" } });
	});

	it("reads the bare include", () => {
		expect(readComponentTag(`{% include "${FORM}" %}`)).toEqual({ path: FORM, values: {} });
	});

	it("is nothing for any other text", () => {
		for (const text of [
			"",
			null,
			undefined,
			"plain text",
			"{{ frappe.conf }}",
			`hello {% include "${FORM}" %}`,
			`{% include "${FORM}" %}{% include "${FORM}" %}`,
			'{% include "somewhere/else.html" %}',
		]) {
			expect(readComponentTag(text as string)).toBeNull();
		}
	});
});

describe("summarize", () => {
	it("says the options in the words of the catalogue", () => {
		const read = readComponentTag(
			`{%- set contact_model = "questions" -%}{%- set contact_dialog = true -%}{% include "${FORM}" %}`,
		)!;
		expect(summarize(read, component)).toBe("Form: Quote request · Open in a window: yes");
	});

	it("shows an empty text as such, and an option the catalogue does not know by its name", () => {
		const read = readComponentTag(
			`{%- set contact_button_text = "" -%}{%- set old_option = 3 -%}{% include "${FORM}" %}`,
		)!;
		expect(summarize(read, component)).toBe("Button text: ∅ · old_option: 3");
	});
});

describe("chosenOptions", () => {
	it("sends only what was set", () => {
		const form = { typed: { contact_model: "questions" }, flags: { contact_dialog: true } };
		expect(chosenOptions(component, form)).toEqual({ contact_model: "questions", contact_dialog: true });
	});

	it("takes a blank field for silence, except where an empty text is a choice", () => {
		const form = { typed: { consent_text: "  ", contact_button_text: "" }, flags: {} };
		expect(chosenOptions(component, form)).toEqual({ contact_button_text: "" });
	});

	it("sends a number as a number, and what is not one as typed", () => {
		expect(chosenOptions(component, { typed: { zoom: "12" }, flags: {} })).toEqual({ zoom: 12 });
		expect(chosenOptions(component, { typed: { zoom: "twelve" }, flags: {} })).toEqual({ zoom: "twelve" });
	});

	it("keeps an explicit false", () => {
		expect(chosenOptions(component, { typed: {}, flags: { contact_dialog: false } })).toEqual({
			contact_dialog: false,
		});
	});
});

describe("formFromValues", () => {
	it("puts what a tag carries back in the form, and the form sends it back unchanged", () => {
		const values = { contact_model: "questions", contact_dialog: true, contact_button_text: "", zoom: 12 };
		const form = formFromValues(component, values);
		expect(form).toEqual({
			typed: { contact_model: "questions", contact_button_text: "", zoom: "12" },
			flags: { contact_dialog: true },
		});
		expect(chosenOptions(component, form)).toEqual(values);
	});

	it("is an empty form for a block written by hand", () => {
		expect(formFromValues(component, null)).toEqual({ typed: {}, flags: {} });
	});
});
