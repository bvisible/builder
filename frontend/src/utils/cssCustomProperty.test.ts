//// Neoffice — added file (no upstream equivalent): a CSS custom property of a block keeps its name in the
//// editor (neoffice-maintenance#2671).
import { describe, expect, it, vi } from "vitest";

// only the naming of style keys is under test: the editor's stores, blocks and dialogs are not loaded
vi.mock("@/block", () => ({ default: class {} }));
vi.mock("@/stores/canvasStore", () => ({ default: () => ({}) }));
vi.mock("@/translation", () => ({ __: (text: string) => text }));
vi.mock("@/utils/blockTemplate", () => ({ default: () => ({}) }));
vi.mock("@/utils/editorDemo", () => ({ editorDemo: {} }));
vi.mock("frappe-ui", () => ({ dialog: vi.fn(), toast: vi.fn(), FileUploadHandler: class {} }));

import { repairCustomPropertyKeys, repairedCustomProperty } from "@/utils/cssCustomProperty";
import { toCSSProperty, toStyleProperty } from "@/utils/helpers";

describe("a block's style keys", () => {
	it("keeps a custom property as written when a legacy rawStyles key is read", () => {
		// what mergeLegacyRawStyles hands every key of a block's rawStyles to
		expect(toStyleProperty("--primary-color")).toBe("--primary-color");
		expect(toStyleProperty("--primary-rgb")).toBe("--primary-rgb");
		expect(toStyleProperty("hover:--accent")).toBe("hover:--accent");
		expect(toCSSProperty(toStyleProperty("--primary-color"))).toBe("--primary-color");
	});

	it("still camel-cases a real property", () => {
		expect(toStyleProperty("background-color")).toBe("backgroundColor");
		expect(toStyleProperty("hover:border-color")).toBe("hover:borderColor");
	});

	it("puts back the keys an older editor broke", () => {
		expect(repairedCustomProperty("-PrimaryColor")).toBe("--primary-color");
		expect(repairedCustomProperty("-PrimaryRgb")).toBe("--primary-rgb");
		expect(repairedCustomProperty("-GfPrimary")).toBe("--gf-primary");
		expect(repairedCustomProperty("hover:-SecondaryColor")).toBe("hover:--secondary-color");
	});

	it("leaves every other key alone", () => {
		for (const key of [
			"backgroundColor",
			"WebkitLineClamp",
			"--primary-color",
			"hover:color",
			"-webkit-box",
		]) {
			expect(repairedCustomProperty(key)).toBeNull();
		}
	});

	it("repairs a style map, the correct key winning over its broken twin", () => {
		const styles = repairCustomPropertyKeys({
			"-PrimaryColor": "var(--gf-primary)",
			"-SecondaryColor": "#000",
			"--secondary-color": "#fff",
			color: "var(--primary-color)",
		});
		expect(styles).toEqual({
			"--primary-color": "var(--gf-primary)",
			"--secondary-color": "#fff",
			color: "var(--primary-color)",
		});
	});
});
