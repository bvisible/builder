//// Neoffice — added file (no upstream equivalent). "Create with AI" no longer opens a modal of
//// its own: the editor agent (Nora) creates whole sites from its panel. This composable finds or
//// creates the page whose editor hosts that conversation (the agent's sessions are page-scoped),
//// routes to it with ?nora=site, and the panel seeds the first message from that query.
import { __ } from "@/translation";
import router from "@/router";
import { createResource, toast } from "frappe-ui";
import type { RouteLocationNormalizedLoaded } from "vue-router";

export const SITE_CREATION_QUERY = "nora";
export const SITE_CREATION_VALUE = "site";

/** the first user message of a site conversation; the agent runs its site playbook from there */
export const siteCreationSeed = () => __("I want to create a new website. Guide me step by step.");

export const isSiteCreationRoute = (route: RouteLocationNormalizedLoaded) =>
	route.query[SITE_CREATION_QUERY] === SITE_CREATION_VALUE;

//// Neoffice — "Edit with Nora" in the Website space opens a site's page with ?nora=chat: the agent's tab is
//// open and waiting for what to change, and nothing is sent (the "new website" sentence of ?nora=site would
//// send an existing site down the whole-site playbook).
export const SITE_CHAT_VALUE = "chat";
export const opensTheAssistant = (route: RouteLocationNormalizedLoaded) =>
	isSiteCreationRoute(route) || route.query[SITE_CREATION_QUERY] === SITE_CHAT_VALUE;

/** the profile's home page (or first page, or a fresh blank draft), then the editor on it. `reload`: the editor is loaded
 * anew there, for a caller whose open page is gone (a site deleted by Nora, 18.11): the panel sends the site's first
 * message once it has read the page's chat, which an editor moving from page to page had already done. */
export async function startSiteCreation(websiteProfile?: string, reload = false) {
	try {
		const result = (await createResource({ url: "builder.site_ai.nora.api.site_creation_page" }).submit({
			website_profile: websiteProfile || null,
		})) as { page_id: string };
		const target = {
			name: "builder",
			params: { pageId: result.page_id },
			query: { [SITE_CREATION_QUERY]: SITE_CREATION_VALUE },
		};
		if (reload) {
			window.location.assign(router.resolve(target).href);
			return;
		}
		await router.push(target);
	} catch (error) {
		toast.error((error as { messages?: string[] })?.messages?.[0] || __("Could not start the site assistant"));
	}
}
