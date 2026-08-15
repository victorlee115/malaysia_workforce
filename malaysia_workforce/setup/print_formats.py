from __future__ import annotations

import frappe
from frappe import _


SALARY_SLIP_PRINT_FORMAT = "Malaysia Payslip"
STANDARD_SALARY_SLIP_FORMATS = {
	"Standard",
	"Salary Slip Standard",
	"Salary Slip with Year to Date",
	"Salary Slip based on Timesheet",
}


SALARY_SLIP_HTML = r"""
<style>
    .mw-payslip {
        color: #171717;
        font-family: var(--font-stack, Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
        font-size: 10.5px;
        line-height: 1.35;
    }

    .mw-payslip table {
        border-collapse: collapse;
        margin: 0;
        width: 100%;
    }

    .mw-payslip th,
    .mw-payslip td {
        padding: 5px 7px;
        vertical-align: top;
    }

    .mw-payslip .letterhead {
        margin-bottom: 10px;
    }

    .mw-payslip .fallback-letterhead {
        border-bottom: 2px solid #2490ef;
        margin-bottom: 12px;
        padding: 0 0 8px;
    }

    .mw-payslip .company-name {
        font-size: 16px;
        font-weight: 700;
    }

    .mw-payslip .company-registration {
        color: #6b7280;
        font-size: 9px;
        margin-top: 2px;
    }

    .mw-payslip .title-row {
        border-bottom: 1px solid #d1d5db;
        margin-bottom: 10px;
        padding-bottom: 7px;
    }

    .mw-payslip .title {
        font-size: 18px;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .mw-payslip .document-number {
        color: #6b7280;
        font-size: 9px;
        text-align: right;
    }

    .mw-payslip .meta {
        margin-bottom: 10px;
    }

    .mw-payslip .meta td {
        border: 1px solid #e5e7eb;
        width: 25%;
    }

    .mw-payslip .label {
        color: #6b7280;
        display: block;
        font-size: 8.5px;
        margin-bottom: 2px;
        text-transform: uppercase;
    }

    .mw-payslip .value {
        font-weight: 600;
        overflow-wrap: anywhere;
    }

    .mw-payslip .summary {
        margin-bottom: 12px;
    }

    .mw-payslip .summary td {
        background: #f5f7fa;
        border: 1px solid #e5e7eb;
        padding: 8px 9px;
        width: 25%;
    }

    .mw-payslip .summary .summary-value {
        font-size: 14px;
        font-weight: 700;
    }

    .mw-payslip .summary .net-pay {
        background: #eaf6ef;
        border-color: #b9dec6;
    }

    .mw-payslip .section {
        margin: 12px 0 0;
        page-break-inside: avoid;
    }

    .mw-payslip .section-title {
        background: #f5f7fa;
        border-bottom: 2px solid #2490ef;
        font-size: 11px;
        font-weight: 700;
        padding: 6px 7px;
    }

    .mw-payslip .data-table {
        page-break-inside: auto;
    }

    .mw-payslip .data-table thead {
        display: table-header-group;
    }

    .mw-payslip .data-table tr {
        page-break-inside: avoid;
    }

    .mw-payslip .data-table th {
        background: #fafafa;
        border-bottom: 1px solid #d1d5db;
        color: #4b5563;
        font-size: 8.5px;
        font-weight: 600;
        text-transform: uppercase;
    }

    .mw-payslip .data-table td {
        border-bottom: 1px solid #edf0f2;
    }

    .mw-payslip .data-table .amount {
        text-align: right;
        white-space: nowrap;
        width: 20%;
    }

    .mw-payslip .data-table .scheme {
        width: 40%;
    }

    .mw-payslip .statutory-table .scheme {
        width: 24%;
    }

    .mw-payslip .statutory-table .base {
        text-align: right;
        white-space: nowrap;
        width: 19%;
    }

    .mw-payslip .statutory-table .amount {
        width: 19%;
    }

    .mw-payslip .statutory-table {
        table-layout: fixed;
        font-size: 9.5px;
    }

    .mw-payslip .statutory-table th,
    .mw-payslip .statutory-table td {
        box-sizing: border-box;
        padding-left: 4px;
        padding-right: 4px;
    }

    .mw-payslip .statutory-table th.amount {
        white-space: normal;
    }

    .mw-payslip .muted {
        color: #6b7280;
    }

    .mw-payslip .totals {
        margin-top: 12px;
        page-break-inside: avoid;
    }

    .mw-payslip .totals td {
        border-top: 1px solid #d1d5db;
        padding: 6px 7px;
    }

    .mw-payslip .totals .total-label {
        text-align: right;
        width: 75%;
    }

    .mw-payslip .totals .net-row td {
        border-top: 2px solid #171717;
        font-size: 12px;
        font-weight: 700;
    }

    .mw-payslip .footer {
        border-top: 1px solid #e5e7eb;
        color: #6b7280;
        font-size: 8.5px;
        margin-top: 14px;
        padding-top: 7px;
        page-break-inside: avoid;
    }

    @media print {
        @page {
            size: A4 portrait;
            margin: 11mm 12mm;
        }

        .mw-payslip .section,
        .mw-payslip .totals,
        .mw-payslip .footer {
            break-inside: avoid;
        }
    }
</style>

<div class="mw-payslip">
    {% if letter_head %}
        <div class="letterhead">{{ letter_head }}</div>
    {% else %}
        <div class="fallback-letterhead">
            <div class="company-name">{{ doc.company }}</div>
            {% set registration_number = frappe.db.get_value("Company", doc.company, "custom_company_registration_number") %}
            {% if registration_number %}
                <div class="company-registration">{{ registration_number }}</div>
            {% endif %}
        </div>
    {% endif %}

    <table class="title-row">
        <tr>
            <td style="padding-left: 0;">
                <div class="title">{{ _("Salary Slip") }}</div>
                <div class="muted">{{ doc.get_formatted("start_date") }} – {{ doc.get_formatted("end_date") }}</div>
            </td>
            <td class="document-number" style="padding-right: 0;">
                {{ doc.name }}<br>
                {{ doc.get_formatted("posting_date") }}
            </td>
        </tr>
    </table>

    <table class="meta">
        <tr>
            <td>
                <span class="label">{{ _("Employee") }}</span>
                <span class="value">{{ doc.employee_name or doc.employee }}</span>
            </td>
            <td>
                <span class="label">{{ _("Employee Number") }}</span>
                <span class="value">{{ doc.employee }}</span>
            </td>
            <td>
                <span class="label">{{ _("Designation") }}</span>
                <span class="value">{{ doc.designation or "—" }}</span>
            </td>
            <td>
                <span class="label">{{ _("Department / Branch") }}</span>
                <span class="value">{{ doc.department or "—" }}{% if doc.branch %} / {{ doc.branch }}{% endif %}</span>
            </td>
        </tr>
        <tr>
            <td>
                <span class="label">{{ _("Payroll Frequency") }}</span>
                <span class="value">{{ doc.payroll_frequency or "—" }}</span>
            </td>
            <td>
                <span class="label">{{ _("Payment Days") }}</span>
                <span class="value">{{ doc.payment_days or 0 }}</span>
            </td>
            <td>
                <span class="label">{{ _("Working Days") }}</span>
                <span class="value">{{ doc.total_working_days or 0 }}</span>
            </td>
            <td>
                <span class="label">{{ _("Leave Without Pay") }}</span>
                <span class="value">{{ doc.leave_without_pay or 0 }}</span>
            </td>
        </tr>
    </table>

    <table class="summary">
        <tr>
            <td>
                <span class="label">{{ _("Gross Earnings") }}</span>
                <span class="summary-value">{{ doc.get_formatted("gross_pay") }}</span>
            </td>
            <td>
                <span class="label">{{ _("Total Deductions") }}</span>
                <span class="summary-value">{{ doc.get_formatted("total_deduction") }}</span>
            </td>
            <td class="net-pay">
                <span class="label">{{ _("Net Pay") }}</span>
                <span class="summary-value">{{ doc.get_formatted("net_pay") }}</span>
            </td>
            <td>
                <span class="label">{{ _("Currency") }}</span>
                <span class="summary-value">{{ doc.currency or "MYR" }}</span>
            </td>
        </tr>
    </table>

    <div class="section">
        <div class="section-title">{{ _("Earnings") }}</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th class="scheme">{{ _("Component") }}</th>
                    <th>{{ _("Notes") }}</th>
                    <th class="amount">{{ _("Amount") }}</th>
                </tr>
            </thead>
            <tbody>
                {% set earnings = namespace(has_rows=false) %}
                {% for row in doc.earnings or [] %}
                    {% if row.amount %}
                        {% set earnings.has_rows = true %}
                        <tr>
                            <td>{{ row.salary_component }}</td>
                            <td class="muted">{% if row.depends_on_payment_days %}{{ _("Payment-day based") }}{% endif %}</td>
                            <td class="amount">{{ row.get_formatted("amount", doc) }}</td>
                        </tr>
                    {% endif %}
                {% endfor %}
                {% if not earnings.has_rows %}
                    <tr><td colspan="3" class="muted">{{ _("No earnings recorded for this period.") }}</td></tr>
                {% endif %}
            </tbody>
        </table>
    </div>

    <div class="section">
        <div class="section-title">{{ _("Deductions") }}</div>
        <table class="data-table">
            <thead>
                <tr>
                    <th class="scheme">{{ _("Component") }}</th>
                    <th>{{ _("Notes") }}</th>
                    <th class="amount">{{ _("Amount") }}</th>
                </tr>
            </thead>
            <tbody>
                {% set deductions = namespace(has_rows=false) %}
                {% for row in doc.deductions or [] %}
                    {% if row.amount %}
                        {% set deductions.has_rows = true %}
                        <tr>
                            <td>{{ row.salary_component }}</td>
                            <td class="muted">{% if row.depends_on_payment_days %}{{ _("Payment-day based") }}{% endif %}</td>
                            <td class="amount">{{ row.get_formatted("amount", doc) }}</td>
                        </tr>
                    {% endif %}
                {% endfor %}
                {% if not deductions.has_rows %}
                    <tr><td colspan="3" class="muted">{{ _("No deductions recorded for this period.") }}</td></tr>
                {% endif %}
            </tbody>
        </table>
    </div>

    {% set statutory_rows = doc.custom_malaysia_statutory_results or [] %}
    {% set statutory = namespace(has_rows=false) %}
    {% for row in statutory_rows %}
        {% if row.applicable and (row.wage_base or row.employee_amount or row.employer_amount or row.extra_employee_amount) %}
            {% set statutory.has_rows = true %}
        {% endif %}
    {% endfor %}
    {% if statutory.has_rows %}
        <div class="section statutory-section">
            <div class="section-title">{{ _("Statutory Contributions") }}</div>
            <table class="data-table statutory-table">
                <thead>
                    <tr>
                        <th class="scheme">{{ _("Scheme") }}</th>
                        <th class="base">{{ _("Wage Base") }}</th>
                        <th class="amount">{{ _("Employee") }}</th>
                        <th class="amount">{{ _("Additional Employee") }}</th>
                        <th class="amount">{{ _("Employer") }}</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in statutory_rows|sort(attribute="scheme") %}
                        {% if row.applicable and (row.wage_base or row.employee_amount or row.employer_amount or row.extra_employee_amount) %}
                            <tr>
                                <td>{{ row.scheme }}</td>
                                <td class="base">{{ row.get_formatted("wage_base", doc) }}</td>
                                <td class="amount">{{ row.get_formatted("employee_amount", doc) }}</td>
                                <td class="amount">{% if row.extra_employee_amount %}{{ row.get_formatted("extra_employee_amount", doc) }}{% else %}—{% endif %}</td>
                                <td class="amount">{{ row.get_formatted("employer_amount", doc) }}</td>
                            </tr>
                        {% endif %}
                    {% endfor %}
                </tbody>
            </table>
        </div>
    {% endif %}

    <table class="totals">
        <tr>
            <td class="total-label">{{ _("Gross Earnings") }}</td>
            <td class="amount">{{ doc.get_formatted("gross_pay") }}</td>
        </tr>
        <tr>
            <td class="total-label">{{ _("Total Deductions") }}</td>
            <td class="amount">{{ doc.get_formatted("total_deduction") }}</td>
        </tr>
        <tr class="net-row">
            <td class="total-label">{{ _("Net Pay") }}</td>
            <td class="amount">{{ doc.get_formatted("net_pay") }}</td>
        </tr>
        {% if doc.total_in_words %}
            <tr>
                <td class="total-label">{{ _("Total in Words") }}</td>
                <td>{{ doc.total_in_words }}</td>
            </tr>
        {% endif %}
    </table>

    {% set bank_account = doc.bank_account_no or "" %}
    <div class="footer">
        {% if bank_account %}{{ _("Payment account") }}: ****{{ bank_account[-4:] }} &nbsp;·&nbsp; {% endif %}
        {{ _("This payslip is provided for the employee's records. Statutory calculation details are retained in Frappe HR for authorised payroll users.") }}
    </div>
</div>
"""


SALARY_SLIP_CSS = """
.print-format {
    margin: 0;
    padding: 0;
}
"""


def ensure_salary_slip_print_format() -> None:
	"""Ensure the one employee-facing Salary Slip format is installed and selected."""
	if not frappe.db.exists("DocType", "Salary Slip"):
		return

	if frappe.db.exists("Print Format", SALARY_SLIP_PRINT_FORMAT):
		print_format = frappe.get_doc("Print Format", SALARY_SLIP_PRINT_FORMAT)
		if print_format.doc_type not in {None, "Salary Slip"}:
			frappe.throw(
				_("Print Format {0} belongs to {1}; rename it before enabling Malaysia Payroll.").format(
					frappe.bold(SALARY_SLIP_PRINT_FORMAT), frappe.bold(print_format.doc_type)
				)
			)
	else:
		print_format = frappe.new_doc("Print Format")
		print_format.name = SALARY_SLIP_PRINT_FORMAT

	print_format.update(
		{
			"doc_type": "Salary Slip",
			"print_format_for": "DocType",
			"standard": "No",
			"custom_format": 1,
			"disabled": 0,
			"print_format_type": "Jinja",
			"html": SALARY_SLIP_HTML,
			"css": SALARY_SLIP_CSS,
			"pdf_generator": None,
			"font": "Default",
			"font_size": 10,
			"margin_top": 11,
			"margin_bottom": 11,
			"margin_left": 12,
			"margin_right": 12,
			"page_number": "Bottom Right",
		}
	)
	if print_format.is_new():
		print_format.insert(ignore_permissions=True)
	else:
		print_format.save(ignore_permissions=True)

	default_print_format = frappe.get_meta("Salary Slip").default_print_format
	if (
		default_print_format not in (None, "", SALARY_SLIP_PRINT_FORMAT)
		and default_print_format not in STANDARD_SALARY_SLIP_FORMATS
	):
		frappe.throw(
			_("Salary Slip already uses the custom Print Format {0}. Set it to {1} before enabling Malaysia Payroll.").format(
				frappe.bold(default_print_format), frappe.bold(SALARY_SLIP_PRINT_FORMAT)
			)
		)

	if default_print_format != SALARY_SLIP_PRINT_FORMAT:
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		make_property_setter(
			"Salary Slip",
			None,
			"default_print_format",
			SALARY_SLIP_PRINT_FORMAT,
			"Data",
			for_doctype=True,
			validate_fields_for_doctype=False,
		)
		frappe.clear_cache(doctype="Salary Slip")
