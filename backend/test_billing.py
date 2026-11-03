"""Offline payment integration tests; no network or real payments."""
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from backend.test_support import BrowserClient as TestClient, session_headers
from fastapi import HTTPException
from backend import main, billing, auth


class BillingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.patches=[patch.object(main,"DB",root/"test.db"),patch.object(main,"DEMO_DB",root/"demo.db"),patch.object(main,"CREDENTIALS",root/"credentials.txt"),patch.object(auth,"OUTBOX",root/"outbox")]
        env={"STRIPE_SECRET_KEY":"sk_test_fixture","STRIPE_WEBHOOK_SECRET":"whsec_fixture","MH_PUBLIC_URL":"http://127.0.0.1:5181"}
        env.update({"STRIPE_PRICE_"+sku.upper():"price_"+sku for sku in billing.CATALOG})
        self.patches.append(patch.dict(os.environ,env))
        for item in self.patches:item.start()
        main.init_db();self.client=TestClient(main.app)
        passwords=dict(line.split() for line in main.CREDENTIALS.read_text().splitlines()[1:])
        self.a=self.login("admin@mueller.local",passwords);self.b=self.login("admin@autohaus.local",passwords);self.admin=self.login("admin@flh.local",passwords)
        self.org=self.client.get("/organizations",headers=self.a).json()[0]["id"]
        self.now=int(time.time());self.calls=[];self.sessions={};self.invoices={}
        self.sub={"id":"sub_one","customer":"cus_one","status":"active","metadata":{"order_id":f"{self.org}_request_123456789"},"items":{"data":[{"price":{"id":"price_starter"},"quantity":1}]},"cancel_at_period_end":False}
        self.ai_mock=patch.object(main.ai,"generate",return_value=(main.make_content({"role":"Test","location":"Berlin"},"Firma"),{"model":"fixture","response_id":"resp_fixture","input_tokens":1000,"output_tokens":2000,"cached_tokens":0}));self.ai_provider=self.ai_mock.start()
        self.network=patch.object(billing,"stripe_call",side_effect=self.provider);self.network.start()
    def tearDown(self):
        self.ai_mock.stop();self.network.stop();self.client.close()
        for item in reversed(self.patches):item.stop()
        self.tmp.cleanup()
    def login(self,email,passwords):
        response=self.client.post("/auth/login",json={"email":email,"password":passwords[email]})
        self.assertEqual(response.status_code,200,response.text)
        headers=session_headers(self.client)
        self.client.cookies.clear()
        return headers
    def provider(self,method,path,data=None,key=None):
        self.calls.append((method,path,data,key))
        if path.startswith("prices/"):
            sku=path.split("price_",1)[1];item=billing.CATALOG[sku]
            return {"id":"price_"+sku,"active":True,"currency":"eur","unit_amount":item["cents"],"tax_behavior":"exclusive","recurring":{"interval":item["interval"],"interval_count":1} if item["kind"]=="subscription" else None}
        if path=="customers":return {"id":"cus_one"}
        if path=="checkout/sessions":
            ident="cs_"+str(len(self.sessions)+1)
            sku=data["metadata"]["sku"]
            result={"id":ident,"url":"https://checkout.stripe.com/test/"+ident,"customer":data["customer"],"metadata":data["metadata"],"mode":data["mode"],"status":"open","payment_status":"unpaid","amount_subtotal":billing.CATALOG[sku]["cents"],"currency":"eur","customer_details":{"address":{"country":"DE"}},"subscription":"sub_one" if data["mode"]=="subscription" else None}
            if data["mode"]=="payment":
                invoice_id="in_payment_"+ident
                result["invoice"]=invoice_id
                self.invoices[invoice_id]={"id":invoice_id,"customer":data["customer"],"status":"draft","currency":"eur","subtotal":billing.CATALOG[sku]["cents"],"customer_address":{"country":"DE"},"number":"MH-"+ident,"invoice_pdf":"https://pay.stripe.com/invoice/test/"+invoice_id+"/pdf"}
            self.sessions[ident]=result;return copy.deepcopy(result)
        if path.startswith("checkout/sessions/"):
            ident=path.split("/")[2]
            if path.endswith("/expire"):self.sessions[ident]["status"]="expired"
            return copy.deepcopy(self.sessions[ident])
        if path.startswith("subscriptions/"):return copy.deepcopy(self.sub)
        if path.startswith("invoices/"):return copy.deepcopy(self.invoices[path.split("/")[1]])
        if path=="billing_portal/configurations":return {"id":"bpc_one"}
        if path=="billing_portal/sessions":return {"url":"https://billing.stripe.com/test/session"}
        raise AssertionError(f"Unexpected Stripe call {method} {path}")
    def checkout(self,sku="starter",key="request_123456789",country="DE",headers=None):
        return self.client.post("/billing/checkout",headers=headers or self.a,json={"sku":sku,"country":country,"business":True,"pdf_consent":True,"request_id":key})
    def webhook(self,typ,obj,ident="evt_one",timestamp=None):
        payload=json.dumps({"id":ident,"type":typ,"livemode":False,"data":{"object":obj}}).encode()
        stamp=str(timestamp or int(time.time()));sig=hmac.new(b"whsec_fixture",stamp.encode()+b"."+payload,hashlib.sha256).hexdigest()
        return self.client.post("/billing/webhook",content=payload,headers={"Stripe-Signature":f"t={stamp},v1={sig}","Content-Type":"application/json"})
    def pay_checkout(self,ident="cs_1",event="evt_checkout"):
        self.sessions[ident].update(status="complete",payment_status="paid")
        if self.sessions[ident].get("invoice"):
            self.invoices[self.sessions[ident]["invoice"]]["status"]="paid"
        return self.webhook("checkout.session.completed",self.sessions[ident],event)
    def invoice(self,ident="in_one",start=None,end=None):
        data={"id":ident,"customer":"cus_one","status":"paid","billing_reason":"subscription_cycle","currency":"eur","subtotal":billing.CATALOG["starter"]["cents"],"customer_address":{"country":"DE"},"number":"MH-"+ident,"invoice_pdf":"https://pay.stripe.com/invoice/test/"+ident+"/pdf","parent":{"subscription_details":{"subscription":"sub_one"}},"lines":{"data":[{"quantity":1,"pricing":{"price_details":{"price":"price_starter"}},"period":{"start":start or self.now-60,"end":end or self.now+3600}}]}}
        self.invoices[ident]=data;return data
    def activate(self):
        self.assertEqual(self.checkout().status_code,200)
        self.assertEqual(self.pay_checkout().status_code,200)
        self.assertEqual(self.webhook("invoice.paid",self.invoice(),"evt_invoice").status_code,200)
    def status(self):return self.client.get("/billing/status",headers=self.a).json()

    def test_onboarding_checkout_returns_to_onboarding_without_unlocking_account(self):
        body={"sku":"team","country":"DE","business":True,"pdf_consent":True,"request_id":"onboarding_return_123","onboarding":True}
        self.assertEqual(self.client.post('/billing/checkout',headers=self.a,json=body).status_code,200)
        payload=next(call[2] for call in self.calls if call[1]=='checkout/sessions')
        self.assertEqual(payload['success_url'],'http://127.0.0.1:5181/onboarding?billing=success')
        self.assertEqual(payload['cancel_url'],'http://127.0.0.1:5181/onboarding?billing=cancelled')
        self.assertFalse(self.status()['active']);self.assertEqual(self.status()['included'],0)

    def test_checkout_progress_is_company_scoped_and_does_not_confirm_payment(self):
        self.checkout('team')
        state=self.status()
        self.assertEqual(state['checkout']['sku'],'team')
        self.assertEqual(state['checkout']['url'],'https://checkout.stripe.com/test/cs_1')
        self.assertFalse(state['active'])
        self.assertNotIn('cs_1',self.client.get('/billing/status',headers=self.b).text)
        # Provider payment alone is insufficient: the signed webhook must arrive.
        self.sessions['cs_1'].update(status='complete',payment_status='paid')
        self.assertFalse(self.status()['active'])
        self.assertEqual(self.webhook('checkout.session.completed',self.sessions['cs_1']).status_code,200)
        self.assertIsNone(self.status()['checkout']);self.assertFalse(self.status()['active'])

    def test_expired_or_invalid_checkout_urls_cannot_be_resumed(self):
        self.checkout()
        with main.db() as conn:conn.execute('UPDATE billing_orders SET expires_at=?',(self.now-1,))
        state=self.status()['checkout']
        self.assertEqual(state['status'],'expired');self.assertIsNone(state['url'])
        with main.db() as conn:conn.execute("UPDATE billing_orders SET expires_at=?,url='https://other.example/private'",(self.now+600,))
        self.assertIsNone(self.status()['checkout']['url'])

    def test_checkout_price_is_server_owned_and_tax_and_card_enabled(self):
        response=self.checkout();self.assertEqual(response.status_code,200,response.text)
        payload=[c[2] for c in self.calls if c[1]=="checkout/sessions"][0]
        self.assertEqual(payload["line_items"],[{"price":"price_starter","quantity":1}])
        self.assertEqual(payload["ui_mode"],"hosted_page")
        self.assertEqual(payload["payment_method_types"],["card"])
        self.assertTrue(payload["automatic_tax"]["enabled"]);self.assertTrue(payload["tax_id_collection"]["enabled"])
        self.assertEqual(payload["billing_address_collection"],"required")
        self.assertFalse(payload["phone_number_collection"]["enabled"])
        self.assertFalse(payload["allow_promotion_codes"])
        self.assertEqual(payload["payment_method_collection"],"always")
        self.assertEqual(payload["submit_type"],"auto")
        self.assertEqual(payload["integration_identifier"],"hosted_web_0001")
        self.assertEqual(payload["origin_context"],"web")
        self.assertEqual(payload["metadata"]["order_id"],f"{self.org}_request_123456789")
        self.assertEqual(self.status()["included"],0)

    def test_one_time_checkout_omits_subscription_payment_collection(self):
        self.activate()
        self.assertEqual(self.checkout("tokens_250","one_time_checkout_123").status_code,200)
        payload=[c[2] for c in self.calls if c[1]=="checkout/sessions"][-1]
        self.assertEqual(payload["mode"],"payment")
        self.assertNotIn("payment_method_collection",payload)
        self.assertTrue(payload["invoice_creation"]["enabled"])

    def test_checkout_and_portal_follow_browser_language(self):
        headers = {**self.a, "Accept-Language": "en-GB,de;q=0.8"}
        self.assertEqual(self.checkout(headers=headers).status_code, 200)
        payload = next(c[2] for c in self.calls if c[1] == "checkout/sessions")
        self.assertEqual(payload["locale"], "en")
        self.assertIn("Prices are net", payload["custom_text"]["submit"]["message"])
        self.assertEqual(self.status()["included"], 0)
        response = self.client.post("/billing/portal", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        portal = next(c[2] for c in self.calls if c[1] == "billing_portal/sessions")
        self.assertEqual(portal["locale"], "en")
        config = next(c[2] for c in self.calls if c[1] == "billing_portal/configurations")
        self.assertEqual(config["business_profile"]["headline"], "MH · Billing")

    def test_checkout_keeps_german_for_german_browser_preferences(self):
        headers = {**self.a, "Accept-Language": "de-AT,en;q=0.8"}
        self.assertEqual(self.checkout(headers=headers).status_code, 200)
        payload = next(c[2] for c in self.calls if c[1] == "checkout/sessions")
        self.assertEqual(payload["locale"], "de")
        self.assertIn("Preise netto", payload["custom_text"]["submit"]["message"])

    def test_checkout_requires_pdf_invoice_consent(self):
        response=self.client.post("/billing/checkout",headers=self.a,json={"sku":"starter","country":"DE","business":True,"pdf_consent":False,"request_id":"consent_request_123"})
        self.assertEqual(response.status_code,422)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.checkout().status_code,200)
        with main.db() as conn:
            self.assertEqual(conn.execute("SELECT pdf_consent FROM billing_orders WHERE organization_id=?",(self.org,)).fetchone()[0],1)

    def test_eu_only_and_unknown_sku_rejected(self):
        for country in ("US","GB","CH","NO",""):
            self.assertEqual(self.checkout(country=country).status_code,422)
        self.assertEqual(self.checkout(sku="arbitrary_price").status_code,422)
        self.assertEqual(len(billing.EU),27);self.assertEqual(self.calls,[])

    def test_checkout_idempotent_and_second_open_checkout_prevented(self):
        first=self.checkout();second=self.checkout();self.assertEqual(first.json(),second.json())
        self.assertEqual(len(self.sessions),1)
        self.assertEqual(self.checkout(sku="team",key="different_request_123").status_code,409)
        self.assertEqual(self.checkout(sku="team").status_code,409)

    def test_signature_rejects_tampering_and_old_replay(self):
        self.assertEqual(self.client.post("/billing/webhook",content=b'{}',headers={"Stripe-Signature":"t=1,v1=bad"}).status_code,400)
        self.assertEqual(self.webhook("invoice.paid",{"id":"x"},timestamp=self.now-400).status_code,400)

    def test_checkout_does_not_grant_monthly_tokens_and_invoice_is_idempotent(self):
        self.checkout();self.pay_checkout();self.assertEqual(self.status()["included"],0);self.assertFalse(self.status()["active"])
        invoice=self.invoice()
        for event in ("evt_invoice","evt_invoice","evt_new_delivery"):
            self.assertEqual(self.webhook("invoice.paid",invoice,event).status_code,200)
        self.assertEqual(self.status()["included"],250);self.assertTrue(self.status()["active"])
        self.assertEqual(len(self.status()["ledger"]),1)

    def test_paid_invoice_mail_is_queued_and_sent_once(self):
        self.checkout();self.pay_checkout();invoice=self.invoice()
        self.assertEqual(self.webhook("invoice.paid",invoice,"evt_invoice").status_code,200)
        self.assertEqual(self.webhook("invoice.paid",invoice,"evt_invoice").status_code,200)
        with main.db() as conn:
            row=conn.execute("SELECT recipient,status FROM invoice_deliveries WHERE invoice_id=?",(invoice["id"],)).fetchone()
            self.assertEqual(tuple(row),("admin@mueller.local","sent"))
        messages=list(auth.OUTBOX.glob("*.eml"))
        self.assertEqual(len(messages),1)
        self.assertIn(invoice["invoice_pdf"],messages[0].read_text())

    def test_invoice_uses_recipient_language_without_browser_request(self):
        from email import message_from_string
        with main.db() as conn:
            conn.execute("UPDATE users SET email_language='en' WHERE email='admin@mueller.local'")
        self.checkout();self.pay_checkout()
        self.assertEqual(self.webhook("invoice.paid",self.invoice(),"evt_english_invoice").status_code,200)
        message = message_from_string(next(auth.OUTBOX.glob("*.eml")).read_text())
        self.assertIn("Invoice", str(message["Subject"]))
        self.assertIn("We have received your payment",message.get_payload(decode=True).decode())

    def test_failed_invoice_mail_retries_without_duplicate_credit(self):
        self.checkout();self.pay_checkout();invoice=self.invoice()
        with patch.object(auth,"deliver_message",side_effect=HTTPException(503,"SMTP unavailable")):
            self.assertEqual(self.webhook("invoice.paid",invoice,"evt_invoice").status_code,503)
        self.assertEqual(self.status()["included"],250)
        self.assertEqual(self.webhook("invoice.paid",invoice,"evt_invoice").status_code,200)
        self.assertEqual(len(self.status()["ledger"]),1)
        self.assertEqual(len(list(auth.OUTBOX.glob("*.eml"))),1)

    def test_invoice_can_arrive_before_checkout_event(self):
        self.checkout();self.assertEqual(self.webhook("invoice.paid",self.invoice()).status_code,200)
        self.pay_checkout();self.assertEqual(self.status()["included"],250)

    def test_renewal_resets_included_preserves_purchased_and_ignores_old_invoice(self):
        self.activate()
        with main.db() as conn:conn.execute("UPDATE billing_accounts SET included=25,purchased=250 WHERE organization_id=?",(self.org,))
        new=self.invoice("in_new",self.now-10,self.now+7200)
        self.webhook("invoice.paid",new,"evt_new")
        self.webhook("invoice.paid",self.invoice("in_old",self.now-120,self.now+1800),"evt_old")
        s=self.status();self.assertEqual((s["included"],s["purchased"],s["period_end"]),(250,250,self.now+7200))

    def test_annual_subscription_grants_monthly_credits_without_second_invoice(self):
        self.sub["items"]["data"][0]["price"]["id"]="price_starter_yearly"
        self.assertEqual(self.checkout("starter_yearly").status_code,200)
        self.assertEqual(self.pay_checkout().status_code,200)
        invoice=self.invoice("in_year",self.now-60,self.now+365*86400)
        invoice["subtotal"]=billing.CATALOG["starter_yearly"]["cents"]
        invoice["lines"]["data"][0]["pricing"]["price_details"]["price"]="price_starter_yearly"
        self.assertEqual(self.webhook("invoice.paid",invoice,"evt_year").status_code,200)
        self.assertEqual(self.status()["included"],250)
        with main.db() as conn:
            anchor=self.now-40*86400
            conn.execute("UPDATE billing_accounts SET included=100,period_start=?,credit_period_start=?,period_end=? WHERE organization_id=?",
                         (anchor,anchor,self.now+325*86400,self.org))
        wallet=self.client.get("/tokens/wallet",headers=self.a).json()
        self.assertEqual(wallet["included"],250)
        self.assertGreater(wallet["credit_period_end"],self.now)
        self.assertEqual(self.status()["included"],250)
        with main.db() as conn:
            rows=conn.execute("SELECT COUNT(*) FROM token_ledger WHERE organization_id=? AND reference LIKE 'annual-credit:%'",(self.org,)).fetchone()[0]
        self.assertEqual(rows,1)

    def test_yearly_price_rejects_monthly_stripe_interval(self):
        item=billing.CATALOG["starter_yearly"]
        price={"active":True,"currency":"eur","unit_amount":item["cents"],"tax_behavior":"exclusive",
               "recurring":{"interval":"month","interval_count":1}}
        with self.assertRaises(billing.HTTPException) as error:
            billing.validate_price(price,item)
        self.assertEqual(error.exception.status_code,503)
        price["recurring"]["interval"]="year"
        billing.validate_price(price,item)

    def test_calendar_anniversary_clamps_end_of_month(self):
        from datetime import datetime,timezone
        anchor=int(datetime(2026,1,31,12,tzinfo=timezone.utc).timestamp())
        self.assertEqual(datetime.fromtimestamp(billing.month_anniversary(anchor,1),timezone.utc).date().isoformat(),"2026-02-28")
        self.assertEqual(datetime.fromtimestamp(billing.month_anniversary(anchor,2),timezone.utc).date().isoformat(),"2026-03-31")

    def test_topup_only_once_even_with_different_event_ids(self):
        self.activate();self.assertEqual(self.checkout("tokens_250","topup_request_1234").status_code,200)
        self.pay_checkout("cs_2","evt_topup");self.pay_checkout("cs_2","evt_topup_again")
        self.assertEqual(self.status()["purchased"],250)

    def test_topup_invoice_is_sent_once_with_credit(self):
        self.activate()
        self.assertEqual(self.checkout("tokens_250","topup_invoice_request_123").status_code,200)
        self.assertEqual(self.pay_checkout("cs_2","evt_paid_topup").status_code,200)
        self.assertEqual(self.pay_checkout("cs_2","evt_paid_topup_again").status_code,200)
        self.assertEqual(self.status()["purchased"],250)
        with main.db() as conn:
            row=conn.execute("SELECT status FROM invoice_deliveries WHERE invoice_id='in_payment_cs_2'").fetchone()
            self.assertEqual(row[0],"sent")
        self.assertEqual(len(list(auth.OUTBOX.glob("*.eml"))),2)

    def test_non_eu_checkout_and_invoice_never_grant_access(self):
        self.checkout();self.sessions["cs_1"]["customer_details"]["address"]["country"]="US"
        self.pay_checkout();self.assertTrue(self.status()["hold"])
        invoice=self.invoice();invoice["customer_address"]["country"]="US"
        self.webhook("invoice.paid",invoice,"evt_invoice");self.assertEqual(self.status()["included"],0);self.assertFalse(self.status()["active"])

    def test_active_subscription_prevents_duplicate_and_unpaid_blocks_topup(self):
        self.assertEqual(self.checkout("tokens_250").status_code,402)
        self.activate();self.assertEqual(self.checkout("team","another_sub_request").status_code,409)
        self.sub["status"]="past_due"
        self.webhook("customer.subscription.updated",self.sub,"evt_past_due")
        self.assertFalse(self.status()["active"])
        self.assertEqual(self.checkout("tokens_250","topup_unpaid_1234").status_code,402)

    def test_refund_freezes_tokens(self):
        self.activate();self.webhook("charge.refunded",{"id":"ch_one","customer":"cus_one"},"evt_refund")
        self.assertFalse(self.status()["active"]);self.assertTrue(self.status()["hold"])

    def test_only_real_company_admin_can_bill(self):
        self.assertEqual(self.checkout(headers=self.admin).status_code,403)
        self.client.post("/demo/context",headers=self.admin,json={"role":"firmen_admin","organization_id":self.org})
        self.assertEqual(self.checkout(headers=self.admin).status_code,403)
        self.assertEqual(self.client.get("/billing/status",headers=self.b).json()["managed"],False)
        self.assertEqual(self.client.get("/billing/status").status_code,401)

    def test_editors_and_clients_cannot_access_billing(self):
        for role in ('user','kunde'):
            with main.db() as conn:
                conn.execute("UPDATE users SET role=? WHERE email='admin@mueller.local'",(role,))
            self.assertEqual(self.client.get('/billing/status',headers=self.a).status_code,403)
            self.assertEqual(self.checkout(headers=self.a).status_code,403)
            self.assertEqual(self.client.post('/billing/portal',headers=self.a,json={}).status_code,403)
            self.assertEqual(self.client.post('/billing/checkout/cancel',headers=self.a,json={}).status_code,403)
        self.assertEqual(self.calls,[])

    def test_generation_atomic_idempotent_and_failed_operation_rolls_back(self):
        self.activate()
        campaign=self.client.post("/campaigns",headers=self.a,json={"organization_id":self.org,"briefing":{"role":"Test","location":"Berlin"}}).json()["id"]
        headers={**self.a,"Idempotency-Key":"generation_request_123"}
        for _ in range(2):self.assertEqual(self.client.post(f"/campaigns/{campaign}/generate",headers=headers).status_code,200)
        self.assertEqual(self.status()["included"],200)
        self.assertEqual(self.ai_provider.call_count,1)
        with main.db() as conn:
            usage=conn.execute("SELECT input_tokens,output_tokens,mh_tokens FROM ai_usage WHERE organization_id=?",(self.org,)).fetchall()
            self.assertEqual([tuple(row) for row in usage],[(1000,2000,50)])
        with patch.object(main.ai,"generate",side_effect=HTTPException(503,"AI failed")):
            response=self.client.post(f"/campaigns/{campaign}/generate",headers={**self.a,"Idempotency-Key":"failed_generation_123"})
            self.assertEqual(response.status_code,503)
        self.assertEqual(self.status()["included"],200)
        with main.db() as conn:conn.execute("UPDATE billing_accounts SET included=20,purchased=40 WHERE organization_id=?",(self.org,))
        self.client.post(f"/campaigns/{campaign}/generate",headers={**self.a,"Idempotency-Key":"second_generation_123"})
        self.assertEqual((self.status()["included"],self.status()["purchased"]),(0,10))
        self.assertEqual(self.client.post(f"/campaigns/{campaign}/generate",headers={**self.a,"Idempotency-Key":"third_generation_123"}).status_code,402)

    def test_local_test_package_uses_test_credit_once_and_never_calls_ai(self):
        self.activate()
        campaign = self.client.post('/campaigns',headers=self.a,json={'organization_id':self.org,'briefing':{'role':'Elektriker','location':'Berlin','benefits':'Verified benefit'}}).json()['id']
        with patch.dict(os.environ, {'MH_ENV':'development','OPENAI_API_KEY':''}), patch.object(main,'read_integration_settings',return_value={'openai':{}}):
            self.assertEqual(self.client.get('/tokens/wallet',headers=self.a).json()['generation_mode'], 'local_test')
            for _ in range(2):
                result = self.client.post(f'/campaigns/{campaign}/generate?test_package=true',headers={**self.a,'Idempotency-Key':'local_test_package_123'})
                self.assertEqual(result.status_code,200,result.text)
            self.assertEqual(result.json()['generation_mode'], 'local_test')
            self.assertEqual(self.client.get('/onboarding',headers=self.a).json()['campaign']['generation_mode'], 'local_test')
            self.assertEqual(set(result.json()['generated']), {'jobAd','social','meta'})
            self.assertIn('Verified benefit',result.json()['generated']['social'])
            self.assertFalse(result.json()['briefing_stale'])
            self.assertEqual(self.status()['included'],200)
            self.ai_provider.assert_not_called()
            with main.db() as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM ai_usage WHERE organization_id=?',(self.org,)).fetchone()[0],0)
            import io,zipfile
            archive = self.client.get(f'/campaigns/{campaign}/export',headers=self.a)
            with zipfile.ZipFile(io.BytesIO(archive.content)) as package:
                self.assertIn('MH TESTPAKET',package.read('README.txt').decode())
            with patch.object(main,'make_content',side_effect=ValueError('template failure')):
                with self.assertRaises(ValueError):
                    self.client.post(f'/campaigns/{campaign}/generate?test_package=true',headers={**self.a,'Idempotency-Key':'failed_test_package_123'})
            self.assertEqual(self.status()['included'],200)

    def test_local_test_packages_cannot_bypass_live_production_or_billing_gates(self):
        self.activate()
        campaign=self.client.post('/campaigns',headers=self.a,json={'organization_id':self.org,'briefing':{'role':'Test','location':'Berlin'}}).json()['id']
        url=f'/campaigns/{campaign}/generate?test_package=true'
        for env, expected in (({'MH_ENV':'production'},403), ({'STRIPE_SECRET_KEY':'sk_live_fixture'},402), ({'MH_PUBLIC_URL':'https://public.example.test'},403)):
            with patch.dict(os.environ,env):
                self.assertEqual(self.client.post(url,headers={**self.a,'Idempotency-Key':'forbidden_test_123'}).status_code,expected)
        with main.db() as conn: conn.execute("UPDATE billing_accounts SET status='past_due' WHERE organization_id=?", (self.org,))
        self.assertEqual(self.client.post(url,headers={**self.a,'Idempotency-Key':'unpaid_test_123'}).status_code,402)
        self.ai_provider.assert_not_called()
        with main.db() as conn:
            self.assertEqual(conn.execute('SELECT included FROM billing_accounts WHERE organization_id=?',(self.org,)).fetchone()[0],250)

    def test_concurrent_token_debits_cannot_overdraw(self):
        self.activate()
        with main.db() as conn:conn.execute("UPDATE billing_accounts SET included=50 WHERE organization_id=?",(self.org,))
        def debit(i):
            try:
                with main.db() as conn:
                    conn.execute("BEGIN IMMEDIATE");billing.debit_generation(conn,self.org,f"concurrent_request_{i}",1)
                return True
            except HTTPException:return False
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(debit,[1,2]))
        self.assertEqual(sum(results),1);self.assertEqual(self.status()["included"],0)

    def test_seats_and_portal_configuration(self):
        self.activate()
        for i in range(2):
            self.assertEqual(self.client.post("/auth/invitations",headers=self.a,json={"email":f"person{i}@example.test","role":"user"}).status_code,201)
        self.assertEqual(self.client.post("/auth/invitations",headers=self.a,json={"email":"person3@example.test","role":"user"}).status_code,409)
        self.assertEqual(self.client.post("/billing/portal",headers=self.a,json={}).status_code,200)
        config=[c[2] for c in self.calls if c[1]=="billing_portal/configurations"][0]
        self.assertFalse(config["features"]["subscription_update"]["enabled"])
        self.assertEqual(config["features"]["subscription_cancel"]["mode"],"at_period_end")

    def test_pending_account_cannot_write_campaigns(self):
        self.checkout()
        self.assertEqual(self.client.post("/campaigns",headers=self.a,json={"organization_id":self.org,"briefing":{"role":"Test","location":"Berlin"}}).status_code,402)

    def test_registration_scoped_pending_and_rate_limited(self):
        body={"company":"New Company","name":"Jane Doe","email":"jane@example.test","password":"a_secure_test_password","country":"DE","business":True}
        self.assertEqual(self.client.post("/auth/register",json={**body,"country":"GB"}).status_code,422)
        response=self.client.post("/auth/register",json=body);self.assertEqual(response.status_code,201,response.text)
        headers=session_headers(self.client)
        self.assertFalse(self.client.get("/auth/me",headers=headers).json()["email_verified"])
        self.assertEqual(self.client.get("/organizations",headers=headers).status_code,403)
        self.assertEqual(self.client.get("/billing/status",headers=headers).status_code,403)
        for _ in range(5):last=self.client.post("/auth/register",json=body)
        self.assertEqual(last.status_code,429)

    def test_cancel_checkout_allows_different_plan(self):
        self.checkout();self.assertEqual(self.client.post("/billing/checkout/cancel",headers=self.a,json={}).status_code,200)
        self.assertEqual(self.checkout("team","new_order_request_123").status_code,200)

    def test_missing_config_and_live_gates_fail_closed(self):
        with patch.dict(os.environ,{"STRIPE_SECRET_KEY":""}):
            self.assertFalse(self.client.get("/billing/config").json()["ready"])
            self.assertEqual(self.checkout().status_code,503)
        with patch.dict(os.environ,{"STRIPE_SECRET_KEY":"sk_live_fixture"}):
            self.assertFalse(billing.configuration()["ready"])
            self.assertIn("MH_EU_RADAR_CONFIRMED",billing.configuration()["missing"])

    def test_unexpected_price_amount_rejected_before_checkout(self):
        with patch.object(billing,"remote",return_value={"active":True,"currency":"eur","unit_amount":1,"tax_behavior":"exclusive","recurring":{"interval":"month","interval_count":1}}):
            self.assertEqual(self.checkout().status_code,503)
        self.assertFalse(self.sessions)

    def test_provider_failure_is_retryable_with_same_order(self):
        original=self.provider
        def flaky(method,path,data=None,key=None):
            if path=="checkout/sessions":raise HTTPException(502,"Unavailable")
            return original(method,path,data,key)
        with patch.object(billing,"stripe_call",side_effect=flaky):self.assertEqual(self.checkout().status_code,502)
        self.assertEqual(self.checkout().status_code,200)
        self.assertEqual(len(self.sessions),1)

    def test_test_balance_is_never_usable_in_live_mode(self):
        self.activate()
        with main.db() as conn: a=billing.account(conn,self.org)
        self.assertTrue(billing.usable(a))
        with patch.dict(os.environ,{"STRIPE_SECRET_KEY":"sk_live_fixture"}):
            self.assertFalse(billing.usable(a))

    def test_expired_paid_period_does_not_allow_generation_or_topup(self):
        self.activate()
        with main.db() as conn:conn.execute("UPDATE billing_accounts SET period_end=?,purchased=250 WHERE organization_id=?",(self.now-10,self.org))
        self.assertFalse(self.status()["active"])
        self.assertEqual(self.status()["included"],0)
        self.assertEqual(self.checkout("tokens_250","expired_topup_1234").status_code,402)

    def test_invoice_with_wrong_amount_is_held(self):
        self.checkout();invoice=self.invoice();invoice["subtotal"]=100
        self.assertEqual(self.webhook("invoice.paid",invoice).status_code,200)
        self.assertTrue(self.status()["hold"]);self.assertEqual(self.status()["included"],0)

    def test_checkout_cannot_credit_a_different_company(self):
        self.activate();self.checkout("tokens_250","scope_topup_12345")
        self.sessions["cs_2"]["customer"]="cus_other"
        self.assertEqual(self.pay_checkout("cs_2","evt_foreign").status_code,200)
        self.assertEqual(self.status()["purchased"],0)


    def test_multiple_topups_add_to_wallet_without_duplicate_credit(self):
        self.activate()
        self.checkout("tokens_250", "additive_topup_one")
        self.pay_checkout("cs_2", "evt_add_one")
        self.checkout("tokens_1000", "additive_topup_two")
        self.pay_checkout("cs_3", "evt_add_two")
        self.pay_checkout("cs_3", "evt_add_duplicate")
        wallet = self.client.get("/tokens/wallet", headers=self.a).json()
        self.assertEqual(wallet["purchased"], 1250)
        self.assertEqual(wallet["available"], 1500)
        self.assertFalse(self.client.get("/tokens/wallet",headers=self.b).json()["managed"])
        with main.db() as conn:
            conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id) VALUES(?,?,?,?,?)",("wallet-reader@example.com","Kunde",main.password_hash("long-test-password"),"kunde",self.org))
        customer=self.login("wallet-reader@example.com",{"wallet-reader@example.com":"long-test-password"})
        self.assertEqual(self.client.get("/tokens/wallet",headers=customer).json()["available"],1500)
        self.assertEqual(self.client.get("/billing/status",headers=customer).status_code,403)
        self.assertEqual(self.client.get("/tokens/wallet").status_code,401)


if __name__ == "__main__":unittest.main()
