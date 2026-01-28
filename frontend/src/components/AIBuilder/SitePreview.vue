<template>
	<div class="site-preview min-h-[600px] overflow-auto bg-white">
		<!-- Render blocks if available -->
		<template v-if="blocks && blocks.length > 0">
			<div v-for="block in blocks" :key="block.blockId" v-html="renderBlockToHTML(block)"></div>
		</template>

		<!-- Render context-based preview if no blocks -->
		<template v-else-if="context && Object.keys(context).length > 0">
			<!-- Hero Section -->
			<section
				v-if="hasSection('hero') || context.tagline"
				class="hero-section flex flex-col items-center justify-center px-5 py-24 text-center"
				:style="heroStyles">
				<div class="mx-auto max-w-3xl">
					<h1
						class="mb-6 text-5xl font-bold leading-tight"
						:style="{ color: textColor }">
						{{ getHeroHeadline }}
					</h1>
					<p
						class="mb-8 text-xl leading-relaxed"
						:style="{ color: secondaryTextColor }">
						{{ getHeroSubheadline }}
					</p>
					<div class="flex flex-wrap justify-center gap-4">
						<a
							:href="getHeroCTALink"
							class="rounded-xl px-7 py-3.5 text-base font-medium text-white transition-opacity hover:opacity-90"
							:style="{ backgroundColor: primaryColor }">
							{{ getHeroCTAText }}
						</a>
					</div>
				</div>
			</section>

			<!-- Features Section -->
			<section
				v-if="hasSection('features')"
				class="features-section px-5 py-20"
				:style="{ backgroundColor: backgroundColor }">
				<div class="mx-auto max-w-6xl">
					<div class="mb-12 text-center">
						<h2
							class="mb-4 text-4xl font-bold"
							:style="{ color: textColor }">
							{{ getFeaturesHeadline }}
						</h2>
						<p
							class="mx-auto max-w-2xl text-lg"
							:style="{ color: secondaryTextColor }">
							{{ getFeaturesSubheadline }}
						</p>
					</div>
					<div class="grid gap-6 md:grid-cols-3">
						<div
							v-for="(feature, index) in getFeatureItems"
							:key="index"
							class="rounded-2xl bg-gray-50 p-8">
							<div
								class="mb-4 flex size-12 items-center justify-center rounded-xl text-xl text-white"
								:style="{ backgroundColor: primaryColor }">
								{{ feature.icon || getDefaultIcon(index) }}
							</div>
							<h3
								class="mb-2 text-xl font-semibold"
								:style="{ color: textColor }">
								{{ feature.title }}
							</h3>
							<p :style="{ color: secondaryTextColor }">
								{{ feature.description }}
							</p>
						</div>
					</div>
				</div>
			</section>

			<!-- CTA Section -->
			<section
				v-if="hasSection('cta')"
				class="cta-section px-5 py-20 text-center text-white"
				:style="{ backgroundColor: primaryColor }">
				<div class="mx-auto max-w-2xl">
					<h2 class="mb-4 text-4xl font-bold">
						{{ getCTAHeadline }}
					</h2>
					<p class="mb-8 text-lg opacity-90">
						{{ getCTADescription }}
					</p>
					<a
						:href="getCTALink"
						class="inline-block rounded-xl bg-white px-8 py-4 text-base font-semibold transition-opacity hover:opacity-90"
						:style="{ color: primaryColor }">
						{{ getCTAButtonText }}
					</a>
				</div>
			</section>

			<!-- Footer -->
			<footer class="border-t border-gray-200 bg-gray-50 px-5 py-12 text-center">
				<p class="text-lg font-semibold" :style="{ color: textColor }">
					{{ context.business_name || "Company" }}
				</p>
				<p class="mt-2 text-sm" :style="{ color: secondaryTextColor }">
					&copy; 2025 {{ context.business_name || "Company" }}. All rights reserved.
				</p>
			</footer>
		</template>

		<!-- Empty state -->
		<div v-else class="flex min-h-[400px] items-center justify-center text-gray-400">
			<p>Preview will appear here as you describe your website</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface Props {
	context: Record<string, any>;
	blocks?: any[];
}

const props = withDefaults(defineProps<Props>(), {
	context: () => ({}),
	blocks: () => [],
});

// Colors
const primaryColor = computed(() => props.context?.style?.primary_color || "#171717");
const secondaryColor = computed(() => props.context?.style?.secondary_color || "#525252");
const backgroundColor = computed(() => props.context?.style?.background_color || "#ffffff");
const textColor = computed(() => props.context?.style?.text_color || "#171717");
const secondaryTextColor = computed(() => props.context?.style?.secondary_color || "#525252");

// Hero styles
const heroStyles = computed(() => ({
	backgroundColor: backgroundColor.value,
}));

// Section helpers
function hasSection(type: string): boolean {
	return props.context?.sections?.some((s: any) => s.type === type) || false;
}

function getSection(type: string): any {
	return props.context?.sections?.find((s: any) => s.type === type) || {};
}

// Hero getters
const getHeroHeadline = computed(() => {
	const hero = getSection("hero");
	return hero.headline || props.context?.tagline || "Welcome to Our Site";
});

const getHeroSubheadline = computed(() => {
	const hero = getSection("hero");
	return hero.subheadline || hero.description || props.context?.description || "Discover what makes us different";
});

const getHeroCTAText = computed(() => {
	const hero = getSection("hero");
	return hero.cta_text || "Get Started";
});

const getHeroCTALink = computed(() => {
	const hero = getSection("hero");
	return hero.cta_link || "/get-started";
});

// Features getters
const getFeaturesHeadline = computed(() => {
	const features = getSection("features");
	return features.headline || "Features";
});

const getFeaturesSubheadline = computed(() => {
	const features = getSection("features");
	return features.subheadline || features.description || "Everything you need to succeed";
});

const getFeatureItems = computed(() => {
	const features = getSection("features");
	return features.items || [
		{ title: "Feature 1", description: "Description of feature 1" },
		{ title: "Feature 2", description: "Description of feature 2" },
		{ title: "Feature 3", description: "Description of feature 3" },
	];
});

// CTA getters
const getCTAHeadline = computed(() => {
	const cta = getSection("cta");
	return cta.headline || "Ready to get started?";
});

const getCTADescription = computed(() => {
	const cta = getSection("cta");
	return cta.description || "Join thousands of satisfied customers today.";
});

const getCTAButtonText = computed(() => {
	const cta = getSection("cta");
	return cta.cta_text || "Get Started Free";
});

const getCTALink = computed(() => {
	const cta = getSection("cta");
	return cta.cta_link || "/signup";
});

// Default icons
function getDefaultIcon(index: number): string {
	const icons = ["", "", "", "", "", ""];
	return icons[index % icons.length];
}

// Block to HTML renderer
function renderBlockToHTML(block: any): string {
	if (!block) return "";

	const element = block.element || "div";
	const styles = convertStylesToCSS(block.baseStyles || {});
	const innerHTML = block.innerHTML || "";
	const attributes = Object.entries(block.attributes || {})
		.map(([key, value]) => `${key}="${value}"`)
		.join(" ");

	let childrenHTML = "";
	if (block.children && block.children.length > 0) {
		childrenHTML = block.children.map((child: any) => renderBlockToHTML(child)).join("");
	}

	const content = childrenHTML || innerHTML;

	return `<${element} style="${styles}" ${attributes}>${content}</${element}>`;
}

function convertStylesToCSS(styles: Record<string, any>): string {
	return Object.entries(styles)
		.map(([key, value]) => {
			const cssKey = key.replace(/([A-Z])/g, "-$1").toLowerCase();
			return `${cssKey}: ${value}`;
		})
		.join("; ");
}
</script>

<style scoped>
.site-preview {
	font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.site-preview :deep(*) {
	box-sizing: border-box;
}
</style>
