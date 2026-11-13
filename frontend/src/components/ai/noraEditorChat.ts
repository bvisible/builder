//// Neoffice — added file (no upstream equivalent). What the Chat tab shows of the editor's conversation, drawn by
//// Nora's one conversation (nora.chat.Core, see utils/noraChatHost.ts). The controller (AIChatController) keeps the
//// conversation as data and runs the turns, unchanged; this turns its messages into the calls of the conversation,
//// and keeps them in step as they stream (NoraEditorChat.vue watches the controller and calls `paint`). No Vue here:
//// the painter is plain, so it can be tried on its own.
import { __ } from "@/translation";
import { cardAnswers } from "@/components/ai/cardAnswers";
import type { AffectedBlock, AffectedScript, AITurnStep, ChatMessage } from "@/components/ai/types";

/** What the painter needs of the page around it (the editor's state, the assistant's name). */
export type PaintContext = {
	assistant: string;
	/** a turn of this tab is running */
	working: boolean;
	/** Stop was asked: the pill says it, the answer waits (the controller writes « Cancelling… » there) */
	cancelling: boolean;
	/** the canvas shows the page (not a component): what Nora edits */
	editingPage: boolean;
	/** the page has changes visitors do not see yet */
	pageHasDraft: boolean;
	/** a block still on the canvas (a removed one has nothing to select) */
	blockExists: (id: string) => boolean;
	/** what a block says on the canvas, for a block without a name (its words, its image) */
	blockLabel: (id: string) => string;
	/** « Inspect this turn » (Administrator, developer mode) */
	inspect: boolean;
};

// ─────────────── the messages, as the upstream panel shows them ───────────────

/** A card that reads back every answer makes the reply under it a second copy of itself: the card is the record
 * (upstream's rule, BuilderAIChatPanel.vue). */
export function visibleMessages(messages: ChatMessage[]): ChatMessage[] {
	return messages.filter((message, i) => {
		if (message.role !== "user") return true;
		const card = messages[i - 1]?.metadata;
		if (card?.status !== "ui" || !card?.ui?.length) return true;
		return !cardAnswers(card.ui, message.content, card.text).length;
	});
}

/** The reply a card was answered with: the person's message right after it. */
export function replyTo(messages: ChatMessage[], message: ChatMessage): string {
	const next = messages[messages.findIndex((m) => m.id === message.id) + 1];
	return next?.role === "user" ? next.content : "";
}

/** The fields as the person would name them (« Name, Email, Message »). */
function fieldNames(fields: any[]): string {
	return (fields || [])
		.map((f) => f?.label || f?.fieldname)
		.filter(Boolean)
		.join(", ");
}

/** A sensitive action Nora proposes, said as its question (upstream's pendingPreview, same strings). */
export function pendingQuestion(meta: Record<string, any>): string {
	const p = meta.payload || {};
	const fields = fieldNames(p.fields);
	switch (meta.kind) {
		case "create_doctype":
			return __("Create “{0}” to store this page's data{1}.", [p.name, fields ? ` (${fields})` : ""]);
		case "connect_form":
			return __("Save this form's submissions as “{0}” records{1}.", [
				p.doctype_name,
				fields ? ` (${fields})` : "",
			]);
		case "seed_sample_data": {
			const n = (p.rows || []).length;
			return n === 1
				? __("Add {0} sample record to “{1}”.", [n, p.doctype])
				: __("Add {0} sample records to “{1}”.", [n, p.doctype]);
		}
		case "global_settings":
			return __("Update site-wide code ({0}). This loads on every page.", [Object.keys(p).join(", ")]);
		case "home_page":
			return __("Make “/{0}” the site's home page.", [String(p.route || "").replace(/^\//, "")]);
		default:
			return __("Confirm this change?");
	}
}

/** The button names what it does (upstream's applyLabel, same strings). */
export function applyLabel(kind?: string): string {
	const labels: Record<string, string> = {
		create_doctype: __("Create it"),
		connect_form: __("Connect form"),
		seed_sample_data: __("Add records"),
		home_page: __("Set home page"),
		global_settings: __("Apply"),
	};
	return labels[kind || ""] || __("Apply");
}

/** Nora's words of a message: a card's lead-in, a pending action's question, a stopped turn said as such. */
export function assistantText(message: ChatMessage, cancelling = false): string {
	const meta = message.metadata || {};
	// a sensitive action is said as its question, asked or decided (its content is the model's summary, in English)
	if (["pending_action", "action_skipped", "action_applied"].includes(meta.status) && meta.kind)
		return pendingQuestion(meta);
	if (message.message_type === "status" && message.content === "Skipped. Nothing was changed.")
		return __("Skipped. Nothing was changed.");
	// a stopped turn is said as the Website space's tab says it (the stored answer is English)
	if (meta.status === "cancelled") return __("Stopped. What was done so far is kept.");
	if (cancelling && meta.status === "running") return "";
	if (meta.status === "ui") return meta.text ?? message.content;
	return message.content || "";
}

// ─────────────── what she changed ───────────────

// The short words of what changed carry a context of their own: a bare « text » or « look » is another app's word
// on the desk, and the editor carries only Builder's catalogue (with the cockpit's), not the desk's.
const SAID = "Nora's answer";

/** What changed in a block, said for a person (the tools record CSS and attribute names). */
export function changedWords(props: string[]): string {
	const words = new Set<string>();
	for (const raw of props || []) {
		const prop = String(raw);
		const bare = prop.replace(/^[mt]:/, "");
		if (prop === "text" || prop === "html") words.add(__("text", [], SAID));
		else if (prop === "removed") words.add(__("removed", [], SAID));
		else if (prop === "moved") words.add(__("moved", [], SAID));
		else if (prop.startsWith("added")) words.add(__("content added", [], SAID));
		else if (["src", "srcset", "alt"].includes(bare)) words.add(__("photo", [], SAID));
		else if (["href", "target"].includes(bare)) words.add(__("link", [], SAID));
		else if (prop.startsWith("m:")) words.add(__("look on a phone", [], SAID));
		else if (prop.startsWith("t:")) words.add(__("look on a tablet", [], SAID));
		else if (["element", "classes", "props", "client_script"].includes(prop))
			words.add(__("content", [], SAID));
		else words.add(__("look", [], SAID));
	}
	return capitalized([...words].join(" · "));
}

function capitalized(word: string): string {
	return word ? word.charAt(0).toUpperCase() + word.slice(1) : "";
}

/** What kind of block it is, in a word (no word for a plain container). */
export function elementWord(element?: string): string {
	const tag = String(element || "").toLowerCase();
	if (tag === "section") return __("section", [], SAID);
	if (tag === "button" || tag === "a") return __("button", [], SAID);
	if (tag === "img" || tag === "picture") return __("photo", [], SAID);
	if (/^h[1-6]$/.test(tag)) return __("title", [], SAID);
	if (["p", "span", "li"].includes(tag)) return __("text", [], SAID);
	if (tag === "form") return __("form", [], SAID);
	return "";
}

export type Card = {
	icon: string;
	title: string;
	meta?: string;
	lines?: string[];
	pill?: { tone: string; label: string };
	buttons?: { label: string; value: string; icon?: string; primary?: boolean }[];
};

export type Cards = {
	cards: Card[];
	title?: string;
	footer: { label: string; value: string; icon?: string; primary?: boolean; disabled?: boolean }[];
	note?: string;
};

/** The cards under a turn: one per block or script it changed, then going back (and the inspector). */
export function changeCards(message: ChatMessage, isLast: boolean, ctx: PaintContext): Cards | null {
	const meta = message.metadata || {};
	const footer: Cards["footer"] = [];
	// a sensitive action waits for the person, on the last message only (upstream's rule)
	if (meta.status === "pending_action") {
		if (!isLast) return null;
		return {
			cards: [],
			footer: [
				{ label: applyLabel(meta.kind), value: "apply", primary: true, disabled: !ctx.editingPage },
				{ label: __("No"), value: "skip", disabled: !ctx.editingPage },
			],
		};
	}
	const blocks: AffectedBlock[] = meta.affectedBlocks || [];
	const scripts: AffectedScript[] = meta.affectedScripts || [];
	const pill = ctx.pageHasDraft
		? { tone: "warn", label: __("Draft") }
		: { tone: "success", label: __("Online", [], "Website") };
	const cards: Card[] = [
		...blocks.map((block) => {
			const here = ctx.blockExists(block.block_id);
			// a block the agent did not name is said by its words on the canvas (« <p> » says nothing)
			// the page's root (« body »): what was added to the page itself
			const root = block.blockName === "body" || block.element === "body";
			const label = root
				? __("The whole page", [], SAID)
				: block.blockName || (here ? ctx.blockLabel(block.block_id) : "");
			return {
				icon: "block",
				title: label || capitalized(elementWord(block.element)) || __("Block", [], SAID),
				meta: label && !root ? elementWord(block.element) : "",
				lines: [changedWords(block.changedProps)].filter(Boolean),
				pill: here ? pill : { tone: "muted", label: __("Removed", [], SAID) },
				buttons:
					here && !root ? [{ label: __("Select"), value: `block:${block.block_id}`, icon: "pointer" }] : [],
			};
		}),
		...scripts.map((script) => ({
			icon: "code",
			title: script.script_name,
			meta: __("script", [], SAID),
			lines: [],
			buttons: [{ label: __("Open the script"), value: `script:${script.script_name}`, icon: "code" }],
		})),
	];
	if (meta.revertSnapshot)
		footer.push({
			label: __("Go back", [], "Nora's answer"),
			value: "revert",
			icon: "undo",
			disabled: ctx.working || !ctx.editingPage,
		});
	if (ctx.inspect && meta.debug) footer.push({ label: __("Inspect this turn"), value: "inspect" });
	if (!cards.length && !footer.length) return null;
	return {
		cards,
		title: cards.length ? __("What {0} changed", [ctx.assistant]) : undefined,
		footer,
		note: cards.length && ctx.pageHasDraft ? __("Visitors see it once the page is published.") : undefined,
	};
}

// ─────────────── the painter ───────────────

type Row = { role: string; coreId: number; sig: string; message: ChatMessage };

/** Keeps nora.chat.Core in step with the controller's messages: the rows that still match are updated in place
 * (an answer as it streams, its steps, its cards), the first that does not and everything after it are drawn
 * again (another conversation, a turn taken back). */
export class Painter {
	rows: Row[] = [];
	constructor(private core: any) {}

	reset() {
		this.core.clearMessages();
		this.rows = [];
	}

	/** The message a row of the conversation stands for (its id in nora.chat.Core). */
	messageOf(coreId: number): ChatMessage | undefined {
		return this.rows.find((row) => row.coreId === coreId)?.message;
	}

	paint(all: ChatMessage[], ctx: PaintContext) {
		const list = visibleMessages(all);
		const lastId = all.at(-1)?.id;
		let i = 0;
		for (; i < list.length && i < this.rows.length; i++) {
			const message = list[i];
			const row = this.rows[i];
			if (row.role !== message.role) break;
			const sig = this.signature(all, message, message.id === lastId, ctx);
			if (message.role === "user" && sig !== row.sig) break;
			row.message = message;
			if (sig === row.sig) continue;
			this.drawAssistant(row.coreId, all, message, message.id === lastId, ctx);
			row.sig = sig;
		}
		for (const row of this.rows.splice(i)) this.core.removeMessage(row.coreId);
		for (; i < list.length; i++) {
			const message = list[i];
			const isLast = message.id === lastId;
			const coreId =
				message.role === "user" ? this.addUser(message) : this.addAssistant(all, message, isLast, ctx);
			this.rows.push({ role: message.role, coreId, sig: this.signature(all, message, isLast, ctx), message });
		}
	}

	private signature(all: ChatMessage[], message: ChatMessage, isLast: boolean, ctx: PaintContext): string {
		const meta = message.metadata || {};
		if (message.role === "user")
			return JSON.stringify([
				meta.displayText || message.content,
				meta.selectedBlockContext,
				meta.attachedImageUrl,
			]);
		return JSON.stringify([
			assistantText(message, isLast && ctx.cancelling),
			(meta.steps || []).map((s: AITurnStep) => [
				s.id,
				s.status,
				s.summary,
				s.ms,
				s.kind === "text" ? s.text : "",
			]),
			meta.status,
			meta.ui?.length ? [meta.ui, replyTo(all, message)] : null,
			meta.affectedBlocks,
			meta.affectedScripts,
			Boolean(meta.revertSnapshot),
			Boolean(meta.debug),
			isLast,
			ctx.working,
			ctx.editingPage,
			ctx.pageHasDraft,
			(meta.affectedBlocks || []).map((b: AffectedBlock) => [
				ctx.blockExists(b.block_id),
				ctx.blockLabel(b.block_id),
			]),
		]);
	}

	private addUser(message: ChatMessage): number {
		const meta = message.metadata || {};
		return this.core.addMessage("user", meta.displayText || message.content, {
			attachment: meta.attachedImageUrl || null,
			chips: (meta.selectedBlockContext || []).map((block: { id: string; label: string }) => ({
				label: block.label,
				value: `block:${block.id}`,
			})),
		});
	}

	private addAssistant(all: ChatMessage[], message: ChatMessage, isLast: boolean, ctx: PaintContext): number {
		const coreId = this.core.addMessage("assistant", "");
		this.drawAssistant(coreId, all, message, isLast, ctx);
		return coreId;
	}

	private drawAssistant(
		coreId: number,
		all: ChatMessage[],
		message: ChatMessage,
		isLast: boolean,
		ctx: PaintContext,
	) {
		const meta = message.metadata || {};
		this.core.setMessageText(coreId, assistantText(message, isLast && ctx.cancelling));
		this.core.setSteps(coreId, meta.steps || []);
		if (meta.status === "ui" && meta.ui?.length) {
			this.core.setForm(coreId, meta.ui, {
				answered_with: replyTo(all, message),
				lead: meta.text,
				disabled: !isLast || ctx.working || !ctx.editingPage,
			});
		} else {
			this.core.message(coreId).find(".nora-chat-form").remove();
		}
		const cards = changeCards(message, isLast, ctx);
		this.core.setCards(coreId, cards?.cards || [], {
			title: cards?.title,
			footer: cards?.footer || [],
			note: cards?.note,
		});
	}
}
