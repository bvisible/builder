<!-- //// Neoffice — added file (no upstream equivalent). The editor's Chat tab drawn by Nora's one conversation,
     nora.chat.Core of the app nora, the same as the desk's pages that talk with her (Jérémy, 13.11: « quand on
     améliore le chat on améliore partout »). What is the editor's own stays here and in upstream's controller
     (AIChatController, unchanged): the operations applied to the canvas, a block selected, a script opened, the model,
     the chats of each page. Upstream's panel (BuilderAIChatPanel.vue) is the tab where nora is not installed, and here
     if the conversation's files do not load. Canvas « Panneau Nora — Éditeur du Builder » (3 boards). -->
<template>
	<BuilderAIChatPanel v-if="fallback" />
	<div v-else ref="root" class="nora-editor-chat">
		<div class="nec-head">
			<img :src="orb" alt="" class="nec-head-orb" />
			<span class="nec-head-title">
				{{ __("{0} works on", [assistantLabel]) }}
				<strong>{{ pageTitle }}</strong>
			</span>
			<button
				v-if="modelPicker && builderStore.isAIEnabled"
				type="button"
				class="nec-head-model"
				:disabled="isSubmitting"
				@click="menu.open(modelLevel(bob))">
				<span>{{ modelLabel }}</span>
				<span class="lucide-chevron-down size-3.5" />
			</button>
			<Dropdown v-if="sessionOptions.length" :options="sessionOptions" :offset="6">
				<button
					type="button"
					class="nec-head-tool"
					:aria-label="__('Chats on this page')"
					:title="__('Chats on this page')"
					:disabled="isSubmitting">
					<span class="lucide-history size-[18px]" />
				</button>
			</Dropdown>
			<button
				v-if="builderStore.isAIEnabled"
				type="button"
				class="nec-head-tool"
				:aria-label="__('New chat')"
				:title="__('New chat')"
				:disabled="isSubmitting"
				@click="newSession">
				<span class="lucide-square-pen size-[18px]" />
			</button>
		</div>

		<div v-if="builderStore.isAIStateKnown && !builderStore.isAIEnabled" class="nec-setup">
			<img :src="orb" alt="" class="nec-setup-orb" />
			<p class="nec-setup-title">{{ __("Build pages by describing them") }}</p>
			<p class="nec-setup-text">
				{{ __("Connect a model first. Takes a minute if you already have an API key.") }}
			</p>
			<button type="button" class="nec-ink" @click="menu.open(connectLevel(bob))">
				{{ __("Set up AI") }}
			</button>
		</div>
		<div v-show="!builderStore.isAIStateKnown || builderStore.isAIEnabled" ref="host" class="nec-host" />

		<!-- the editor's own controls, above the entry: what the words will point at, the three doors, what holds -->
		<Teleport v-if="above" :to="above">
			<div v-if="selectedModelUnusable" class="nec-notice">
				<span class="lucide-key-round size-3.5 shrink-0" />
				<span class="flex-1">{{ __("{0} has no API key.", [modelLabel]) }}</span>
				<button type="button" @click="menu.open(providersLevel(bob))">{{ __("Add one") }}</button>
			</div>
			<div v-else-if="!isEditingPage" class="nec-notice">
				<span class="lucide-box size-3.5 shrink-0" />
				<span class="flex-1">{{ __("{0} only edits the page.", [assistantLabel]) }}</span>
				<button type="button" @click="canvasStore.exitFragmentMode()">{{ __("Back to page") }}</button>
			</div>
			<div v-if="attachedBlocks.length || attachableBlocks.length || showDoors" class="nec-tools">
				<span v-if="attachedBlocks.length" class="nec-tools-label">
					{{ __("For {0}:", [assistantLabel]) }}
				</span>
				<span v-for="block in attachedBlocks" :key="block.id" class="nec-chip">
					<span class="lucide-square-dashed size-3.5 shrink-0" />
					<span class="nec-chip-text">{{ block.label }}</span>
					<button
						type="button"
						class="nec-chip-x"
						:aria-label="__('Remove from context')"
						:title="__('Remove from context')"
						@click="chat.detachBlock(block.id)">
						<span class="lucide-x size-3" />
					</button>
				</span>
				<button
					v-if="attachableBlocks.length"
					type="button"
					class="nec-chip is-add"
					@click="chat.attachSelection()">
					<span class="lucide-plus size-3.5 shrink-0" />
					<span class="nec-chip-text">
						{{
							attachableBlocks.length === 1
								? attachableBlocks[0].getBlockDescription()
								: __("{0} selected blocks", [attachableBlocks.length])
						}}
					</span>
				</button>
				<template v-if="showDoors">
					<button
						v-for="door in doors"
						:key="door.key"
						type="button"
						class="nec-door"
						:disabled="sendingImages"
						@click="useDoor(door)">
						<span :class="door.icon" class="size-4 shrink-0" />
						<span>{{ door.key === "images" && sendingImages ? sendingLabel : door.label }}</span>
					</button>
				</template>
			</div>
			<!-- the "/" commands, just above the entry -->
			<div class="nec-menu-anchor">
				<AICommandMenu v-if="menuOpen" :menu="menu" />
			</div>
		</Teleport>
		<Teleport v-if="below" :to="below">
			<span>{{ __("Enter sends, Shift+Enter makes a new line. Type / for commands.") }}</span>
		</Teleport>
		<input ref="imagesInput" type="file" accept="image/*" multiple class="hidden" @change="pickImages" />
		<Dialog v-model="debugOpen" :title="__('Turn debug')" size="3xl">
			<template #default>
				<AIDebugPanel :debug="debugData" />
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import AIDebugPanel from "@/components/AIDebugPanel.vue";
import { AIChatController } from "@/components/AIChatController";
import BuilderAIChatPanel from "@/components/BuilderAIChatPanel.vue";
import Dialog from "@/components/Controls/Dialog.vue";
import AICommandMenu from "@/components/ai/AICommandMenu.vue";
import { registerBobCommands } from "@/components/ai/bobCommands";
import { useCommandMenu } from "@/components/ai/commandMenu";
import { connectLevel } from "@/components/ai/commands/connect";
import { modelLevel } from "@/components/ai/commands/models";
import { providersLevel } from "@/components/ai/commands/providers";
import type { BobContext } from "@/components/ai/commands/shared";
import { Painter, type PaintContext } from "@/components/ai/noraEditorChat";
import type { ChatMessage } from "@/components/ai/types";
import { isSiteCreationRoute, siteCreationSeed, SITE_CREATION_QUERY } from "@/composables/useSiteCreation";
import { reloadAIRegistry } from "@/data/aiModels";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { assistantName, showModelPicker } from "@/utils/neofficeBoot";
import { loadNoraChat } from "@/utils/noraChatHost";
import { Dropdown, toast } from "frappe-ui";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const assistantLabel = assistantName("Nora");
const modelPicker = showModelPicker();
const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

// the conversation's files may fail to load: upstream's panel then takes the tab, with a controller of its own
const fallback = ref(false);
const chat = new AIChatController();
const { prompt, isSubmitting, isCancelling, messages, modelLabel, isEditingPage, selectedModelUnusable } =
	chat;
const { sessions, sessionId, switchSession, newSession, deleteSession, isVisionModel } = chat;
const { attachedBlocks, attachableBlocks } = chat;

const orb = computed(() => `/assets/nora/images/nora-orb${builderStore.isDark ? "-dark" : ""}.svg`);
const pageTitle = computed(
	() => pageStore.activePage?.page_title || pageStore.activePage?.route || __("this page"),
);

// ─────────────── the chats of this page ───────────────

const truncateTitle = (title: string, max = 44) =>
	title.length > max ? title.slice(0, max - 1).trimEnd() + "…" : title;
const sessionOptions = computed(() => {
	if (!sessions.value.length) return [];
	return [
		{
			group: "Chats",
			hideLabel: true,
			options: sessions.value.map((s) => ({
				label: truncateTitle(s.title || __("New chat")),
				icon: s.name === sessionId.value ? "lucide-check" : "lucide-message-circle",
				onClick: () => switchSession(s.name),
			})),
		},
		{
			group: "Manage",
			hideLabel: true,
			options: [
				{ label: __("Delete current chat"), icon: "lucide-trash-2", theme: "red", onClick: deleteSession },
			],
		},
	];
});

// ─────────────── "/" commands (the model, the providers: the host's Administrator) ───────────────

const menu = useCommandMenu(prompt);
const { isOpen: menuOpen } = menu;
const bob: BobContext = {
	chat,
	menu,
	refreshAI: async () => {
		await reloadAIRegistry();
		chat.loadModels();
		await builderStore.refreshAIState();
	},
};
onUnmounted(registerBobCommands(bob));
onUnmounted(menu.close);

// ─────────────── the three doors (neoffice-maintenance#2614), as upstream's panel has them ───────────────

type Door = { key: string; icon: string; label: string; prompt: string; send: boolean };
const doors = computed<Door[]>(() => [
	{
		key: "text",
		icon: "lucide-pen-line",
		label: __("My text"),
		prompt: __("Here is the text for my site:") + "\n",
		send: false,
	},
	{ key: "images", icon: "lucide-image-plus", label: __("My images"), prompt: "", send: false },
	{
		key: "find",
		icon: "lucide-search",
		label: __("Find images"),
		prompt: __("Find images for my site and suggest a few for me to choose from."),
		send: true,
	},
]);
const showDoors = computed(() => builderStore.isAIEnabled && isEditingPage.value && !isSubmitting.value);
const imagesInput = ref<HTMLInputElement | null>(null);
const sendingImages = ref(false);
const sentImages = ref(0);
const totalImages = ref(0);
const sendingLabel = computed(() => __("Sending {0}/{1}…", [sentImages.value, totalImages.value]));

function useDoor(door: Door) {
	if (door.key === "images") return imagesInput.value?.click();
	prompt.value = door.prompt;
	if (door.send) chat.submitPrompt();
	else core?.focus();
}

async function pickImages(event: Event) {
	const input = event.target as HTMLInputElement;
	const chosen = Array.from(input.files || []);
	input.value = "";
	await sendImages(chosen);
}

/** The images go up as the editor's assets, then the assistant gets their addresses (the door « Mes images », and the
 * files dropped on the conversation's drop zone). */
async function sendImages(files: File[]) {
	const chosen = files.filter((file) => file.type.startsWith("image/"));
	if (!chosen.length || sendingImages.value) return;
	sendingImages.value = true;
	sentImages.value = 0;
	totalImages.value = chosen.length;
	const urls: string[] = [];
	for (const file of chosen) {
		const form = new FormData();
		form.append("file", file, file.name);
		form.append("is_private", "0");
		form.append("folder", "Home/Builder Uploads");
		try {
			const response = await fetch("/api/method/builder.api.upload_builder_asset", {
				method: "POST",
				headers: { "X-Frappe-CSRF-Token": (window as any).csrf_token || "" },
				body: form,
			});
			const url = (await response.json())?.message?.file_url;
			if (url) urls.push(url);
		} catch (e) {
			console.error("upload failed", file.name, e);
		}
		sentImages.value += 1;
	}
	sendingImages.value = false;
	if (!urls.length) return toast.error(__("Your images could not be sent."));
	prompt.value = __("Here are my images (logo, photos):") + "\n" + urls.join("\n");
	chat.submitPrompt();
}

// ─────────────── the first visit ───────────────

type Suggestion = { label: string; prompt: string };
// upstream panel's pools, the same strings (a fresh page: a site to describe; a page with content: a change)
const BUILD_POOL: Suggestion[] = [
	{
		label: __("A wood-fired pizzeria in Lausanne"),
		prompt: __(
			"Build a website for Forno, a wood-fired pizzeria in Lausanne. Warm, rustic-modern feel with big appetizing food photography and a cozy dark-terracotta palette. Sections: a hero with our story, the menu (wood-fired pizzas, small plates, natural wines), a photo gallery, and a visit section with hours and location.",
		),
	},
	{
		label: __("Landing page for a yoga studio"),
		prompt: __(
			"Build a landing page for Stillpoint, a boutique yoga studio. Calm, airy, minimal with soft natural tones and gentle motion. Sections: a hero, class types and schedule, the teachers, a membership/pricing section, and a book-a-first-class CTA.",
		),
	},
	{
		label: __("A craft coffee roaster"),
		prompt: __(
			"Build a website for Ember & Oak, a craft coffee roaster. Warm, artisanal, rich browns and texture. Sections: a hero, our roasts with tasting notes, the roasting story, wholesale info, and where to buy or visit.",
		),
	},
	{
		label: __("Event page for a design meetup"),
		prompt: __(
			"Build an event page for Design Jam, a monthly design meetup in Fribourg. Energetic, modern, poster-like. Sections: a hero with date, venue and RSVP, the speaker lineup, the schedule, past-event highlights, and sponsors.",
		),
	},
];
const EDIT_POOL: Suggestion[] = [
	{
		label: __("Add a testimonials section"),
		prompt: __(
			"Add a testimonials section with three or four short customer quotes, each with a name and role, styled to match the rest of the page.",
		),
	},
	{
		label: __("Make the hero more dramatic"),
		prompt: __(
			"Make the hero more dramatic: a larger headline, stronger contrast, a full-bleed background image or bold color, and a clear primary call-to-action.",
		),
	},
	{
		label: __("Tighten the spacing everywhere"),
		prompt: __(
			"Tighten the spacing across the page: reduce oversized gaps, align section padding to a consistent rhythm, and improve the vertical flow.",
		),
	},
	{
		label: __("Add a pricing section"),
		prompt: __(
			"Add a pricing section with three tiers (name, price, feature list, and a CTA button each), styled to match the page.",
		),
	},
	{
		label: __("Make it feel more premium"),
		prompt: __(
			"Make the page feel more premium: refine the typography and spacing, add depth with subtle shadows and borders, and elevate the color and imagery treatment.",
		),
	},
];
const sample3 = (pool: Suggestion[]) => [...pool].sort(() => Math.random() - 0.5).slice(0, 3);
const buildPicks = sample3(BUILD_POOL);
const editPicks = sample3(EDIT_POOL);
const pageHasContent = computed(() => (canvasStore.activeCanvas?.getRootBlock()?.children?.length ?? 0) > 0);

function welcome() {
	if (!core) return;
	const edit = pageHasContent.value;
	// the POT's extractor loses a call whose list of values opens on its line and closes on another (`__("…", [`)
	const named = [assistantLabel];
	const knows = __(
		"{0} knows this page and the style of the site. Say it in your own words: she does it in the draft, before your eyes.",
		named,
	);
	const describe = __(
		"Describe the page in your own words: {0} builds it in the draft, before your eyes.",
		named,
	);
	core.showWelcome({
		place: "center",
		title: edit ? __("What should we change?") : __("Tell me what you're building"),
		text: edit ? knows : describe,
		suggestions: (edit ? editPicks : buildPicks).map((s) => ({ label: s.label, value: s.prompt })),
	});
}

// ─────────────── the conversation ───────────────

const root = ref<HTMLElement | null>(null);
const host = ref<HTMLElement | null>(null);
const above = ref<HTMLElement | null>(null);
const below = ref<HTMLElement | null>(null);
let core: any = null;
let painter: Painter | null = null;

const inspect =
	(window as any).is_developer_mode === true && document.cookie.includes("user_id=Administrator");
const context = (): PaintContext => ({
	assistant: assistantLabel,
	working: isSubmitting.value,
	cancelling: isCancelling.value,
	editingPage: isEditingPage.value,
	pageHasDraft: Boolean(pageStore.activePage?.draft_blocks) || !pageStore.activePage?.published,
	blockExists: (id: string) => Boolean(canvasStore.activeCanvas?.findBlock(id)),
	blockLabel: (id: string) => {
		// « p | C'est ce regard… »: the words, without the element the canvas puts first
		const said = String(canvasStore.activeCanvas?.findBlock(id)?.getBlockDescription?.() || "");
		return said.includes(" | ") ? said.split(" | ").slice(1).join(" | ") : "";
	},
	inspect,
});

let frame = 0;
function repaint() {
	if (frame) return;
	frame = requestAnimationFrame(() => {
		frame = 0;
		if (!core || !painter) return;
		// the reader at the end of the conversation stays there as it grows (a long card arrives in one piece)
		const scroller = host.value?.querySelector<HTMLElement>(".nora-chat-messages");
		const atEnd = !scroller || scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 200;
		painter.paint(messages.value, context());
		if (scroller && atEnd) scroller.scrollTop = scroller.scrollHeight;
		// a card waiting counts as a conversation (see watchCards)
		const empty = !messages.value.length && !cardsDrawn.value;
		if (empty && !chat.isLoadingSession.value && builderStore.isAIEnabled) welcome();
		else if (!empty) core.hideWelcome();
		activity();
		core.setInputDisabled(isSubmitting.value || !isEditingPage.value || !builderStore.isAIEnabled);
		core.setUploadEnabled(
			isVisionModel.value && isEditingPage.value && !isSubmitting.value,
			__("{0} can't read images", [modelLabel.value]),
		);
	});
}

/** What she is doing, in the pill with Stop: the tool on the clock in the reader's words, else that she works. */
function activity() {
	if (!isSubmitting.value) return core.hideActivity();
	if (isCancelling.value) return core.showActivity(__("{0} stops…", [assistantLabel]));
	const last = messages.value.at(-1);
	const running = (last?.metadata?.steps || [])
		.filter((s: any) => s.kind === "tool" && s.status === "running")
		.at(-1);
	const label = running ? window.nora.chat.doing(running).running : __("{0} is working…", [assistantLabel]);
	core.showActivity(label, { on_stop: () => chat.cancel() });
}

watch(
	() => [
		messages.value,
		isSubmitting.value,
		isCancelling.value,
		isEditingPage.value,
		isVisionModel.value,
		builderStore.isAIEnabled,
		chat.isLoadingSession.value,
		pageStore.activePage?.draft_blocks,
		pageStore.activePage?.published,
	],
	repaint,
	{ deep: true },
);

/** A card's, a chip's or a step's gesture: what the editor does with it. */
function act(value: string, coreId: number) {
	const [what, ...rest] = String(value || "").split(":");
	const arg = rest.join(":");
	const message = painter?.messageOf(coreId);
	if (what === "block") return chat.selectBlockById(arg);
	if (what === "script") return chat.openScriptByName(arg);
	if (!message) return;
	if (what === "apply" || what === "skip") return chat.confirmPendingAction(message as ChatMessage, what);
	if (what === "revert") return chat.revertTurn(message as ChatMessage);
	if (what === "inspect") {
		debugData.value = message.metadata?.debug || null;
		debugOpen.value = true;
	}
}

const debugOpen = ref(false);
const debugData = ref<Record<string, any> | null>(null);

/** The conversation's modules, on as everywhere (Jérémy, 13.11: « si on fait partout la même chose, c'est mieux »); each
 * shows only when it serves. « Aide » and the blocks of an answer as on the desk; the drop zone's files go up as the
 * door « Mes images » sends them. `resume` keeps which chat of the page this is, and never offers its banner: the editor
 * reopens the page's last chat from the server by itself. The cards to validate are the person's waiting ones (an
 * e-mail to send, a dunning…): the editor has no chat of Nora's of its own, so they are read as anywhere else Nora is
 * and decided on the card. `use` is once per conversation: a module the conversation already turned on keeps its
 * options. */
function modules() {
	if (!core || !window.nora?.chat?.features) return;
	core.use("blocks", { help: true });
	core.use("dropzone", { accept: "image/*", multiple: true });
	core.use("resume", {
		key: `builder:${route.params.pageId || ""}`,
		offer: false,
		state: { session_id: sessionId.value },
	});
	// the editor's chat is the conversation the cards belong to (the page's, until its chat has an id): the server then
	// gives the cards still waiting and that chat's own, never the person's decided ones of every other conversation
	// (asked with none, it gave the twenty last ones, decided or not)
	core.use("action_cards", { conversation: () => sessionId.value || `builder:${route.params.pageId || ""}` });
	watchCards();
	core.on("files", ({ files }: { files: File[] }) => sendImages(files || []));
	core.on("resume", ({ state }: { state?: { session_id?: string } }) => {
		painter?.reset();
		// the conversation drawn again from nothing: the cards still waiting come back with it
		core?.features?.action_cards?.load();
		if (state?.session_id) switchSession(state.session_id);
	});
}

watch(sessionId, (id) => core?.features?.resume?.setState({ session_id: id }));

/** The cards are drawn by their module, not by the painter. A card waiting is a conversation too: the first visit
 * (which hides the conversation) steps aside for it, or the person would never see what waits for them. */
const cardsDrawn = ref(false);
let cardsWatch: MutationObserver | null = null;
function watchCards() {
	const list: HTMLElement | undefined = core?.$messages?.[0];
	if (!list || cardsWatch) return;
	cardsWatch = new MutationObserver(() => {
		const drawn = Boolean(list.querySelector(".nora-qc-action-card"));
		if (drawn === cardsDrawn.value) return;
		cardsDrawn.value = drawn;
		repaint();
	});
	cardsWatch.observe(list, { childList: true });
}

async function start() {
	let Core: any;
	try {
		Core = await loadNoraChat();
	} catch (error) {
		console.warn("[nora chat] upstream's panel takes the tab", error);
		chat.unmount();
		fallback.value = true;
		return;
	}
	if (!host.value) return;
	core = new Core({
		wrapper: host.value,
		assistant_name: assistantLabel,
		placeholder: __("Write to {0}…", [assistantLabel]),
		echo_user: false,
		enable_upload: true,
		upload_accept: "image/*",
		max_upload_size: 10 * 1024 * 1024,
	});
	painter = new Painter(core);
	above.value = core.slot("above");
	below.value = core.slot("below");
	modules();
	core.on("send", ({ message }: { message: string }) => {
		// the "/" menu is open: the words are a command being typed, they stay in the entry
		if (menuOpen.value) return core.setInputValue(message);
		prompt.value = message;
		if (!chat.canSubmit.value) {
			// nothing left: the words go back in the entry
			core.setInputValue(message);
			return;
		}
		chat.submitPrompt();
	});
	core.on("form_submit", ({ reply, display }: { reply: string; display: string }) =>
		chat.selectOption(reply, display),
	);
	core.on("card_action", ({ value, message_id }: { value: string; message_id: number }) =>
		act(value, message_id),
	);
	core.on("chip_click", ({ value, message_id }: { value: string; message_id: number }) =>
		act(value, message_id),
	);
	core.on("file_select", ({ file }: { file: File }) => chat.attachImageFile(file));
	core.on("file_remove", () => chat.clearImage());
	// the entry and the controller's prompt say the same thing (the "/" menu reads the prompt, the doors write it)
	host.value.addEventListener("input", (event) => {
		const target = event.target as HTMLTextAreaElement;
		if (target?.classList?.contains("nora-chat-input")) prompt.value = target.value;
	});
	// the "/" menu takes its keys before the entry sends
	host.value.addEventListener(
		"keydown",
		(event) => {
			if (event.isComposing || !menuOpen.value) return;
			if (menu.onKeydown(event)) event.stopPropagation();
		},
		true,
	);
	// a pasted image goes the paperclip's way
	host.value.addEventListener("paste", (event) => {
		const item = Array.from(event.clipboardData?.items || []).find((i) => i.type.startsWith("image/"));
		const file = item?.getAsFile();
		if (!file || !isVisionModel.value) return;
		event.preventDefault();
		core.attachFile(file);
	});
	repaint();
}

watch(prompt, (value) => {
	if (!core) return;
	const field = host.value?.querySelector<HTMLTextAreaElement>(".nora-chat-input");
	if (field && field.value !== value) core.setInputValue(value);
});

onMounted(() => {
	chat.mount();
	builderStore.refreshAIState();
	start();
});
onUnmounted(() => {
	if (!fallback.value) chat.unmount();
	cancelAnimationFrame(frame);
	cardsWatch?.disconnect();
});

// the tab usually loads behind another one, where the conversation cannot scroll
watch(
	() => builderStore.leftPanelActiveTab,
	(tab) => {
		if (tab === "Chat") nextTick(() => core?.scrollToBottom());
	},
);

// ─────────────── « Create my site with Nora » (?nora=site): the first message, once the chat is read ───────────────

const route = useRoute();
const router = useRouter();
const sessionRead = ref(false);
watch(
	chat.isLoadingSession,
	(loading, wasLoading) => {
		if (wasLoading && !loading) sessionRead.value = true;
	},
	{ immediate: true },
);
watch(
	() => [sessionRead.value, chat.selectedModel.value, isSubmitting.value],
	() => {
		if (!isSiteCreationRoute(route) || !sessionRead.value || !chat.selectedModel.value || isSubmitting.value)
			return;
		const query = { ...route.query };
		delete query[SITE_CREATION_QUERY];
		router.replace({ query });
		if (messages.value.length) return;
		prompt.value = siteCreationSeed();
		chat.submitPrompt();
	},
	{ immediate: true },
);
</script>

<style>
/* Karla and Forum, the design system's faces, are the desk's (neoffice_theme); the editor does not load them */
@font-face {
	font-family: "Forum";
	font-display: swap;
	src: url("/assets/neoffice_theme/fonts/webfonts/Forum-Regular.woff2") format("woff2");
}
@font-face {
	font-family: "Karla";
	font-weight: 200 800;
	font-display: swap;
	src: url("/assets/neoffice_theme/fonts/webfonts/Karla-VariableFont_wght.woff2") format("woff2");
}

/* the pane is the paper; Nora's answers lift off it on their cards (design system § 6.12) */
.nora-editor-chat {
	--nora-chat-bg: var(--color-bg);
	/* the desk's entry (neoffice_activity.nora_input) reads the desk's colours, which the editor does not have */
	--text-color: var(--text-primary);
	--text-muted: var(--text-secondary);
	--border-color: var(--border-default);
	display: flex;
	flex-direction: column;
	height: 100%;
	min-height: 100%;
	background: var(--color-bg);
	color: var(--text-primary);
	font-family: var(--font-sans);
}
.nora-editor-chat .nec-host {
	flex: 1;
	min-height: 0;
	display: flex;
	flex-direction: column;
}
.nec-head {
	flex: none;
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 10px 8px 14px;
	background: var(--surface-subtle);
	border-bottom: 1px solid var(--border-subtle);
}
.nec-head-orb {
	width: 22px;
	height: 22px;
	max-width: none;
}
.nec-head-title {
	flex: 1;
	min-width: 0;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	font-size: 14px;
	color: var(--text-secondary);
}
.nec-head-title strong {
	color: var(--text-primary);
}
.nec-head-tool,
.nec-head-model {
	display: inline-grid;
	place-items: center;
	height: 36px;
	min-width: 36px;
	border: 0;
	border-radius: 10px;
	background: transparent;
	color: var(--text-secondary);
	cursor: pointer;
}
.nec-head-model {
	display: inline-flex;
	gap: 4px;
	padding: 0 8px;
	max-width: 140px;
	font: inherit;
	font-size: 13px;
}
.nec-head-model span:first-child {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.nec-head-tool:hover:not(:disabled),
.nec-head-model:hover:not(:disabled) {
	background: var(--surface-sunken);
	color: var(--text-primary);
}
.nec-head-tool:disabled,
.nec-head-model:disabled {
	opacity: 0.5;
	cursor: default;
}
.nec-setup {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 10px;
	padding: 24px 24px 120px;
	text-align: center;
}
.nec-setup-orb {
	width: 56px;
	height: 56px;
	max-width: none;
}
.nec-setup-title {
	margin: 0;
	font-family: var(--font-display);
	font-size: 26px;
	line-height: 1.15;
}
.nec-setup-text {
	margin: 0;
	max-width: 320px;
	color: var(--text-secondary);
}
.nec-ink {
	height: 38px;
	padding: 0 16px;
	border: 0;
	border-radius: 10px;
	background: var(--sand-950);
	color: var(--paper-bright);
	font: inherit;
	font-weight: 600;
	cursor: pointer;
}
[data-theme="dark"] .nec-ink {
	background: var(--paper-bright);
	color: var(--sand-950);
}
.nec-notice {
	display: flex;
	align-items: center;
	gap: 8px;
	margin-bottom: 8px;
	padding: 6px 10px;
	border-radius: 10px;
	background: var(--surface-sunken);
	font-size: 13px;
	color: var(--text-secondary);
}
.nec-notice button {
	border: 0;
	background: transparent;
	font: inherit;
	font-weight: 600;
	color: var(--text-primary);
	text-decoration: underline;
	text-underline-offset: 2px;
	cursor: pointer;
}
.nec-tools {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 6px;
	padding-bottom: 8px;
}
.nec-tools-label {
	font-size: 13px;
	color: var(--text-secondary);
}
.nec-chip,
.nec-door {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	max-width: 100%;
	border: 1px solid var(--border-default);
	border-radius: 999px;
	background: var(--surface-card);
	font: inherit;
	color: var(--text-primary);
}
.nec-chip {
	height: 28px;
	padding: 0 4px 0 10px;
	font-size: 13px;
}
.nec-chip.is-add {
	padding: 0 10px;
	border-style: dashed;
	border-color: var(--border-strong);
	background: transparent;
	color: var(--text-secondary);
	cursor: pointer;
}
.nec-chip-text {
	max-width: 12rem;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.nec-chip-x {
	display: grid;
	place-items: center;
	width: 22px;
	height: 22px;
	border: 0;
	border-radius: 999px;
	background: transparent;
	color: var(--text-secondary);
	cursor: pointer;
}
.nec-door {
	height: 34px;
	padding: 0 12px;
	font-size: 14px;
	cursor: pointer;
}
.nec-door:hover:not(:disabled),
.nec-chip.is-add:hover,
.nec-chip-x:hover {
	border-color: var(--signal-400);
	background: var(--color-accent-soft);
}
.nec-door:disabled {
	opacity: 0.6;
	cursor: default;
}
.nec-menu-anchor {
	position: relative;
	height: 0;
}
</style>
