# Copyright (c) 2026, Frappe and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import telemetry as frappe_telemetry

from wiki import telemetry
from wiki.tests import WikiTestCase as IntegrationTestCase


class TestTelemetryIsOff(IntegrationTestCase):
	def test_capture_sends_nothing(self):
		with patch.object(frappe_telemetry, "capture") as framework_capture:
			telemetry.capture("space_created", visibility="public")

		framework_capture.assert_not_called()

	def test_the_reader_template_loads_no_pulse_client(self):
		template = open(frappe.get_app_path("wiki", "templates/wiki/document.html")).read()

		self.assertNotIn("PulseClient", template)
		self.assertNotIn("capturePageAction", template)
