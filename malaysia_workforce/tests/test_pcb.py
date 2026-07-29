from decimal import Decimal

from malaysia_workforce.statutory.calculators.pcb import calculate_pcb
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


def test_invalid_month_rejected():
	try:
		calculate_pcb(PCBInput(month=13, resident=True, category=1, current_normal_gross=d(1000)))
	except ValueError as exc:
		assert "month" in str(exc).lower()
	else:
		raise AssertionError("Expected ValueError")
