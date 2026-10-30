import asyncio
import unittest
import httpx
from app.dashboard_local import create_app


class DashboardBoundaryTest(unittest.TestCase):
    def test_external_urls_rejected(self):
        for url in ('http://127.0.0.1', 'https://evil.invalid', 'https://127.0.0.1@evil.invalid', 'https://127.0.0.1/extra', 'https://127.0.0.1?target=evil'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                create_app(url, 'test-token')

    def test_cross_origin_and_missing_cookie_rejected(self):
        async def run():
            app = create_app('https://127.0.0.1:8130', 'test-token')
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://127.0.0.1:8150') as client:
                result = await client.get('/dashboard/v1/status')
                self.assertEqual(result.status_code, 401)
                result = await client.get('/', headers={'Origin': 'https://evil.invalid'})
                self.assertEqual(result.status_code, 403)
                result = await client.get('/', headers={'Host': 'evil.invalid'})
                self.assertEqual(result.status_code, 403)
        asyncio.run(run())
