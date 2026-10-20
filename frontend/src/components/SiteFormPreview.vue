<!-- //// Neoffice — added file (no upstream equivalent): the live preview of a form while it is edited.

	 It draws the copy the dialog is working on, question by question, in the steps the form has, with the Next and
	 Back buttons working so a person can walk it. It is not the published form: the page draws that from the saved
	 record (builder/templates/includes/site_form.html) in the site's own style. This is the shape of it. -->
<template>
	<div
		class="rounded-lg border border-outline-gray-2 bg-surface-white p-4 text-ink-gray-8"
		data-testid="site-form-preview">
		<p v-if="count > 1" class="mb-2 text-p-sm text-ink-gray-5">
			{{ __("Step {0} of {1}", [step, count]) }}
		</p>
		<h4 v-if="count > 1 && definition.steps[step - 1]" class="mb-3 text-base font-semibold">
			{{ definition.steps[step - 1] }}
		</h4>

		<div v-for="(question, index) in current" :key="question.fieldname || `new-${index}`" class="mb-3">
			<!-- a consent box carries its sentence as its label -->
			<label v-if="question.type === 'Consent'" class="flex items-start gap-2 text-p-sm">
				<input type="checkbox" disabled class="mt-0.5" />
				<span>{{ question.label || __("The sentence to agree to") }}</span>
			</label>
			<template v-else>
				<p class="mb-1 text-p-sm font-medium">
					{{ question.label || __("Your question") }}
					<span v-if="question.required" class="text-ink-red-3">*</span>
				</p>
				<textarea
					v-if="question.type === 'Long text'"
					disabled
					rows="3"
					:placeholder="question.help"
					class="w-full rounded border border-outline-gray-2 bg-transparent px-2 py-1.5 text-base" />
				<div
					v-else-if="question.type === 'Single choice' || question.type === 'Checkboxes'"
					class="flex flex-col gap-1">
					<label
						v-for="(option, optionIndex) in choicesOf(question)"
						:key="optionIndex"
						class="flex items-center gap-2 text-p-sm">
						<input :type="question.type === 'Single choice' ? 'radio' : 'checkbox'" disabled />
						<span>{{ option }}</span>
					</label>
					<p v-if="question.help" class="text-p-xs text-ink-gray-5">{{ question.help }}</p>
				</div>
				<input
					v-else
					disabled
					:type="inputType(question)"
					:placeholder="question.type === 'Date' ? '' : question.help"
					class="w-full rounded border border-outline-gray-2 bg-transparent px-2 py-1.5 text-base" />
			</template>
		</div>

		<div class="mt-4 flex items-center justify-between gap-2">
			<button
				v-if="step > 1"
				type="button"
				class="text-p-sm text-ink-gray-6 underline"
				data-testid="preview-back"
				@click="step -= 1">
				{{ __("Back") }}
			</button>
			<span v-else />
			<button
				v-if="step < count"
				type="button"
				class="rounded bg-surface-gray-7 px-3 py-1.5 text-p-sm font-medium text-ink-white"
				data-testid="preview-next"
				@click="step += 1">
				{{ __("Next") }}
			</button>
			<button
				v-else
				type="button"
				disabled
				class="rounded bg-surface-gray-7 px-3 py-1.5 text-p-sm font-medium text-ink-white opacity-80">
				{{ definition.submit_text || __("Send Message") }}
			</button>
		</div>
		<p v-if="definition.dialog" class="mt-3 text-p-xs text-ink-gray-5">
			{{
				definition.button_text
					? __("On the page, the form waits behind the button “{0}”.", [definition.button_text])
					: __("On the page, the form waits in a window that any link to #contact opens.")
			}}
		</p>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { questionsOfStep, stepCount, type Question, type SiteFormDefinition } from "@/utils/siteForms";
import { computed, ref, watch } from "vue";

const props = defineProps<{ definition: SiteFormDefinition }>();

const step = ref(1);
const count = computed(() => stepCount(props.definition));
const current = computed(() => questionsOfStep(props.definition, step.value));

// a step removed while it was shown: stay on a step that exists
watch(count, (now) => {
	if (step.value > now) step.value = now;
});

const choicesOf = (question: Question) => {
	const options = question.options.map((option) => option.trim()).filter(Boolean);
	return options.length ? options : [__("A choice"), __("Another choice")];
};

const inputType = (question: Question) =>
	({ Email: "email", Phone: "tel", Date: "date" })[question.type as "Email" | "Phone" | "Date"] ?? "text";
</script>
