import { chatsLevel } from "@/components/ai/commands/chats";
import { modelLevel } from "@/components/ai/commands/models";
import { providersLevel } from "@/components/ai/commands/providers";
import type { BobContext } from "@/components/ai/commands/shared";
import { slashCommands, type SlashCommand } from "@/components/ai/slashCommands";
//// Neoffice — whether the host lets this user pick the model (see the composer in BuilderAIChatPanel.vue)
import { showModelPicker } from "@/utils/neofficeBoot";

/** Bob's built-in "/" commands. Returns the unregister for when the chat panel unmounts. */
export function registerBobCommands(ctx: BobContext): () => void {
	const commands: SlashCommand[] = [
		{
			name: "model",
			description: "Switch model",
			icon: "lucide-cpu",
			submenu: true,
			run: (arg) => modelLevel(ctx, arg),
		},
		{
			name: "providers",
			submenu: true,
			aliases: ["credits", "connect", "setup"],
			description: "Connect providers, see credits",
			icon: "lucide-server",
			run: () => providersLevel(ctx),
		},
		{
			name: "chats",
			submenu: true,
			aliases: ["history", "resume"],
			description: "Chats on this page",
			icon: "lucide-history",
			run: () => chatsLevel(ctx),
		},
		{
			name: "new",
			aliases: ["clear"],
			description: "New chat",
			icon: "lucide-plus",
			run: () => ctx.chat.newSession(),
		},
	];
	//// Neoffice — on a managed instance the model is the host's choice: a client has no "/model" to switch it and no
	//// "/providers" to connect a key of their own (the 1.36 menu moved both out of the composer, where we hid them).
	const hostChoosesTheModel = !showModelPicker();
	const offered = commands.filter((command) => !(hostChoosesTheModel && ["model", "providers"].includes(command.name)));
	const unregisters = offered.map((command) => slashCommands.register(command));
	return () => unregisters.forEach((unregister) => unregister());
}
