<template>
	<DashboardSidebar v-if="failed" />
	<NeoCockpitBridge
		v-else
		:surface-app="surfaceApp"
		:context-nav="contextNav"
		:navigate="navigate"
		@failed="failed = true"
	/>
</template>

<script setup lang="ts">
/**
 * Builder flavor of the shared Neoffice chrome (NeoCockpit). Maps the
 * dashboard sidebar nav (All Pages / Settings / Folders) into contextNav;
 * the native DashboardSidebar stays as an automatic fallback. Only the
 * dashboard (page list) gets the cockpit — the full-screen page editor is
 * left untouched. Recipe: neoffice ADR-015.
 */
import DashboardSidebar from "@/components/DashboardSidebar.vue";
import NeoCockpitBridge from "@/components/NeoCockpitBridge.vue";

import builderProjectFolder from "@/data/builderProjectFolder";
import useBuilderStore from "@/stores/builderStore";
import { useDashboardState } from "@/composables/useDashboardState";
import { useRouter } from "vue-router";
import { computed, ref } from "vue";

const router = useRouter();
const builderStore = useBuilderStore();
const { showSettingsDialog } = useDashboardState();
const failed = ref(false);

const surfaceApp = {
	name: "builder",
	title: "Builder",
	logo: "/builder_logo.png",
};

function navigate(r: string) {
	if (!r) return;
	if (r.startsWith("/app") || r.startsWith("http")) window.location.href = r;
	else router.push(r);
}

const contextNav = computed(() => {
	const folders = (builderProjectFolder.data || []).map(
		(p: { folder_name: string }) => ({
			label: p.folder_name,
			icon: "lucide-folder",
			active: builderStore.activeFolder === p.folder_name,
			onClick: () => {
				builderStore.activeFolder = p.folder_name;
			},
		})
	);
	return [
		{
			items: [
				{
					label: "All Pages",
					icon: "lucide-files",
					active: !builderStore.activeFolder,
					onClick: () => {
						builderStore.activeFolder = "";
					},
				},
				{
					label: "Settings",
					icon: "lucide-settings",
					onClick: () => {
						showSettingsDialog.value = true;
					},
				},
			],
		},
		folders.length ? { label: "Folders", items: folders } : null,
	].filter(Boolean);
});
</script>
