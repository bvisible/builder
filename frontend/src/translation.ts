// Builder i18n. Mirrors the standard Frappe frontend pattern (lms, insights,
// mail): `__("...")` looks the string up in the catalog the server sends for
// the logged-in user's language, and falls back to the source string.
// Extraction: frappe's default babel map routes **.vue through the html_template
// extractor, whose regex pass picks up __() in both <template> and <script>.
import { createResource } from "frappe-ui";
import { ref, type App } from "vue";

type Formattable = { format: (...args: unknown[]) => string };

// Reactive on purpose. The catalog arrives from the server after the first
// render, and a plain object would leave every already-evaluated computed
// (a sidebar's nav list, say) stuck on the English source string forever.
const catalog = ref<Record<string, string>>({});

export function translate(message: string): string & Partial<Formattable> {
	const translated = catalog.value[message] || message;

	if (!/{\d+}/.test(message)) {
		return translated;
	}
	// keep the {0}-placeholder contract of frappe's __("..").format(x)
	const formattable = new String(translated) as unknown as string & Formattable;
	formattable.format = (...args: unknown[]) =>
		translated.replace(/{(\d+)}/g, (match, index) =>
			typeof args[Number(index)] !== "undefined" ? String(args[Number(index)]) : match,
		);
	return formattable;
}

export default function translationPlugin(app: App) {
	app.config.globalProperties.__ = translate;
	window.__ = translate;
	if (window.translatedMessages) {
		catalog.value = window.translatedMessages;
		return;
	}
	createResource({
		url: "builder.i18n.get_translations",
		cache: "translations",
		auto: true,
		transform: (data: Record<string, string>) => {
			window.translatedMessages = data;
			catalog.value = data;
		},
	});
}
