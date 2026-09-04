import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import path from "path";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
	define: {
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
	},
	plugins: [
		frappeui({
			frontendRoute: "/_builder",
			//// Neoffice — commit-the-build: the SPA is built on a Mac and in GitHub Actions, outside
			//// a bench, where frappe-ui's plugin cannot infer these paths from an apps/ layout.
			buildConfig: {
				// Standalone builds (local Mac / GitHub Actions) run outside a bench,
				// where the plugin cannot infer these from an apps/ folder layout.
				outDir: "../builder/public/frontend",
				indexHtmlPath: "../builder/www/_builder.html",
				baseUrl: "/assets/builder/frontend/",
			},
			frappeProxy: {
				port: 8080,
				source: "^/(app|desk|login|api|assets|files|pages|builder_assets)",
			},
			lucideIcons: true,
			frappeTypes: {
				input: {
					builder: [
						"block_template",
						"builder_client_script",
						"builder_component",
						"builder_page",
						"builder_page_client_script",
						"builder_project_folder",
						"builder_settings",
						"builder_variable",
						"user_font",
					],
				},
			},
		}),
		vue(),
	],
	build: {
		chunkSizeWarningLimit: 1500,
		target: "es2015",
		//// Neoffice — same standalone build: these bench-relative imports do not resolve there.
		rollupOptions: {
			// Ignore Frappe bench-specific imports that don't exist in standalone builds
			external: [
				/common_site_config\.json/,
				/\.\.\/\.\.\/\.\.\/frappe\//,
			],
		},
	},
	resolve: {
		dedupe: ["prosemirror-model", "prosemirror-view", "prosemirror-state", "prosemirror-transform"],
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	server: {
		allowedHosts: true,
	},
	optimizeDeps: {
		include: ["frappe-ui > feather-icons", "engine.io-client", "interactjs", "highlight.js/lib/core"],
	},
});
