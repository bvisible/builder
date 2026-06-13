<template>
	<div class="flex h-screen">
		<NeoCockpitBuilderSidebar></NeoCockpitBuilderSidebar>
		<div class="flex w-full flex-1 flex-col overflow-hidden pb-10">
			<DashboardToolbar class="sticky top-0" />
			<DashboardHead />
			<DashboardContent />
		</div>
	</div>
	<BuilderCommandPalette />
	<TemplatesDialog />
	<Dialog v-model="showSettingsDialog" :dismissable="false" size="5xl" bare>
		<template #default>
			<DialogTitle class="sr-only">Global Builder Settings</DialogTitle>
			<DialogDescription class="sr-only">
				Configure global settings for this builder project.
			</DialogDescription>
			<BuilderSettings @close="showSettingsDialog = false" :onlyGlobal="true" bare />
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import BuilderCommandPalette from "@/components/BuilderCommandPalette.vue";
import DashboardContent from "@/components/DashboardContent.vue";
import DashboardHead from "@/components/DashboardHead.vue";
import DashboardToolbar from "@/components/DashboardToolbar.vue";
import NeoCockpitBuilderSidebar from "@/components/NeoCockpitBuilderSidebar.vue";
import TemplatesDialog from "@/components/Templates/TemplatesDialog.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import { Dialog } from "frappe-ui";
import { DialogDescription, DialogTitle } from "reka-ui";
import { defineAsyncComponent } from "vue";

const BuilderSettings = defineAsyncComponent(() => import("@/components/BuilderSettings.vue"));
const { showSettingsDialog } = useDashboardState();
</script>
