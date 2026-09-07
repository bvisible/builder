//// Neoffice — added file (no upstream equivalent). The three Global panes upstream does not
//// have: Theme, Header & Footer (050b8aa3), Social Accounts (3a033121) and Plugins (45e67b23).
//// Declared here and registered by ./index.ts right after upstream's own panes, so the dialog,
//// the command palette and the idle prefetch all list them without any other change to upstream.
import type { SettingsItem } from "@/components/Settings";
import { __ } from "@/translation";
import type { Component } from "vue";

type SettingsPane = Omit<SettingsItem, "component"> & { load: () => Promise<{ default: Component }> };

export const neofficePanes: SettingsPane[] = [
	{
		name: "global_theme",
		label: __("Theme"),
		title: __("Theme, Header & Footer"),
		icon: "lucide-palette",
		group: "Global",
		// right after General: colours, fonts and the site chrome are what a site owner opens first
		after: "global_general",
		load: () => import("@/components/Settings/GlobalTheme.vue"),
	},
	{
		name: "global_social",
		label: __("Social"),
		title: __("Social Accounts"),
		icon: "lucide-at-sign",
		group: "Global",
		load: () => import("@/components/Settings/GlobalSocial.vue"),
	},
	{
		name: "global_plugins",
		label: __("Plugins"),
		title: __("Plugins"),
		icon: "lucide-puzzle",
		group: "Global",
		load: () => import("@/components/Settings/GlobalPlugins.vue"),
	},
];
