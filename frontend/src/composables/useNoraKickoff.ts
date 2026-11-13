//// Neoffice — added file (no upstream equivalent). « Design with Nora » over an empty page (EmptyDraftHint.vue): the
//// request waits here until Nora's tab (NoraEditorChat.vue) has read its conversation, then the tab sends it. Jérémy,
//// 13.11: an empty page stays empty in the editor, with a way to design it with Nora.
import { __ } from "@/translation";
import { ref } from "vue";

export type NoraKickoff = { kind: "site" | "page"; pageId: string };

/** « Design with Nora » asked on a page, not sent yet. */
export const noraKickoff = ref<NoraKickoff | null>(null);

/** The pages whose editor conversation has begun in this tab (a message of the person). */
export const noraStartedPages = ref<string[]>([]);

export function markNoraStarted(pageId: string) {
	if (pageId && !noraStartedPages.value.includes(pageId))
		noraStartedPages.value = [...noraStartedPages.value, pageId];
}

/** What the person's message says, in the conversation. */
export const pageSeed = () =>
	__("Design this page with me: ask me first what it is for, then draw it in the style of my site.");

/** What Nora reads: one question first, then the whole page at once, in the site's theme. The POT's extractor loses a
 * string that starts on the line after `__(`, hence one line. */
// prettier-ignore
export const pageSeedForNora = () => __("This page is empty. Ask me first, in one question, what the page is for and who it speaks to. Then design the whole page at once in the theme of this site: read one of its pages first and carry its colours, fonts and section style into the new page.");
