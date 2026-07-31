<template>
	<Dialog v-model="show" :options="{ size: '3xl' }">
		<template #body>
			<div class="flex h-[78vh] flex-col gap-3 p-5">
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

				<div v-if="!generating && !genDone && !imagesRunning" class="flex flex-col gap-2">
					<!-- the client's own material: the brief reads the logo for its
					     palette and typographic personality, and the references
					     steer the visual direction -->
					<div class="flex items-center gap-3 text-xs text-ink-gray-6">
						<FileUploader file-types="image/*" @success="(f: FileDoc) => attach('logo', f.file_url)">
							<template v-slot="{ openFileSelector }">
								<button class="flex items-center gap-1 hover:text-ink-gray-9" @click="openFileSelector">
									<span class="lucide-image size-3.5" aria-hidden="true" />
									{{ logoName ? __("Logo: {0}").format(logoName) : __("Add the logo") }}
								</button>
							</template>
						</FileUploader>
						<FileUploader
							file-types="image/*"
							@success="(f: FileDoc) => attach('inspiration', f.file_url)">
							<template v-slot="{ openFileSelector }">
								<button class="flex items-center gap-1 hover:text-ink-gray-9" @click="openFileSelector">
									<span class="lucide-sparkles size-3.5" aria-hidden="true" />
									{{
										inspirationCount
											? __("{0} reference(s)").format(inspirationCount)
											: __("Add a reference")
									}}
								</button>
							</template>
						</FileUploader>
						<span v-if="uploading" class="text-ink-gray-5">{{ __("Uploading...") }}</span>
					</div>

					<div class="flex items-center gap-2">
						<FormControl
							type="textarea"
							class="flex-1"
							:modelValue="draft"
							@update:modelValue="(v: string) => (draft = v)"
							:placeholder="__('Describe your site — for example: a showcase site for my bakery in Lausanne')"
							:disabled="thinking"
							@keydown.enter.exact.prevent="send" />
						<div class="flex flex-col gap-2">
							<Button variant="solid" :label="__('Send')" :disabled="thinking || !draft.trim()" @click="send" />
							<Button
								v-if="canGenerate"
								variant="solid"
								theme="blue"
								:label="__('Generate')"
								:disabled="triggering"
								@click="triggerGeneration" />
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { allWebPages } from "@/data/allWebPages";
import { createResource, Dialog, FileUploader, FormControl } from "frappe-ui";
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

type FileDoc = { file_url: string; file_name?: string };

// `__` is installed globally by the translation plugin (see src/translation.ts).
// The cast keeps the `{0}` placeholder contract (`__("..").format(x)`) visible to TS.
const __ = window.__ as (message: string) => string & { format: (...args: unknown[]) => string };

type ChatMessage = { role: string; content: string };
type ChatButton = { label: string; value: string };

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits(["update:modelValue"]);
const show = computed({
	get: () => props.modelValue,
	set: (v: boolean) => emit("update:modelValue", v),
});

// v15 keeps the whole chat/generation stack inside the builder app itself
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
const genMessage = ref("");
const msgBox = ref<HTMLElement>();
const uploading = ref(false);
const logoName = ref("");
const inspirationCount = ref(0);
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
const call = (method: string, params?: Record<string, any>) =>
	createResource({ url: `${API}.${method}` }).submit(params || {});

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
	if (r.messages) {
		messages.value = r.messages.map((m: ChatMessage) => ({
			role: m.role === "user" ? "user" : "bot",
			content: m.content,
		}));
		scrollDown();
	}
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
		inspirationCount.value = r.inspiration_count || 0;
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
		if (r && r.success === false) pushMessage("err", r.message || __("Something went wrong"));
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

const answerConfirm = async (button: ChatButton) => {
	confirmButtons.value = [];
	try {
		const r = await call("chat_send_message", { session_id: sid.value, message: button.value });
		applyState(r);
		generating.value = true;
		pollGeneration();
	} catch (error) {
		pushMessage("err", error instanceof Error ? error.message : String(error));
	}
};

// The FileUploader has already stored the file; we only tell the session about it.
const attach = async (kind: "logo" | "inspiration", fileUrl: string) => {
	if (!sid.value || !fileUrl) return;
	uploading.value = true;
	try {
		const method = kind === "logo" ? "chat_upload_logo" : "chat_upload_inspiration";
		const r = await call(method, { session_id: sid.value, file_url: fileUrl });
		if (r && r.success === false) {
			pushMessage("err", r.message || __("The upload failed."));
			return;
		}
		if (kind === "logo") {
			logoName.value = fileUrl.split("/").pop() || "";
			pushMessage("bot", r?.message || __("Logo received — I will use its colours and style."));
		} else {
			inspirationCount.value += 1;
			pushMessage("bot", r?.message || __("Reference received — I will draw inspiration from it."));
		}
		applyState(r);
	} catch (error) {
		pushMessage("err", error instanceof Error ? error.message : String(error));
	} finally {
		uploading.value = false;
	}
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
	inspirationCount.value = 0;
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
	show.value = false;
};

watch(show, (open) => {
	if (open && !sid.value) boot();
	if (!open) {
		// nothing is displayed, so stop hitting the server
		if (pollTimer) {
			clearTimeout(pollTimer);
			pollTimer = null;
		}
		if (imagePollTimer) {
			clearTimeout(imagePollTimer);
			imagePollTimer = null;
		}
	}
	if (open && generating.value) pollGeneration();
	if (open && imagesRunning.value) pollImages();
});

onBeforeUnmount(() => {
	if (pollTimer) clearTimeout(pollTimer);
	if (imagePollTimer) clearTimeout(imagePollTimer);
});
</script>
