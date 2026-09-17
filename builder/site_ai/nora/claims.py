# //// Neoffice — added file (no upstream equivalent): a turn that says a site was built when no
# //// tool ran is sent back to the model once.
"""Work claimed in a turn that did none.

Asked to rebuild a site, the chat model answered in eleven seconds "[the site] is rebuilt
and published… All four pages are live", word for word its answer to the previous build,
and called no tool: nothing was built (2026-09-13). A site is built by generate_site only.
The loop asks the model again, once, with that fact, and never lets such a claim end a turn
that ran nothing: see AgentRunner.send_back_unrun_claim.
"""

import re

# the user asks for a site to be built or rebuilt
BUILD_ASKED = re.compile(
	r"\b(?:re-?build|build|re-?do|re-?create|re-?generate|regenerate|make)\b[^.?!\n]{0,60}\b(?:site|website|pages?)\b"
	r"|\b(?:re)?constru\w*|\brefai\w*|\br[ée]g[ée]n[èe]r\w*|\brecr[ée]\w*|\bneu (?:erstellen|aufbauen)",
	re.IGNORECASE,
)
# the answer says it is done
BUILD_CLAIMED = re.compile(
	r"\b(?:is|are|was|were|has been|have been)\s+(?:now\s+)?(?:re)?(?:built|published|live|online)\b"
	r"|\b(?:est|sont|a été|ont été)\s+(?:maintenant\s+)?(?:re)?(?:construit|publié|en ligne)"
	r"|\bist\s+(?:jetzt\s+)?(?:neu\s+)?(?:gebaut|veröffentlicht|online)"
	# //// Neoffice — a build said LAUNCHED is a claim too (2026-09-17): "J'ai relancé la
	# //// reconstruction complète du site. Le processus est en cours." took six seconds and
	# //// called nothing; the words below are the tell of a build announced, not run.
	r"|\bj'?ai\s+(?:re)?lanc[ée]\b|\bje\s+(?:re)?lance\b|\b(?:le\s+)?processus\s+est\s+en\s+cours\b"
	r"|\b(?:re)?construction\s+(?:est\s+)?en\s+cours\b"
	r"|\bI(?:'ve|\s+have)?\s+(?:re)?(?:launched|started|kicked off)\b[^.?!\n]{0,40}\b(?:build|rebuild|site)\b"
	r"|\b(?:the\s+)?(?:re)?build\s+(?:is|has been)\s+(?:launched|started|running|under\s+way)\b",
	re.IGNORECASE,
)

NUDGE = (
	"Nothing was built in this turn: no tool ran. A site is built only by generate_site, after the recap "
	"card (present_ui) that the user approves. Do what the user asked now, with the tools, and never "
	"describe work that did not happen."
)


# //// Neoffice ▼▼▼ — a question announced is not a question asked (2026-09-16).
# //// Twice in one session the model answered "Avant de reconstruire le site, je te pose les
# //// questions essentielles." and ended the turn, calling nothing: no card, nothing to tap, the
# //// build stalled until a human nudged it. The playbook already forbids writing a card as prose
# //// — this is the other failure, announcing one and stopping. The words are the tell, so the
# //// loop sends the answer back once, exactly as it does for a build claimed but never run.
QUESTION_ANNOUNCED = re.compile(
	r"\b(?:je\s+(?:te|vous)\s+pose|je\s+vais\s+(?:te|vous)\s+poser|voici\s+(?:les|mes|la)\s+(?:questions?|carte))"
	r"|\b(?:quelques|les)\s+questions?\s+(?:essentielles|suivantes|ci-dessous)"
	r"|\b(?:here\s+are|I'?ll\s+ask|let\s+me\s+ask|I\s+will\s+ask)\b[^.?!\n]{0,40}\bquestions?\b"
	r"|\bich\s+stelle\s+(?:dir|Ihnen)\b",
	re.IGNORECASE,
)

NUDGE_QUESTION = (
	"You announced a question and then ended the turn without asking it: no card was shown, the user has "
	"nothing to tap, and the site cannot move on. A question reaches the user ONLY through a present_ui "
	"call. Call present_ui now with the card you just described — the announcement and the card belong to "
	"the same turn."
)


def announced_question_not_asked(answer: str) -> bool:
	"""Whether the answer says a question is coming. The caller knows no tool ran."""
	return bool(answer and QUESTION_ANNOUNCED.search(answer))


def unrun_build_claim(prompt: str, answer: str) -> bool:
	"""Whether the user asked for a build and the answer says one is done. The caller knows
	whether a tool ran; this reads the words only."""
	return bool(prompt and answer and BUILD_ASKED.search(prompt) and BUILD_CLAIMED.search(answer))


# //// Neoffice ▼▼▼ — a tool call written as TEXT (2026-09-17). Asked to rebuild a site, the chat
# //// model printed the arguments of generate_site as a JSON block ("site_name": …, "pages": […],
# //// "replace_existing": "force") and ended its turn: nothing ran, and the user read a wall of
# //// JSON where a build should have started. The loop sends that answer back once.
TOOL_ARGUMENT_KEYS = ("site_name", "pages", "website_profile", "replace_existing", "logo_image", "site_type", "activity")

NUDGE_CALL = (
	"You wrote the tool's arguments as text and ended the turn: nothing ran. A tool runs ONLY when you call it. "
	"Call generate_site now, with exactly the arguments you just wrote, and say nothing else until it answers."
)


def tool_call_written_as_text(answer: str) -> bool:
	"""Whether the answer is (or carries) a JSON object of generate_site arguments instead of a
	call. The caller knows no tool ran."""
	if not answer or "{" not in answer:
		return False
	body = answer.lower()
	quoted = sum(1 for key in TOOL_ARGUMENT_KEYS if f'"{key}"' in body)
	return quoted >= 3
# //// Neoffice ▲▲▲

