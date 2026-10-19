//// Neoffice — added file (no upstream equivalent): from a selected component block to its options.
//
// A block that carries a component's tag is drawn as a card in the canvas (ComponentTagBlock.vue), and its raw HTML is
// the Jinja the person should not have to write: the options are in the Site blocks tab. Selecting the block from the
// canvas leaves the left panel on whatever tab it was on, so this puts the way there in the block's own properties.
import useBuilderStore from "@/stores/builderStore";
import { __ } from "@/translation";
import blockController from "@/utils/blockController";
import { readComponentTag } from "@/utils/siteComponents";
import { Button } from "frappe-ui";

const isComponentBlock = () =>
	blockController.getSelectedBlocks().length === 1 &&
	Boolean(readComponentTag(blockController.getInnerHTML() || null));

export default {
	name: __("Component"),
	properties: [
		{
			component: Button,
			getProps: () => ({ class: "text-base w-full", variant: "subtle" }),
			innerText: __("Change its options"),
			searchKeyWords: "Component, Options, Site block, Contact form, Map, Carousel, Shortcode",
			condition: isComponentBlock,
			events: {
				click: () => {
					useBuilderStore().leftPanelActiveTab = "SiteBlocks";
				},
			},
		},
	],
	condition: isComponentBlock,
};
