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
	r"|\bist\s+(?:jetzt\s+)?(?:neu\s+)?(?:gebaut|veröffentlicht|online)",
	re.IGNORECASE,
)

NUDGE = (
	"Nothing was built in this turn: no tool ran. A site is built only by generate_site, after the recap "
	"card (present_ui) that the user approves. Do what the user asked now, with the tools, and never "
	"describe work that did not happen."
)


def unrun_build_claim(prompt: str, answer: str) -> bool:
	"""Whether the user asked for a build and the answer says one is done. The caller knows
	whether a tool ran; this reads the words only."""
	return bool(prompt and answer and BUILD_ASKED.search(prompt) and BUILD_CLAIMED.search(answer))
