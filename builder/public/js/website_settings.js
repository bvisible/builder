//// Neoffice — added file (no upstream equivalent): desk hint on Website Settings pointing at Website
//// Header Footer Config. builder/templates/includes/header_footer/** = the Neoffice site chrome
//// (Website Header Footer Config). First commit e68c9754 2026-02-27.
// Client script for Website Settings: show link to Website Header Footer Config
frappe.ui.form.on("Website Settings", {
	refresh(frm) {
		frm.set_intro(
			__('Menu and theme are managed in {0}.',
				['<a href="/app/website-header-footer-config">' + __('Website Header Footer Config') + '</a>']
			),
			'blue'
		);
	}
});
