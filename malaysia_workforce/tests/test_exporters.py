import csv
import io
from decimal import Decimal

import pytest

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


def test_lhdn_rejects_overlength_critical_fields():
	with pytest.raises(ValueError, match="TIN"):
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
	assert rows[0] == ["Member No", "IC No", "Name", "Salary", "EM Share", "EMP Share"]
	assert rows[1][-3:] == ["5500.00", "660.00", "605.00"]


def test_exporters_reject_empty_files_negative_amounts_and_silent_ascii_loss():
	with pytest.raises(ValueError, match="at least one"):
		generate_epf_csv([])
	with pytest.raises(ValueError, match="negative"):
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
	with pytest.raises(ValueError, match="non-ASCII"):
		render_detail(
			LHDNPCBRecord(
				tin="IG531367080",
				name="Jöhn",
				new_ic="900101011234",
			)
		)
	with pytest.raises(ValueError, match="non-ASCII"):
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
