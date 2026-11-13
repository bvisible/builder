//// Neoffice — added file (no upstream equivalent). The Chat tab draws Nora's one conversation, nora.chat.Core of
//// the app nora: the desk's pages that talk with Nora share it, so that what improves it improves them all (Jérémy,
//// 13.11: « quand on améliore le chat on améliore partout »). The editor is no desk, so this loads that
//// conversation's files at run time, as NeoCockpitBridge loads the cockpit, after giving them the little of frappe
//// they use. That list is held on nora's side (nora/tests/test_nora_chat_core_runs_outside_the_desk.py): widen both
//// together. Where nora is not installed, or a file does not load, the tab stays upstream's panel.
import { toast } from "frappe-ui";

/** What the boot says of Nora's conversation (builder/www/_builder.py, nora_chat_boot); null without nora. */
export type NoraChatBoot = {
	jquery: string;
	styles: string[];
	scripts: string[];
	lang: string;
};

declare global {
	interface Window {
		nora_chat?: NoraChatBoot | null;
		nora?: any;
		jQuery?: any;
		frappe?: any;
	}
}

export const noraChatBoot = (): NoraChatBoot | null => window.nora_chat || null;

/** Whether the Chat tab draws Nora's conversation (else upstream's panel). */
export const hasNoraChat = (): boolean => Boolean(noraChatBoot()?.scripts?.length);

function cookie(name: string): string {
	const found = document.cookie.split("; ").find((row) => row.startsWith(`${name}=`));
	return found ? decodeURIComponent(found.slice(name.length + 1).replace(/^"|"$/g, "")) : "";
}

const ESCAPES: Record<string, string> = {
	"&": "&amp;",
	"<": "&lt;",
	">": "&gt;",
	'"': "&quot;",
	"'": "&#39;",
};

/** The little of frappe the conversation and the desk's entry use, where the page has no frappe of its own. Only
 * what is missing is set: the cockpit (NeoCockpitBridge) may already have put a frappe.boot here. */
function provideDesk(boot: NoraChatBoot) {
	const frappe = (window.frappe = window.frappe || {});
	frappe.provide =
		frappe.provide ||
		((namespace: string) =>
			namespace.split(".").reduce((scope: any, key: string) => (scope[key] = scope[key] || {}), window));
	frappe.utils = frappe.utils || {};
	frappe.utils.escape_html =
		frappe.utils.escape_html ||
		((text: unknown) => String(text ?? "").replace(/[&<>"']/g, (c) => ESCAPES[c]));
	if (!("csrf_token" in frappe))
		Object.defineProperty(frappe, "csrf_token", { get: () => (window as any).csrf_token || "" });
	frappe.msgprint = frappe.msgprint || ((message: unknown) => toast.error(String(message ?? "")));
	frappe.show_alert =
		frappe.show_alert ||
		((alert: { message?: string } | string) =>
			toast.info(typeof alert === "string" ? alert : String(alert?.message ?? "")));
	frappe.session = frappe.session || { user: cookie("user_id"), user_fullname: cookie("full_name") };
	frappe.user_info = frappe.user_info || (() => ({}));
	frappe.get_abbr =
		frappe.get_abbr ||
		((name: string) =>
			String(name || "")
				.split(/\s+/)
				.map((word) => word[0] || "")
				.join("")
				.slice(0, 2));
	// the desk's entry dictates where Nora runs (neoffice_activity.can_dictate reads boot.versions.nora)
	frappe.boot = frappe.boot || {};
	frappe.boot.lang = frappe.boot.lang || boot.lang;
	frappe.boot.versions = { ...(frappe.boot.versions || {}), nora: frappe.boot.versions?.nora || "1" };
}

function loadScript(src: string): Promise<void> {
	return new Promise((resolve, reject) => {
		const base = src.split("?")[0];
		const existing = document.querySelector<HTMLScriptElement>(`script[data-nora-chat="${base}"]`);
		if (existing) {
			if (existing.dataset.loaded) return resolve();
			existing.addEventListener("load", () => resolve());
			existing.addEventListener("error", () => reject(new Error(`${base} did not load`)));
			return;
		}
		const script = document.createElement("script");
		script.src = src;
		script.dataset.noraChat = base;
		script.onload = () => {
			script.dataset.loaded = "1";
			resolve();
		};
		script.onerror = () => reject(new Error(`${base} did not load`));
		document.head.appendChild(script);
	});
}

function loadStyle(href: string) {
	const base = href.split("?")[0];
	if (document.querySelector(`link[data-nora-chat="${base}"]`)) return;
	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href = href;
	link.dataset.noraChat = base;
	document.head.appendChild(link);
}

let loading: Promise<any> | null = null;

/** nora.chat.Core, once its files are in (they load once per page). Rejects when one does not load. */
export function loadNoraChat(): Promise<any> {
	const boot = noraChatBoot();
	if (!boot) return Promise.reject(new Error("nora is not installed"));
	if (loading) return loading;
	loading = (async () => {
		provideDesk(boot);
		boot.styles.forEach(loadStyle);
		if (!window.jQuery) await loadScript(boot.jquery);
		// in order: the desk's entry, then the conversation, which looks for it when it draws its own
		for (const src of boot.scripts) await loadScript(src);
		const Core = window.nora?.chat?.Core;
		if (!Core) throw new Error("nora.chat.Core is missing");
		// a nora older than the editor's tab (its version 9, 13.11): upstream's panel, rather than a broken one
		const needs = ["slot", "showWelcome", "hideWelcome", "setUploadEnabled", "attachFile"];
		if (
			needs.some((name) => typeof Core.prototype[name] !== "function") ||
			typeof window.nora.chat.doing !== "function"
		)
			throw new Error("nora.chat.Core is older than the editor's tab");
		return Core;
	})();
	loading.catch(() => (loading = null));
	return loading;
}
