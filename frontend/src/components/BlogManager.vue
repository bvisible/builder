<template>
	<!-- The blog app administers itself through the Frappe desk, which the Studio
	     hides. Without this screen, enabling the blog gives an owner a site
	     section they can read but never write. -->
	<Dialog v-model="show" :options="{ size: '5xl' }">
		<template #body>
			<div class="flex h-[82vh] flex-col gap-4 p-5">
				<div class="flex items-center gap-3">
					<span class="lucide-newspaper size-4 text-ink-gray-8" aria-hidden="true" />
					<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Articles") }}</h2>
					<span v-if="status.counts" class="text-xs text-ink-gray-5">
						{{ status.counts.published }} {{ __("published") }} ·
						{{ status.counts.draft }} {{ __("drafts") }}
					</span>
					<div class="flex-1" />
					<Button v-if="!editing" variant="solid" icon-left="lucide-plus" @click="startNew">
						{{ __("New article") }}
					</Button>
				</div>

				<!-- List -->
				<template v-if="!editing">
					<!-- Writing one is the thing this screen is for; searching is
					     what you do once there are enough to search. -->
					<div class="flex items-end gap-2 rounded-lg border border-outline-gray-1 p-3">
						<FormControl
							size="sm"
							class="flex-1"
							:label="__('Ask the AI for an article')"
							:placeholder="__('What should it be about? e.g. how we roast our Ethiopian beans')"
							:modelValue="topic"
							:disabled="writing"
							@update:modelValue="(v: string) => (topic = v)"
							@keydown.enter="writeArticle" />
						<Button
							variant="solid"
							icon-left="lucide-sparkles"
							:loading="writing"
							:disabled="!topic.trim()"
							@click="writeArticle">
							{{ __("Write it") }}
						</Button>
					</div>
					<p v-if="writing" class="text-xs text-ink-gray-5">
						{{ __("Writing — this takes about a minute. It lands as a draft.") }}
					</p>

					<div class="flex items-center gap-2">
						<FormControl
							size="sm"
							class="w-64"
							:placeholder="__('Search articles')"
							:modelValue="search"
							@update:modelValue="(v: string) => (search = v)" />
						<FormControl
							type="select"
							size="sm"
							:options="statusOptions"
							:modelValue="statusFilter"
							@update:modelValue="(v: string) => (statusFilter = v)" />
					</div>

					<div class="min-h-0 flex-1 overflow-y-auto">
						<div v-if="loading" class="p-6 text-sm text-ink-gray-5">{{ __("Loading...") }}</div>
						<div v-else-if="!posts.length" class="p-6 text-sm text-ink-gray-5">
							{{ __("No article yet. The first one takes a title and a paragraph.") }}
						</div>
						<div v-else class="flex flex-col divide-y divide-outline-gray-1">
							<div
								v-for="post in posts"
								:key="post.name"
								class="flex items-center gap-3 py-2.5">
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										<span class="truncate text-sm font-medium text-ink-gray-8">
											{{ post.title }}
										</span>
										<span
											class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
											:class="
												post.published
													? 'bg-surface-green-2 text-ink-green-3'
													: 'bg-surface-gray-2 text-ink-gray-6'
											">
											{{ post.published ? __("Published") : __("Draft") }}
										</span>
									</div>
									<div class="truncate text-xs text-ink-gray-5">
										/{{ post.route }}
										<template v-if="post.blog_category"> · {{ post.blog_category }}</template>
									</div>
								</div>
								<Button
									variant="ghost"
									size="sm"
									:label="post.published ? __('Unpublish') : __('Publish')"
									@click="togglePublished(post)" />
								<Button
									variant="ghost"
									size="sm"
									icon="lucide-external-link"
									:title="__('View on the site')"
									:disabled="!post.published"
									@click="openOnSite(post)" />
								<Button variant="ghost" size="sm" icon="lucide-pencil" @click="startEdit(post)" />
								<Button
									variant="ghost"
									size="sm"
									icon="lucide-trash-2"
									@click="removePost(post)" />
							</div>
						</div>
					</div>
				</template>

				<!-- Editor -->
				<template v-else>
					<div class="min-h-0 flex-1 overflow-y-auto pr-1">
						<div class="flex flex-col gap-3">
							<FormControl
								size="sm"
								:label="__('Title')"
								:modelValue="draft.title"
								@update:modelValue="(v: string) => (draft.title = v)" />
							<div class="grid grid-cols-2 gap-3">
								<FormControl
									type="select"
									size="sm"
									:label="__('Category')"
									:options="categoryOptions"
									:modelValue="draft.blog_category"
									@update:modelValue="(v: string) => (draft.blog_category = v)" />
								<FormControl
									type="select"
									size="sm"
									:label="__('Format')"
									:options="['Markdown', 'Rich Text', 'HTML']"
									:modelValue="draft.content_type"
									@update:modelValue="(v: string) => (draft.content_type = v)" />
							</div>
							<FormControl
								type="textarea"
								size="sm"
								:label="__('Intro')"
								:description="__('The paragraph shown in the list and in search results')"
								:modelValue="draft.blog_intro"
								@update:modelValue="(v: string) => (draft.blog_intro = v)" />
							<div>
								<label class="mb-1.5 block text-xs text-ink-gray-5">{{ __("Content") }}</label>
								<textarea
									v-model="contentField"
									rows="16"
									class="w-full rounded border border-outline-gray-2 bg-surface-white p-3 font-mono text-xs text-ink-gray-8 focus:border-outline-gray-4 focus:outline-none" />
							</div>
							<Switch
								size="sm"
								:label="__('Published')"
								:modelValue="!!draft.published"
								@update:modelValue="(v: boolean) => (draft.published = v ? 1 : 0)" />
						</div>
					</div>
					<div class="flex items-center gap-2 border-t border-outline-gray-1 pt-3">
						<Button variant="solid" :loading="saving" @click="savePost">
							{{ __("Save") }}
						</Button>
						<Button variant="subtle" @click="editing = false">{{ __("Cancel") }}</Button>
						<div class="flex-1" />
						<span v-if="draft.name" class="text-xs text-ink-gray-5">/{{ draftRoute }}</span>
					</div>
				</template>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { Button, createResource, Dialog, FormControl, Switch, toast } from "frappe-ui";
import { computed, reactive, ref, watch } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const API = "builder.blog_api";

const show = defineModel<boolean>({ default: false });

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Post = Record<string, any>;

const loading = ref(false);
const saving = ref(false);
const editing = ref(false);
const search = ref("");
const statusFilter = ref("all");
const posts = ref<Post[]>([]);
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const status = ref<Record<string, any>>({});
const draft = reactive<Post>({});
const draftRoute = ref("");
const topic = ref("");
const writing = ref(false);

// The article is written server-side against this site's own context — its
// business, the tone the design brief settled on, the pages that exist. It
// lands as a draft: nobody should find a post on their site because a
// generation finished.
async function writeArticle() {
	const subject = topic.value.trim();
	if (!subject || writing.value) return;
	writing.value = true;
	try {
		const r = await call("write_article", { topic: subject });
		topic.value = "";
		toast.success(__("Draft ready: {0}").replace("{0}", r.title));
		await refresh();
		startEdit({ name: r.name });
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	} finally {
		writing.value = false;
	}
}

const statusOptions = [
	{ label: __("All"), value: "all" },
	{ label: __("Published"), value: "published" },
	{ label: __("Drafts"), value: "draft" },
];

const categoryOptions = computed(() =>
	(status.value.categories || []).map((c: Post) => ({ label: c.title || c.name, value: c.name })),
);

// Blog Post keeps the body in one of three fields depending on the format; the
// editor edits whichever one the chosen format uses.
const contentField = computed({
	get() {
		if (draft.content_type === "Rich Text") return draft.content || "";
		if (draft.content_type === "HTML") return draft.content_html || "";
		return draft.content_md || "";
	},
	set(value: string) {
		if (draft.content_type === "Rich Text") draft.content = value;
		else if (draft.content_type === "HTML") draft.content_html = value;
		else draft.content_md = value;
	},
});

async function call(method: string, args: Record<string, unknown> = {}) {
	return await createResource({ url: `${API}.${method}` }).submit(args);
}

async function refresh() {
	loading.value = true;
	try {
		status.value = await call("get_status");
		if (!status.value.ready) {
			posts.value = [];
			return;
		}
		posts.value = await call("list_posts", {
			search: search.value || undefined,
			status: statusFilter.value === "all" ? undefined : statusFilter.value,
		});
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	} finally {
		loading.value = false;
	}
}

watch(show, (open) => {
	if (open) {
		editing.value = false;
		refresh();
	}
});
watch([search, statusFilter], () => {
	if (show.value && !editing.value) refresh();
});

function startNew() {
	Object.keys(draft).forEach((k) => delete draft[k]);
	Object.assign(draft, {
		title: "",
		blog_intro: "",
		content_type: "Markdown",
		content_md: "",
		published: 0,
		blog_category: status.value.categories?.[0]?.name || "",
	});
	draftRoute.value = "";
	editing.value = true;
}

async function startEdit(post: Post) {
	try {
		const full = await call("get_post", { name: post.name });
		Object.keys(draft).forEach((k) => delete draft[k]);
		Object.assign(draft, full);
		draftRoute.value = full.route || "";
		editing.value = true;
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	}
}

async function savePost() {
	if (!draft.title?.trim()) {
		toast.error(__("An article needs a title."));
		return;
	}
	saving.value = true;
	try {
		const r = await call("save_post", { post: { ...draft } });
		draft.name = r.name;
		draftRoute.value = r.route;
		toast.success(__("Saved"));
		editing.value = false;
		refresh();
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	} finally {
		saving.value = false;
	}
}

async function togglePublished(post: Post) {
	try {
		await call("set_published", { name: post.name, published: post.published ? 0 : 1 });
		refresh();
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	}
}

async function removePost(post: Post) {
	try {
		await call("delete_post", { name: post.name });
		toast.success(__("Deleted"));
		refresh();
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	}
}

function openOnSite(post: Post) {
	window.open(`/${post.route}`, "_blank");
}
</script>
