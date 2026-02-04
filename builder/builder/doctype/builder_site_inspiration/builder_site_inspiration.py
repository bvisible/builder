# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
from typing import Optional

import frappe
from frappe.model.document import Document


class BuilderSiteInspiration(Document):
    """
    Builder Site Inspiration DocType

    Allows users to capture websites or upload images for design inspiration.
    Automatically analyzes images to extract dominant colors and patterns.
    """

    def before_save(self):
        """Trigger capture/analysis before save if needed."""
        # For uploaded images, analyze immediately
        if self.source_type == "Image" and self.image:
            if self.status == "pending" or not self.analysis:
                self.analyze_image()

    def after_insert(self):
        """Queue capture for URL sources after insert."""
        if self.source_type == "URL" and self.url and self.status == "pending":
            # Queue the capture as a background job
            frappe.enqueue(
                "builder.builder.doctype.builder_site_inspiration.builder_site_inspiration.capture_and_analyze",
                doc_name=self.name,
                queue="default",
                timeout=120,
            )
            frappe.db.set_value(
                self.doctype, self.name, "status", "capturing", update_modified=False
            )
            frappe.db.commit()

    def analyze_image(self):
        """Analyze the uploaded image to extract colors."""
        try:
            from builder.ai.inspiration.analyzer import DesignAnalyzer

            analyzer = DesignAnalyzer()

            # Get the image source
            if self.source_type == "Image" and self.image:
                image_path = self.image
            elif self.screenshot:
                image_path = self.screenshot
            else:
                return

            # Analyze
            result = analyzer.analyze_from_file_url(image_path)

            # Store analysis
            self.analysis = json.dumps(result, indent=2)
            self.status = "captured"
            self.captured_at = frappe.utils.now()

        except Exception as e:
            frappe.log_error("Inspiration analysis failed", str(e))
            self.status = "failed"
            self.error_message = str(e)[:500]

    def capture_website(self):
        """Capture screenshot of the website URL."""
        if not self.url or self.source_type != "URL":
            return

        try:
            from builder.ai.inspiration.screenshotter import WebsiteScreenshotter

            screenshotter = WebsiteScreenshotter()
            result = screenshotter.capture_and_save(self.url)

            if result.get("success"):
                self.screenshot = result["file_url"]
                self.status = "captured"
                self.captured_at = frappe.utils.now()

                # Now analyze the screenshot
                self.analyze_image()
            else:
                self.status = "failed"
                self.error_message = result.get("error", "Unknown error")

        except Exception as e:
            frappe.log_error("Website capture failed", str(e))
            self.status = "failed"
            self.error_message = str(e)[:500]

    def get_analysis_dict(self) -> dict:
        """Get the analysis data as a dict."""
        if not self.analysis:
            return {}
        try:
            return json.loads(self.analysis)
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_dominant_colors(self) -> list[str]:
        """Get list of dominant color hex codes."""
        analysis = self.get_analysis_dict()
        colors = analysis.get("dominant_colors", [])
        return [c.get("hex") for c in colors if c.get("hex")]


def capture_and_analyze(doc_name: str):
    """
    Background job to capture website and analyze.

    Args:
        doc_name: Name of the Builder Site Inspiration document
    """
    doc = frappe.get_doc("Builder Site Inspiration", doc_name)

    try:
        doc.capture_website()
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("Capture job failed", str(e))
        frappe.db.set_value(
            "Builder Site Inspiration",
            doc_name,
            {
                "status": "failed",
                "error_message": str(e)[:500],
            },
            update_modified=False,
        )
        frappe.db.commit()


@frappe.whitelist()
def capture_inspiration(
    url: str = None,
    image: str = None,
    sentiment: str = "like",
    description: str = None,
) -> dict:
    """
    API to capture a new inspiration source.

    Args:
        url: Website URL to capture (optional)
        image: Uploaded image file URL (optional)
        sentiment: User sentiment (like, dislike, neutral)
        description: User description/notes

    Returns:
        dict with doc name and status
    """
    if not url and not image:
        frappe.throw("Either url or image is required")

    source_type = "URL" if url else "Image"

    doc = frappe.get_doc({
        "doctype": "Builder Site Inspiration",
        "source_type": source_type,
        "url": url,
        "image": image,
        "sentiment": sentiment,
        "description": description,
        "status": "pending",
    })
    doc.insert(ignore_permissions=True)

    return {
        "name": doc.name,
        "status": doc.status,
        "message": "Capture started" if source_type == "URL" else "Image analyzed",
    }


@frappe.whitelist()
def get_inspirations(limit: int = 20, sentiment: str = None) -> list[dict]:
    """
    Get list of inspirations.

    Args:
        limit: Max number to return
        sentiment: Optional filter by sentiment

    Returns:
        List of inspiration summaries
    """
    filters = {"status": "captured"}
    if sentiment:
        filters["sentiment"] = sentiment

    inspirations = frappe.get_all(
        "Builder Site Inspiration",
        filters=filters,
        fields=[
            "name", "source_type", "url", "image", "screenshot", "thumbnail",
            "sentiment", "description", "status", "captured_at", "analysis"
        ],
        order_by="creation desc",
        limit=limit,
    )

    # Parse analysis and extract colors for preview
    for insp in inspirations:
        if insp.get("analysis"):
            try:
                analysis = json.loads(insp["analysis"])
                insp["dominant_colors"] = [
                    c.get("hex") for c in analysis.get("dominant_colors", [])[:5]
                ]
            except (json.JSONDecodeError, TypeError):
                insp["dominant_colors"] = []
        else:
            insp["dominant_colors"] = []

    return inspirations


@frappe.whitelist()
def analyze_inspirations_for_generation(inspiration_names: str = None) -> dict:
    """
    Analyze inspirations and return data for AI generation.

    Args:
        inspiration_names: JSON array of inspiration names (or None for all)

    Returns:
        Aggregated inspiration data for the design brief
    """
    filters = {"status": "captured"}

    if inspiration_names:
        names = json.loads(inspiration_names)
        filters["name"] = ["in", names]

    inspirations = frappe.get_all(
        "Builder Site Inspiration",
        filters=filters,
        fields=["sentiment", "description", "analysis"],
    )

    # Aggregate data
    liked_colors = []
    disliked_colors = []
    notes = {"like": [], "dislike": []}

    for insp in inspirations:
        sentiment = insp.get("sentiment", "neutral")

        if insp.get("analysis"):
            try:
                analysis = json.loads(insp["analysis"])
                colors = [c.get("hex") for c in analysis.get("dominant_colors", [])[:3]]

                if sentiment == "like":
                    liked_colors.extend(colors)
                elif sentiment == "dislike":
                    disliked_colors.extend(colors)
            except (json.JSONDecodeError, TypeError):
                pass

        if insp.get("description") and sentiment in notes:
            notes[sentiment].append(insp["description"])

    return {
        "liked_colors": list(dict.fromkeys(liked_colors))[:8],
        "disliked_colors": list(dict.fromkeys(disliked_colors))[:5],
        "liked_notes": notes["like"][:5],
        "disliked_notes": notes["dislike"][:3],
        "total_inspirations": len(inspirations),
    }
