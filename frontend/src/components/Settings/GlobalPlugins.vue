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
					:class="plugin.icon || 'lucide-puzzle'"
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
			</div>
		</div>

		<p class="text-xs text-ink-gray-5">
			{{ __("More plugins will come from the community hub. This list is where they land.") }}
		</p>
	</div>
</template>
<script setup lang="ts">
import { Switch, createResource, toast } from "frappe-ui";
import { ref } from "vue";

// `__` is installed globally by the translation plugin (see src/translation.ts).
const __ = window.__!;

const API = "builder.plugins";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Plugin = Record<string, any>;

const loading = ref(true);
const busy = ref("");
const plugins = ref<Plugin[]>([]);

createResource({
	url: `${API}.list_plugins`,
	auto: true,
	onSuccess(data: Plugin[]) {
		plugins.value = data || [];
		loading.value = false;
	},
	onError() {
		loading.value = false;
	},
});

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
