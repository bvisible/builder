<template>
	<div class="flex h-screen w-full">
		<!-- Sidebar -->
		<div class="flex w-80 flex-col border-r border-outline-gray-1 bg-surface-white">
			<!-- Header -->
			<div class="flex flex-col border-b border-outline-gray-1">
				<div class="flex items-center justify-between p-4">
					<div class="flex items-center gap-2">
						<button
							@click="goBack"
							class="flex size-8 items-center justify-center rounded text-ink-gray-7 hover:bg-surface-gray-2">
							<FeatherIcon name="arrow-left" class="size-4" />
						</button>
						<h1 class="text-lg font-semibold text-ink-gray-9">AI Builder</h1>
					</div>
					<button
						v-if="canGenerate"
						@click="generatePage"
						:disabled="generating"
						class="flex items-center gap-2 rounded-lg bg-surface-gray-7 px-3 py-2 text-sm font-medium text-white hover:bg-surface-gray-6 disabled:opacity-50">
						<FeatherIcon v-if="generating" name="loader" class="size-4 animate-spin" />
						<FeatherIcon v-else name="zap" class="size-4" />
						<span>{{ generating ? "Generating..." : "Generate" }}</span>
					</button>
				</div>
				<!-- AI Provider Badge -->
				<div v-if="aiConfig" class="flex items-center gap-2 border-t border-outline-gray-1 bg-surface-gray-1 px-4 py-2">
					<div
						:class="[
							'flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
							aiConfig.provider === 'ollama'
								? 'bg-green-100 text-green-700'
								: 'bg-blue-100 text-blue-700'
						]">
						<span class="size-1.5 rounded-full" :class="aiConfig.provider === 'ollama' ? 'bg-green-500' : 'bg-blue-500'"></span>
						{{ aiConfig.provider === 'ollama' ? 'Ollama' : 'OpenAI' }}
						<span v-if="aiConfig.ollama_model" class="text-green-600">{{ aiConfig.ollama_model }}</span>
					</div>
					<span v-if="connectionError" class="text-xs text-red-500">{{ connectionError }}</span>
				</div>
			</div>

			<!-- Chat Area -->
			<div class="flex flex-1 flex-col overflow-hidden">
				<div ref="chatContainer" class="flex-1 space-y-4 overflow-y-auto p-4">
					<div
						v-for="(message, index) in messages"
						:key="index"
						:class="[
							'flex',
							message.role === 'user' ? 'justify-end' : 'justify-start'
						]">
						<div
							:class="[
								'max-w-[85%] rounded-lg px-4 py-2 text-sm',
								message.role === 'user'
									? 'bg-surface-gray-7 text-white'
									: 'bg-surface-gray-2 text-ink-gray-9'
							]">
							<p class="whitespace-pre-wrap">{{ message.content }}</p>
						</div>
					</div>

					<div v-if="loading" class="flex justify-start">
						<div class="flex items-center gap-2 rounded-lg bg-surface-gray-2 px-4 py-2">
							<div class="flex gap-1">
								<div class="size-2 animate-bounce rounded-full bg-ink-gray-5" style="animation-delay: 0ms"></div>
								<div class="size-2 animate-bounce rounded-full bg-ink-gray-5" style="animation-delay: 150ms"></div>
								<div class="size-2 animate-bounce rounded-full bg-ink-gray-5" style="animation-delay: 300ms"></div>
							</div>
						</div>
					</div>
				</div>

				<!-- Input Area -->
				<div class="border-t border-outline-gray-1 p-4">
					<div class="flex gap-2">
						<input
							v-model="userInput"
							@keydown.enter="sendMessage"
							:disabled="loading || generating"
							type="text"
							placeholder="Describe your website..."
							class="flex-1 rounded-lg border border-outline-gray-2 bg-surface-white px-4 py-2 text-sm text-ink-gray-9 placeholder:text-ink-gray-4 focus:border-outline-gray-3 focus:outline-none disabled:opacity-50" />
						<button
							@click="sendMessage"
							:disabled="!userInput.trim() || loading || generating"
							class="flex size-10 items-center justify-center rounded-lg bg-surface-gray-7 text-white hover:bg-surface-gray-6 disabled:opacity-50">
							<FeatherIcon name="send" class="size-4" />
						</button>
					</div>
				</div>
			</div>
		</div>

		<!-- Preview Area -->
		<div class="flex flex-1 flex-col bg-surface-gray-1">
			<!-- Preview Header -->
			<div class="flex items-center justify-between border-b border-outline-gray-1 bg-surface-white px-4 py-3">
				<h2 class="text-sm font-medium text-ink-gray-7">Preview</h2>
				<div class="flex items-center gap-2">
					<button
						v-for="device in devices"
						:key="device.name"
						@click="previewDevice = device.name"
						:class="[
							'flex size-8 items-center justify-center rounded',
							previewDevice === device.name
								? 'bg-surface-gray-3 text-ink-gray-9'
								: 'text-ink-gray-5 hover:bg-surface-gray-2'
						]">
						<FeatherIcon :name="device.icon" class="size-4" />
					</button>
				</div>
			</div>

			<!-- Preview Content -->
			<div class="flex flex-1 items-center justify-center overflow-auto p-8">
				<div
					v-if="siteContext && Object.keys(siteContext).length > 0"
					:class="[
						'overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white shadow-lg transition-all duration-300',
						deviceWidthClass
					]">
					<SitePreview :context="siteContext" :blocks="previewBlocks" />
				</div>
				<div v-else class="flex flex-col items-center gap-4 text-center">
					<div class="flex size-16 items-center justify-center rounded-full bg-surface-gray-2">
						<FeatherIcon name="message-circle" class="size-8 text-ink-gray-4" />
					</div>
					<div>
						<h3 class="text-lg font-medium text-ink-gray-7">Start a conversation</h3>
						<p class="mt-1 text-sm text-ink-gray-5">
							Describe the website you want to create and I'll help you build it.
						</p>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from "vue";
import { useRouter } from "vue-router";
import { createResource } from "frappe-ui";
import SitePreview from "@/components/AIBuilder/SitePreview.vue";

const router = useRouter();

// State
const conversationId = ref<string | null>(null);
const messages = ref<Array<{ role: string; content: string }>>([]);
const siteContext = ref<Record<string, any>>({});
const previewBlocks = ref<any[]>([]);
const userInput = ref("");
const loading = ref(false);
const generating = ref(false);
const collectionComplete = ref(false);
const previewDevice = ref("desktop");
const chatContainer = ref<HTMLElement | null>(null);
const aiConfig = ref<{ provider: string; ollama_model?: string; ollama_base_url?: string } | null>(null);
const connectionError = ref<string | null>(null);

// Devices for preview
const devices = [
	{ name: "desktop", icon: "monitor", width: "w-full max-w-4xl" },
	{ name: "tablet", icon: "tablet", width: "w-[768px]" },
	{ name: "mobile", icon: "smartphone", width: "w-[375px]" },
];

const deviceWidthClass = computed(() => {
	const device = devices.find((d) => d.name === previewDevice.value);
	return device?.width || "w-full max-w-4xl";
});

const canGenerate = computed(() => {
	return collectionComplete.value && siteContext.value && Object.keys(siteContext.value).length > 0;
});

// API Resources
const startConversationResource = createResource({
	url: "builder.builder_ai.start_conversation",
	onSuccess(data: any) {
		conversationId.value = data.conversation_id;
		connectionError.value = null;
		if (data.message) {
			messages.value.push({
				role: "assistant",
				content: data.message,
			});
		}
		if (data.site_context) {
			siteContext.value = data.site_context;
		}
		loading.value = false;
		scrollToBottom();
	},
	onError(error: any) {
		console.error("Failed to start conversation:", error);
		loading.value = false;
		const errorMsg = error?.messages?.[0] || error?.message || "Connection failed";
		if (errorMsg.includes("Ollama") || errorMsg.includes("Cannot connect")) {
			connectionError.value = "Cannot connect to Ollama. Make sure it's running.";
			messages.value.push({
				role: "assistant",
				content: "I couldn't connect to the AI service. Please make sure Ollama is running (`ollama serve`) and try again.",
			});
		} else {
			messages.value.push({
				role: "assistant",
				content: `Error: ${errorMsg}`,
			});
		}
		scrollToBottom();
	},
});

const sendMessageResource = createResource({
	url: "builder.builder_ai.send_message",
	onSuccess(data: any) {
		if (data.message) {
			messages.value.push({
				role: "assistant",
				content: data.message,
			});
		}
		if (data.site_context) {
			siteContext.value = data.site_context;
		}
		if (data.collection_complete) {
			collectionComplete.value = true;
			fetchPreviewBlocks();
		}
		loading.value = false;
		scrollToBottom();
	},
	onError(error: any) {
		console.error("Failed to send message:", error);
		loading.value = false;
		messages.value.push({
			role: "assistant",
			content: "Sorry, I encountered an error. Please try again.",
		});
	},
});

const previewBlocksResource = createResource({
	url: "builder.builder_ai.preview_blocks",
	onSuccess(data: any) {
		if (data.blocks) {
			previewBlocks.value = data.blocks;
		}
	},
});

const generatePageResource = createResource({
	url: "builder.builder_ai.generate_page",
	onSuccess(data: any) {
		generating.value = false;
		if (data.success && data.page_name) {
			router.push(`/page/${data.page_name}`);
		}
	},
	onError(error: any) {
		console.error("Failed to generate page:", error);
		generating.value = false;
		messages.value.push({
			role: "assistant",
			content: "Sorry, I couldn't generate the page. Please try again.",
		});
	},
});

const aiConfigResource = createResource({
	url: "builder.builder_ai.get_ai_config",
	onSuccess(data: any) {
		aiConfig.value = data;
	},
});

const testConnectionResource = createResource({
	url: "builder.builder_ai.test_llm_connection",
	onSuccess(data: any) {
		if (!data.success) {
			connectionError.value = data.error || "Connection failed";
		} else {
			connectionError.value = null;
		}
	},
	onError(error: any) {
		connectionError.value = "Failed to test connection";
	},
});

// Methods
function goBack() {
	router.push("/");
}

function startConversation() {
	loading.value = true;
	startConversationResource.submit({ title: "New Website" });
}

function sendMessage() {
	if (!userInput.value.trim() || loading.value || generating.value) return;

	const message = userInput.value.trim();
	messages.value.push({
		role: "user",
		content: message,
	});
	userInput.value = "";
	loading.value = true;
	scrollToBottom();

	if (!conversationId.value) {
		// Start conversation first, then send message
		startConversationResource.submit({ title: "New Website" }).then(() => {
			sendMessageResource.submit({
				conversation_id: conversationId.value,
				message: message,
			});
		});
	} else {
		sendMessageResource.submit({
			conversation_id: conversationId.value,
			message: message,
		});
	}
}

function fetchPreviewBlocks() {
	if (conversationId.value) {
		previewBlocksResource.submit({
			conversation_id: conversationId.value,
		});
	}
}

function generatePage() {
	if (!conversationId.value || generating.value) return;
	generating.value = true;
	generatePageResource.submit({
		conversation_id: conversationId.value,
	});
}

async function scrollToBottom() {
	await nextTick();
	if (chatContainer.value) {
		chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
	}
}

// Watch for context changes to update preview
watch(
	siteContext,
	() => {
		if (conversationId.value && Object.keys(siteContext.value).length > 0) {
			fetchPreviewBlocks();
		}
	},
	{ deep: true }
);

// Initialize
onMounted(() => {
	// Load AI config first
	aiConfigResource.submit();
	// Then start conversation
	startConversation();
});
</script>
