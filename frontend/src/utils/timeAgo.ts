// //// Neoffice — added file (no upstream equivalent): the words of « 3 weeks ago » in the person's language. vueuse's
// //// UseTimeAgo writes them in English unless it is given its messages, and every list of pages read « Modifié 3 weeks
// //// ago » on a French site (neoffice-maintenance#1200). Each phrase goes through __() so the catalogue translates it.
import { __ } from "@/translation";
import type { UseTimeAgoMessages, UseTimeAgoUnitNamesDefault } from "@vueuse/core";

const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

export function timeAgoMessages(): UseTimeAgoMessages<UseTimeAgoUnitNamesDefault> {
	return {
		justNow: __("just now"),
		past: (n: string) => (/\d/.test(n) ? __("{0} ago", [n]) : n),
		future: (n: string) => (/\d/.test(n) ? __("in {0}", [n]) : n),
		month: (n: number, past: boolean) =>
			n === 1 ? (past ? __("last month") : __("next month")) : __("{0} months", [n]),
		year: (n: number, past: boolean) =>
			n === 1 ? (past ? __("last year") : __("next year")) : __("{0} years", [n]),
		day: (n: number, past: boolean) =>
			n === 1 ? (past ? __("yesterday") : __("tomorrow")) : __("{0} days", [n]),
		week: (n: number, past: boolean) =>
			n === 1 ? (past ? __("last week") : __("next week")) : __("{0} weeks", [n]),
		hour: (n: number) => plural(n, __("1 hour"), __("{0} hours", [n])),
		minute: (n: number) => plural(n, __("1 minute"), __("{0} minutes", [n])),
		second: (n: number) => plural(n, __("1 second"), __("{0} seconds", [n])),
		invalid: "",
	};
}
