import { useStorage } from "@vueuse/core";
import { computed, ref, Ref } from "vue";

const searchFilter = ref("");
const selectionMode = ref(false);
const selectedPages = ref(new Set<string>());
const treeExpanded = ref(true);
const showTemplatesDialog = ref(false);
//// Neoffice — the Settings dialog moved out of DashboardSidebar (which the cockpit replaces)
//// onto the dashboard, so its open state and its tab have to be shared (575f427e, 8f116e8a).
// shared so the cockpit sidebar wrapper can open Settings too (the dialog
// itself is rendered on the dashboard, not inside the native sidebar)
const showSettingsDialog = ref(false);
// which tab the dialog opens on ("" / undefined = its default). Shared so a
// sidebar entry can send the user straight to Theme.
const settingsTab = ref<string | undefined>(undefined);

// remembers the template group the picker was last drilled into ("" = gallery)
const lastTemplateGroup = useStorage("lastTemplateGroup", "") as Ref<string>;

// active category filter in the template gallery ("" = All)
const templateCategoryFilter = useStorage("templateCategoryFilter", "") as Ref<string>;

const displayType = useStorage("displayType", "grid") as Ref<"grid" | "list" | "tree">;
// a fresh key: values saved under the old "typeFilter" key (published/unpublished) no longer exist
const statusFilter = useStorage("pageStatusFilter", "") as Ref<
	"" | "all" | "live" | "staging" | "draft" | "unpublished_changes"
>;
const accessFilter = useStorage("pageAccessFilter", "all") as Ref<"all" | "public" | "protected">;
const createdByFilter = useStorage("pageCreatedByFilter", "") as Ref<string>;
const activeFilterCount = computed(
	() =>
		[
			!["", "all"].includes(statusFilter.value),
			accessFilter.value !== "all",
			Boolean(createdByFilter.value),
		].filter(Boolean).length,
);
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
		//// Neoffice — see above (575f427e, 8f116e8a).
		showSettingsDialog,
		settingsTab,
		lastTemplateGroup,
		templateCategoryFilter,
		displayType,
		statusFilter,
		accessFilter,
		createdByFilter,
		activeFilterCount,
		orderBy,
		expandTreeFn,
		collapseTreeFn,
	};
}
