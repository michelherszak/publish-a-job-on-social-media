"""No-network checks for the local Gmail setup helper."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend import gmail_test
from backend.stripe_test import read_env, save_env


class GmailSetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / ".env.local"
        save_env(self.path, {"STRIPE_SECRET_KEY": "sk_test_fixture", "MH_MAIL_MODE": "local"})
        self.patcher = patch.object(gmail_test, "ENV_FILE", self.path)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def test_prepare_keeps_mail_local_and_preserves_stripe_settings(self):
        gmail_test.prepare()
        values = read_env(self.path)
        self.assertEqual(values["STRIPE_SECRET_KEY"], "sk_test_fixture")
        self.assertEqual(values["MH_MAIL_MODE"], "local")
        self.assertEqual(values["MH_SMTP_USER"], gmail_test.ACCOUNT)
        self.assertNotIn("MH_SMTP_PASSWORD", values)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_connect_enables_smtp_only_after_successful_self_test(self):
        gmail_test.prepare()
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        with patch.object(gmail_test.getpass, "getpass", return_value="abcd efgh ijkl mnop"), \
             patch.object(gmail_test.smtplib, "SMTP", return_value=smtp):
            gmail_test.connect()
        self.assertEqual(smtp.send_message.call_count, 1)
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["To"], gmail_test.ACCOUNT)
        values = read_env(self.path)
        self.assertEqual(values["MH_SMTP_PASSWORD"], "abcdefghijklmnop")
        self.assertEqual(values["MH_MAIL_MODE"], "smtp")

    def test_failed_login_does_not_store_password_or_enable_smtp(self):
        gmail_test.prepare()
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.login.side_effect = gmail_test.smtplib.SMTPAuthenticationError(535, b"rejected")
        with patch.object(gmail_test.getpass, "getpass", return_value="abcdefghijklmnop"), \
             patch.object(gmail_test.smtplib, "SMTP", return_value=smtp):
            with self.assertRaises(RuntimeError):
                gmail_test.connect()
        values = read_env(self.path)
        self.assertEqual(values["MH_MAIL_MODE"], "local")
        self.assertNotIn("MH_SMTP_PASSWORD", values)


if __name__ == "__main__":
    unittest.main()
