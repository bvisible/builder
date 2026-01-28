export interface BuilderAIConversation {
	name: string;
	title: string;
	status: "collecting" | "generating" | "completed" | "failed";
	page?: string;
	messages?: string;
	site_context?: string;
	generated_blocks?: string;
	creation?: string;
	modified?: string;
	owner?: string;
}

export interface AIMessage {
	role: "user" | "assistant" | "system";
	content: string;
}

export interface AISiteContext {
	site_type?: "landing_page" | "portfolio" | "business" | "blog" | "ecommerce";
	business_name?: string;
	tagline?: string;
	description?: string;
	target_audience?: string;
	style?: {
		primary_color?: string;
		secondary_color?: string;
		accent_color?: string;
		background_color?: string;
		text_color?: string;
		style_preference?: "modern" | "classic" | "minimal" | "bold" | "playful";
		font_style?: "sans-serif" | "serif" | "modern" | "classic";
	};
	sections?: AISection[];
	contact_info?: {
		email?: string;
		phone?: string;
		address?: string;
		social_links?: Record<string, string>;
	};
}

export interface AISection {
	type: "hero" | "features" | "testimonials" | "pricing" | "contact" | "about" | "cta" | "footer" | "navbar";
	headline?: string;
	subheadline?: string;
	description?: string;
	cta_text?: string;
	cta_link?: string;
	items?: AISectionItem[];
	image_description?: string;
}

export interface AISectionItem {
	title?: string;
	description?: string;
	icon?: string;
	price?: string;
	author?: string;
	image?: string;
}
