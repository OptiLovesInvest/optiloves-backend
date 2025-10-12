from typing import Iterable, Callable, Tuple

_ALLOWED = {
    'https://optilovesinvest.com',
    'https://www.optilovesinvest.com',
}

def allow_cors(app, allowed: set = None):
    allow = allowed or _ALLOWED

    def _mw(environ, start_response):
        origin = environ.get('HTTP_ORIGIN', '')
        path   = environ.get('PATH_INFO', '') or ''
        method = environ.get('REQUEST_METHOD', 'GET').upper()

        # Preflight for our API
        if method == 'OPTIONS' and path.startswith('/api/'):
            def _sr(status, headers, exc_info=None):
                if origin in allow:
                    headers.append(('Access-Control-Allow-Origin', origin))
                    headers.append(('Vary', 'Origin'))
                    headers.append(('Access-Control-Allow-Credentials', 'true'))
                    headers.append(('Access-Control-Allow-Headers', 'Content-Type, X-API-Key'))
                    headers.append(('Access-Control-Allow-Methods', 'GET,POST,OPTIONS'))
                return start_response(status, headers, exc_info)
            _sr('204 No Content', [])
            return [b'']

        def _sr(status: str, headers: Iterable[Tuple[str,str]], exc_info=None):
            headers = list(headers)
            if origin in allow:
                headers.append(('Access-Control-Allow-Origin', origin))
                headers.append(('Vary', 'Origin'))
                headers.append(('Access-Control-Allow-Credentials', 'true'))
            return start_response(status, headers, exc_info)

        return app(environ, _sr)

    return _mw
