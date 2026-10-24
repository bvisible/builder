//// Neoffice — added file (no upstream equivalent): on a managed instance the model is the host's choice, so a client
//// has no "/model" and no "/providers" (bobCommands.ts), the host's Administrator keeps both.
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/ai/commands/chats", () => ({ chatsLevel: vi.fn() }));
vi.mock("@/components/ai/commands/models", () => ({ modelLevel: vi.fn() }));
vi.mock("@/components/ai/commands/providers", () => ({ providersLevel: vi.fn() }));

import { registerBobCommands } from "@/components/ai/bobCommands";
import { slashCommands } from "@/components/ai/slashCommands";

const names = () => slashCommands.all.value.map((command) => command.name);

function boot(modelPicker?: boolean) {
	(globalThis as any).window = { capabilities: { ai: { assistant_name: "Nora", managed: true, disabled_tools: [], users_tab: false, model_picker: modelPicker } } };
}

describe("bobCommands", () => {
	let unregister: (() => void) | undefined;
	afterEach(() => {
		unregister?.();
		delete (globalThis as any).window;
	});

	it("offers every command to the host", () => {
		boot(true);
		unregister = registerBobCommands({} as any);
		expect(names()).toEqual(expect.arrayContaining(["model", "providers", "chats", "new"]));
	});

	it("offers every command when the boot says nothing about the picker", () => {
		boot(undefined);
		unregister = registerBobCommands({} as any);
		expect(names()).toEqual(expect.arrayContaining(["model", "providers", "chats", "new"]));
	});

	it("keeps a client of a managed instance from switching the model or connecting a provider", () => {
		boot(false);
		unregister = registerBobCommands({} as any);
		expect(names()).toEqual(expect.arrayContaining(["chats", "new"]));
		expect(names()).not.toContain("model");
		expect(names()).not.toContain("providers");
	});

	it("unregisters what it registered", () => {
		boot(false);
		registerBobCommands({} as any)();
		expect(names()).toEqual([]);
	});
});
