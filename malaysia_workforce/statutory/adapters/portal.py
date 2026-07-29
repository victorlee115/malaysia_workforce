from __future__ import annotations

from malaysia_workforce.statutory.adapters.base import SubmissionAdapter, SubmissionResponse


class PortalFileAdapter(SubmissionAdapter):
	mode = "File Upload"

	def submit(self, submission) -> SubmissionResponse:
		return SubmissionResponse(
			status="Ready for Portal",
			message="File generated and validated. An authorised user must upload it through the official portal.",
		)
