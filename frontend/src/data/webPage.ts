import { createListResource, createResource } from "frappe-ui";

const webPages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: [
		"name",
		"route",
		"page_name",
		"preview",
		"page_title",
		"meta_image",
		"creation",
		"published",
		"staging",
		"dynamic_route",
		"modified_by",
		"modified",
		"is_template",
		"authenticated_access",
		"project_folder",
		"is_standard",
		"owner",
	],
	filters: {
		is_template: 0,
	},
	cache: "pages",
	pageLength: 50,
});

// names of live/staged pages carrying edits that aren't published yet, kept out of
// the main list so the heavy draft_blocks column never has to be fetched
const pagesWithUnpublishedChanges = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name"],
	filters: {
		is_template: 0,
		draft_blocks: ["is", "set"],
	},
	orFilters: {
		published: 1,
		staging: 1,
	},
	cache: "pages-with-unpublished-changes",
	// a truncated lookup would quietly show a pending page as fully published, so this
	// matches the ceiling the route tree already fetches pages at
	pageLength: 9999,
});

const pageCreators = createListResource({
	doctype: "Builder Page",
	fields: ["owner"],
	filters: {
		is_template: 0,
	},
	groupBy: "owner",
	orderBy: "owner asc",
	cache: "page-creators",
	pageLength: 999,
});

//// Neoffice — the editor's draft save goes through builder.api.save_page_draft instead of
//// frappe.client.set_value. set_value RE-READS the document before writing, so frappe's
//// optimistic lock compares the document to itself and never fires: a draft computed before
//// a server-side rewrite (the AI's generate_site rewrites blocks AND draft_blocks) was
//// accepted as-is and silently reverted the freshly built page (neoffice-maintenance#306).
//// The endpoint refuses a draft whose loaded version is older than the document's.
const savePageDraft = createResource({
	url: "builder.api.save_page_draft",
});

const templateGroups = createResource({
	url: "builder.api.get_template_groups",
	cache: "template-groups",
});

const searchablePages = createListResource({
	method: "GET",
	doctype: "Builder Page",
	fields: ["name", "route", "page_name", "page_title"],
	filters: {
		is_template: 0,
	},
	cache: "searchable-pages",
	orderBy: "modified desc",
	pageLength: 10,
});

//// Neoffice — see the block marker above: savePageDraft exported alongside the others
export { pageCreators, pagesWithUnpublishedChanges, savePageDraft, searchablePages, templateGroups, webPages };
