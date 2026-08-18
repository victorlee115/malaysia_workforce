from __future__ import annotations

STANDARD_PAYROLL_PROFILE = "Standard Payroll"
SOCSO_EIS_LINDUNG_PROFILE = "SOCSO + EIS — LINDUNG Optional"
SOCSO_EIS_PROFILE_RULE_VERSION = "PROFILE-SOCSO-EIS-LINDUNG"
STATUTORY_PROFILE_FIELD = "custom_malaysia_statutory_profile"
STATUTORY_PROFILE_OPTIONS = f"{STANDARD_PAYROLL_PROFILE}\n{SOCSO_EIS_LINDUNG_PROFILE}"

SCHEMES_BY_PROFILE = {
	STANDARD_PAYROLL_PROFILE: frozenset({"EPF", "SOCSO", "EIS", "HRD Corp", "PCB", "CP38", "Zakat"}),
	SOCSO_EIS_LINDUNG_PROFILE: frozenset({"SOCSO", "EIS"}),
}


def normalize_statutory_profile(value: str | None) -> str:
	"""Return the profile used by payroll; blank values preserve legacy behaviour."""
	return value or STANDARD_PAYROLL_PROFILE


def is_socso_eis_lindung_profile(value: str | None) -> bool:
	return normalize_statutory_profile(value) == SOCSO_EIS_LINDUNG_PROFILE


def applicable_schemes(value) -> frozenset[str]:
	"""Return the schemes a normalised profile includes.

	Blank values become Standard Payroll. An unknown non-blank profile raises
	so callers that inspect the set cannot treat garbage as Standard.
	"""
	profile = normalize_statutory_profile(value)
	try:
		return SCHEMES_BY_PROFILE[profile]
	except KeyError:
		raise ValueError(f"Unsupported statutory profile: {profile}") from None


def scheme_applies(value, scheme: str) -> bool:
	"""Return whether *scheme* belongs to the normalised profile.

	Unknown non-blank profiles return False rather than raising, so a
	company-wide scan cannot be aborted by one bad Employee row.
	"""
	profile = normalize_statutory_profile(value)
	schemes = SCHEMES_BY_PROFILE.get(profile)
	if schemes is None:
		return False
	return scheme in schemes
