from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SubmissionResponse:
	status: str
	external_reference: str = ""
	message: str = ""
	raw: dict[str, Any] | None = None


class SubmissionAdapter(ABC):
	mode = "File Upload"

	@abstractmethod
	def validate(self, submission) -> list[str]:
		raise NotImplementedError

	@abstractmethod
	def generate(self, submission) -> tuple[str, bytes]:
		raise NotImplementedError

	def submit(self, submission) -> SubmissionResponse:
		raise NotImplementedError(
			"No approved public employer-payroll API is configured. Generate the official file and use the authority portal."
		)

	def check_status(self, submission) -> SubmissionResponse:
		raise NotImplementedError("Status polling is available only for an approved authority API connector.")
