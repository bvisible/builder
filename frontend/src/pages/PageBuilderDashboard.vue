<template>
	<div class="flex h-screen">
		<!-- //// Neoffice — the NeoCockpit chrome replaces upstream's DashboardSidebar here; the native
		     //// sidebar stays as the fallback inside NeoCockpitBuilderSidebar (575f427e). -->
		<NeoCockpitBuilderSidebar></NeoCockpitBuilderSidebar>
		<div class="flex w-full flex-1 flex-col overflow-hidden pb-10">
			<DashboardToolbar class="sticky top-0" />
			<DashboardHead />
			<DashboardContent />
		</div>
	</div>
	<BuilderCommandPalette />
	<TemplatesDialog />
	<!-- //// Neoffice — the Settings dialog, moved out of DashboardSidebar so it survives the cockpit
	     //// replacing that sidebar; initialTab lets a cockpit entry open straight on Theme (575f427e,
	     //// 8f116e8a). -->
	<Dialog v-model="showSettingsDialog" :dismissable="false" size="5xl" bare>
		<template #default>
			<DialogTitle class="sr-only">Global Builder Settings</DialogTitle>
			<DialogDescription class="sr-only">
				Configure global settings for this builder project.
			</DialogDescription>
			<BuilderSettings
				@close="showSettingsDialog = false"
				:onlyGlobal="true"
				:initialTab="settingsTab"
				bare />
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import BuilderCommandPalette from "@/components/BuilderCommandPalette.vue";
import DashboardContent from "@/components/DashboardContent.vue";
//// Neoffice — upstream imported DashboardSidebar here; it is now pulled in by
//// NeoCockpitBuilderSidebar instead (575f427e).
import DashboardHead from "@/components/DashboardHead.vue";
import DashboardToolbar from "@/components/DashboardToolbar.vue";
//// Neoffice — see the template above (575f427e).
import NeoCockpitBuilderSidebar from "@/components/NeoCockpitBuilderSidebar.vue";
import TemplatesDialog from "@/components/Templates/TemplatesDialog.vue";
//// Neoffice — the shared dialog state (575f427e, 8f116e8a).
import { useDashboardState } from "@/composables/useDashboardState";
import { builderSettings } from "@/data/builderSettings";
import router, { sessionUser } from "@/router";
import { prefetchBuilderSettings } from "@/utils/prefetch";
//// Neoffice — for the Settings dialog above (575f427e).
import { Dialog } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
//// Neoffice — moved here with the dialog, together with defineAsyncComponent for BuilderSettings
//// (575f427e).
import { DialogDescription, DialogTitle } from "reka-ui";
import { defineAsyncComponent, onMounted, watch } from "vue";

const BuilderSettings = defineAsyncComponent(() => import("@/components/BuilderSettings.vue"));
const { showSettingsDialog, settingsTab } = useDashboardState();

const telemetry = useTelemetry();

onMounted(prefetchBuilderSettings);
// Dev benches have telemetry (and thus the survey) off; ?persona_survey=test forces the redirect.
const devForceShow = new URLSearchParams(window.location.search).get("persona_survey") === "test";

watch(
	[() => telemetry.isEnabled, () => builderSettings.doc, sessionUser],
	() => {
		if (!telemetry.isEnabled && !devForceShow) return;
		if (!builderSettings.doc) return;
		if (builderSettings.doc.persona_survey_done && !devForceShow) return;
		if (!sessionUser.value || sessionUser.value === "Guest") return;
		router.replace({
			name: "persona-survey",
			query: devForceShow ? { persona_survey: "test" } : {},
		});
	},
	{ immediate: true },
);
</script>
