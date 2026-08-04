<template>
				<div class="flex h-full flex-1 flex-col gap-4 overflow-hidden p-6">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<span class="lucide-sparkles size-4 text-ink-gray-8" aria-hidden="true" />
						<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Create with AI") }}</h2>
					</div>
					<div class="flex items-center gap-3">
						<div v-if="progressPct > 0 && !generating && !genDone" class="flex items-center gap-2">
							<span class="text-xs capitalize text-ink-gray-6">{{ progressStep }}</span>
							<div class="h-1.5 w-24 overflow-hidden rounded-full bg-surface-gray-2">
								<div
									class="h-full rounded-full bg-surface-gray-7 transition-all"
									:style="{ width: progressPct + '%' }" />
							</div>
							<span class="text-xs text-ink-gray-6">{{ Math.round(progressPct) }}%</span>
						</div>
						<Button variant="ghost" :label="__('Start over')" @click="resetSession" />
					</div>
				</div>

				<div ref="msgBox" class="flex flex-1 flex-col gap-2 overflow-y-auto rounded-lg border border-outline-gray-1 p-4">
					<div
						v-for="(m, i) in messages"
						:key="i"
						class="max-w-[82%] whitespace-pre-wrap rounded-xl px-3.5 py-2 text-base leading-relaxed"
						:class="
							m.role === 'user'
								? 'self-end rounded-br-sm bg-surface-gray-7 text-ink-white'
								: m.role === 'err'
									? 'self-center bg-surface-red-1 text-ink-red-6 text-sm'
									: 'self-start rounded-bl-sm bg-surface-gray-1 text-ink-gray-9'
						"
						v-html="md(m.content)" />
					<div v-if="confirmButtons.length" class="flex gap-2 self-start">
						<Button
							v-for="b in confirmButtons"
							:key="b.value"
							variant="subtle"
							:label="b.label"
							@click="answerConfirm(b)" />
					</div>
					<div v-if="thinking" class="self-start text-sm text-ink-gray-5">{{ __("Thinking...") }}</div>
				</div>

				<div v-if="generating" class="flex items-center gap-3 rounded-lg border border-outline-gray-1 p-3">
					<span class="size-4 animate-spin rounded-full border-2 border-outline-gray-3 border-t-ink-gray-8" />
					<div class="flex flex-col">
						<span class="text-base text-ink-gray-9">{{ __("Generating your site...") }}</span>
						<span class="text-sm text-ink-gray-6">{{ genMessage || __("This takes a few minutes.") }}</span>
					</div>
				</div>
				<div
					v-else-if="imagesRunning"
					class="flex items-center gap-3 rounded-lg border border-outline-gray-1 p-3">
					<span class="size-4 animate-spin rounded-full border-2 border-outline-gray-3 border-t-ink-gray-8" />
					<div class="flex flex-1 flex-col gap-1">
						<span class="text-base text-ink-gray-9">
							{{ __("Generating images ({0}/{1})").format(imagesDone, imagesTotal) }}
						</span>
						<div class="h-1.5 w-full overflow-hidden rounded-full bg-surface-gray-2">
							<div
								class="h-full rounded-full bg-surface-gray-7 transition-all"
								:style="{ width: imagesPct + '%' }" />
						</div>
						<span class="text-sm text-ink-gray-6">{{ __("Your pages are ready — you can already edit them.") }}</span>
					</div>
				</div>
				<div v-else-if="genDone" class="flex items-center justify-between rounded-lg bg-surface-green-1 p-3">
					<span class="text-base text-ink-green-6">{{ __("Your site is ready!") }}</span>
					<Button variant="solid" :label="__('View my pages')" @click="finish" />
				</div>

				<!-- The brief is what every page was generated from. It was already
				     saved on the session and read back to generate the remaining
				     pages; it just had nowhere to be read by a person. "Why is my
				     site like this?" has an answer now — and it stays available
				     long after the generation that produced it. -->
				<div v-if="briefGroups.length && !generating && !imagesRunning" class="flex flex-col gap-2">
					<button
						class="flex w-fit items-center gap-1.5 text-sm text-ink-gray-6 hover:text-ink-gray-8"
						@click="showBrief = !showBrief">
						<span
							class="inline-block size-3.5"
							:class="showBrief ? 'lucide-chevron-down' : 'lucide-chevron-right'"
							aria-hidden="true" />
						{{ __("What the AI decided") }}
					</button>
					<div
						v-if="showBrief"
						class="flex flex-col gap-3 rounded-lg border border-outline-gray-1 p-3">
						<div v-for="group in briefGroups" :key="group.title" class="flex flex-col gap-1">
							<span class="text-xs font-medium uppercase text-ink-gray-5">{{ group.title }}</span>
							<div
								v-for="row in group.rows"
								:key="row.label"
								class="flex items-start gap-2 text-sm">
								<span class="w-36 shrink-0 text-ink-gray-5">{{ row.label }}</span>
								<span class="flex items-center gap-1.5 text-ink-gray-8">
									<span
										v-if="row.is_color"
										class="size-3 shrink-0 rounded-sm border border-outline-gray-2"
										:style="{ background: row.value }" />
									{{ row.value }}
								</span>
							</div>
						</div>
					</div>
				</div>

				<!-- One composer, the way a chat should look: the textarea and its
				     controls share a single rounded surface, attachments sit bottom
				     left, send is a round arrow bottom right. No stack of buttons
				     hanging off the side. -->
				<div
					v-if="!generating && !genDone && !imagesRunning"
					class="flex flex-col gap-2 rounded-2xl border border-outline-gray-2 bg-surface-white p-2 focus-within:border-outline-gray-4">
					<textarea
						ref="composer"
						v-model="draft"
						rows="2"
						class="max-h-40 w-full resize-none border-0 bg-transparent px-2 py-1.5 text-base text-ink-gray-9 outline-none placeholder:text-ink-gray-4 focus:ring-0"
						:placeholder="__('Describe your site — for example: a showcase site for my bakery in Lausanne')"
						:disabled="thinking"
						@input="autoGrow"
						@keydown.enter.exact.prevent="send" />

					<div class="flex items-center justify-between gap-2 px-1">
						<div class="flex items-center gap-2 text-ink-gray-6">
							<!-- One attach button. A client hands over what they have —
							     a logo, photos of the shop, a PDF menu — without having to
							     say which is which; the server sorts it out. -->
							<input
								ref="contentInput"
								type="file"
								multiple
								class="hidden"
								@change="onFilesPicked" />
							<button
								class="flex size-8 items-center justify-center rounded-full hover:bg-surface-gray-2 hover:text-ink-gray-9"
								:class="{ 'text-ink-gray-9': attachmentSummary }"
								:title="__('Attach your logo, photos or documents')"
								@click="contentInput?.click()">
								<span class="lucide-paperclip size-4" aria-hidden="true" />
							</button>
							<!-- the logo, once it is the site's logo, shown as such -->
							<img
								v-if="logoUrl"
								:src="logoUrl"
								:title="__('This is your site logo')"
								class="size-7 rounded border border-outline-gray-2 bg-surface-white object-contain p-0.5"
								alt="" />
							<span v-if="attachmentSummary" class="text-xs text-ink-gray-5">
								{{ attachmentSummary }}
							</span>
							<span v-if="uploading" class="text-xs text-ink-gray-5">{{ __("Uploading...") }}</span>
						</div>

						<div class="flex items-center gap-2">
							<Button
								v-if="canGenerate"
								variant="solid"
								theme="blue"
								:label="__('Generate')"
								:disabled="triggering"
								@click="triggerGeneration" />
							<button
								class="flex size-8 items-center justify-center rounded-full bg-surface-gray-7 text-ink-white transition disabled:cursor-not-allowed disabled:bg-surface-gray-3"
								:disabled="thinking || !draft.trim()"
								:title="__('Send')"
								@click="send">
								<span class="lucide-arrow-up size-4" aria-hidden="true" />
							</button>
						</div>
					</div>
				</div>
			</div>
</template>
<script setup lang="ts">
import { allWebPages } from "@/data/allWebPages";
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import { createResource, FileUploadHandler, FormControl } from "frappe-ui";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";


const builderStore = useBuilderStore();

// `__` is installed globally by the translation plugin (see src/translation.ts).
// The cast keeps the `{0}` placeholder contract (`__("..").format(x)`) visible to TS.
const __ = window.__ as (message: string) => string & { format: (...args: unknown[]) => string };

type ChatMessage = { role: string; content: string };
type ChatButton = { label: string; value: string };



const API = "builder.api";

const sid = ref("");
const messages = ref<ChatMessage[]>([]);
const confirmButtons = ref<ChatButton[]>([]);
const draft = ref("");
const thinking = ref(false);
const triggering = ref(false);
const canGenerate = ref(false);
const progressStep = ref("");
const progressPct = ref(0);
const generating = ref(false);
const genDone = ref(false);

// The brief the generator worked from. Loaded once the site is done, because
// that is when someone asks why it looks the way it does.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const briefGroups = ref<any[]>([]);
const showBrief = ref(false);

// Once the site exists, writing an article is the obvious next thing — but
// only if this site has a blog. Offered as a chip so nobody has to guess the
// phrasing; typing "écris un article sur…" works just as well.
async function offerArticle() {
	try {
		const caps = await createResource({
			url: "builder.plugins.get_capabilities",
		}).submit({});
		if (caps?.blog === false) return;
	} catch {
		return;
	}
	confirmButtons.value = [
		...(confirmButtons.value || []),
		{ label: __("Write an article"), value: "__WRITE_ARTICLE__" },
	];
}

async function loadBrief() {
	if (!sid.value || briefGroups.value.length) return;
	try {
		const r = await createResource({ url: "builder.brief_view.get_brief" }).submit({
			session_id: sid.value,
		});
		briefGroups.value = r?.exists ? r.groups || [] : [];
	} catch {
		// the panel simply does not appear; never break the "site is ready" screen
		briefGroups.value = [];
	}
}

watch(genDone, (done) => {
	if (done) loadBrief();
});
const genMessage = ref("");
const msgBox = ref<HTMLElement>();
const uploading = ref(false);
const logoName = ref("");
const logoUrl = ref("");
const inspirationCount = ref(0);
const contentCount = ref(0);
const contentInput = ref<HTMLInputElement>();
const composer = ref<HTMLTextAreaElement>();

// the composer grows with the text instead of scrolling inside two fixed rows
const autoGrow = () => {
	const el = composer.value;
	if (!el) return;
	el.style.height = "auto";
	el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
};

// what is attached, in one short line under the icons — the icons alone say
// "you can attach", this says "you did"
const attachmentSummary = computed(() => {
	const bits: string[] = [];
	if (logoName.value) bits.push(__("logo"));
	if (inspirationCount.value) bits.push(__("{0} reference(s)").format(inspirationCount.value));
	if (contentCount.value) bits.push(__("{0} file(s)").format(contentCount.value));
	return bits.join(" · ");
});
// image generation runs after the pages exist, so it has its own progress
const imagesRunning = ref(false);
const imagesDone = ref(0);
const imagesTotal = ref(0);
const imagesPct = computed(() =>
	imagesTotal.value ? Math.round((imagesDone.value / imagesTotal.value) * 100) : 0,
);
let pollTimer: ReturnType<typeof setTimeout> | null = null;
let imagePollTimer: ReturnType<typeof setTimeout> | null = null;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const callPath = (path: string, params?: Record<string, any>) =>
	createResource({ url: path }).submit(params || {});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const call = (method: string, params?: Record<string, any>) => callPath(`${API}.${method}`, params);

const md = (t: string) => {
	const esc = String(t || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;");
	return esc.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
};

const scrollDown = () => nextTick(() => msgBox.value?.scrollTo({ top: msgBox.value.scrollHeight }));

const pushMessage = (role: string, content: string) => {
	messages.value.push({ role, content });
	scrollDown();
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const applyState = (r: any) => {
	if (!r) return;
	// a resumed session may already carry a brief, and it is worth reading long
	// after the generation that produced it
	if (sid.value) loadBrief();
	if (r.messages) {
		messages.value = r.messages.map((m: ChatMessage) => ({
			role: m.role === "user" ? "user" : "bot",
			content: m.content,
		}));
		scrollDown();
	}
	// every step comes with its own suggestions (themes, palettes, pages) —
	// they are how the wizard is meant to be answered
	if (r.buttons !== undefined) confirmButtons.value = r.buttons || [];
	if (r.current_step) progressStep.value = String(r.current_step).replace(/_/g, " ");
	if (r.completion_percentage != null) progressPct.value = r.completion_percentage;
	canGenerate.value = !!(
		r.status === "confirmation_required" ||
		r.ready_to_generate ||
		r.can_generate ||
		(r.completion_percentage || 0) >= 100 ||
		String(r.current_step || "").toLowerCase() === "generation"
	);
};

const boot = async () => {
	try {
		const r = await call("chat_start_session");
		sid.value = r.session_id;
		applyState(r);
		// a resumed session already carries what the user attached last time
		if (r.logo_image) logoName.value = String(r.logo_image).split("/").pop() || "";
		if (r.logo_url) logoUrl.value = r.logo_url;
		inspirationCount.value = r.inspiration_count || 0;
		contentCount.value = r.content_count || 0;
		// a generation may already be running from a previous visit
		try {
			const s = await call("chat_get_generation_status", { session_id: sid.value });
			const st = (s && (s.status || s.state)) || "";
			if (st === "running" || st === "queued") {
				generating.value = true;
				pollGeneration();
			} else if (st === "completed" || st === "success") {
				genDone.value = true;
				if (s.image_job_id) {
					imagesTotal.value = s.remaining_image_slots || 0;
					imagesRunning.value = true;
					pollImages();
				}
			}
		} catch {
			/* no active generation */
		}
	} catch (error) {
		pushMessage("err", error instanceof Error ? error.message : String(error));
	}
};

// process_message can itself start the generation (typing "go", or confirming a
// replace), and then the answer carries a job. Without this the modal keeps
// chatting while the site is already being built.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const maybeStartGenerating = (r: any) => {
	if (generating.value) return;
	if (r?.job_id || r?.status === "queued") {
		generating.value = true;
		pollGeneration();
	}
};

const send = async () => {
	const text = draft.value.trim();
	if (!text || !sid.value || thinking.value) return;
	draft.value = "";
	confirmButtons.value = [];
	pushMessage("user", text);
	thinking.value = true;
	try {
		const r = await call("chat_send_message", { session_id: sid.value, message: text });
		applyState(r);
		if (r && r.success === false) {
			pushMessage("err", r.message || __("Something went wrong"));
			return;
		}
		// the service answers under `response`; without this the assistant is
		// mute and the conversation cannot be carried on by typing at all
		if (r?.response || r?.message) pushMessage("bot", r.response || r.message);
		maybeStartGenerating(r);
	} catch (error) {
		pushMessage("err", error instanceof Error ? error.message : String(error));
	} finally {
		thinking.value = false;
	}
};

const triggerGeneration = async () => {
	triggering.value = true;
	messages.value = messages.value.filter((m) => m.role !== "err");
	try {
		const r = await call("chat_trigger_generation", { session_id: sid.value });
		if (r && r.success === false) {
			pushMessage("err", r.message || __("Could not start the generation"));
			return;
		}
		if (r && r.status === "confirmation_required") {
			pushMessage("bot", r.message || __("Please confirm."));
			confirmButtons.value = r.buttons || [];
			return;
		}
		generating.value = true;
		pollGeneration();
	} catch (error) {
		pushMessage("err", error instanceof Error ? error.message : String(error));
	} finally {
		triggering.value = false;
	}
};

// A chip is an answer like any other. Only the replace-confirmation ones start
// a generation, and the server says so — assuming it here left the modal
// claiming "generating" after every single suggestion click.
const answerConfirm = async (button: ChatButton) => {
	confirmButtons.value = [];
	pushMessage("user", button.label || button.value);
	thinking.value = true;
	try {
		const r = await call("chat_send_message", { session_id: sid.value, message: button.value });
		applyState(r);
		if (r && r.success === false) {
			pushMessage("err", r.message || __("Something went wrong"));
			return;
		}
		if (r?.response || r?.message) pushMessage("bot", r.response || r.message);
		maybeStartGenerating(r);
	} catch (error) {
		pushMessage("err", error instanceof Error ? error.message : String(error));
	} finally {
		thinking.value = false;
	}
};

// Photos and documents the client already has. They are not decoration: the
// generator places these photos in the pages and quotes the documents, so the
// site says what the business actually says.
const onFilesPicked = async (event: Event) => {
	const input = event.target as HTMLInputElement;
	const files = Array.from(input.files || []);
	input.value = ""; // let the same file be picked again after a failure
	if (!files.length || !sid.value) return;

	uploading.value = true;
	const uploaded: { file_url: string; filename: string }[] = [];
	try {
		for (const file of files) {
			const doc = await new FileUploadHandler().upload(file, {
				private: false,
				folder: "Home/Builder Uploads",
			});
			if (doc?.file_url) uploaded.push({ file_url: doc.file_url, filename: file.name });
		}
		if (!uploaded.length) throw new Error(__("No file could be uploaded."));

		const r = await call("chat_attach_files", {
			session_id: sid.value,
			files: JSON.stringify(uploaded),
		});
		if (r && r.success === false) {
			pushMessage("err", r.message || __("The upload failed."));
			return;
		}
		if (r?.logo_taken) logoName.value = uploaded[0]?.filename || "";
		if (r?.logo_url) logoUrl.value = r.logo_url;
		inspirationCount.value += r?.references_added || 0;
		contentCount.value += r?.content_added || 0;
		pushMessage("bot", r?.response || __("Files received."));
		applyState(r);
	} catch (error) {
		pushMessage("err", error instanceof Error ? error.message : String(error));
	} finally {
		uploading.value = false;
	}
};

// The understanding pass runs in a worker and announces itself when done.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const onContentUnderstood = (data: any) => {
	const results = (data && data.results) || [];
	if (!results.length) return;
	const bySection: Record<string, number> = {};
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	results.forEach((r: any) => {
		const s = r.section || "generic";
		bySection[s] = (bySection[s] || 0) + 1;
	});
	const detail = Object.entries(bySection)
		.map(([s, n]) => `${n} ${s}`)
		.join(", ");
	pushMessage(
		"bot",
		__("Content analysed — {0} item(s) ({1}). I will reuse it on the site.").format(
			results.length,
			detail,
		),
	);
};

const pollImages = async () => {
	try {
		const s = await call("chat_get_image_generation_status", { session_id: sid.value });
		imagesTotal.value = s?.total_images || imagesTotal.value;
		imagesDone.value = (s?.images_completed || 0) + (s?.images_failed || 0);
		const st = (s && (s.status || s.state)) || "";
		if (st === "completed" || st === "success" || st === "failed" || st === "error") {
			imagesRunning.value = false;
			allWebPages.reload();
			return;
		}
	} catch {
		// no image job on this session, or a transient error — stop claiming progress
		imagesRunning.value = false;
		return;
	}
	imagePollTimer = setTimeout(pollImages, 4000);
};

const pollGeneration = async () => {
	try {
		const s = await call("chat_get_generation_status", { session_id: sid.value });
		const st = (s && (s.status || s.state)) || "";
		if (s && (s.message || s.progress_message || s.current_step))
			genMessage.value = s.message || s.progress_message || s.current_step;
		if (st === "completed" || st === "success" || s.done) {
			generating.value = false;
			genDone.value = true;
			allWebPages.reload();
			offerArticle();
			// pages exist; illustrations keep coming in the background
			if (s.image_job_id) {
				imagesTotal.value = s.remaining_image_slots || 0;
				imagesDone.value = 0;
				imagesRunning.value = true;
				pollImages();
			}
			return;
		}
		if (st === "failed" || st === "error") {
			generating.value = false;
			pushMessage("err", (s && s.error) || __("The generation failed."));
			return;
		}
	} catch {
		/* transient */
	}
	pollTimer = setTimeout(pollGeneration, 3000);
};

const resetSession = async () => {
	try {
		if (sid.value) await call("chat_clear_session", { session_id: sid.value });
	} catch {
		/* best effort */
	}
	sid.value = "";
	messages.value = [];
	confirmButtons.value = [];
	canGenerate.value = false;
	progressPct.value = 0;
	progressStep.value = "";
	generating.value = false;
	genDone.value = false;
	logoName.value = "";
	logoUrl.value = "";
	inspirationCount.value = 0;
	contentCount.value = 0;
	imagesRunning.value = false;
	imagesDone.value = 0;
	imagesTotal.value = 0;
	if (imagePollTimer) {
		clearTimeout(imagePollTimer);
		imagePollTimer = null;
	}
	boot();
};

const finish = () => {
	allWebPages.reload();
	router.push({ name: "home" });
};

// A page now: it boots when it mounts and lets go when it unmounts.
onMounted(() => {
	if (!sid.value) boot();
	builderStore.realtime?.on("content_assets_understood", onContentUnderstood);
});
onBeforeUnmount(() => {
	builderStore.realtime?.off("content_assets_understood", onContentUnderstood);
});


onBeforeUnmount(() => {
	builderStore.realtime?.off("content_assets_understood", onContentUnderstood);
	if (pollTimer) clearTimeout(pollTimer);
	if (imagePollTimer) clearTimeout(imagePollTimer);
});
</script>
