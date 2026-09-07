//// Neoffice — added file (no upstream equivalent). Typed access to what the Studio boot carries
//// beyond translations: the assistant's name and what this instance allows (builder/www/_builder.py,
//// get_boot). Registry conditions read these at module load, so they must be synchronous: the
//// values are inlined by _builder.html before the app script runs. The vite dev server has no boot,
//// hence the permissive defaults.
export type AICapabilities = {
	assistant_name: string;
	managed: boolean;
	disabled_tools: string[];
	users_tab: boolean;
};

export type Capabilities = Record<string, boolean | AICapabilities | undefined> & { ai?: AICapabilities };

declare global {
	interface Window {
		assistant_name?: string;
		capabilities?: Capabilities;
	}
}

const defaultAI: AICapabilities = { assistant_name: "", managed: false, disabled_tools: [], users_tab: true };

export const capabilities = (): Capabilities => window.capabilities || {};

export const aiCapabilities = (): AICapabilities => capabilities().ai || defaultAI;

/** the name the assistant is called everywhere it is named; the fallback is upstream's own label */
export const assistantName = (fallback: string): string =>
	window.assistant_name || aiCapabilities().assistant_name || fallback;

/** the host runs the models: no provider setup, a read-only AI pane */
export const isManagedAI = (): boolean => aiCapabilities().managed === true;

/** invitations create users outside a licence quota; a managed instance hides the tab */
export const showUsersTab = (): boolean => aiCapabilities().users_tab !== false;
