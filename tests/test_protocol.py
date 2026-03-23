import unittest

from MCP_Server.protocol import error_response, normalize_response, success_response


class ProtocolTests(unittest.TestCase):
    def test_success_response_shape(self):
        response = success_response("track", object_ref={"track_index": 1}, state={"name": "Bass"})
        self.assertTrue(response["ok"])
        self.assertIsNone(response["error"])
        self.assertEqual(response["object_type"], "track")
        self.assertEqual(response["object_ref"]["track_index"], 1)
        self.assertEqual(response["state"]["name"], "Bass")

    def test_error_response_shape(self):
        response = error_response("invalid_index", "Track index out of range")
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_index")
        self.assertEqual(response["error"]["message"], "Track index out of range")

    def test_normalize_legacy_success(self):
        response = normalize_response({"status": "success", "result": {"tempo": 120}})
        self.assertTrue(response["ok"])
        self.assertEqual(response["state"]["tempo"], 120)

    def test_normalize_legacy_error(self):
        response = normalize_response({"status": "error", "message": "bad request"})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "remote_error")


if __name__ == "__main__":
    unittest.main()
