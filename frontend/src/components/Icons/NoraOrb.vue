<!-- //// Neoffice — added file (no upstream equivalent). Nora's one icon, her orb (design system § 4: « the Nora
     interface icon is the orb, and nothing else »), for the Chat tab where her conversation draws it (LeftPanelTabs).
     The sphere fills 78 % of its image, hence 24 px beside the rail's 16 px line icons. -->
<template>
	<img :src="src" alt="" aria-hidden="true" style="width: 24px; height: 24px; max-width: none" />
</template>

<script setup lang="ts">
import useBuilderStore from "@/stores/builderStore";
import { computed } from "vue";

const builderStore = useBuilderStore();
const src = computed(() => `/assets/nora/images/nora-orb${builderStore.isDark ? "-dark" : ""}.svg`);
</script>
