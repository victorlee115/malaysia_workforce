import frappe
from frappe import _


def get_context(context):
	context.no_cache = 1
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/workforce"
		raise frappe.Redirect
	context.title = _("My Workforce")
	context.show_sidebar = False
	return context
