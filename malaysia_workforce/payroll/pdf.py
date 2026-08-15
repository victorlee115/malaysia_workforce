from __future__ import annotations

import base64
import shutil

import frappe
from frappe import _


def select_pdf_generator() -> str:
	"""Choose the standard host renderer without probing it by rendering first."""
	return "wkhtmltopdf" if shutil.which("wkhtmltopdf") else "chrome"


@frappe.whitelist()
def download_salary_slip_pdf(doctype: str, docname: str) -> str:
	"""Return the native HRMS payslip download response with a safe PDF fallback.

	HRMS currently hard-codes ``wkhtmltopdf`` in its employee self-service
	endpoint. Frappe v16 also supports its native headless-Chrome renderer, so
	select the former when installed and the latter otherwise. The underlying
	Frappe print function still performs normal print permission checks.
	"""
	if doctype != "Salary Slip":
		frappe.throw(_("This endpoint only serves Salary Slip PDFs."))

	from frappe.utils.print_format import download_pdf

	print_format = frappe.get_meta(doctype).default_print_format or "Standard"
	pdf_generator = select_pdf_generator()

	try:
		download_pdf(doctype, docname, format=print_format, pdf_generator=pdf_generator)
	except Exception as exc:
		frappe.throw(_("Failed to download PDF: {0}").format(str(exc)))

	base64content = base64.b64encode(frappe.local.response.filecontent)
	content_type = frappe.local.response.type
	return f"data:{content_type};base64," + base64content.decode("utf-8")
