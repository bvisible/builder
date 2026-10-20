//// Neoffice — added file (no upstream equivalent): the editing rules of the forms of the website.
import { beforeAll, describe, expect, it, vi } from "vitest";
import {
	addStep,
	moveQuestion,
	newQuestion,
	normalised,
	payload,
	problems,
	questionsOfStep,
	removeQuestion,
	removeStep,
	setStep,
	stepCount,
	type Question,
	type SiteFormDefinition,
} from "@/utils/siteForms";

// the endpoints are not under test, only the rules of editing: frappe-ui's resource layer is not loaded
vi.mock("frappe-ui", () => ({ createResource: vi.fn() }));

// the translation function reads the catalogue the server booted the page with
beforeAll(() => vi.stubGlobal("window", { translated_messages: {} }));

const question = (over: Partial<Question>): Question => ({
	fieldname: "",
	label: "Question",
	type: "Text",
	required: false,
	step: 1,
	options: [],
	help: "",
	role: "",
	...over,
});

const quote = (): SiteFormDefinition => ({
	name: "quote",
	title: "Quote request",
	kind: "Quote",
	profile: "",
	enabled: true,
	steps: ["About you", "Your request"],
	dialog: false,
	button_text: "",
	submit_text: "",
	success_message: "",
	recipients: "",
	visitor_copy: "",
	fields: [
		question({ fieldname: "full_name", label: "Name", role: "Name", required: true }),
		question({ fieldname: "sender", label: "Email", type: "Email", role: "Email", required: true }),
		question({
			fieldname: "budget",
			label: "Budget",
			type: "Single choice",
			options: ["Under 1,000", "Over 5,000"],
			step: 2,
		}),
		question({ fieldname: "message", label: "Message", type: "Long text", role: "Message", step: 2 }),
	],
});

describe("moving questions", () => {
	it("moves a question up and down within the form", () => {
		const form = quote();
		expect(moveQuestion(form, 3, -1)).toBe(true);
		expect(form.fields.map((f) => f.fieldname)).toEqual(["full_name", "sender", "message", "budget"]);
		expect(moveQuestion(form, 2, 1)).toBe(true);
		expect(form.fields[3].fieldname).toBe("message");
	});

	it("does not move past either end", () => {
		const form = quote();
		expect(moveQuestion(form, 0, -1)).toBe(false);
		expect(moveQuestion(form, 3, 1)).toBe(false);
		expect(moveQuestion(form, 9, -1)).toBe(false);
		expect(form.fields.map((f) => f.fieldname)[0]).toBe("full_name");
	});
});

describe("removing a question", () => {
	it("removes an ordinary question", () => {
		const form = quote();
		expect(removeQuestion(form, 2)).toBe(true);
		expect(form.fields.some((f) => f.fieldname === "budget")).toBe(false);
	});

	it("keeps the e-mail question: a message needs someone to answer", () => {
		const form = quote();
		expect(removeQuestion(form, 1)).toBe(false);
		expect(form.fields).toHaveLength(4);
	});
});

describe("steps", () => {
	it("counts at least one step", () => {
		const form = quote();
		form.steps = [];
		expect(stepCount(form)).toBe(1);
		form.steps = ["a", "b", "c"];
		expect(stepCount(form)).toBe(3);
	});

	it("turns a single page into two steps, the questions staying in the first", () => {
		const form = quote();
		form.steps = [];
		form.fields.forEach((f) => (f.step = 1));
		expect(addStep(form, 5)).toBe(true);
		expect(form.steps).toHaveLength(2);
		expect(questionsOfStep(form, 2)).toHaveLength(0);
		expect(problems(form).join(" ")).toMatch(/Step 2 has no question/);
	});

	it("stops at the limit", () => {
		const form = quote();
		form.steps = ["1", "2", "3", "4", "5"];
		expect(addStep(form, 5)).toBe(false);
	});

	it("removing a step moves its questions to the step before it", () => {
		const form = quote();
		form.steps = ["One", "Two", "Three"];
		form.fields[3].step = 3;
		expect(removeStep(form, 2)).toBe(true);
		expect(form.steps).toEqual(["One", "Three"]);
		// the budget was in step 2: it joins step 1; the message was in step 3, now step 2
		expect(form.fields.find((f) => f.fieldname === "budget")?.step).toBe(1);
		expect(form.fields.find((f) => f.fieldname === "message")?.step).toBe(2);
	});

	it("removing the first step gives its questions to the one that follows", () => {
		const form = quote();
		removeStep(form, 1);
		expect(form.steps).toEqual([]);
		expect(new Set(form.fields.map((f) => f.step))).toEqual(new Set([1]));
	});

	it("removing the second of two steps leaves a single page", () => {
		const form = quote();
		expect(removeStep(form, 2)).toBe(true);
		expect(form.steps).toEqual([]);
		expect(stepCount(form)).toBe(1);
		expect(problems(form)).toEqual([]);
	});

	it("will not remove the only step", () => {
		const form = quote();
		form.steps = [];
		expect(removeStep(form, 1)).toBe(false);
	});

	it("puts a question in a step that exists", () => {
		const form = quote();
		setStep(form, 0, 9);
		expect(form.fields[0].step).toBe(2);
		setStep(form, 0, 0);
		expect(form.fields[0].step).toBe(1);
	});
});

describe("what the server would refuse", () => {
	it("accepts a well-formed form", () => {
		expect(problems(quote())).toEqual([]);
	});

	it("wants a name, a question and a label for each", () => {
		const form = quote();
		form.title = " ";
		form.fields[2].label = "";
		expect(problems(form)).toHaveLength(2);
		form.fields = [];
		expect(problems(form).join(" ")).toMatch(/at least one question/);
	});

	it("wants two choices for a question of choices", () => {
		const form = quote();
		form.fields[2].options = ["Only one", " "];
		expect(problems(form).join(" ")).toMatch(/at least two choices/);
	});

	it("wants exactly one e-mail question", () => {
		const form = quote();
		form.fields = form.fields.filter((f) => f.role !== "Email");
		expect(problems(form).join(" ")).toMatch(/exactly one e-mail question/);
	});

	it("wants a question in every step", () => {
		const form = quote();
		form.fields.forEach((f) => (f.step = 1));
		expect(problems(form).join(" ")).toMatch(/Step 2 has no question/);
	});
});

describe("new questions", () => {
	it("a choice question starts with two empty choices, a consent box is required", () => {
		expect(newQuestion("Single choice").options).toEqual(["", ""]);
		expect(newQuestion("Text").options).toEqual([]);
		expect(newQuestion("Consent").required).toBe(true);
		expect(newQuestion("Text", 2).step).toBe(2);
	});
});

describe("what is sent", () => {
	it("sends the editable parts as numbers and clean lists, and nothing the server decides", () => {
		const form = quote();
		form.fields[2].options = [" Under 1,000 ", "", "Over 5,000"];
		form.steps = ["One", " ", "Two"];
		const sent = payload(form);
		expect(sent.enabled).toBe(1);
		expect(sent.dialog).toBe(0);
		expect(sent.steps).toEqual(["One", "Two"]);
		expect(sent.fields[2].options).toEqual(["Under 1,000", "Over 5,000"]);
		expect(sent.fields[1].required).toBe(1);
		expect(sent).not.toHaveProperty("name");
		expect(sent).not.toHaveProperty("profile");
	});

	it("reads a definition into booleans and lists", () => {
		const raw = { ...quote(), enabled: 1, dialog: 0 } as unknown as SiteFormDefinition;
		const form = normalised(raw);
		expect(form.enabled).toBe(true);
		expect(form.dialog).toBe(false);
		expect(form.fields[0].required).toBe(true);
	});
});
