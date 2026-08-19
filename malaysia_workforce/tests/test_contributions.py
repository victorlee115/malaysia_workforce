from datetime import date
from decimal import Decimal

import pytest

from malaysia_workforce.statutory.calculators.eis import calculate_eis, is_eis_age_eligible
from malaysia_workforce.statutory.calculators.epf import calculate_epf, determine_category
from malaysia_workforce.statutory.calculators.socso import calculate_socso, determine_socso_category


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


def test_socso_category_age_boundary():
	assert determine_socso_category(17) == "First"
	assert determine_socso_category(59) == "First"
	assert determine_socso_category(60) == "Second"
	assert determine_socso_category(61) == "Second"


def test_eis_age_eligibility_boundary():
	assert is_eis_age_eligible(17) is False
	assert is_eis_age_eligible(18) is True
	assert is_eis_age_eligible(59) is True
	assert is_eis_age_eligible(60) is False


def test_socso_first_category_and_skbbk():
	result = calculate_socso(d(5500), "First", contribution_date=date(2026, 6, 30))
	assert result.employee == d("27.25")
	assert result.employer == d("95.35")
	assert result.extra_employee == d("40.85")


def test_socso_second_category():
	result = calculate_socso(d(5500), "Second", contribution_date=date(2026, 6, 30))
	assert result.employee == d("0.00")
	assert result.employer == d("68.10")
	assert result.extra_employee == d("40.85")


def test_socso_and_eis_ceiling_band():
	socso = calculate_socso(d(20000), "First", contribution_date=date(2026, 6, 30))
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


@pytest.mark.parametrize("participation", [None, "", "Participating"])
def test_lindung_continues_by_default_after_8_july_2026(participation):
	"""Release is an opt-out, so an employee who recorded nothing still pays."""
	result = calculate_socso(
		d(5500),
		"First",
		contribution_date=date(2026, 7, 31),
		lindung_participation=participation,
	)
	assert result.extra_employee == d("40.85")


def test_lindung_starts_on_1_june_2026():
	before = calculate_socso(d(5500), "First", contribution_date=date(2026, 5, 31))
	on_start = calculate_socso(d(5500), "First", contribution_date=date(2026, 6, 1))
	assert before.extra_employee == d("0.00")
	assert on_start.extra_employee == d("40.85")


def test_release_notice_stops_lindung_from_its_effective_date():
	kwargs = {"lindung_participation": "Not Participating", "lindung_effective_from": date(2026, 8, 1)}
	july = calculate_socso(d(5500), "First", contribution_date=date(2026, 7, 31), **kwargs)
	august = calculate_socso(d(5500), "First", contribution_date=date(2026, 8, 31), **kwargs)
	assert july.extra_employee == d("40.85")
	assert august.extra_employee == d("0.00")


def test_release_notice_without_an_effective_date_keeps_deducting():
	result = calculate_socso(
		d(5500),
		"First",
		contribution_date=date(2026, 7, 31),
		lindung_participation="Not Participating",
	)
	assert result.extra_employee == d("40.85")


def test_release_cannot_take_effect_before_the_mechanism_existed():
	"""June 2026 contributions are not refundable, so the floor clamps them."""
	kwargs = {"lindung_participation": "Not Participating", "lindung_effective_from": date(2026, 6, 1)}
	june = calculate_socso(d(5500), "First", contribution_date=date(2026, 6, 30), **kwargs)
	july = calculate_socso(d(5500), "First", contribution_date=date(2026, 7, 31), **kwargs)
	assert june.extra_employee == d("40.85")
	assert july.extra_employee == d("0.00")


@pytest.mark.parametrize(
	"participation", [None, "", "Participating", "Not Participating", "Not Set", "whatever"]
)
def test_socso_never_raises_for_any_lindung_state(participation):
	result = calculate_socso(
		d(5500),
		"First",
		contribution_date=date(2026, 7, 31),
		lindung_participation=participation,
	)
	assert result.employee == d("27.25")
