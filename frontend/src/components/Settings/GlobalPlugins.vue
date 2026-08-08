<template>
	<div v-if="loading" class="text-base text-ink-gray-5">{{ __("Loading...") }}</div>
	<div v-else class="flex flex-col gap-4">
		<p class="text-sm text-ink-gray-6">
			{{
				__(
					"Turning a plugin off hides it in the Studio, refuses its endpoints and frees the routes it owns. Nothing is uninstalled and no content is deleted — turning it back on restores everything.",
				)
			}}
		</p>

		<div class="flex flex-col divide-y divide-outline-gray-1">
			<div v-for="plugin in plugins" :key="plugin.name" class="flex items-start gap-3 py-3">
				<span
					class="mt-0.5 size-4 shrink-0 text-ink-gray-7"
					:class="plugin.icon"
					aria-hidden="true" />
				<div class="min-w-0 flex-1">
					<div class="flex items-center gap-2">
						<span class="text-sm font-medium text-ink-gray-8">{{ __(plugin.title) }}</span>
						<span
							v-if="plugin.is_core"
							class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] uppercase text-ink-gray-6">
							{{ __("Core") }}
						</span>
						<span
							v-else-if="!plugin.is_available"
							class="rounded bg-surface-amber-1 px-1.5 py-0.5 text-[10px] uppercase text-ink-amber-3">
							{{ __("Not installed") }}
						</span>
					</div>
					<p class="text-xs text-ink-gray-5">{{ __(plugin.description) }}</p>
					<p v-if="plugin.route_prefix" class="mt-0.5 text-xs text-ink-gray-4">
						{{ __("Owns") }} /{{ plugin.route_prefix }}
					</p>
				</div>
				<Switch
					size="sm"
					:disabled="!!plugin.is_core || !plugin.is_available || busy === plugin.name"
					:modelValue="!!plugin.enabled"
					@update:modelValue="(v: boolean) => toggle(plugin, v)" />
				<Button
					v-if="canInstall && !plugin.is_core && plugin.app_name && plugin.is_available"
					variant="ghost"
					size="sm"
					icon="lucide-trash-2"
					:title="__('Remove from the site')"
					@click="askRemove(plugin)" />
			</div>
		</div>

		<!-- Installing is a different kind of act from switching: a Frappe app
		     runs with full server access, so the URL is explicit, the operator
		     can turn the whole thing off, and nothing is installed from a name. -->
		<div v-if="canInstall" class="flex flex-col gap-2 border-t border-outline-gray-1 pt-4">
			<span class="text-sm font-medium text-ink-gray-8">{{ __("Install a plugin") }}</span>
			<p class="text-xs text-ink-gray-5">
				{{ __("A plugin is a Frappe app. It runs with full access to this server — install only what you trust.") }}
			</p>
			<div class="flex items-end gap-2">
				<FormControl
					size="sm"
					class="flex-1"
					:label="__('Git URL')"
					placeholder="https://github.com/owner/app"
					:modelValue="installUrl"
					@update:modelValue="(v: string) => (installUrl = v)" />
				<FormControl
					size="sm"
					class="w-40"
					:label="__('Branch')"
					placeholder="main"
					:modelValue="installBranch"
					@update:modelValue="(v: string) => (installBranch = v)" />
				<Button
					variant="solid"
					:loading="!!jobId"
					:disabled="!installUrl.trim()"
					@click="startInstall">
					{{ __("Install") }}
				</Button>
			</div>
			<div v-if="jobStep" class="flex items-center gap-2 text-xs">
				<span
					v-if="jobId"
					class="size-3 animate-spin rounded-full border-2 border-outline-gray-2 border-t-ink-gray-6" />
				<span :class="jobFailed ? 'text-ink-red-3' : 'text-ink-gray-6'">{{ jobStep }}</span>
			</div>
			<p v-if="jobNeedsRestart" class="text-xs text-ink-amber-3">
				{{ __("Installed. Restart the site's workers for the new app's hooks to take effect.") }}
			</p>
		</div>

		<Dialog
			v-model="confirmRemove"
			:options="{
				title: __('Remove this plugin?'),
				message: removeMessage,
				actions: [
					{ label: __('Remove'), variant: 'solid', theme: 'red', onClick: doRemove },
					{ label: __('Cancel'), onClick: () => (confirmRemove = false) },
				],
			}" />

		<p class="text-xs text-ink-gray-5">
			{{ __("More plugins will come from the community hub. This list is where they land.") }}
		</p>
	</div>
</template>
<script setup lang="ts">
import { Button, Dialog, FormControl, Switch, createResource, toast } from "frappe-ui";
import { computed, ref } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const API = "builder.plugins";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Plugin = Record<string, any>;

const loading = ref(true);
const busy = ref("");
const plugins = ref<Plugin[]>([]);

const listResource = createResource({
	url: `${API}.list_plugins`,
	auto: true,
	onSuccess(data: Plugin[]) {
		plugins.value = (data || []).map((p) => ({ ...p, icon: drawableIcon(p.icon) }));
		loading.value = false;
	},
	onError() {
		loading.value = false;
	},
});

function reload() {
	listResource.reload();
	window.dispatchEvent(new CustomEvent("unpress:capabilities-changed"));
}

const INSTALL_API = "builder.plugin_install";

const canInstall = ref(false);
const installUrl = ref("");
const installBranch = ref("");
const jobId = ref("");
const jobStep = ref("");
const jobFailed = ref(false);
const jobNeedsRestart = ref(false);
const confirmRemove = ref(false);
const removeTarget = ref<Plugin | null>(null);

const FALLBACK_ICON = "lucide-puzzle";
const iconCache = new Map<string, string>();

// Icon classes are compiled by scanning source files, and a plugin's icon name
// arrives from a database row — so a name no source file mentions gets a class
// with no rule behind it, and the entry shows an empty square. `icon ||
// 'puzzle'` does not catch it: the name is there, it just cannot draw. Ask the
// browser, once per name. Built-ins look right today only because their names
// happen to appear elsewhere in the frontend, which is luck, not design.
function drawableIcon(name?: string): string {
	if (!name) return FALLBACK_ICON;
	const cached = iconCache.get(name);
	if (cached) return cached;

	const probe = document.createElement("span");
	probe.className = name;
	probe.style.position = "fixed";
	probe.style.visibility = "hidden";
	document.body.appendChild(probe);
	const style = getComputedStyle(probe);
	const drawable = style.maskImage !== "none" || style.backgroundImage !== "none";
	probe.remove();

	const resolved = drawable ? name : FALLBACK_ICON;
	iconCache.set(name, resolved);
	return resolved;
}

const removeMessage = computed(() =>
	removeTarget.value
		? __(
				"This uninstalls {0} from the site and drops its tables. Turning it off instead keeps everything and is instant.",
			).replace("{0}", __(removeTarget.value.title))
		: "",
);

createResource({
	url: `${INSTALL_API}.install_capability`,
	auto: true,
	onSuccess(data: { allowed?: boolean }) {
		canInstall.value = !!data?.allowed;
	},
	onError() {
		canInstall.value = false;
	},
});

// One poll loop for both install and uninstall — same progress shape.
async function follow(id: string, onDone: () => void) {
	jobId.value = id;
	jobFailed.value = false;
	jobNeedsRestart.value = false;
	const tick = async () => {
		try {
			const r = await createResource({ url: `${INSTALL_API}.install_status` }).submit({ job_id: id });
			jobStep.value = r?.step || "";
			if (r?.status === "done") {
				jobId.value = "";
				jobNeedsRestart.value = !!r.needs_restart;
				onDone();
				return;
			}
			if (r?.status === "failed") {
				jobId.value = "";
				jobFailed.value = true;
				return;
			}
		} catch {
			// a dropped poll is not a failed job; keep waiting
		}
		setTimeout(tick, 2000);
	};
	tick();
}

async function startInstall() {
	try {
		const r = await createResource({ url: `${INSTALL_API}.install_plugin` }).submit({
			git_url: installUrl.value.trim(),
			branch: installBranch.value.trim() || undefined,
		});
		follow(r.job_id, () => {
			installUrl.value = "";
			installBranch.value = "";
			toast.success(__("Plugin installed"));
			reload();
		});
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	}
}

function askRemove(plugin: Plugin) {
	removeTarget.value = plugin;
	confirmRemove.value = true;
}

async function doRemove() {
	const plugin = removeTarget.value;
	confirmRemove.value = false;
	if (!plugin) return;
	try {
		const r = await createResource({ url: `${INSTALL_API}.uninstall_plugin` }).submit({
			plugin_name: plugin.plugin_name,
		});
		follow(r.job_id, () => {
			toast.success(__("Plugin removed"));
			reload();
		});
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	}
}

async function toggle(plugin: Plugin, enabled: boolean) {
	busy.value = plugin.name;
	try {
		await createResource({ url: `${API}.set_plugin_enabled` }).submit({
			plugin_name: plugin.plugin_name,
			enabled: enabled ? 1 : 0,
		});
		plugin.enabled = enabled ? 1 : 0;
		toast.success(
			enabled
				? __("{0} is on").replace("{0}", __(plugin.title))
				: __("{0} is off").replace("{0}", __(plugin.title)),
		);
		// the sidebar reads the capabilities it was given at boot
		window.dispatchEvent(new CustomEvent("unpress:capabilities-changed"));
	} catch (error) {
		toast.error(error instanceof Error ? error.message : String(error));
	} finally {
		busy.value = "";
	}
}
</script>
