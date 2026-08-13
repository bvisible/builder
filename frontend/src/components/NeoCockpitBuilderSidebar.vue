<template>
	<DashboardSidebar v-if="failed" />
	<template v-else>
		<NeoCockpitBridge
			:surface-app="surfaceApp"
			:context-nav="contextNav"
			:navigate="navigate"
			@failed="failed = true"
		/>
		<!-- the fallback DashboardSidebar mounts its own, so only here -->
		<AIChatModal v-model="showAIChat" />
		<MediaLibrary v-model="showMedia" />
		<ThemeDialog v-model="showTheme" />
	</template>
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
import { useChatDeepLink } from "@/composables/useChatDeepLink";
import { useDashboardState } from "@/composables/useDashboardState";
import { useRouter } from "vue-router";
import { computed, defineAsyncComponent, ref } from "vue";

// loaded on demand: the chat pulls in its own chunk and most visits never open it
const AIChatModal = defineAsyncComponent(() => import("@/components/AIChatModal.vue"));
const MediaLibrary = defineAsyncComponent(() => import("@/components/MediaLibrary.vue"));
const ThemeDialog = defineAsyncComponent(() => import("@/components/ThemeDialog.vue"));

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const router = useRouter();
const builderStore = useBuilderStore();
const { showSettingsDialog, settingsTab } = useDashboardState();
const failed = ref(false);
// a desk workspace shortcut lands here with ?chat=1 — the chat has no route
const showAIChat = useChatDeepLink();
const showMedia = ref(false);
const showTheme = ref(false);

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
					label: __("All Pages"),
					icon: "lucide-files",
					active: !builderStore.activeFolder,
					onClick: () => {
						builderStore.activeFolder = "";
					},
				},
				{
					label: __("Create with AI"),
					icon: "lucide-sparkles",
					onClick: () => {
						showAIChat.value = true;
					},
				},
				{
					label: __("Theme"),
					icon: "lucide-palette",
					onClick: () => {
						// colours and fonts are what a site owner touches first;
						// its own screen, not a tab three clicks into Settings
						showTheme.value = true;
					},
				},
				{
					label: __("Media"),
					icon: "lucide-image",
					onClick: () => {
						// which images the site holds, where each one is used, and
						// which links lead nowhere — none of it was visible before
						showMedia.value = true;
					},
				},
				{
					label: __("Settings"),
					icon: "lucide-settings",
					onClick: () => {
						settingsTab.value = undefined;
						showSettingsDialog.value = true;
					},
				},
			],
		},
		folders.length ? { label: __("Folders"), items: folders } : null,
	].filter(Boolean);
});
</script>
