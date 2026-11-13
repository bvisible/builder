//// Neoffice — added file (no upstream equivalent). What the cards to validate of Nora's conversation (nora_chat_cards.js
//// of the app nora, a module of the one conversation, 13.11) use of the desk, where the editor has no desk: a call to the
//// server, a desk page (opened in a new tab, the way the desk opens one with its options), a field's type, the defaults,
//// how the desk writes a figure, an amount and a date, and its charts. noraChatHost.ts gives them to the conversation
//// with the rest of its seam; nora's test of the seam holds the same list: widen them together. Only what is missing
//// is set.
import { toast } from "frappe-ui";

import { __ } from "@/translation";

/** The desk's defaults the cards read (builder/www/_builder.py, desk_defaults). */
export type NoraChatDesk = {
	defaults: Record<string, string | number | null>;
	currency: { name: string; symbol?: string; symbol_on_right?: number; number_format?: string } | null;
};

type CallOptions = {
	method: string;
	args?: Record<string, unknown>;
	callback?: (r: any) => void;
	error?: (r: any) => void;
};

/** The first of the messages the server said with its answer, as text. */
function serverMessage(r: any): string {
	try {
		const first = JSON.parse(r?._server_messages || "[]")[0];
		const text = typeof first === "string" ? JSON.parse(first).message : "";
		return String(text || "").replace(/<[^>]*>/g, "");
	} catch {
		return "";
	}
}

/** frappe.call: the method, its arguments as a form, the callback with the answer, `error` (or the server's word) else. */
function call(frappe: any, options: CallOptions | string, args?: Record<string, unknown>): Promise<any> {
	const opts: CallOptions = typeof options === "string" ? { method: options, args } : options;
	const body = new URLSearchParams();
	Object.entries(opts.args || {}).forEach(([key, value]) => {
		if (value === undefined || value === null) return;
		body.append(key, typeof value === "object" ? JSON.stringify(value) : String(value));
	});
	const done = fetch(`/api/method/${opts.method}`, {
		method: "POST",
		headers: {
			"X-Frappe-CSRF-Token": frappe.csrf_token,
			Accept: "application/json",
			"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
		},
		body,
		credentials: "same-origin",
	}).then(async (response) => {
		const r = await response.json().catch(() => ({}));
		if (!response.ok || r.exc) {
			if (opts.error) opts.error(r);
			else frappe.msgprint(serverMessage(r) || __("Something went wrong"));
			throw Object.assign(new Error(`${opts.method}: HTTP ${response.status}`), { response: r });
		}
		opts.callback?.(r);
		return r;
	});
	// a caller that only gives callbacks leaves no rejection unhandled
	done.catch(() => {});
	return done;
}

const slug = (name: string) => String(name).toLowerCase().replace(/ /g, "-");

/** The desk's address of a route, as frappe.router writes it (["List", "Item"] → /app/item, ["Form", "Item", "x"] →
 * /app/item/x, "app/x/y" as it is). */
export function deskUrl(route: unknown[]): string {
	const parts = (route.length === 1 && Array.isArray(route[0]) ? route[0] : route).filter(
		(part) => part !== undefined && part !== null && typeof part !== "object",
	) as string[];
	if (parts.length === 1 && String(parts[0]).includes("/")) {
		const path = String(parts[0]).replace(/^\/+/, "");
		return path.startsWith("app/") ? `/${path}` : `/app/${path}`;
	}
	const view = String(parts[0] || "").toLowerCase();
	let path: string[] = parts.map(String);
	if (view === "list") {
		path =
			parts[2] && String(parts[2]).toLowerCase() !== "list"
				? [slug(parts[1]), "view", String(parts[2]).toLowerCase()]
				: [slug(parts[1])];
	} else if (view === "form") {
		path = parts[2] ? [slug(parts[1]), String(parts[2])] : [slug(parts[1])];
	} else if (view === "tree") {
		path = [slug(parts[1]), "view", "tree"];
	}
	return `/app/${path.map((part) => encodeURIComponent(part)).join("/")}`;
}

/** A desk page, in a new tab: its options travel as the desk's own new tab carries them (localStorage route_options,
 * read by frappe.router when the page opens). */
function setRoute(frappe: any, ...route: unknown[]) {
	const flat = route.length === 1 && Array.isArray(route[0]) ? route[0] : route;
	const options = flat.find((part) => part && typeof part === "object" && !Array.isArray(part));
	if (options) frappe.route_options = options;
	try {
		if (frappe.route_options) localStorage.setItem("route_options", JSON.stringify(frappe.route_options));
	} catch {
		/* the page opens without its options */
	}
	frappe.route_options = null;
	window.open(deskUrl(route), "_blank", "noopener");
	return Promise.resolve();
}

// frappe.number_format_info (frappe/public/js/frappe/utils/number_format.js)
const NUMBER_FORMATS: Record<string, { decimal_str: string; group_sep: string }> = {
	"#,###.##": { decimal_str: ".", group_sep: "," },
	"#.###,##": { decimal_str: ",", group_sep: "." },
	"# ###.##": { decimal_str: ".", group_sep: " " },
	"# ###,##": { decimal_str: ",", group_sep: " " },
	"#'###.##": { decimal_str: ".", group_sep: "'" },
	"#, ###.##": { decimal_str: ".", group_sep: ", " },
	"#,##,###.##": { decimal_str: ".", group_sep: "," },
	"#,###.###": { decimal_str: ".", group_sep: "," },
	"#.###": { decimal_str: "", group_sep: "." },
	"#,###": { decimal_str: "", group_sep: "," },
};

/** format_number of the desk: the figure in the site's number format (« 18'957.00 »). */
export function formatNumber(
	desk: NoraChatDesk,
	value: unknown,
	format?: string | null,
	decimals?: number | null,
) {
	if (!format) {
		format = String(desk.defaults.number_format || "#,###.##");
		if (decimals == null) decimals = Number(desk.defaults.float_precision) || 3;
	}
	const info = NUMBER_FORMATS[format] || { decimal_str: ".", group_sep: "," };
	const precision = info.decimal_str ? (format.split(info.decimal_str)[1] || "").length : 0;
	const places = decimals == null ? precision : decimals;
	const number = Number(value) || 0;
	const [whole, fraction] = Math.abs(number).toFixed(places).split(".");
	// the Indian format groups by three, then by two
	const indian = format === "#,##,###.##";
	let grouped = whole;
	if (info.group_sep) {
		const head = indian ? whole.slice(0, -3) : whole;
		const tail = indian ? whole.slice(-3) : "";
		const size = indian ? 2 : 3;
		const groups: string[] = [];
		for (let end = head.length; end > 0; end -= size)
			groups.unshift(head.slice(Math.max(0, end - size), end));
		grouped = [...groups.filter(Boolean), ...(tail ? [tail] : [])].join(info.group_sep) || "0";
	}
	// as the desk: a figure that rounds to nothing has no sign
	const sign = number < 0 && Number(Math.abs(number).toFixed(places)) !== 0 ? "-" : "";
	return sign + grouped + (fraction && info.decimal_str ? info.decimal_str + fraction : "");
}

/** format_currency of the desk: the default currency's symbol on its side, its number format where the site says so. */
export function formatCurrency(
	desk: NoraChatDesk,
	value: unknown,
	currency?: string | null,
	decimals?: number | null,
) {
	const name = currency || String(desk.defaults.currency || "");
	const known = desk.currency && desk.currency.name === name ? desk.currency : null;
	const format =
		(Number(desk.defaults.use_number_format_from_currency) && known?.number_format) ||
		String(desk.defaults.number_format || "#,###.##");
	if (decimals === undefined)
		decimals = desk.defaults.currency_precision ? Number(desk.defaults.currency_precision) : null;
	const figure = formatNumber(desk, value, format, decimals);
	const symbol = desk.defaults.hide_currency_symbol === "Yes" ? "" : known?.symbol || name;
	if (!symbol) return figure;
	return known?.symbol_on_right ? `${figure} ${__(symbol)}` : `${__(symbol)} ${figure}`;
}

/** frappe.datetime.str_to_user of the desk: a date of the server (yyyy-mm-dd) as the site writes dates. */
export function dateToUser(desk: NoraChatDesk, value: unknown) {
	const found = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""));
	if (!found) return String(value || "");
	const [, year, month, day] = found;
	return String(desk.defaults.date_format || "dd-mm-yyyy")
		.replace("yyyy", year)
		.replace("mm", month)
		.replace("dd", day);
}

/** The doctypes the cards asked for, by name (frappe.model.with_doctype, frappe.meta.get_docfield). */
const doctypes: Record<string, any[]> = {};

async function withDoctype(doctype: string) {
	if (doctypes[doctype]) return;
	const response = await fetch(
		`/api/method/frappe.desk.form.load.getdoctype?${new URLSearchParams({ doctype, with_parent: "1" })}`,
		{ credentials: "same-origin", headers: { Accept: "application/json" } },
	);
	if (!response.ok) throw new Error(`${doctype}: HTTP ${response.status}`);
	doctypes[doctype] = ((await response.json()).docs || []) as any[];
}

function docfield(doctype: string, fieldname: string) {
	const meta = (doctypes[doctype] || []).find((doc) => doc.name === doctype);
	return (meta?.fields || []).find((field: any) => field.fieldname === fieldname);
}

// frappe-charts, the desk's library of charts, as frappe serves it (its node_modules under /assets): loaded with the
// first chart a card draws, never with the editor
const CHARTS = "/assets/frappe/node_modules/frappe-charts/dist/frappe-charts.esm.js";
const CHARTS_STYLE = "/assets/frappe/node_modules/frappe-charts/dist/frappe-charts.min.css";
export const charts = {
	load: (): Promise<any> => import(/* @vite-ignore */ CHARTS).then((lib) => lib.Chart),
};
let chartClass: Promise<any> | null = null;

/** frappe.Chart of the desk: the chart is drawn once its library is in, and, as the desk's own
 * (frappe/public/js/frappe/ui/chart.js), a chart drawn again on the same element ends the one before. Where the
 * library does not load, the card keeps its title. */
export class DeskChart {
	constructor(parent: Element | string, options: Record<string, unknown>) {
		const host: any = typeof parent === "string" ? document.querySelector(parent) : parent;
		if (!host) return;
		if (!document.querySelector(`link[data-nora-chat="${CHARTS_STYLE}"]`)) {
			const link = document.createElement("link");
			link.rel = "stylesheet";
			link.href = CHARTS_STYLE;
			link.dataset.noraChat = CHARTS_STYLE;
			document.head.appendChild(link);
		}
		chartClass = chartClass || charts.load();
		chartClass
			.then((Chart) => {
				if (!host.isConnected) return;
				host.__frappe_chart?.destroy?.();
				host.__frappe_chart = new Chart(host, options);
			})
			.catch(() => {
				chartClass = null;
			});
	}
}

/** What the cards use of the desk, set where the page has none of it. */
export function provideDeskCards(frappe: any, desk: NoraChatDesk) {
	frappe.call =
		frappe.call ||
		((options: CallOptions | string, args?: Record<string, unknown>) => call(frappe, options, args));
	frappe.set_route = frappe.set_route || ((...route: unknown[]) => setRoute(frappe, ...route));
	if (!("route_options" in frappe)) frappe.route_options = null;
	frappe.model = frappe.model || {};
	frappe.model.with_doctype = frappe.model.with_doctype || withDoctype;
	frappe.meta = frappe.meta || {};
	frappe.meta.get_docfield = frappe.meta.get_docfield || docfield;
	frappe.defaults = frappe.defaults || {};
	frappe.defaults.get_default = frappe.defaults.get_default || ((key: string) => desk.defaults[key] ?? null);
	frappe.boot = frappe.boot || {};
	frappe.boot.sysdefaults = frappe.boot.sysdefaults || { ...desk.defaults };
	frappe.datetime = frappe.datetime || {};
	frappe.datetime.str_to_user = frappe.datetime.str_to_user || ((value: unknown) => dateToUser(desk, value));
	frappe.Chart = frappe.Chart || DeskChart;
	const page = window as any;
	page.format_number =
		page.format_number ||
		((value: unknown, format?: string | null, decimals?: number | null) =>
			formatNumber(desk, value, format, decimals));
	page.format_currency =
		page.format_currency ||
		((value: unknown, currency?: string | null, decimals?: number | null) =>
			formatCurrency(desk, value, currency, decimals));
}

/** frappe.show_alert of the desk: the message, in the colour its indicator says. */
export function showAlert(alert: { message?: string; indicator?: string } | string) {
	const message = typeof alert === "string" ? alert : String(alert?.message ?? "");
	const indicator = typeof alert === "string" ? "" : String(alert?.indicator || "");
	if (["green"].includes(indicator)) return toast.success(message);
	if (["red"].includes(indicator)) return toast.error(message);
	if (["orange", "yellow"].includes(indicator)) return toast.warning(message);
	return toast.info(message);
}
