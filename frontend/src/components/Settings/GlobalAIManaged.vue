<!-- //// Neoffice — added file (no upstream equivalent). The AI pane of a managed instance: the
     //// host runs the models, so there is nothing to set up and nothing to disclose (no endpoint,
     //// no model id, no key). Replaces upstream's GlobalAI under the same registry name when the
     //// boot says the AI is managed (see Settings/neoffice.ts). -->
<template>
	<div class="flex flex-col gap-5">
		<div class="flex flex-col gap-1">
			<span class="text-lg-semibold text-ink-gray-9">{{ assistant }}</span>
			<p class="text-p-sm text-ink-gray-6">
				{{ __("{0} is provided and operated by your host. The models, the keys and the updates are managed for you: there is nothing to configure here.", [assistant]) }}
			</p>
		</div>
		<hr class="w-full border-outline-gray-2" />
		<div class="flex items-center gap-2">
			<span
				class="inline-block size-2 rounded-full"
				:class="ready ? 'bg-green-600' : 'bg-orange-500'"
				aria-hidden="true" />
			<span class="text-p-sm text-ink-gray-8">
				{{ ready ? __("Ready") : __("Not ready yet. If this persists, contact support.") }}
			</span>
		</div>
		<p class="text-p-xs text-ink-gray-5">
			{{ __("Ask {0} for changes from the AI tab of any page. It edits the page you have open and never another site's pages.", [assistant]) }}
		</p>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { assistantName } from "@/utils/neofficeBoot";
import { createResource } from "frappe-ui";
import { onMounted, ref } from "vue";

const assistant = assistantName(__("AI"));
// the same state upstream's setup flow reads; it never returns a key
const ready = ref(false);

onMounted(async () => {
	const state = (await createResource({ url: "builder.ai.api.ai_setup_state" })
		.submit()
		.catch(() => null)) as { configured?: boolean } | null;
	ready.value = !!state?.configured;
});
</script>
