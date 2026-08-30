import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from bot_state import BotState
from main import YHTCatcher
from settings import update_env, validate_settings
from terminal_ui import (
    choose_classes,
    choose_station,
    choose_times,
    configuration_issues,
    configure_whatsapp,
)
from whatsapp_notifier import WhatsAppNotifier
from tcdd_checker import TCDDTicketChecker


class BotStateTests(unittest.TestCase):
    def test_notification_cooldown_is_keyed(self):
        with tempfile.TemporaryDirectory() as directory:
            state = BotState(os.path.join(directory, "state.json"))
            state.mark_notified("train-a", now=100)
            self.assertFalse(state.can_notify("train-a", 60, now=150))
            self.assertTrue(state.can_notify("train-b", 60, now=150))
            self.assertTrue(state.can_notify("train-a", 60, now=160))

    def test_error_recovery_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = BotState(os.path.join(directory, "state.json"))
            self.assertEqual(state.record_error(), 1)
            state.mark_error_alerted()
            self.assertTrue(state.record_success())
            self.assertFalse(state.error_alerted)


class SettingsTests(unittest.TestCase):
    def test_update_env_preserves_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, ".env")
            with open(path, "w", encoding="utf-8") as env_file:
                env_file.write("TWILIO_AUTH_TOKEN=secret\nSAAT=10:00\n")
            update_env({"SAAT": "15:10", "MINIMUM_KOLTUK": "2"}, path)
            with open(path, encoding="utf-8") as env_file:
                content = env_file.read()
            self.assertIn("TWILIO_AUTH_TOKEN=secret", content)
            self.assertIn("SAAT=15:10", content)
            self.assertIn("MINIMUM_KOLTUK=2", content)

    def test_validation_rejects_short_interval(self):
        with self.assertRaises(ValueError):
            validate_settings("A", "B", "2026-08-30", ["15:10"], 10)

    def test_numbered_station_selection(self):
        stations = ["ANKARA GAR , ANKARA", "SELÇUKLU YHT (KONYA) , KONYA"]
        with patch("builtins.input", side_effect=["konya", "1"]):
            selected = choose_station("Varış", "ANKARA GAR", stations)
        self.assertEqual(selected, stations[1])

    def test_multiple_class_selection(self):
        with patch("builtins.input", return_value="1 3"):
            self.assertEqual(choose_classes("EKONOMİ"), ["EKONOMİ", "LOCA"])

    def test_all_class_selection(self):
        with patch("builtins.input", return_value="hepsi"):
            self.assertEqual(choose_classes("EKONOMİ"), ["EKONOMİ", "BUSINESS", "LOCA"])

    def test_multiple_time_selection(self):
        with patch("builtins.input", return_value="1 3"):
            selected = choose_times(["06:00", "12:00", "18:00"], ["12:00"])
        self.assertEqual(selected, ["06:00", "18:00"])

    def test_all_time_selection(self):
        times = ["06:00", "12:00", "18:00"]
        with patch("builtins.input", return_value="hepsi"):
            self.assertEqual(choose_times(times, ["12:00"]), times)

    def test_placeholder_credentials_are_reported(self):
        values = {
            "TWILIO_ACCOUNT_SID": "your_account_sid",
            "TWILIO_AUTH_TOKEN": "your_auth_token",
            "TWILIO_WHATSAPP_NUMBER": "whatsapp:+14155238886",
            "KULLANICI_WHATSAPP_NUMARASI": "whatsapp:+90xxxxxxxxxx",
        }
        with patch.dict(os.environ, values, clear=False):
            issues = configuration_issues()
        self.assertTrue(any("ACCOUNT_SID" in issue for issue in issues))
        self.assertTrue(any("AUTH_TOKEN" in issue for issue in issues))

    def test_whatsapp_setup_normalizes_turkish_phone(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch("builtins.input", side_effect=["AC" + "1" * 32, "", "05551234567"]), \
             patch("terminal_ui.getpass.getpass", return_value="a" * 32), \
             patch("terminal_ui.update_env") as update:
            configure_whatsapp()
        saved = update.call_args.args[0]
        self.assertEqual(saved["KULLANICI_WHATSAPP_NUMARASI"], "whatsapp:+905551234567")


class CatcherTests(unittest.TestCase):
    def make_catcher(self, directory, **kwargs):
        with patch("main.TCDDTicketChecker"), patch("main.WhatsAppNotifier"):
            return YHTCatcher(
                "A", "B", "2026-08-30", ["15:10"], kontrol_sikligi=180,
                state_path=os.path.join(directory, "state.json"), sleep_fn=lambda _: None,
                **kwargs,
            )

    def test_found_seat_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            catcher = self.make_catcher(directory)
            catcher.checker.check_tickets.side_effect = [
                {"success": True, "found_seats": True, "seats": 2},
                {"success": True, "found_seats": False},
            ]
            result = catcher.run_once("15:10")
            self.assertTrue(result["confirmation_failed"])
            catcher.notifier.send_ticket_found_notification.assert_not_called()

    def test_confirmed_seat_notifies_and_starts_only_its_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            catcher = self.make_catcher(directory)
            catcher.notifier.send_ticket_found_notification.return_value = True
            catcher.checker.check_tickets.side_effect = [
                {"success": True, "found_seats": True, "seats": 2},
                {"success": True, "found_seats": True, "seats": 2},
            ]
            catcher.run_once("15:10")
            catcher.notifier.send_ticket_found_notification.assert_called_once()
            key = catcher._notification_key("15:10")
            self.assertFalse(catcher.state.can_notify(key, 3600))

    def test_error_alert_is_sent_only_at_threshold(self):
        with tempfile.TemporaryDirectory() as directory:
            catcher = self.make_catcher(directory, confirmation_checks=1, error_threshold=3)
            catcher.notifier.send_error_notification.return_value = True
            catcher.checker.check_tickets.return_value = {"success": False, "error": "timeout"}
            catcher.run_once("15:10")
            catcher.run_once("15:10")
            catcher.notifier.send_error_notification.assert_not_called()
            catcher.run_once("15:10")
            catcher.notifier.send_error_notification.assert_called_once()


class NotifierTests(unittest.TestCase):
    def test_failed_delivery_returns_false(self):
        notifier = WhatsAppNotifier()
        notifier.client = Mock()
        created = Mock(sid="SM1")
        notifier.client.messages.create.return_value = created
        notifier.client.messages.return_value.fetch.return_value = Mock(
            status="failed", error_code=63015
        )
        self.assertFalse(notifier.send_notification("test"))

    def test_notifier_reads_updated_environment(self):
        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "ACnew",
            "TWILIO_AUTH_TOKEN": "new-token",
            "TWILIO_WHATSAPP_NUMBER": "whatsapp:+1",
            "KULLANICI_WHATSAPP_NUMARASI": "whatsapp:+90",
        }):
            notifier = WhatsAppNotifier()
        self.assertEqual(notifier.account_sid, "ACnew")
        self.assertEqual(notifier.auth_token, "new-token")


class ResultParsingTests(unittest.TestCase):
    def test_full_economy_does_not_count_wheelchair_seats(self):
        checker = TCDDTicketChecker(debug_file=os.devnull)
        checker.driver = Mock()
        with open("debug_page.html", encoding="utf-8") as page_file:
            checker.driver.page_source = page_file.read()
        checker.driver.execute_script.return_value = "NO_EXPANDED"
        result = checker.analyze_results("15:10", sinif="EKONOMİ", minimum_koltuk=1)
        self.assertTrue(result["success"])
        self.assertFalse(result["found_seats"])

    def test_all_classes_exclude_wheelchair_inventory(self):
        checker = TCDDTicketChecker(debug_file=os.devnull)
        checker.driver = Mock()
        with open("debug_page.html", encoding="utf-8") as page_file:
            checker.driver.page_source = page_file.read()
        checker.driver.execute_script.return_value = "NO_EXPANDED"
        result = checker.analyze_results(
            "15:10", sinif=["EKONOMİ", "BUSINESS", "LOCA"], minimum_koltuk=1
        )
        self.assertFalse(result["found_seats"])
        self.assertNotIn("TEKERLEKLİ SANDALYE", result.get("classes", {}))

    def test_available_class_payload_is_formatted(self):
        checker = TCDDTicketChecker(debug_file=os.devnull)
        checker.driver = Mock()
        checker.driver.page_source = "<time datetime=\"15:10\"></time>"
        checker.driver.execute_script.return_value = '{"BUSINESS":3,"EKONOMİ":0,"LOCA":2}'
        result = checker.analyze_results(
            "15:10", sinif=["EKONOMİ", "BUSINESS", "LOCA"], minimum_koltuk=1
        )
        self.assertTrue(result["found_seats"])
        self.assertEqual(result["classes"], {"BUSINESS": 3, "LOCA": 2})
        self.assertNotIn("9", result["message"])


if __name__ == "__main__":
    unittest.main()
