import unittest

from fastapi.testclient import TestClient

from app.main import app, frontend_origin


class CorsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_farm_preflight_allows_frontend_authorization_header(self) -> None:
        assert frontend_origin is not None
        response = self.client.options(
            "/farms",
            headers={
                "Origin": frontend_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            frontend_origin,
        )
        self.assertIn("GET", response.headers["access-control-allow-methods"])
        self.assertIn(
            "authorization",
            response.headers["access-control-allow-headers"].lower(),
        )
        self.assertIn(
            "content-type",
            response.headers["access-control-allow-headers"].lower(),
        )

    def test_unconfigured_origin_is_not_allowed(self) -> None:
        response = self.client.options(
            "/farms",
            headers={
                "Origin": "https://not-allowed.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 400)
