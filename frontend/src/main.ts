import { createApp } from "vue";

import { Button, FormControl, FrappeUI } from "frappe-ui";
import { telemetryPlugin } from "frappe-ui/frappe";
import { createPinia } from "pinia";
import "./index.css";
import router from "./router";
import "./setupFrappeUIResource";

import App from "@/App.vue";
import Input from "@/components/Controls/Input.vue";
//// Neoffice — upstream's SPA is English-only. We install the same translation plugin the other
//// Frappe SPAs use, fed by builder/i18n.py (0ab11671).
import translationPlugin from "@/translation";

const app = createApp(App);
const pinia = createPinia();

app.use(router);
app.use(FrappeUI);
app.use(pinia);
//// Neoffice — see the import above (0ab11671).
app.use(translationPlugin);
app.use(telemetryPlugin, { app_name: "builder" });

window.name = "frappe-builder";
app.config.globalProperties.window = window;

app.component("Button", Button);
app.component("FormControl", FormControl);
app.component("BuilderInput", Input);

app.mount("#app");

declare global {
	interface Window {
		is_developer_mode?: boolean;
		builder_version: string;
		//// Neoffice — globals the translation plugin installs (0ab11671).
		translatedMessages?: Record<string, string>;
		__?: (message: string) => string;
	}
}

if (window.is_developer_mode && typeof window.is_developer_mode === "string") {
	window.is_developer_mode =
		window.is_developer_mode === "1" ||
		window.is_developer_mode === "True" ||
		(window.is_developer_mode as string).startsWith("{{");
}

if (window.builder_version && window.builder_version.startsWith("{{")) {
	window.builder_version = "develop";
}
