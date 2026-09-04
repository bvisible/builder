<template>
	<Dialog
		title="Save as Block Template"
		size="sm"
		:actions="[
			{
				label: 'Save',
				variant: 'solid',
				//// Neoffice — the dialog's fields are read into locals before the await: the reactive object is
				//// reset while the save is in flight (83b20f91, re-applied at merge 721cf013).
				onClick: async (close: () => void) => {
					// Copy values before async operation
					const name = blockTemplateProperties.templateName;
					const cat = blockTemplateProperties.category;
					const preview = blockTemplateProperties.previewImage;
					const desc = blockTemplateProperties.description;

					await blockTemplateStore.saveBlockTemplate(block, name, cat, preview, desc);
					close();
				},
			},
		]"
		v-model="showBlockTemplateDialog">
		<template #default>
			<div class="flex flex-col gap-3">
				<BuilderInput
					type="text"
					v-model="blockTemplateProperties.templateName"
					label="Template Name"
					required
					:hideClearButton="true" />
				<BuilderInput
					type="select"
					v-model="blockTemplateProperties.category"
					label="Category"
					:options="blockTemplateStore.blockTemplateCategoryOptions"
					:hideClearButton="true" />
				<!-- //// Neoffice — a description field: it is what the AI generator picks a template by (83b20f91). -->
				<BuilderInput
					type="textarea"
					v-model="blockTemplateProperties.description"
					label="Description"
					placeholder="Describe this template for AI selection..."
					:hideClearButton="true" />
				<div class="relative">
					<BuilderInput
						type="text"
						v-model="blockTemplateProperties.previewImage"
						label="Preview Image"
						:hideClearButton="true" />
					<FileUploader
						file-types="image/*"
						@success="
							(file: FileDoc) => {
								blockTemplateProperties.previewImage = file.file_url;
							}
						">
						<template v-slot="{ openFileSelector }">
							<div class="absolute bottom-0 right-0 place-items-center">
								<Button size="sm" @click="openFileSelector" class="text-sm">Upload</Button>
							</div>
						</template>
					</FileUploader>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import type Block from "@/block";
import Dialog from "@/components/Controls/Dialog.vue";
import useBlockTemplateStore from "@/stores/blockTemplateStore";
import { FileUploader } from "frappe-ui";
import { ref } from "vue";

const showBlockTemplateDialog = ref(false);
defineProps<{
	block: Block;
}>();

const blockTemplateStore = useBlockTemplateStore();
const blockTemplateProperties = ref({
	templateName: "",
	category: "" as (typeof blockTemplateStore.blockTemplateCategoryOptions)[number],
	previewImage: "",
	//// Neoffice — see the description field above (83b20f91).
	description: "",
});
</script>
