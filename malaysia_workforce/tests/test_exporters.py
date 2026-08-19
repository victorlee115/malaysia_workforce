import csv
import io
from decimal import Decimal

from malaysia_workforce.tests._assertions import raises

from malaysia_workforce.statutory.exporters.epf_csv import EPFCSVRecord, generate_epf_csv
from malaysia_workforce.statutory.exporters.lhdn_pcb import (
	DETAIL_LENGTH,
	HEADER_LENGTH,
	LHDNPCBRecord,
	generate_lhdn_pcb_file,
	render_detail,
	render_header,
)
from malaysia_workforce.statutory.exporters.perkeso_combined import (
	RECORD_LENGTH,
	PERKESOCombinedRecord,
	generate_perkeso_combined_file,
	render_record,
)


def test_lhdn_exhibit_4_lengths_and_totals():
	records = (
		LHDNPCBRecord(
			tin="IG 531367-080",
			name="Employee A",
			new_ic="900101011234",
			mtd_amount=Decimal("110.00"),
			cp38_amount=Decimal("25.50"),
			employee_number="EMP0000001",
		),
	)
	header = render_header(hq_number="E90891510", employer_number="E123456789", year=2026, month=1, records=records)
	detail = render_detail(records[0])
	assert len(header) == HEADER_LENGTH
	assert len(detail) == DETAIL_LENGTH
	assert header.startswith("H")
	assert detail.startswith("D00531367080")
	assert header[27:37] == "0000011000"
	assert header[42:52] == "0000002550"
	content = generate_lhdn_pcb_file(
		hq_number="E90891510", employer_number="E123456789", year=2026, month=1, records=records
	)
	assert content.endswith(b"\r\n")
	assert [len(line) for line in content.decode("ascii").splitlines()] == [57, 136]


def test_lhdn_header_counts_every_emitted_detail_line():
	"""A zero-MTD low earner still gets a D-line, so the header count must include it too."""
	records = (
		LHDNPCBRecord(
			tin="IG 531367-080", name="Employee A", new_ic="900101011234",
			mtd_amount=Decimal("110.00"), cp38_amount=Decimal("25.50"), employee_number="EMP0000001",
		),
		LHDNPCBRecord(
			tin="IG 531367-081", name="Employee B", new_ic="900101011235",
			mtd_amount=Decimal("0.00"), cp38_amount=Decimal("0.00"), employee_number="EMP0000002",
		),
	)
	header = render_header(hq_number="E90891510", employer_number="E123456789", year=2026, month=1, records=records)
	content = generate_lhdn_pcb_file(
		hq_number="E90891510", employer_number="E123456789", year=2026, month=1, records=records
	)
	detail_line_count = len(content.decode("ascii").splitlines()) - 1
	assert header[37:42] == "00002"
	assert header[52:57] == "00002"
	assert detail_line_count == 2


def test_lhdn_rejects_overlength_critical_fields():
	with raises(ValueError, match="TIN"):
		render_detail(
			LHDNPCBRecord(
				tin="123456789012",
				name="Employee",
				new_ic="900101011234",
				employee_number="EMP001",
			)
		)


def test_perkeso_278_character_record():
	item = PERKESOCombinedRecord(
		employer_code="A12345678901",
		company_registration_number="202001234567",
		employee_identity_number="900101011234",
		employee_name="Employee A",
		contribution_month="012026",
		wages=Decimal("5500.00"),
		socso_employer=Decimal("95.35"),
		socso_employee=Decimal("27.25"),
		eis_employer=Decimal("10.90"),
		eis_employee=Decimal("10.90"),
		skbbk_employee=Decimal("40.85"),
	)
	line = render_record(item)
	assert len(line) == RECORD_LENGTH
	assert line[194:200] == "012026"
	assert line[200:214] == "00000000550000"
	content = generate_perkeso_combined_file([item])
	assert content.endswith(b"\r\n")
	assert len(content.decode("ascii").splitlines()[0]) == 278


def test_perkeso_ssm_number_is_optional_and_ic_dashes_are_stripped():
	"""MyCoID/SSM Number is Mandatory: N per PERKESO's own text-file spec; a dashed NRIC
	must still fit the 12-character identification number field."""
	item = PERKESOCombinedRecord(
		employer_code="A12345678901",
		company_registration_number="",
		employee_identity_number="900101-01-1234",
		employee_name="Employee A",
		contribution_month="012026",
		wages=Decimal("5500.00"),
		socso_employer=Decimal("95.35"),
		socso_employee=Decimal("27.25"),
		eis_employer=Decimal("10.90"),
		eis_employee=Decimal("10.90"),
		skbbk_employee=Decimal("40.85"),
	)
	line = render_record(item)
	assert len(line) == RECORD_LENGTH
	assert line[32:44] == "900101011234"


def test_epf_csv_has_expected_columns_and_bom():
	content = generate_epf_csv(
		[
			EPFCSVRecord(
				member_number="12345678",
				identity_number="900101011234",
				name="Employee A",
				wages=Decimal("5500.00"),
				employer_share=Decimal("660.00"),
				employee_share=Decimal("605.00"),
			)
		]
	)
	assert content.startswith(b"\xef\xbb\xbf")
	rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
	assert rows[0] == ["Member No", "IC No", "Name", "Salary", "Employer Share", "Employee Share"]
	assert rows[1][-3:] == ["5500.00", "660.00", "605.00"]


def test_epf_csv_normalizes_dashed_identity_numbers_and_rejects_non_ascii_names():
	content = generate_epf_csv(
		[
			EPFCSVRecord(
				member_number=" 12345678 ",
				identity_number="900101-01-1234",
				name="Employee A",
				wages=Decimal("5500.00"),
				employer_share=Decimal("660.00"),
				employee_share=Decimal("605.00"),
			)
		]
	)
	rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))
	assert rows[1][:2] == ["12345678", "900101011234"]
	with raises(ValueError, match="non-ASCII"):
		generate_epf_csv(
			[
				EPFCSVRecord(
					member_number="12345678",
					identity_number="900101011234",
					name="Jöhn",
					wages=Decimal("1"),
					employer_share=Decimal("0"),
					employee_share=Decimal("0"),
				)
			]
		)


def test_exporters_reject_empty_files_and_negative_amounts():
	with raises(ValueError, match="at least one"):
		generate_epf_csv([])
	with raises(ValueError, match="negative"):
		generate_epf_csv(
			[
				EPFCSVRecord(
					member_number="123",
					identity_number="900101011234",
					name="Employee",
					wages=Decimal("-1"),
					employer_share=Decimal("0"),
					employee_share=Decimal("0"),
				)
			]
		)
	with raises(ValueError, match="non-ASCII"):
		render_detail(
			LHDNPCBRecord(
				tin="IG531367080",
				name="Jöhn",
				new_ic="900101011234",
			)
		)
	with raises(ValueError, match="non-ASCII"):
		render_record(
			PERKESOCombinedRecord(
				employer_code="A123",
				company_registration_number="202001234567",
				employee_identity_number="900101011234",
				employee_name="Jöhn",
				contribution_month="012026",
				wages=Decimal("1"),
				socso_employer=Decimal("0"),
				socso_employee=Decimal("0"),
				eis_employer=Decimal("0"),
				eis_employee=Decimal("0"),
				skbbk_employee=Decimal("0"),
			)
		)
