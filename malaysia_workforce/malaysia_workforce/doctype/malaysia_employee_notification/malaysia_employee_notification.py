import json

import frappe
from frappe.model.document import Document


class MalaysiaEmployeeNotification(Document):
	def validate(self):
		self.payload_snapshot = json.dumps({key: value for key, value in self.as_dict().items() if key not in {"payload_snapshot", "_comments"}}, default=str, sort_keys=True)
