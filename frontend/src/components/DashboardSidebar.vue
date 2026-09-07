<template>
	<Sidebar class="border-r border-outline-gray-1">
		<SidebarHeader title="Builder" :logo="builderLogo" :menuItems="appMenuItems" class="px-1.5" />

		<ScrollArea class="min-h-0 flex-1" viewport-class="px-2 pt-0.5 pb-2">
			<nav class="space-y-0.5">
				<SidebarItem
					:label="__('All Pages')"
					:active="!builderStore.activeFolder"
					@click="setFolderActive('')">
					<template #prefix><FilesIcon class="size-4" /></template>
				</SidebarItem>
				<SidebarItem :label="__('Settings')" @click="showSettingsDialog = true">
					<template #prefix><SettingsIcon class="size-4" /></template>
				</SidebarItem>
				<!-- //// Neoffice — added entries: Create with AI (0ab11671), Theme (050b8aa3), Media (798e7817)
				     //// and Articles (45e67b23, hidden when the blog plugin is off). Upstream's sidebar lists
				     //// pages only. This native sidebar is the fallback of NeoCockpitBuilderSidebar, which
				     //// offers the same entries inside the cockpit. -->
				<SidebarItem :label="__('Create with AI')" icon="lucide-sparkles" @click="showAIChat = true" />
				<SidebarItem :label="__('Theme')" icon="lucide-palette" @click="showTheme = true" />
				<SidebarItem :label="__('Media')" icon="lucide-image" @click="showMedia = true" />
				<SidebarItem
					v-if="capabilities.blog !== false"
					:label="__('Articles')"
					icon="lucide-newspaper"
					@click="showBlog = true" />
			</nav>

			<div class="mt-5 flex h-7 items-center justify-between">
				<SidebarLabel>{{ __("Folders") }}</SidebarLabel>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-plus text-ink-gray-5"
					:label="__('New folder')"
					@click="promptCreateFolder()" />
			</div>

			<p
				v-if="!builderProjectFolder.data?.length"
				class="mt-0.5 flex h-7 items-center pl-2 text-sm text-ink-gray-5">
				{{ __("No folders yet") }}
			</p>
			<nav class="mt-0.5 space-y-0.5">
				<SidebarItem
					v-for="project in builderProjectFolder.data"
					:key="project.folder_name"
					icon="lucide-folder"
					:label="project.folder_name"
					:active="isFolderActive(project.folder_name)"
					@click="setFolderActive(project.folder_name)">
					<EditableSpan
						v-model="project.folder_name"
						:editable="renamingFolder === project.folder_name"
						:onChange="
							async (newName) => {
								await renameFolder(newName, project);
								renamingFolder = '';
							}
						"
						@blur="renamingFolder = ''"
						class="w-full truncate text-sm capitalize">
						{{ project.folder_name }}
					</EditableSpan>
					<template #suffix>
						<Button
							v-if="isFolderActive(project.folder_name) && project.is_standard"
							variant="ghost"
							size="sm"
							icon="lucide-info"
							disabled
							:tooltip="__('System generated folder cannot be edited or deleted')"
							class="cursor-pointer" />
						<Dropdown
							v-else-if="isFolderActive(project.folder_name)"
							placement="right"
							:options="[
								{
									label: __('Rename'),
									onClick: () => {
										renamingFolder = project.folder_name;
									},
									icon: 'lucide-edit',
								},
								{
									label: __('Delete Folder'),
									onClick: () => deleteFolder(project.folder_name),
									icon: 'lucide-trash',
								},
							]">
							<template v-slot="{ open }">
								<Button icon="lucide-more-horizontal" size="sm" variant="ghost" @click="open" />
							</template>
						</Dropdown>
					</template>
				</SidebarItem>
			</nav>
		</ScrollArea>

		<div class="mt-auto">
			<p class="p-2 text-center text-sm text-ink-gray-4">{{ __("Version") }}: {{ builderVersion }}</p>
			<TrialBanner v-if="builderStore.isFCSite" />
		</div>
	</Sidebar>
	<!-- //// Neoffice — the Settings dialog upstream rendered HERE lives in PageBuilderDashboard, because
	     //// the cockpit replaces this sidebar and the dialog must stay reachable (575f427e); its open
	     //// state is the shared one in useDashboardState. Below, the modals our entries open. -->
	<AIChatModal v-model="showAIChat" />
	<MediaLibrary v-model="showMedia" />
	<BlogManager v-model="showBlog" />
	<ThemeDialog v-model="showTheme" />
</template>
<script lang="ts" setup>
import { __ } from "@/translation";
import builderLogo from "/builder_logo.png";
import EditableSpan from "@/components/EditableSpan.vue";
import FilesIcon from "@/components/Icons/Files.vue";
import SettingsIcon from "@/components/Icons/SettingsGear.vue";
//// Neoffice — a desk workspace shortcut lands on /builder?chat=1; the chat has no route of its own.
import { useChatDeepLink } from "@/composables/useChatDeepLink";
import { useDashboardState } from "@/composables/useDashboardState";
import builderProjectFolder from "@/data/builderProjectFolder";
import useBuilderStore from "@/stores/builderStore";
import { BuilderProjectFolder } from "@/types/doctypes";
import { promptCreateFolder } from "@/utils/dialogs";
import { confirm } from "@/utils/helpers";
import { useDark, useToggle } from "@vueuse/core";
//// Neoffice — Dialog is no longer imported here: the Settings dialog moved to the dashboard
//// (575f427e). The reka-ui DialogDescription/DialogTitle import went with it.
import {
	createResource,
	Dropdown,
	ScrollArea,
	Sidebar,
	SidebarHeader,
	SidebarHeaderProps,
	SidebarItem,
	SidebarLabel,
} from "frappe-ui";
import { TrialBanner } from "frappe-ui/frappe";
import { computed, defineAsyncComponent, h, ref } from "vue";

//// Neoffice — the four screens our entries open, lazily: each pulls in its own chunk and most
//// visits never open them. BuilderSettings is no longer imported here (575f427e).
const AIChatModal = defineAsyncComponent(() => import("@/components/AIChatModal.vue"));
const MediaLibrary = defineAsyncComponent(() => import("@/components/MediaLibrary.vue"));
const BlogManager = defineAsyncComponent(() => import("@/components/BlogManager.vue"));
const ThemeDialog = defineAsyncComponent(() => import("@/components/ThemeDialog.vue"));
const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
const builderStore = useBuilderStore();
//// Neoffice — showSettingsDialog is the shared dashboard state, not the local ref upstream declared
//// at the bottom of this file (575f427e).
const { showTemplatesDialog, showSettingsDialog } = useDashboardState();
const renamingFolder = ref("");
//// Neoffice — state of our entries (see the template).
const showAIChat = useChatDeepLink();
const showMedia = ref(false);
const showBlog = ref(false);
const showTheme = ref(false);

// What this bench is allowed to show. A plugin the owner turned off must not
// leave a dead button behind — and `!== false` is deliberate: an unknown
// plugin, or a bench whose registry has not synced yet, stays visible.
const capabilities = ref<Record<string, boolean>>({});
const capabilitiesResource = createResource({
	url: "builder.plugins.get_capabilities",
	auto: true,
	onSuccess(data: Record<string, boolean>) {
		capabilities.value = data || {};
	},
	onError() {
		capabilities.value = {};
	},
});
window.addEventListener("unpress:capabilities-changed", () => capabilitiesResource.reload());

const apps = createResource({
	url: "builder.api.get_apps",
	cache: "other_apps",
	auto: true,
});

const appsSubmenu = computed(() => {
	return (apps.data || []).map((app: { route: string; logo: string; title: string }) => ({
		label: app.title,
		icon: h("img", { src: app.logo }),
		onClick: () => window.open(app.route, "_self"),
	}));
});

// grouped options render fine (the header hands them to Dropdown), but its prop
// type only describes a flat list
const appMenuItems = computed(
	() =>
		[
			{
				group: "Builder",
				hideLabel: true,
				items: [
					{
						label: __("New Page"),
						onClick: () => (showTemplatesDialog.value = true),
						icon: "lucide-plus",
					},
				],
			},
			{
				group: "Options",
				hideLabel: true,
				items: [
					{
						label: __("Apps"),
						icon: "lucide-grid",
						submenu: appsSubmenu.value,
					},
					{
						label: __("Toggle Theme"),
						onClick: () => toggleDark(),
						icon: isDark.value ? "lucide-sun" : "lucide-moon",
					},
					{
						label: __("Settings"),
						onClick: () => (showSettingsDialog.value = true),
						icon: "lucide-settings",
					},
				],
			},
			{
				group: "Help",
				hideLabel: true,
				items: [
					{
						label: __("Help"),
						onClick: () => window.open("https://t.me/frappebuilder"),
						icon: "lucide-info",
					},
				],
			},
		] as unknown as SidebarHeaderProps["menuItems"],
);

const isFolderActive = (folderName: string) => {
	return builderStore.activeFolder === folderName;
};
const setFolderActive = (folderName: string) => {
	builderStore.activeFolder = folderName;
};

const renameFolder = async (newFolderName: string, targetFolder: BuilderProjectFolder) => {
	if (!newFolderName) return;
	return createResource({
		url: "frappe.client.rename_doc",
	})
		.submit({
			doctype: "Builder Project Folder",
			old_name: targetFolder.folder_name,
			new_name: newFolderName,
		})
		.then(() => {
			builderProjectFolder.data = (builderProjectFolder.data ?? []).map((folder: BuilderProjectFolder) => {
				if (folder.folder_name === builderStore.activeFolder) {
					folder.folder_name = newFolderName;
				}
				return folder;
			});
			setFolderActive(newFolderName);
		});
};

const deleteFolder = async (folderName: string) => {
	const confirmed = await confirm(
		__(
			'Are you sure you want to delete this folder? All the pages under this folder will be visible under "All Pages"',
		),
	);
	if (!confirmed) return;
	await createResource({
		url: "builder.api.delete_folder",
		method: "POST",
		params: {
			folder_name: folderName,
		},
		auto: true,
	});
	builderProjectFolder.data = (builderProjectFolder.data ?? []).filter(
		(folder: BuilderProjectFolder) => folder.folder_name !== folderName,
	);
	setFolderActive("");
};
//// Neoffice — upstream declared `const showSettingsDialog = ref(false)` right here; it is the shared
//// dashboard state now (575f427e).
const builderVersion = (window as any).builder_version;
</script>
