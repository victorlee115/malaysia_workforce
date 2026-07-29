from decimal import Decimal

from malaysia_workforce.statutory.calculators.eis import calculate_eis
from malaysia_workforce.statutory.calculators.epf import calculate_epf, determine_category
from malaysia_workforce.statutory.calculators.socso import calculate_socso


def d(value) -> Decimal:
	return Decimal(str(value))


def test_epf_part_a_table_band():
	result = calculate_epf(d(5500), "A")
	assert result.employee == d("605.00")
	assert result.employer == d("660.00")
	assert result.total == d("1265.00")


def test_epf_above_table_rounds_each_share_up_to_ringgit():
	result = calculate_epf(d("20000.01"), "A")
	assert result.employee == d("2201.00")
	assert result.employer == d("2401.00")


def test_foreign_worker_two_percent_category():
	assert determine_category(citizenship_status="Foreign Citizen", age=30) == "F"
	result = calculate_epf(d("1234.56"), "F")
	assert result.employee == d("25.00")
	assert result.employer == d("25.00")


def test_malaysian_age_categories():
	assert determine_category(citizenship_status="Malaysian", age=59) == "A"
	assert determine_category(citizenship_status="Malaysian", age=60) == "E"
	assert determine_category(citizenship_status="Permanent Resident", age=60) == "C"


def test_socso_first_category_and_skbbk():
	result = calculate_socso(d(5500), "First")
	assert result.employee == d("27.25")
	assert result.employer == d("95.35")
	assert result.extra_employee == d("40.85")


def test_socso_second_category():
	result = calculate_socso(d(5500), "Second")
	assert result.employee == d("0.00")
	assert result.employer == d("68.10")
	assert result.extra_employee == d("40.85")


def test_socso_and_eis_ceiling_band():
	socso = calculate_socso(d(20000), "First")
	eis = calculate_eis(d(20000))
	assert socso.employer == d("104.15")
	assert socso.employee == d("29.75")
	assert socso.extra_employee == d("44.65")
	assert eis.employer == d("11.90")
	assert eis.employee == d("11.90")


def test_zero_wages_are_zero():
	assert calculate_epf(0, "A").total == d("0.00")
	assert calculate_socso(0).total == d("0.00")
	assert calculate_eis(0).total == d("0.00")
