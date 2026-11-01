//// Neoffice — added file (no upstream equivalent): from a selected component block to its options.
//
// A block that carries a component's tag draws its component in the canvas (ComponentTagBlock.vue), and its raw HTML is
// the Jinja the person should not have to write. Click the block and its options are here, in the block's own
// properties, and each change shows in the canvas as it is made (SiteComponentOptions.vue).
import SiteComponentOptions from "@/components/SiteComponentOptions.vue";
import { __ } from "@/translation";
import blockController from "@/utils/blockController";
import { readComponentTag } from "@/utils/siteComponents";

const isComponentBlock = () =>
	blockController.getSelectedBlocks().length === 1 &&
	Boolean(readComponentTag(blockController.getInnerHTML() || null));

export default {
	name: __("Component"),
	properties: [
		{
			component: SiteComponentOptions,
			searchKeyWords: "Component, Options, Site block, Contact form, Map, Carousel, Shortcode",
			condition: isComponentBlock,
		},
	],
	condition: isComponentBlock,
};
