<template>
	<Dialog v-model="show" :options="{ size: '5xl' }">
		<template #body>
			<div class="flex h-[80vh] flex-col gap-4 p-5">
				<div class="flex items-center justify-between gap-3">
					<div class="flex items-center gap-2">
						<span class="lucide-image size-4 text-ink-gray-8" aria-hidden="true" />
						<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Media") }}</h2>
					</div>
					<div class="flex items-center gap-1 rounded-md bg-surface-gray-2 p-0.5">
						<button
							v-for="t in tabs"
							:key="t.key"
							class="rounded px-3 py-1 text-sm"
							:class="
								tab === t.key
									? 'bg-surface-white text-ink-gray-9 shadow-sm'
									: 'text-ink-gray-6 hover:text-ink-gray-8'
							"
							@click="tab = t.key">
							{{ t.label }}
						</button>
					</div>
				</div>

				<!-- ============================== IMAGES ============================== -->
				<template v-if="tab === 'images'">
					<div class="flex flex-wrap items-center gap-3">
						<FormControl
							size="sm"
							type="text"
							class="w-64"
							:placeholder="__('Search by file name')"
							:modelValue="search"
							@update:modelValue="(v: string) => (search = v)" />
						<Switch
							size="sm"
							:label="__('Unused only')"
							:modelValue="unusedOnly"
							@update:modelValue="(v: boolean) => (unusedOnly = v)" />
						<span v-if="media.data" class="text-sm text-ink-gray-5">
							{{
								__("{0} image(s), {1} unused").format(
									media.data.total,
									media.data.unused,
								)
							}}
						</span>
						<span v-if="media.data?.external?.length" class="text-sm text-ink-gray-5">
							·
							{{ __("{0} remote image(s) on pages").format(media.data.external.length) }}
						</span>
					</div>

					<div class="flex min-h-0 flex-1 gap-4">
						<div class="flex-1 overflow-y-auto rounded-lg border border-outline-gray-1 p-3">
							<div v-if="media.loading" class="p-4 text-base text-ink-gray-5">
								{{ __("Loading...") }}
							</div>
							<div
								v-else-if="!media.data?.items?.length"
								class="p-4 text-base text-ink-gray-5">
								{{ __("No image yet.") }}
							</div>
							<div v-else class="grid grid-cols-4 gap-3">
								<button
									v-for="item in media.data.items"
									:key="item.name"
									class="flex flex-col gap-1.5 rounded-lg border p-1.5 text-left"
									:class="
										selected?.name === item.name
											? 'border-outline-gray-4 bg-surface-gray-1'
											: 'border-outline-gray-1 hover:border-outline-gray-3'
									"
									@click="selected = item">
									<div
										v-if="item.missing"
										class="flex aspect-[4/3] w-full items-center justify-center rounded bg-surface-gray-2">
										<span class="lucide-file-x size-5 text-ink-gray-4" aria-hidden="true" />
									</div>
									<img
										v-else
										:src="item.thumbnail_url || item.file_url"
										:alt="item.file_name"
										loading="lazy"
										class="aspect-[4/3] w-full rounded bg-surface-gray-1 object-contain" />
									<span class="truncate text-xs text-ink-gray-7">{{ item.file_name }}</span>
									<span
										class="truncate text-xs"
										:class="usageClass(item)">
										{{ usageLabel(item) }}
									</span>
								</button>
							</div>
						</div>

						<!-- the detail panel answers the only question that matters:
						     can I delete this, and what breaks if I do -->
						<div
							v-if="selected"
							class="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto rounded-lg border border-outline-gray-1 p-3">
							<img
								:src="selected.file_url"
								:alt="selected.file_name"
								class="w-full rounded border border-outline-gray-2 bg-surface-white object-contain" />
							<div class="flex flex-col gap-1">
								<span class="break-all text-sm font-medium text-ink-gray-8">
									{{ selected.file_name }}
								</span>
								<span class="text-xs text-ink-gray-5">{{ humanSize(selected.file_size) }}</span>
							</div>
							<div class="flex items-center gap-2">
								<code
									class="flex-1 truncate rounded bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-7">
									{{ selected.file_url }}
								</code>
								<Button
									size="sm"
									variant="ghost"
									icon="lucide-copy"
									:title="__('Copy the address')"
									@click="copyUrl(selected)" />
							</div>

							<div class="flex flex-col gap-1">
								<span class="text-xs font-medium uppercase tracking-wide text-ink-gray-5">
									{{ __("Used on") }}
								</span>
								<span v-if="selected.in_chrome" class="text-sm text-ink-gray-8">
									{{ __("The site logo") }}
								</span>
								<a
									v-for="page in selected.used_in"
									:key="page.page"
									:href="`/${page.route || ''}`"
									target="_blank"
									class="text-sm text-ink-blue-3 hover:underline">
									{{ page.title }}
									<span v-if="!page.published" class="text-ink-gray-5">
										({{ __("draft") }})
									</span>
								</a>
								<span
									v-if="!selected.in_chrome && !selected.used_in.length"
									class="text-sm text-ink-gray-5">
									{{ __("Nowhere — safe to delete.") }}
								</span>
							</div>

							<Button
								class="mt-auto"
								size="sm"
								theme="red"
								variant="subtle"
								:label="__('Delete')"
								:disabled="!selected.missing && (!!selected.in_chrome || selected.used_in.length > 0)"
								:loading="deleting"
								@click="remove(selected)" />
						</div>
					</div>
				</template>

				<!-- ============================== LINKS =============================== -->
				<template v-else>
					<div v-if="links.loading" class="text-base text-ink-gray-5">{{ __("Loading...") }}</div>
					<template v-else-if="links.data">
						<div class="flex gap-3 text-sm">
							<span class="rounded bg-surface-gray-2 px-2.5 py-1 text-ink-gray-7">
								{{ __("{0} internal").format(links.data.counts.internal) }}
							</span>
							<span class="rounded bg-surface-gray-2 px-2.5 py-1 text-ink-gray-7">
								{{ __("{0} external").format(links.data.counts.external) }}
							</span>
							<span
								class="rounded px-2.5 py-1"
								:class="
									links.data.counts.broken
										? 'bg-surface-red-1 text-ink-red-4'
										: 'bg-surface-green-1 text-ink-green-3'
								">
								{{ __("{0} leading nowhere").format(links.data.counts.broken) }}
							</span>
						</div>

						<div class="min-h-0 flex-1 overflow-y-auto rounded-lg border border-outline-gray-1">
							<div v-if="links.data.broken.length" class="p-3">
								<p class="mb-2 text-sm text-ink-gray-6">
									{{ __("These links point at a page that does not exist:") }}
								</p>
								<table class="w-full text-sm">
									<tbody>
										<tr
											v-for="(row, i) in links.data.broken"
											:key="i"
											class="border-b border-outline-gray-1 last:border-0">
											<td class="py-1.5 pr-3 text-ink-gray-7">{{ row.title }}</td>
											<td class="py-1.5 font-mono text-xs text-ink-red-4">{{ row.href }}</td>
										</tr>
									</tbody>
								</table>
							</div>
							<div v-else class="p-4 text-base text-ink-gray-5">
								{{ __("Every internal link lands somewhere.") }}
							</div>

							<div v-if="links.data.external.length" class="border-t border-outline-gray-1 p-3">
								<p class="mb-2 text-sm text-ink-gray-6">{{ __("External links") }}</p>
								<table class="w-full text-sm">
									<tbody>
										<tr
											v-for="(row, i) in links.data.external"
											:key="i"
											class="border-b border-outline-gray-1 last:border-0">
											<td class="py-1.5 pr-3 text-ink-gray-7">{{ row.title }}</td>
											<td class="truncate py-1.5 font-mono text-xs text-ink-gray-6">
												{{ row.href }}
											</td>
										</tr>
									</tbody>
								</table>
							</div>
						</div>
					</template>
				</template>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { watchDebounced } from "@vueuse/core";
import { Button, createResource, Dialog, FormControl, Switch, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const API = "builder.media";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MediaItem = any;

const show = defineModel<boolean>({ default: false });

const tabs = computed(() => [
	{ key: "images", label: __("Images") },
	{ key: "links", label: __("Links") },
]);
const tab = ref("images");
const search = ref("");
const unusedOnly = ref(false);
const selected = ref<MediaItem | null>(null);
const deleting = ref(false);

const media = createResource({
	url: `${API}.list_media`,
	makeParams: () => ({ search: search.value, unused_only: unusedOnly.value ? 1 : 0 }),
});

const links = createResource({ url: `${API}.list_links` });

// The index is built by walking every page, so it is not free: only fetch it
// when the tab is actually looked at, and re-fetch when the dialog reopens
// (a page may have changed in between).
watch(show, (open) => {
	if (!open) return;
	selected.value = null;
	media.fetch();
	if (tab.value === "links") links.fetch();
});
watch(tab, (value) => {
	if (value === "links" && !links.data) links.fetch();
});
watchDebounced([search, unusedOnly], () => show.value && media.fetch(), { debounce: 300 });

const usageLabel = (item: MediaItem) => {
	if (item.missing) return __("File is gone");
	if (item.in_chrome) return __("Site logo");
	const count = item.used_in?.length || 0;
	if (!count) return __("Not used");
	if (count === 1) return item.used_in[0].title;
	return __("{0} pages").format(count);
};

const usageClass = (item: MediaItem) => {
	if (item.missing) return "text-ink-red-4";
	return item.in_chrome || item.used_in?.length ? "text-ink-gray-5" : "text-ink-amber-3";
};

const humanSize = (bytes: number) => {
	if (!bytes) return "—";
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} kB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const copyUrl = async (item: MediaItem) => {
	try {
		await navigator.clipboard.writeText(item.file_url);
		toast.success(__("Address copied"));
	} catch {
		toast.error(__("Could not copy the address"));
	}
};

const remove = async (item: MediaItem) => {
	deleting.value = true;
	try {
		await createResource({ url: `${API}.delete_media` }).submit({ file_url: item.file_url });
		selected.value = null;
		toast.success(__("Image deleted"));
		media.fetch();
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	} finally {
		deleting.value = false;
	}
};
</script>
