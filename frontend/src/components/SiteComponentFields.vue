<!-- //// Neoffice — added file (no upstream equivalent): the options form of one catalogued component.

	 One form for both uses of the Site blocks panel, adding a component and changing the one that is selected:
	 the labels, the choices and the bounds come from what the component declares on the server, so a new
	 parameter appears here the day it is declared. The form only holds what was typed; what is sent, and what
	 is refused, is decided on the server (builder.api.render_component_tag). -->
<template>
	<div class="flex flex-col gap-2">
		<div v-for="param in component.params" :key="param.name">
			<!-- a parameter with a few valid values is a list to pick from, not a text to get right -->
			<BuilderInput
				v-if="param.choices?.length"
				type="select"
				:label="param.label"
				:options="optionsOf(param)"
				:modelValue="selected(param)"
				@update:modelValue="(v: string) => (form.typed[param.name] = String(v))" />
			<label v-else-if="param.type === 'bool'" class="flex items-start gap-2 text-p-sm text-ink-gray-7">
				<input
					type="checkbox"
					class="mt-0.5"
					:checked="Boolean(form.flags[param.name] ?? param.default)"
					@change="(e) => (form.flags[param.name] = (e.target as HTMLInputElement).checked)" />
				<span>
					<span class="font-medium">{{ param.label }}</span>
					<span v-if="param.about" class="block text-ink-gray-5">{{ param.about }}</span>
				</span>
			</label>
			<!-- //// BuilderInput emits update:modelValue on `change` — that is, on blur — and debounced by
				 100ms, while it emits `input` on every keystroke. Clicking the button right after typing
				 fired the handler BEFORE the debounce, so the value was still unset and the block landed
				 without it (found on screen, 2026-09-16). Listening to both closes that race: `input` for
				 typing, and update:modelValue for the number arrows, which emit only that one. -->
			<BuilderInput
				v-else
				:type="param.type === 'int' ? 'number' : 'text'"
				:label="param.label"
				:description="param.about"
				:placeholder="String(param.default ?? '')"
				:min="param.min"
				:max="param.max"
				:modelValue="form.typed[param.name] ?? ''"
				@input="(v: string) => (form.typed[param.name] = v)"
				@update:modelValue="(v: string) => (form.typed[param.name] = String(v ?? ''))" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import type { OptionsForm, Param, SiteComponent } from "@/utils/siteComponents";

defineProps<{ component: SiteComponent }>();
// the form is the parent's: this component fills it in place, the parent reads it when it sends
const form = defineModel<OptionsForm>("form", { required: true });

// what a select shows before anything is picked: the component's own default, which is also what an untouched
// field sends (nothing)
const selected = (param: Param) =>
	form.value.typed[param.name] ?? String(param.default ?? param.choices?.[0]?.value ?? "");

const optionsOf = (param: Param) =>
	(param.choices || []).map((choice) => ({
		value: choice.value,
		label: choice.value === String(param.default) ? __("{0} (default)", [choice.label]) : choice.label,
	}));
</script>
