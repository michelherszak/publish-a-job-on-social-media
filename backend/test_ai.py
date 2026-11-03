import io
import json
import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from backend import ai

class AITests(unittest.TestCase):
    def test_missing_key_and_oversized_input_do_not_call_provider(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY":""}), patch.object(ai.urllib.request,"urlopen") as network:
            with self.assertRaises(HTTPException) as error: ai.generate({},"Firma",{})
            self.assertEqual(error.exception.status_code,503)
            with self.assertRaises(HTTPException): ai.generate({"tasks":"x"*20001},"Firma",{"api_key":"fixture"})
            network.assert_not_called()
    def test_structured_response_and_actual_usage(self):
        response={"status":"completed","id":"resp_fixture","model":ai.DEFAULT_MODEL,"output":[{"type":"message","content":[{"type":"output_text","text":json.dumps({k:"Entwurf" for k in ai.CHANNELS})}]}],"usage":{"input_tokens":1000,"output_tokens":2000,"input_tokens_details":{"cached_tokens":100}}}
        with patch.dict(os.environ,{"OPENAI_API_KEY":"","OPENAI_BASE_URL":"https://api.openai.com/v1"}), patch.object(ai.urllib.request,"urlopen",return_value=io.BytesIO(json.dumps(response).encode())) as network:
            content, usage=ai.generate({"role":"Elektriker"},"Firma",{"api_key":"fixture"})
            payload=json.loads(network.call_args.args[0].data)
            self.assertFalse(payload["store"])
            self.assertEqual(payload["max_output_tokens"],4000)
            self.assertTrue(payload["text"]["format"]["strict"])
            self.assertEqual(set(content),{"jobAd","social","meta"})
            self.assertEqual(set(payload["text"]["format"]["schema"]["required"]),{"jobAd","social","meta"})
            self.assertEqual(usage["output_tokens"],2000)
            response["status"]="incomplete"
            with patch.object(ai.urllib.request,"urlopen",return_value=io.BytesIO(json.dumps(response).encode())):
                with self.assertRaises(HTTPException):ai.generate({},"Firma",{"api_key":"fixture"})
