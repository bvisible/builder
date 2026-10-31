import { createListResource } from "frappe-ui";

const builderBlockTemplate = createListResource({
	method: "GET",
	doctype: "Block Template",
	fields: ["template_name", "category", "preview", "name", "preview_width", "preview_height", "sort_order"],
	orderBy: "sort_order asc",
	cache: "blockTemplates",
	start: 0,
	//// Neoffice — the hub's library is offered as templates too (site_ai/nora/hub_templates.py): a hundred cards is not the whole panel.
	pageLength: 500,
});

export default builderBlockTemplate;
