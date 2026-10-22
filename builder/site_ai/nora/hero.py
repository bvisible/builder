# //// Neoffice — added file (no upstream equivalent): what stands behind the home's hero, and how its copy sits on it.
"""The page writer was told "hero style: image" and nothing more. Over 23 test builds of the home page the hero was a flat
block of the primary colour in 17, a photograph in none (five carried a placeholder that was never filled), a real
gradient of two colours in two, and its copy was always left-aligned (2026-10-20): the brief's `hero_background` never
reached the writer, the plan's hero line says "the promise, a sentence, the CTA", and the one example it was shown was a flat,
left-aligned block. The recipe is said in the page brief of the home, with the site's own handles and the structure in the
writer's YAML, because a model of this size copies an example before it obeys a rule.

What stands behind the copy:
  - the hero style "image", with a photograph to put there: the photograph under the site's own veil (`u-over-image`);
  - every other style, and "image" without a photograph: a gradient of two brand colours, deep on a site that has a dark
    primary, a soft tint of the brand on a light ground and on the light styles (minimal, split, asymmetric, cards).
How the copy sits (the composition), one per site, from the brief's hero style and tone and the same on every revision:
  - left: the copy on the left over the left-hand veil (a professional or a bold direction);
  - centred: the copy centred, low on the photograph over the even `--center` veil (an elegant or a minimal direction);
  - split: the copy in a narrow column and a photograph in a wide one, on the light gradient (split, asymmetric, cards).

No model is called."""

from builder.site_ai.nora.contrast import luminance, parse_color

LIGHT_STYLES = ("minimal", "split", "asymmetric", "cards")
SPLIT_STYLES = ("split", "asymmetric", "cards")
CENTRED_TONES = ("elegant", "minimal")
DARK = 0.2
GRID_FALLBACKS = {"container": "1200px", "gutter": "48px", "gutter-phone": "24px"}


def composition(hero_style: str, tone: str, photo: str | None) -> str:
	"""How the hero's copy sits, "split", "centred" or "left", from the hero style and the tone of the brief."""
	if (hero_style or "") in SPLIT_STYLES and photo:
		return "split"
	if (hero_style or "") == "minimal" or (tone or "") in CENTRED_TONES:
		return "centred"
	return "left"


def _hex(rgb) -> str:
	return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb[:3])


def _mix(color, toward, share: float):
	return tuple(c + (t - c) * share for c, t in zip(color[:3], toward, strict=False))


def _resolve(handles: dict, palette: dict, role: str):
	"""(r, g, b, a) of a role's token, or None when the site gave none."""
	handle = (handles.get(role) or "").strip()
	if handle.startswith("var(--") and handle.endswith(")"):
		return parse_color(palette.get(handle[6:-1]), palette)
	return parse_color(handle, palette)


def _rgba(color, alpha: float) -> str:
	return f"rgba({round(color[0])}, {round(color[1])}, {round(color[2])}, {alpha})"


def _grid(handles: dict, name: str) -> str:
	return handles.get(name) or GRID_FALLBACKS[name]


def _copy_container(handles: dict, centred: bool, over_photo: bool = False) -> str:
	"""The container of the copy, in the writer's YAML: the grid the header and the footer share, the copy centred or not."""
	align = "alignItems: center, textAlign: center" if centred else "alignItems: flex-start"
	# the veil darkens the photograph where it was drawn to, not where a bright sky happens to sit behind a sentence: the copy over a
	# photograph carries a soft shadow of its own (text-shadow is inherited, so one line on the container serves every line of copy)
	shadow = ", textShadow: '0 1px 14px rgba(0,0,0,0.5)'" if over_photo else ""
	return (
		"    - el: div\n"
		"      name: hero-copy\n"
		f"      style: {{maxWidth: {_grid(handles, 'container')}, width: 100%, paddingLeft: {_grid(handles, 'gutter')}, "
		f"paddingRight: {_grid(handles, 'gutter')}, display: flex, flexDirection: column, {align}{shadow}}}\n"
		f"      m_style: {{paddingLeft: {_grid(handles, 'gutter-phone')}, paddingRight: {_grid(handles, 'gutter-phone')}}}\n"
		"      # the label, the h1 with its accent word, one sentence and the button, as in the example"
		+ (
			" (the h1 maxWidth 46rem, the sentence maxWidth 36rem, the button centred)"
			if centred
			else " (the h1 maxWidth 40rem and the sentence maxWidth 28rem, so that the copy stays on the left half, where the veil is deepest)"
		)
	)


# the alt of the hero photograph is the prompt of the image generator, and the guard that keeps a picture from stating something false
# withholds a slot whose alt names the business: the hero of a site came out a plain beige block (2026-10-21)
def _photo_hero(handles: dict, behind: str, photo: str, language: str, centred: bool) -> str:
	scrim = "[u-over-image, u-over-image--center]" if centred else "[u-over-image]"
	where = "alignItems: flex-end, paddingBottom: 6rem" if centred else "alignItems: center"
	sit = (
		"The copy is CENTRED, low on the photograph so that it breathes above; `u-over-image--center` is the even veil that holds centred copy"
		if centred
		else "The copy sits on the left, where the veil is deepest"
	)
	return (
		"HERO BACKGROUND (the home's first section; it decides the opening and wins over the example above): a PHOTOGRAPH under the "
		"site's own veil, never a flat colour. The class `u-over-image` IS the veil: write no overlay, no gradient and no wash of your own "
		f"over the picture. {sit}. The picture is the section's first child, laid across it; the copy container is the second, in white:\n"
		"- el: section\n"
		"  name: hero\n"
		f"  classes: {scrim}\n"
		f"  style: {{position: relative, minHeight: 85vh, width: 100%, display: flex, {where}, justifyContent: center, backgroundColor: {behind}}}\n"
		"  c:\n"
		"    - el: img\n"
		f"      attrs: {{src: '{photo}', alt: 'WRITE a photographic description of the scene in {language}: the subject, the setting, the light, never the name of the business'}}\n"
		"      style: {position: absolute, inset: '0', width: 100%, height: 100%, objectFit: cover}\n"
		+ _copy_container(handles, centred, over_photo=True)
	)


def _split_hero(handles: dict, stops: str, photo: str, language: str) -> str:
	return (
		"HERO BACKGROUND (the home's first section; it wins over the example above): a SPLIT hero on a soft gradient of two brand colours "
		"(the page background into a tint of the brand): a narrow column of copy beside a wide photograph, never a flat block and "
		"never a full-bleed picture. The ink is the text colour:\n"
		"- el: section\n"
		"  name: hero\n"
		f"  style: {{backgroundColor: {handles['background']}, backgroundImage: '{stops}', width: 100%, display: flex, justifyContent: center, alignItems: center, minHeight: 80vh}}\n"
		"  c:\n"
		"    - el: div\n"
		"      name: hero-grid\n"
		f"      style: {{maxWidth: {_grid(handles, 'container')}, width: 100%, paddingLeft: {_grid(handles, 'gutter')}, paddingRight: {_grid(handles, 'gutter')}, "
		"display: grid, gridTemplateColumns: 5fr 7fr, gap: 4rem, alignItems: center}\n"
		f"      m_style: {{gridTemplateColumns: 1fr, gap: 2rem, paddingLeft: {_grid(handles, 'gutter-phone')}, paddingRight: {_grid(handles, 'gutter-phone')}}}\n"
		"      c:\n"
		"        - el: div\n"
		"          name: hero-copy\n"
		"          # the label, the h1 with its accent word, one sentence and the button, left-aligned, as in the example\n"
		"        - el: img\n"
		"          classes: [u-media]\n"
		f"          attrs: {{src: '{photo}', alt: 'WRITE a photographic description of the scene in {language}: the subject, the setting, the light, never the name of the business'}}\n"
		"          style: {width: 100%, height: 34rem, objectFit: cover}\n"
		"          m_style: {height: 18rem}"
	)


def hero_recipe(
	hero_style: str,
	handles: dict,
	palette: dict | None,
	ground: str,
	photo: str | None,
	language: str = "fr",
	tone: str = "",
) -> str:
	"""The line of the home's page brief that says what stands behind the hero and how its copy sits ("" when the site has no
	colour to build it on)."""
	palette = palette or {}
	primary, text, background = (handles.get(k) for k in ("primary", "text", "background"))
	secondary = handles.get("secondary")
	if not (primary and text and background):
		return ""
	p, t, b = (_resolve(handles, palette, k) for k in ("primary", "text", "background"))
	s = _resolve(handles, palette, "secondary") or p
	style = hero_style or ""
	sits = composition(style, tone, photo)
	centred = sits == "centred"
	if style == "image" and photo and sits != "split":
		# what shows behind a picture that is still a plain block: the ink when it is dark, else the primary
		behind = text if t and luminance(t) <= DARK else primary
		return _photo_hero(handles, behind, photo, language, centred)
	if not (p and t and b):
		return ""
	light = ground == "light" or style in LIGHT_STYLES or (luminance(p) > DARK and ground != "dark")
	if light:
		tint = p if luminance(p) > DARK or not s else s
		stops = f"linear-gradient(160deg, {background} 0%, {_rgba(tint, 0.3)} 100%)"
		if sits == "split":
			return _split_hero(handles, stops, photo, language)
		sit = (
			" Centre the copy: a column that is centred, a centred text, a centred button." if centred else ""
		)
		return (
			"HERO BACKGROUND (the home's first section; it wins over the example above): a soft GRADIENT of two brand colours, never a flat "
			"block: the page background into a tint of the brand. The section's style carries exactly "
			f"backgroundColor: {background}, backgroundImage: '{stops}'. The ink is {text}; the accent word of the h1 is {primary}. "
			f"No photograph and no overlay in the hero.{sit}"
		)
	# a deep hero: the primary into the ink, or into a deeper shade of itself when the ink is not dark (and from the page
	# background when the primary is not dark itself, on a dark site); a glow of the secondary over it
	if luminance(p) <= DARK and luminance(t) <= DARK:
		start, end = primary, text
	else:
		start, end = (primary if luminance(p) <= DARK else background), _hex(_mix(p, (0, 0, 0), 0.55))
	# the copy is the light one of the two: the page background on a site whose ground is light, the text colour on a dark one
	ink = background if luminance(b) > DARK else text
	accent = secondary or ink
	glow = f"radial-gradient(ellipse at 80% 15%, {_rgba(s, 0.28)}, transparent 55%), " if s else ""
	stops = f"{glow}linear-gradient(160deg, {start} 0%, {end} 100%)"
	sit = " Centre the copy: a column that is centred, a centred text, a centred button." if centred else ""
	return (
		"HERO BACKGROUND (the home's first section; it wins over the example above): a GRADIENT of two brand colours with a soft glow, never "
		"a flat block. The section's style carries exactly "
		f"backgroundColor: {start}, backgroundImage: '{stops}'. The ink is {ink}; the accent word of the h1 is {accent}. "
		f"No photograph and no overlay in the hero.{sit}"
	)


# a hero photograph whose description the guard would keep from the image job (it names someone, a portrait, a document) is described by
# the scene of the business instead, so the home never opens on a plain block for that reason alone (2026-10-22: the cabinet's hero)
HERO_SCENE = {
	"fr": "Intérieur lumineux et accueillant d'une activité de {activity}, lumière naturelle, sans personnes ni texte",
	"en": "Bright, welcoming interior of a business in {activity}, natural light, no people, no text",
	"de": "Heller, einladender Innenraum eines Betriebs für {activity}, natürliches Licht, ohne Personen und Text",
	"it": "Interno luminoso e accogliente di un'attività di {activity}, luce naturale, senza persone né testo",
}


def rescue_hero_alt(blocks: list, names, activity: str, lang: str = "fr") -> list[str]:
	"""Gives the picture of the first section of the home a scene to draw when its own description would keep it from the image job.
	Only a placeholder (a photograph still to be made) is touched; a real photograph and a description the guard accepts are left as
	they are. Returns the descriptions it replaced."""
	from builder.site_ai.nora.layout import _walk
	from builder.site_ai.nora.placeholders import must_not_be_drawn

	scene = HERO_SCENE.get(str(lang or "fr")[:2], HERO_SCENE["fr"]).format(activity=" ".join(str(activity or "").split())[:80] or "services")
	known = {str(n).strip().lower() for n in names or () if str(n).strip()}
	roots = [b for b in blocks or [] if isinstance(b, dict)]
	first = next(iter(roots[0].get("children") or []), None) if roots else None
	replaced: list[str] = []
	for block in _walk([first] if isinstance(first, dict) else []):
		attrs = block.get("attributes") or {}
		src = attrs.get("src")
		if str(block.get("element") or "").lower() == "img" and isinstance(src, str) and "placehold.co" in src:
			alt = str(attrs.get("alt") or "")
			if alt and must_not_be_drawn(alt, known):
				attrs["alt"] = scene
				replaced.append(alt[:60])
	return replaced
