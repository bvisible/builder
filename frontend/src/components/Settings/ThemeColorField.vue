<!-- //// Neoffice — added file (no upstream equivalent): a colour of the Theme screen, a text field next to a
     //// swatch. A bare colour input always holds a colour, so the "Empty: …" of a field could not be reached. -->
<template>
	<div class="flex flex-col gap-1.5">
		<div class="flex items-end gap-2">
			<FormControl
				size="sm"
				:label="label"
				:modelValue="modelValue"
				@update:modelValue="(v: string) => emit('update:modelValue', v)"
				placeholder="#000000"
				class="flex-1" />
			<input
				type="color"
				class="h-7 w-9 shrink-0 cursor-pointer rounded border border-outline-gray-2 bg-transparent"
				:value="modelValue || '#000000'"
				@input="(e: Event) => emit('update:modelValue', (e.target as HTMLInputElement).value)" />
		</div>
		<p v-if="description" class="text-p-xs text-ink-gray-5">{{ description }}</p>
	</div>
</template>

<script setup lang="ts">
import { FormControl } from "frappe-ui";

defineProps<{ label: string; description?: string; modelValue?: string }>();
const emit = defineEmits<{ (e: "update:modelValue", value: string): void }>();
</script>
