//// Neoffice — added file (no upstream equivalent): a CSS custom property is a name, not a kebab-case
//// property (neoffice-maintenance#2671). Upstream's toStyleProperty camel-cased every key of a block's
//// legacy rawStyles, and `--primary-color` became `-PrimaryColor`: the section lost its variable in the
//// canvas, and the next save wrote the broken key into the draft. The server renders such a key back to
//// `--primary-color` (camel_case_to_kebab_case), so a published page keeps it: only the editor lost it.

export type StyleMap = Record<string, unknown>;

// `--primary-color`, `hover:--accent`: kept as written
export function isCustomProperty(property: string): boolean {
	return property.trim().startsWith("--");
}

// what camel-casing did to a custom property: `-PrimaryColor`, `hover:-GfPrimary`. A real property never
// starts with a dash in its camel-case form (`WebkitLineClamp`), so the shape is the bug's and nothing else's.
const BROKEN_CUSTOM_PROPERTY = /^(?<prefix>(?:[a-z-]+:)?)-(?<name>[A-Z][A-Za-z0-9]*)$/;

// `-PrimaryColor` → `--primary-color`; null for any other key
export function repairedCustomProperty(key: string): string | null {
	const match = BROKEN_CUSTOM_PROPERTY.exec(key);
	if (!match?.groups) return null;
	const kebab = match.groups.name
		.replace(/([a-z0-9])([A-Z])/g, "$1-$2")
		.replace(/([A-Z])([A-Z][a-z])/g, "$1-$2")
		.toLowerCase();
	return `${match.groups.prefix}--${kebab}`;
}

// the same map with every broken key put back; a key already written correctly wins over its broken twin
export function repairCustomPropertyKeys<T extends StyleMap>(styles: T): T {
	if (!styles) return styles;
	for (const key of Object.keys(styles)) {
		const repaired = repairedCustomProperty(key);
		if (!repaired) continue;
		if (!(repaired in styles)) (styles as StyleMap)[repaired] = styles[key];
		delete (styles as StyleMap)[key];
	}
	return styles;
}
