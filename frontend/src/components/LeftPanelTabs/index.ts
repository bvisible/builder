import LayersIcon from "@/components/Icons/Layers.vue";
import AssetsTab from "@/components/LeftPanelTabs/AssetsTab.vue";
import BlocksTab from "@/components/LeftPanelTabs/BlocksTab.vue";
import CodeTab from "@/components/LeftPanelTabs/CodeTab.vue";
import LayersTab from "@/components/LeftPanelTabs/LayersTab.vue";
//// Neoffice — see the Site blocks tab below.
import SiteBlocksPanel from "@/components/SiteBlocksPanel.vue";
import useBuilderStore from "@/stores/builderStore";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { KeyboardShortcutCombo } from "frappe-ui";
import { defineAsyncComponent, type Component } from "vue";
import { __ } from "@/translation";
//// Neoffice — see the Chat tab below.
import { assistantName } from "@/utils/neofficeBoot";

export type LeftPanelTab = RegistryItem & {
	label: string;
	icon: string | Component;
	component?: Component;
	props?: () => Record<string, unknown>;
	/** binding that opens the tab; the panel labels the button with it */
	shortcut?: KeyboardShortcutCombo;
	/** narrowest the panel may be while this tab shows, if wider than the panel's own minimum */
	minWidth?: number;
	/** mount on first open, then keep alive */
	lazy?: boolean;
	/** mount a lazy tab early, before the user opens it */
	preload?: () => boolean;
	/** clicking runs this instead of switching tab */
	action?: () => void;
	/** for action tabs that own their own active state */
	isActive?: () => boolean;
};

export const leftPanelTabs = createRegistry<LeftPanelTab>();

// the route chunk imports this after pinia is installed, so the lookup resolves
const builderStore = useBuilderStore();

leftPanelTabs.register({
	name: "Blocks",
	label: __("Insert"),
	icon: "lucide-plus",
	component: BlocksTab,
	shortcut: "Mod+Shift+I",
});

leftPanelTabs.register({
	name: "Layers",
	label: __("Layers"),
	icon: LayersIcon,
	component: LayersTab,
	shortcut: "Mod+Shift+L",
});

leftPanelTabs.register({
	name: "Assets",
	label: __("Components"),
	icon: "lucide-box",
	component: AssetsTab,
	shortcut: "Mod+Shift+A",
});

leftPanelTabs.register({
	name: "Code",
	label: __("Code"),
	icon: "lucide-code",
	component: CodeTab,
	shortcut: "Mod+Shift+K",
	// PageScript mounts a CodeMirror instance, so defer it until first open
	lazy: true,
	// a data script dialog needs PageScript mounted even if the tab never opens,
	// and so does a script the chat asks to open: the watchers that open the
	// editor live INSIDE PageScript, so until something mounts it the flag is
	// set for nobody to read
	preload: () => builderStore.showDataScriptDialog !== null || builderStore.openClientScript !== null,
});

// not a tab. It toggles a modal, so it declares an action and its own active state
leftPanelTabs.register({
	name: "tokens",
	label: __("Design Tokens"),
	icon: "lucide-aperture",
	shortcut: "Mod+Shift+V",
	action: () => (builderStore.showTokenManager = !builderStore.showTokenManager),
	isActive: () => builderStore.showTokenManager,
});

//// Neoffice — the site's live blocks (builder/site_ai/components.py, 2026-09-15). NOT the
//// Components tab above, which holds blocks a user designed: these are provided by the apps and
//// they draw the site's own data — its products, its brands, its hours, its posts.
leftPanelTabs.register({
	name: "SiteBlocks",
	label: __("Site blocks"),
	icon: "lucide-layout-template",
	component: SiteBlocksPanel,
	shortcut: { key: "b", ctrl: true, shift: true },
	lazy: true,
});

leftPanelTabs.register({
	name: "Chat",
	//// Neoffice — the assistant is named by the instance (boot), upstream's label is the fallback.
	label: assistantName(__("Bob AI")),
	icon: "lucide-sparkle",
	// the panel brings its own markdown, yaml and sanitiser stack, so it waits to be opened
	component: defineAsyncComponent(() => import("@/components/BuilderAIChatPanel.vue")),
	shortcut: "Mod+Shift+O",
	// the composer's controls and the chat bubbles stop fitting below this
	minWidth: 300,
});
