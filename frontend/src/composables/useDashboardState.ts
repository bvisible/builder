import { useStorage } from "@vueuse/core";
import { ref, Ref } from "vue";

const searchFilter = ref("");
const selectionMode = ref(false);
const selectedPages = ref(new Set<string>());
const treeExpanded = ref(true);
const showTemplatesDialog = ref(false);
// shared so the cockpit sidebar wrapper can open Settings too (the dialog
// itself is rendered on the dashboard, not inside the native sidebar)
const showSettingsDialog = ref(false);
// which tab the dialog opens on ("" / undefined = its default). Shared so a
// sidebar entry can send the user straight to Theme.
const settingsTab = ref<string | undefined>(undefined);

// remembers the template group the picker was last drilled into ("" = gallery)
const lastTemplateGroup = useStorage("lastTemplateGroup", "") as Ref<string>;

const displayType = useStorage("displayType", "grid") as Ref<"grid" | "list" | "tree">;
const typeFilter = useStorage("typeFilter", "") as Ref<"" | "draft" | "published" | "unpublished" | "all">;
const orderBy = useStorage("orderBy", "creation") as Ref<
	"creation" | "modified" | "alphabetically_a_z" | "alphabetically_z_a"
>;

const expandTreeFn = ref<(() => void) | null>(null);
const collapseTreeFn = ref<(() => void) | null>(null);

export function useDashboardState() {
	return {
		searchFilter,
		selectionMode,
		selectedPages,
		treeExpanded,
		showTemplatesDialog,
		showSettingsDialog,
		settingsTab,
		lastTemplateGroup,
		displayType,
		typeFilter,
		orderBy,
		expandTreeFn,
		collapseTreeFn,
	};
}
