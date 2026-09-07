//// Neoffice — added file (no upstream equivalent). What our edition adds to or changes in the
//// Settings dialog, applied by ./index.ts right after upstream's own panes so the dialog, the command
//// palette and the idle prefetch see it without any other change to upstream:
//// - three Global panes upstream does not have: Theme, Header & Footer (050b8aa3), Social Accounts
////   (3a033121) and Plugins (45e67b23);
//// - on a managed instance, the AI pane becomes read-only (same registry name, so every
////   openBuilderSettings("global_ai") still lands on it) and the Users tab is hidden, because
////   invitations create users outside the licence quota. Both are boot capabilities
////   (builder/site_ai/capabilities.py), never a build flag.
import type { SettingsItem } from "@/components/Settings";
import { __ } from "@/translation";
import type { createRegistry } from "@/utils/createRegistry";
import { isManagedAI, showUsersTab } from "@/utils/neofficeBoot";
import { defineAsyncComponent, type Component } from "vue";

type SettingsPane = Omit<SettingsItem, "component"> & { load: () => Promise<{ default: Component }> };
type SettingsRegistry = ReturnType<typeof createRegistry<SettingsItem>>;

const panes: SettingsPane[] = [
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

const withComponent = (pane: SettingsPane): SettingsItem => ({
	...pane,
	component: defineAsyncComponent(pane.load),
});

export function registerNeofficePanes(registry: SettingsRegistry) {
	panes.forEach((pane) => registry.register(withComponent(pane)));

	// re-registering under an existing name keeps its slot and takes the entry over
	const existing = (name: string) => registry.all.value.find((item) => item.name === name);

	const ai = existing("global_ai");
	if (ai && isManagedAI()) {
		const load = () => import("@/components/Settings/GlobalAIManaged.vue");
		registry.register({ ...ai, load, component: defineAsyncComponent(load) });
	}

	const users = existing("global_users");
	if (users) {
		registry.register({ ...users, condition: () => showUsersTab() });
	}
}
