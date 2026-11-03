"""Bound API request bodies before JSON parsing, including chunked requests."""
import re
from starlette.responses import JSONResponse


class RequestSizeLimit:
    def __init__(self, app, maximum=1024 * 1024):
        self.app = app
        self.maximum = maximum

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        image_upload = scope.get('method') == 'POST' and re.fullmatch(r'/campaigns/\d+/images', scope.get('path', ''))
        maximum = 10 * 1024 * 1024 if image_upload else self.maximum
        size_error = 'Bild zu groß oder leer (maximal 10 MiB).' if image_upload else 'Anfrage zu groß (maximal 1 MiB).'
        async def reject(status, detail):
            response = JSONResponse({'detail': detail}, status_code=status,
                                    headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
            await response(scope, receive, send)
        for key, value in scope.get('headers', []):
            if key.lower() == b'content-length':
                try:
                    size = int(value)
                except ValueError:
                    return await reject(400, 'Ungültige Anfragegröße.')
                if size < 0:
                    return await reject(400, 'Ungültige Anfragegröße.')
                if size > maximum:
                    return await reject(413, size_error)
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > maximum:
                return await reject(413, size_error)
            if not message.get('more_body', False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        await self.app(scope, bounded_receive, send)
