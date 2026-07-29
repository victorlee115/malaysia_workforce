import json

import pytest

from malaysia_workforce.statutory.snapshot import parse_statutory_snapshot


def valid_snapshot():
	return {
		"current_wage_bases": {
			"gross": "1000.00",
			"epf": "1000.00",
			"socso": "1000.00",
			"eis": "1000.00",
			"pcb_regular": "1000.00",
			"pcb_additional": "0.00",
		},
		"current_results": [
			{
				"scheme": "EPF",
				"wage_base": "1000.00",
				"employee_amount": "110.00",
				"employer_amount": "130.00",
				"extra_employee_amount": "0.00",
			}
		],
	}


def test_snapshot_accepts_valid_mapping_and_json():
	payload = valid_snapshot()
	assert parse_statutory_snapshot(payload)["current_results"][0]["scheme"] == "EPF"
	assert parse_statutory_snapshot(json.dumps(payload))["current_wage_bases"]["gross"] == "1000.00"


def test_snapshot_is_fail_closed_for_missing_or_malformed_values():
	with pytest.raises(ValueError, match="empty"):
		parse_statutory_snapshot(None)
	payload = valid_snapshot()
	del payload["current_wage_bases"]["epf"]
	with pytest.raises(ValueError, match="missing wage bases"):
		parse_statutory_snapshot(payload)
	payload = valid_snapshot()
	payload["current_results"][0]["employee_amount"] = "NaN"
	with pytest.raises(ValueError, match="finite"):
		parse_statutory_snapshot(payload)
	payload = valid_snapshot()
	payload["current_results"] = {"EPF": {}}
	with pytest.raises(ValueError, match="must be a list"):
		parse_statutory_snapshot(payload)
