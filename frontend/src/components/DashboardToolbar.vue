<template>
	<div
		class="toolbar flex h-12 items-center justify-end border-b-[1px] border-outline-gray-1 bg-surface-base p-2 px-3 py-1">
		<div class="flex gap-2">
			<Button
				variant="solid"
				iconLeft="lucide-plus"
				class="bg-surface-gray-10 !text-ink-base hover:bg-surface-gray-9"
				@click="showTemplatesDialog = true">
				<!-- //// Neoffice i18n — hardcoded English: the dashboard stayed English on a French bench (bd5dc7f1). -->
				{{ __("New") }}
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDashboardState } from "@/composables/useDashboardState";

const { showTemplatesDialog } = useDashboardState();
</script>
