<template>
	<div class="no-scrollbar flex h-full w-full flex-col items-center gap-5 overflow-y-auto px-[2px]">
		<div class="flex w-full gap-5">
			<!-- meta -->
			<div class="flex flex-1 flex-col gap-4">
				<div class="flex flex-1 flex-col gap-4">
					<BuilderInput
						type="text"
						:label="__('Title')"
						:modelValue="pageStore.activePage?.page_title"
						@update:modelValue="(val: string) => pageStore.updateActivePage('page_title', val)" />
					<BuilderInput
						class="[&>div>textarea]:h-28"
						type="textarea"
						:label="__('Description')"
						:modelValue="pageStore.activePage?.meta_description"
						:hideClearButton="true"
						@update:modelValue="(val: string) => pageStore.updateActivePage('meta_description', val)" />
					<!-- //// Neoffice — the page's own settings of the top page band (page_header.py,
					     //// patches/add_page_top_fields.py): a subtitle of its own, or no band at all -->
					<BuilderInput
						type="text"
						:label="__('Top page subtitle')"
						:description="__('Under the title, in the band at the top of this page. Empty: the description, unless the page already shows it.')"
						:modelValue="topPageSubtitle"
						@update:modelValue="(val: string) => setPageField('page_header_subtitle', val)" />
					<Switch
						size="sm"
						:label="__('No top page on this page')"
						:description="__('The breadcrumb stays in the page for search engines.')"
						:modelValue="hideTopPage"
						@update:modelValue="(val: boolean) => setPageField('hide_page_header', val ? 1 : 0)" />
				</div>
				<div class="flex flex-1 flex-col justify-between gap-2">
					<ImageUploadInput
						:modelValue="pageStore.activePage?.meta_image"
						:label="__('Meta Image')"
						:placeholder="__('Upload Meta Image')"
						labelPosition="top"
						@update:modelValue="
							(url: string) => pageStore.updateActivePage('meta_image', url)
						"></ImageUploadInput>
				</div>
			</div>
			<!-- preview -->
			<div class="flex h-fit w-72 flex-shrink-0 flex-col justify-between gap-1">
				<span class="text-sm text-ink-gray-7">{{ __("Social Preview") }}</span>
				<div class="flex flex-1 flex-col rounded border border-outline-gray-2">
					<img
						:src="pageStore.activePage?.meta_image || pageStore.activePage?.preview"
						alt=""
						class="h-40 w-full rounded-t object-cover" />
					<div class="flex flex-1 flex-col gap-1 border-t border-outline-gray-2 p-2">
						<span class="text-base text-ink-gray-6">{{ pageStore.activePage?.route }}</span>
						<span class="text-base-medium mt-2 text-ink-gray-9">
							{{ pageStore.activePage?.page_title }}
						</span>
						<span class="line-clamp-3 text-base leading-5 text-ink-gray-6">
							{{ pageStore.activePage?.meta_description }}
						</span>
					</div>
				</div>
			</div>
		</div>
		<hr class="w-full border-outline-gray-2" />
		<div class="flex w-full flex-col gap-5">
			<BuilderInput
				type="text"
				:label="__('Canonical URL')"
				:description="
					__('Optional. Set this to specify a preferred version of this page for search engines.')
				"
				placeholder="https://example.com/preferred-page-url"
				:modelValue="pageStore.activePage?.canonical_url"
				:hideClearButton="true"
				@update:modelValue="(val: string) => pageStore.updateActivePage('canonical_url', val)" />
			<BuilderInput
				type="text"
				:label="__('Language')"
				:description="__('Language code for HTML (e.g., en, es, fr, de). Uses default if unset.')"
				placeholder="en"
				:modelValue="pageStore.activePage?.language"
				:hideClearButton="true"
				@update:modelValue="(val: string) => pageStore.updateActivePage('language', val)" />
		</div>
	</div>
</template>
<script setup lang="ts">
import ImageUploadInput from "@/components/ImageUploadInput.vue";
import usePageStore from "@/stores/pageStore";
const pageStore = usePageStore();
//// Neoffice — the top page fields are custom fields of Builder Page (patches/add_page_top_fields.py),
//// so they are not in the page's type
import { Switch } from "frappe-ui";
import { computed } from "vue";
const topPageSubtitle = computed(() => (pageStore.activePage as any)?.page_header_subtitle || "");
const hideTopPage = computed(() => !!(pageStore.activePage as any)?.hide_page_header);
const setPageField = (field: string, value: unknown) => pageStore.updateActivePage(field as any, value as any);
</script>
