//// Neoffice — added file (no upstream equivalent).
// The AI chat is a modal, not a route, so nothing outside the Studio can point
// at it — a desk workspace shortcut could only land on the dashboard and leave
// the user to find "Create with AI" on their own. `?chat=1` opens it on load.
// The param is dropped right after: a reload must not reopen what was closed.
import { ref, Ref } from "vue";
import { useRoute, useRouter } from "vue-router";

export function useChatDeepLink(): Ref<boolean> {
	const route = useRoute();
	const router = useRouter();
	const open = ref(route.query.chat === "1");
	if (open.value) {
		const query = { ...route.query };
		delete query.chat;
		router.replace({ query });
	}
	return open;
}
