from malaysia_workforce.staffing.skills import skill_matches


def test_skill_matches_empty_requirement():
	assert skill_matches(None, [])
	assert skill_matches("", ["First Aid"])


def test_skill_matches_exact_standard_skill_link():
	assert skill_matches("First Aid", ["Customer Service", "First Aid"])
	assert not skill_matches("First Aid", ["first aid", "Customer Service"])
