<template>
	<div class="flex flex-col gap-3 rounded-lg border border-outline-gray-1 p-3">
		<div class="flex items-center justify-between gap-3">
			<div class="flex flex-col">
				<span class="text-sm font-medium text-ink-gray-8">{{ __("Codex CLI (ChatGPT plan)") }}</span>
				<span class="text-xs text-ink-gray-6">
					{{
						__(
							"Generate pages and images through a ChatGPT Plus/Pro plan instead of a metered API key.",
						)
					}}
				</span>
			</div>
			<Badge v-if="status.logged_in" theme="green" variant="subtle">{{ __("Paired") }}</Badge>
			<Badge v-else-if="status.unreachable" theme="gray" variant="subtle">
				{{ __("Status unavailable") }}
			</Badge>
			<Badge v-else-if="!status.installed" theme="orange" variant="subtle">
				{{ __("CLI not installed") }}
			</Badge>
			<Badge v-else theme="gray" variant="subtle">{{ __("Not paired") }}</Badge>
		</div>

		<p v-if="status.unreachable" class="text-xs text-ink-gray-6">
			{{ __("Could not reach the server to check. Reload the page.") }}
		</p>
		<p v-else-if="!status.installed" class="text-xs text-ink-gray-6">
			{{ __("Install it on the server:") }}
			<code class="rounded bg-surface-gray-2 px-1">npm install -g @openai/codex</code>
		</p>

		<!-- device code -->
		<div v-if="pending.url" class="flex flex-col gap-2 rounded-lg bg-surface-blue-1 p-3">
			<span class="text-sm text-ink-gray-8">{{ __("Open this page and enter the code:") }}</span>
			<a :href="pending.url" target="_blank" rel="noopener noreferrer" class="text-sm text-ink-blue-8 underline">
				{{ pending.url }}
			</a>
			<span v-if="pending.code" class="font-mono text-xl font-semibold tracking-wider text-ink-gray-9">
				{{ pending.code }}
			</span>
			<span class="text-xs text-ink-gray-6">{{ __("Waiting for your confirmation...") }}</span>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<Button
				v-if="!status.logged_in && status.installed"
				variant="solid"
				:label="pairing ? __('Starting...') : __('Pair with ChatGPT')"
				:disabled="pairing"
				@click="startPairing" />
			<Button
				v-if="status.logged_in"
				variant="subtle"
				:label="testing ? __('Testing...') : __('Test generation')"
				:disabled="testing"
				@click="testCodex" />
			<Button
				v-if="status.logged_in"
				variant="ghost"
				:label="__('Unpair')"
				@click="unpair" />
			<button
				v-if="!status.logged_in && status.installed"
				class="text-xs text-ink-gray-6 underline"
				@click="showToken = !showToken">
				{{ __("or paste an access token") }}
			</button>
		</div>

		<div v-if="showToken && !status.logged_in" class="flex items-center gap-2">
			<FormControl
				type="password"
				size="sm"
				:placeholder="__('Access token')"
				:modelValue="token"
				@update:modelValue="(v: string) => (token = v)"
				class="flex-1" />
			<Button variant="subtle" :label="__('Pair')" :disabled="!token" @click="pairWithToken" />
		</div>

		<div v-if="message" class="rounded-lg p-2 text-sm" :class="messageClass">{{ message }}</div>
	</div>
</template>
<script setup lang="ts">
import { createResource } from "frappe-ui";
import { onBeforeUnmount, onMounted, reactive, ref } from "vue";

const __ = window.__!;
const API = "builder.codex_api";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const status = reactive<Record<string, any>>({ installed: false, logged_in: false, unreachable: false });
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const pending = reactive<Record<string, any>>({ url: null, code: null });
const pairing = ref(false);
const testing = ref(false);
const showToken = ref(false);
const token = ref("");
const message = ref("");
const messageClass = ref("");
let poll: ReturnType<typeof setInterval> | null = null;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const call = (method: string, params?: Record<string, any>) =>
	createResource({ url: `${API}.${method}` }).submit(params || {});

const say = (text: string, ok: boolean) => {
	message.value = text;
	messageClass.value = ok ? "text-ink-green-6 bg-surface-green-1" : "text-ink-red-6 bg-surface-red-1";
};

const refresh = async () => {
	try {
		const data = await call("get_codex_status");
		Object.assign(status, data);
		Object.assign(pending, data.pending_login || { url: null, code: null });
		status.unreachable = false;
	} catch (error) {
		// Swallowing this used to make the panel announce "CLI not installed"
		// for a CLI that was installed: the call failed, the empty default
		// stood, and nothing said so. An unknown state is not a negative one.
		status.unreachable = true;
		status.error = error instanceof Error ? error.message : String(error);
	}
};

const stopPolling = () => {
	if (poll) {
		clearInterval(poll);
		poll = null;
	}
};

const startPairing = async () => {
	pairing.value = true;
	message.value = "";
	try {
		const data = await call("start_codex_login");
		if (data.status === "already") {
			await refresh();
			say(data.message, true);
			return;
		}
		if (!data.url) {
			say(data.error || __("The CLI printed no pairing link"), false);
			return;
		}
		Object.assign(pending, { url: data.url, code: data.code });
		// poll until the user has confirmed on the other device
		stopPolling();
		poll = setInterval(async () => {
			const state = await call("check_codex_login");
			if (state.logged_in) {
				stopPolling();
				Object.assign(pending, { url: null, code: null });
				await refresh();
				say(__("Paired — {0}").format(state.message), true);
			}
		}, 4000);
	} catch (error) {
		say(error instanceof Error ? error.message : String(error), false);
	} finally {
		pairing.value = false;
	}
};

const pairWithToken = async () => {
	try {
		const data = await call("login_with_token", { token: token.value });
		token.value = "";
		showToken.value = false;
		await refresh();
		say(__("Paired — {0}").format(data.message), true);
	} catch (error) {
		say(error instanceof Error ? error.message : String(error), false);
	}
};

const unpair = async () => {
	try {
		await call("logout_codex");
		await refresh();
		say(__("This server is no longer paired"), true);
	} catch (error) {
		say(error instanceof Error ? error.message : String(error), false);
	}
};

const testCodex = async () => {
	testing.value = true;
	message.value = "";
	try {
		const data = await call("test_codex");
		say(data.message, !!data.success);
	} catch (error) {
		say(error instanceof Error ? error.message : String(error), false);
	} finally {
		testing.value = false;
	}
};

onMounted(refresh);
onBeforeUnmount(stopPolling);
</script>
