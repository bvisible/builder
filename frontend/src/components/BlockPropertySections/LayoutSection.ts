import BlockFlexLayoutHandler from "@/components/BlockFlexLayoutHandler.vue";
import BlockGridLayoutHandler from "@/components/BlockGridLayoutHandler.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";
import StylePropertyControl from "../Controls/StylePropertyControl.vue";

//// Neoffice — added. Upstream keeps grid-only props in the block JSON after the user switches
//// to flex (and the reverse): they end up in the published CSS and break the layout. 6bd72e8d.
// Props that only make sense with display: grid. When the user switches
// away from grid, these are stripped from ALL breakpoints of the block —
// otherwise they stay in the stored JSON, get serialised into the page
// CSS, and break layout once the user switches again (or on public render
// where the browser just ignores them but keeps flex items unstyled).
const GRID_ONLY_PROPS: styleProperty[] = [
	"gridTemplateColumns",
	"gridTemplateRows",
	"gridTemplateAreas",
	"gridAutoColumns",
	"gridAutoRows",
	"gridAutoFlow",
	"gridArea",
	"gridColumn",
	"gridColumnStart",
	"gridColumnEnd",
	"gridRow",
	"gridRowStart",
	"gridRowEnd",
	"columnGap",
	"rowGap",
] as unknown as styleProperty[];

// Props that only make sense with display: flex. gap / justify-content /
// align-items are intentionally NOT in this list — they work identically
// in both flex and grid.
const FLEX_ONLY_PROPS: styleProperty[] = [
	"flexDirection",
	"flexFlow",
	"flexWrap",
	"flexGrow",
	"flexShrink",
	"flexBasis",
	"order",
] as unknown as styleProperty[];

function cleanupIncompatibleDisplayProps(newDisplay: StyleValue) {
	const blocks = blockController.getSelectedBlocks();
	const toStrip: styleProperty[] = [];
	if (newDisplay !== "grid") toStrip.push(...GRID_ONLY_PROPS);
	if (newDisplay !== "flex") toStrip.push(...FLEX_ONLY_PROPS);
	blocks.forEach((block) => {
		toStrip.forEach((prop) => block.removeStyle(prop));
	});
}

const layoutSectionProperties = [
	{
		component: StylePropertyControl,
		condition: () => !blockController.isText(),
		getProps: () => {
			return {
				propertyKey: "display",
				component: OptionToggle,
				label: "Type",
				enableStates: false,
				options: [
					{
						label: "Stack",
						value: "flex",
					},
					{
						label: "Grid",
						value: "grid",
					},
				],
			};
		},
		searchKeyWords: "Layout, Display, Flex, Grid, Flexbox, Flex Box, FlexBox",
		events: {
			"update:modelValue": (val: StyleValue) => {
				blockController.setStyle("display", val);
				//// Neoffice — see cleanupIncompatibleDisplayProps above (6bd72e8d).
				// Strip props from the old display mode across all breakpoints.
				// Keeps block JSON clean and prevents "stuck grid-template-columns
				// after switching to flex" which breaks the rendered layout.
				cleanupIncompatibleDisplayProps(val);
				if (val === "grid") {
					if (!blockController.getStyle("gridTemplateColumns")) {
						blockController.setStyle("gridTemplateColumns", "repeat(2, minmax(200px, 1fr))");
					}
					if (!blockController.getStyle("gap")) {
						blockController.setStyle("gap", "10px");
					}
					if (blockController.getStyle("height")) {
						if (blockController.getSelectedBlocks()[0].hasChildren()) {
							blockController.setStyle("height", null);
						}
					}
				}
			},
		},
	},
	{
		component: BlockGridLayoutHandler,
		condition: () => blockController.isGrid() || Boolean(blockController.getParentBlock()?.isGrid()),
		getProps: () => {},
		searchKeyWords:
			"Layout, Grid, GridTemplate, Grid Template, GridGap, Grid Gap, GridRow, Grid Row, GridColumn, Grid Column",
	},
	{
		component: BlockFlexLayoutHandler,
		condition: () => blockController.isFlex() || Boolean(blockController.getParentBlock()?.isFlex()),
		getProps: () => {},
		searchKeyWords:
			"Layout, Flex, Flexbox, Flex Box, FlexBox, Justify, Space Between, Flex Grow, Flex Shrink, Flex Basis, Align Items, Align Content, Align Self, Flex Direction, Flex Wrap, Flex Flow, Flex Grow, Flex Shrink, Flex Basis, Gap, Order",
	},
];

export default {
	name: "Layout",
	properties: layoutSectionProperties,
	condition: () => !blockController.multipleBlocksSelected() && !blockController.isHTML(),
};
