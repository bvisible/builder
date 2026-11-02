<!-- //// Neoffice — added file (no upstream equivalent): the Theme screen as its own dialog — it is what a
     //// site owner touches most. builder/templates/includes/header_footer/** = the Neoffice site chrome
     //// (Website Header Footer Config). First commit 426fcfd3 2026-08-04. -->
<template>
	<!-- The theme is not a setting. It is the thing a site owner touches most,
	     and it was three clicks deep under Settings — same reasoning as Media. -->
	<!-- frappe-ui 1.0 dropped the `options` prop and the `#body` slot: this screen opened empty -->
	<Dialog v-model="show" size="4xl" bare>
		<template #default>
			<DialogDescription class="sr-only">
				{{ __("The site's colours, fonts, header, footer and top page.") }}
			</DialogDescription>
			<div class="flex h-[80vh] flex-col gap-4 p-5">
				<div class="flex items-center gap-2">
					<span class="lucide-palette size-4 text-ink-gray-8" aria-hidden="true" />
					<DialogTitle as="h2" class="text-lg font-semibold text-ink-gray-9">
						{{ __("Theme, Header & Footer") }}
					</DialogTitle>
				</div>
				<div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden pr-1">
					<GlobalTheme v-if="show" />
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { Dialog } from "frappe-ui";
import { DialogDescription, DialogTitle } from "reka-ui";
import { defineAsyncComponent } from "vue";

// only loaded when the dialog is opened
const GlobalTheme = defineAsyncComponent(() => import("./Settings/GlobalTheme.vue"));

const show = defineModel<boolean>({ default: false });
</script>
