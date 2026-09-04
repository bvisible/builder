<!-- //// Neoffice — added file (no upstream equivalent): the on/off switch for the whole
     //// site. Upstream publishes pages one by one and has no notion of a site being offline;
     //// a Neoffice client needs one control that takes everything down at once.
     //// Reads and writes Website Profile.website_online through neoffice_theme; the
     //// server-side validate() guard (at least one published page + a resolvable home page)
     //// holds the authority — this is only the control. Hidden entirely on a bench without
     //// neoffice_theme. -->
<template>
	<div class="flex items-center" v-if="onlineState.data">
		<Dropdown
			v-if="onlineState.data.website_online"
			:options="[
				{
					label: 'Take website offline',
					onClick: goOffline,
					icon: 'lucide-cloud-off',
				},
			]"
			size="sm"
			placement="right">
			<template v-slot="{ open }">
				<Button variant="subtle" theme="green" @click="open" :loading="toggling">
					<template #prefix>
						<span class="inline-block h-2 w-2 rounded-full bg-green-600" aria-hidden="true" />
					</template>
					Live
				</Button>
			</template>
		</Dropdown>
		<Tooltip v-else :text="goLiveTooltip" :hoverDelay="0.4" arrow-class="mb-3">
			<Button
				variant="solid"
				theme="green"
				@click="goOnline"
				:disabled="builderStore.readOnlyMode || !onlineState.data.can_go_online"
				:loading="toggling">
				<template #prefix>
					<span class="lucide-globe h-4 w-4" aria-hidden="true" />
				</template>
				Go Live
			</Button>
		</Tooltip>
	</div>
</template>
<script lang="ts" setup>
import useBuilderStore from "@/stores/builderStore";
import { Dropdown, Tooltip, createResource, toast } from "frappe-ui";
import { computed, ref } from "vue";

type OnlineState = {
	profile: string;
	title: string;
	primary_domain: string;
	website_online: number;
	can_go_online: boolean;
	reason: string;
};

const builderStore = useBuilderStore();
const toggling = ref(false);

const onlineState = createResource({
	url: "neoffice_theme.website_profiles.get_online_state",
	auto: true,
	// Benches without neoffice_theme (vanilla builder) simply never show the control.
	onError: () => {},
});

const goLiveTooltip = computed(() => {
	const state = onlineState.data as OnlineState | null;
	if (!state) return "";
	if (!state.can_go_online) {
		return state.reason || "Publish at least one page and set a home page first";
	}
	return `Put ${state.primary_domain} online`;
});

const setOnline = (online: number) => {
	toggling.value = true;
	createResource({ url: "neoffice_theme.website_profiles.set_online_state" })
		.submit({ online, profile: (onlineState.data as OnlineState)?.profile })
		.then((data: OnlineState) => {
			onlineState.data = data;
			toast.success(online ? "Website is now live" : "Website taken offline");
		})
		.catch((e: { messages?: string[] }) => {
			toast.error(e?.messages?.[0] || "Could not update the website state");
			onlineState.reload();
		})
		.finally(() => (toggling.value = false));
};

const goOnline = () => setOnline(1);
const goOffline = () => setOnline(0);
</script>
