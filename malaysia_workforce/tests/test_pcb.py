from datetime import date
from decimal import Decimal

from malaysia_workforce.statutory.calculators.pcb import calculate_pcb, leaver_breaks_annual_projection
from malaysia_workforce.statutory.common import PCBInput


def d(value: str | int | float) -> Decimal:
	return Decimal(str(value))


def test_lhdn_worked_example_january():
	result = calculate_pcb(
		PCBInput(
			month=1,
			resident=True,
			category=3,
			current_normal_gross=d(5500),
			current_normal_epf=d(605),
			child_units=d(3),
		)
	)
	assert result.payable == d("110.00")
	assert result.chargeable_income_normal == d("47000.07")


def test_lhdn_worked_example_february():
	result = calculate_pcb(
		PCBInput(
			month=2,
			resident=True,
			category=3,
			current_normal_gross=d(5500),
			current_normal_epf=d(605),
			prior_gross=d(5500),
			prior_epf_relief=d(605),
			prior_mtd=d(110),
			child_units=d(3),
		)
	)
	assert result.payable == d("110.00")
	assert result.chargeable_income_normal == d("47000.00")


def test_lhdn_worked_example_march_with_tp1_relief():
	result = calculate_pcb(
		PCBInput(
			month=3,
			resident=True,
			category=3,
			current_normal_gross=d(5500),
			current_normal_epf=d(605),
			prior_gross=d(11000),
			prior_epf_relief=d(1210),
			prior_mtd=d("220.00"),
			current_optional_reliefs=d(300),
			child_units=d(3),
		)
	)
	assert result.payable == d("108.20")
	assert result.chargeable_income_normal == d("46700.07")


def test_lhdn_worked_example_april_bonus():
	result = calculate_pcb(
		PCBInput(
			month=4,
			resident=True,
			category=3,
			current_normal_gross=d(5500),
			current_additional_gross=d(8250),
			current_normal_epf=d(605),
			current_additional_epf=d(908),
			prior_gross=d(16500),
			prior_epf_relief=d(1815),
			prior_mtd=d("328.20"),
			prior_optional_reliefs=d(300),
			current_optional_reliefs=d(300),
			child_units=d(3),
		)
	)
	assert result.normal_mtd_after_zakat == d("106.20")
	assert result.additional_mtd == d("727.50")
	assert result.payable == d("833.70")
	assert result.chargeable_income_with_additional == d("54650.00")


def test_zakat_reduces_pcb_in_additional_remuneration_month():
	base = dict(
		month=4, resident=True, category=3, current_normal_gross=d(5500),
		current_additional_gross=d(8250), current_normal_epf=d(605), current_additional_epf=d(908),
		prior_gross=d(16500), prior_epf_relief=d(1815), prior_mtd=d("328.20"),
		prior_optional_reliefs=d(300), current_optional_reliefs=d(300), child_units=d(3),
	)
	without_zakat = calculate_pcb(PCBInput(**base))
	with_current_zakat = calculate_pcb(PCBInput(**base, current_zakat=d(100)))
	with_prior_and_current = calculate_pcb(PCBInput(**base, prior_zakat=d(300), current_zakat=d(100)))
	assert without_zakat.payable == d("833.70")
	assert with_current_zakat.payable == d("733.70")
	assert with_prior_and_current.payable == d("727.20")
	assert with_current_zakat.payable < without_zakat.payable
	assert with_prior_and_current.payable <= with_current_zakat.payable


def test_nonresident_rate_and_minimum():
	result = calculate_pcb(
		PCBInput(
			month=8,
			resident=False,
			category=1,
			current_normal_gross=d(10000),
		)
	)
	assert result.payable == d("3000.00")


def test_disabled_spouse_relief_gated_on_category_2():
	"""A category 1/3 employee has no spouse relief claimed, so no disabled-spouse relief either."""
	base_args = dict(month=6, resident=True, current_normal_gross=d(8000))
	category_1_not_disabled = calculate_pcb(PCBInput(category=1, spouse_disabled=False, **base_args))
	category_1_disabled = calculate_pcb(PCBInput(category=1, spouse_disabled=True, **base_args))
	category_2_not_disabled = calculate_pcb(PCBInput(category=2, spouse_disabled=False, **base_args))
	category_2_disabled = calculate_pcb(PCBInput(category=2, spouse_disabled=True, **base_args))
	assert category_1_disabled.chargeable_income_normal == category_1_not_disabled.chargeable_income_normal
	assert category_2_disabled.chargeable_income_normal == category_2_not_disabled.chargeable_income_normal - d(6000)


def test_leaver_before_year_end_breaks_projection():
	"""A November leaver still breaks an October slip's projection through December."""
	assert leaver_breaks_annual_projection(date(2026, 11, 15), date(2026, 10, 31)) is True


def test_leaver_on_31_december_does_not_break_projection():
	assert leaver_breaks_annual_projection(date(2026, 12, 31), date(2026, 12, 31)) is False


def test_no_relieving_date_does_not_break_projection():
	assert leaver_breaks_annual_projection(None, date(2026, 6, 30)) is False


def test_relief_code_accepts_codes_and_labels():
	from malaysia_workforce.payroll.tax_validation import canonical_relief_code

	assert canonical_relief_code("C5") == "C5"
	assert canonical_relief_code("C5 - Lifestyle expenses") == "C5"
	assert canonical_relief_code("c16a - First-home") == "C16A"
	assert canonical_relief_code("") == ""


def test_pcb_category_number_accepts_codes_and_labels():
	from malaysia_workforce.payroll.validation import pcb_category_number

	assert pcb_category_number("1") == 1
	assert pcb_category_number("2 - Married, spouse not working") == 2
	assert pcb_category_number("3 - Married, spouse working") == 3
	assert pcb_category_number(None) == 1
	assert pcb_category_number("9") == 1


def test_invalid_month_rejected():
	try:
		calculate_pcb(PCBInput(month=13, resident=True, category=1, current_normal_gross=d(1000)))
	except ValueError as exc:
		assert "month" in str(exc).lower()
	else:
		raise AssertionError("Expected ValueError")
