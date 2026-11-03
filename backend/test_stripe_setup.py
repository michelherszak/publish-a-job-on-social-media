"""Setup safeguards, using no real Stripe account."""
import os
import io
import ssl
from urllib.error import HTTPError
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from backend import billing, stripe_test


class StripeSetupTests(unittest.TestCase):
    def test_listener_saves_secret_before_readiness_and_redacts_output(self):
        with tempfile.TemporaryDirectory() as directory:
            env=Path(directory)/'.env.local';ready=Path(directory)/'ready'
            stripe_test.save_env(env,{'STRIPE_SECRET_KEY':'sk_test_1234567890','OTHER':'preserved'})
            process=Mock(stdout=io.StringIO('Ready! whsec_newfixture\n'),poll=Mock(return_value=0))
            output=io.StringIO()
            save=stripe_test.save_env
            def checked_save(path,values):
                self.assertFalse(ready.exists())
                save(path,values)
            with patch.object(stripe_test,'ENV_FILE',env),patch.object(stripe_test.subprocess,'Popen',return_value=process) as popen,patch.object(stripe_test,'save_env',side_effect=checked_save),patch('sys.stdout',output):
                stripe_test.listen(ready)
            self.assertEqual(stripe_test.read_env(env)['STRIPE_WEBHOOK_SECRET'],'whsec_newfixture')
            self.assertEqual(stripe_test.read_env(env)['OTHER'],'preserved')
            self.assertEqual(ready.read_text(),'ready\n');self.assertEqual(ready.stat().st_mode & 0o777,0o600)
            self.assertNotIn('whsec_newfixture',output.getvalue());self.assertIn('[privat gespeichert]',output.getvalue())
            self.assertIn('invoice.paid',popen.call_args.args[0][3])

    def test_stripe_requests_verify_tls_certificates(self):
        with patch.object(billing, 'urlopen', return_value=io.BytesIO(b'{"ok":true}')) as call:
            self.assertTrue(billing.stripe_call('GET','balance')['ok'])
            context=call.call_args.kwargs['context']
            self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)

    def test_missing_stripe_customer_is_already_gone(self):
        missing = HTTPError("https://api.stripe.com/v1/customers/cus_missing", 404, "missing", None, io.BytesIO(b"{}"))
        with patch.object(billing, "urlopen", side_effect=missing):
            self.assertIsNone(billing.stripe_call("DELETE", "customers/cus_missing", missing_ok=True))

    def test_only_test_keys(self):
        for key in ("sk_live_1234567890", "", "rk_test_1234567890"):
            with self.assertRaises(ValueError):
                stripe_test.test_key(key)

    def test_private_env_roundtrip_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env.local"
            values = {"STRIPE_SECRET_KEY": "sk_test_$(echo unsafe)`echo unsafe`", "OTHER": "value with spaces"}
            stripe_test.save_env(path, values)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(stripe_test.read_env(path), values)

    def test_existing_price_is_reused(self):
        item = billing.CATALOG["starter"]
        price = {"id": "price_existing", "active": True, "livemode": False,
                 "currency": "eur", "unit_amount": billing.CATALOG["starter"]["cents"], "tax_behavior": "exclusive",
                 "recurring": {"interval": "month", "interval_count": 1}}
        with patch.object(billing, "stripe_call", return_value={"data": [price]}) as call:
            self.assertEqual(stripe_test.price_for("starter", item), "price_existing")
            self.assertEqual(call.call_count, 1)
            price["unit_amount"] = 1
            with self.assertRaises(ValueError):
                stripe_test.price_for("starter", item)

    def test_creates_monthly_and_oneoff_prices(self):
        for sku in ("starter", "starter_yearly", "tokens_250"):
            with patch.object(billing, "stripe_call", side_effect=[{"data": []}, {"id": "prod_test"}, {"id": "price_test"}]) as call:
                self.assertEqual(stripe_test.price_for(sku, billing.CATALOG[sku]), "price_test")
                data = call.call_args.args[2]
                self.assertEqual(data["tax_behavior"], "exclusive")
                self.assertEqual(data["unit_amount"], billing.CATALOG[sku]["cents"])
                self.assertEqual("recurring" in data, sku != "tokens_250")
                if sku == "starter_yearly": self.assertEqual(data["recurring"]["interval"], "year")

    def test_start_rejects_live_key_before_server_start(self):
        with patch.object(stripe_test, "read_env", return_value={"STRIPE_SECRET_KEY": "sk_live_1234567890"}):
            with self.assertRaises(ValueError):
                stripe_test.start()

    def test_incomplete_setup_does_not_start_server(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(stripe_test, "read_env", return_value={"STRIPE_SECRET_KEY": "sk_test_1234567890"}):
            with self.assertRaises(ValueError):
                stripe_test.start()

    def test_verify_checks_all_prices_and_tax_without_mutation(self):
        values = {"STRIPE_SECRET_KEY": "sk_test_1234567890", "STRIPE_WEBHOOK_SECRET": "whsec_fixture", "MH_PUBLIC_URL": "http://127.0.0.1:5181"}
        values.update({"STRIPE_PRICE_" + sku.upper(): "price_" + sku for sku in billing.CATALOG})

        def remote(kind, price_id):
            sku = price_id.removeprefix("price_")
            item = billing.CATALOG[sku]
            return {
                "id": price_id, "active": True, "livemode": False, "currency": "eur",
                "unit_amount": item["cents"], "tax_behavior": "exclusive",
                "recurring": {"interval": item["interval"], "interval_count": 1} if item["kind"] == "subscription" else None,
            }

        with patch.object(stripe_test, "read_env", return_value=values), patch.object(billing, "remote", side_effect=remote) as prices:
            with patch.object(billing, "stripe_call", return_value={"status": "pending", "defaults": {}}):
                self.assertFalse(stripe_test.verify())
            with patch.object(billing, "stripe_call", return_value={"status": "active", "defaults": {"tax_code": "txcd_test"}}):
                self.assertTrue(stripe_test.verify())
        self.assertEqual(prices.call_count, len(billing.CATALOG) * 2)
        self.assertIn("invoice.paid", stripe_test.WEBHOOK_EVENTS)
        self.assertIn("charge.refunded", stripe_test.WEBHOOK_EVENTS)
