<template>
	<!-- The theme is not a setting. It is the thing a site owner touches most,
	     and it was three clicks deep under Settings — same reasoning as Media. -->
	<Dialog v-model="show" :options="{ size: '4xl' }">
		<template #body>
			<div class="flex h-[80vh] flex-col gap-4 p-5">
				<div class="flex items-center gap-2">
					<span class="lucide-palette size-4 text-ink-gray-8" aria-hidden="true" />
					<h2 class="text-lg font-semibold text-ink-gray-9">
						{{ __("Theme, Header & Footer") }}
					</h2>
				</div>
				<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1">
					<GlobalTheme v-if="show" />
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { Dialog } from "frappe-ui";
import { defineAsyncComponent } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

// only loaded when the dialog is opened
const GlobalTheme = defineAsyncComponent(() => import("./Settings/GlobalTheme.vue"));

const show = defineModel<boolean>({ default: false });
</script>
