_ALLOWED={'https://optilovesinvest.com','https://www.optilovesinvest.com'}
def allow_cors(app,allowed=None):
    allow=allowed or _ALLOWED
    def _mw(env,start_response):
        o=env.get('HTTP_ORIGIN',''); p=env.get('PATH_INFO','') or ''; m=(env.get('REQUEST_METHOD','GET') or 'GET').upper()
        if m=='OPTIONS' and p.startswith('/api/'):
            def _sr(st,hd,ex=None):
                if o in allow: hd+= [('Access-Control-Allow-Origin',o),('Vary','Origin'),
                    ('Access-Control-Allow-Credentials','true'),
                    ('Access-Control-Allow-Headers','Content-Type, X-API-Key'),
                    ('Access-Control-Allow-Methods','GET,POST,OPTIONS')]
                return start_response(st,hd,ex)
            _sr('204 No Content',[]); return [b'']
        def _sr(st,hd,ex=None):
            hd=list(hd)
            if o in allow: hd+= [('Access-Control-Allow-Origin',o),('Vary','Origin'),
                ('Access-Control-Allow-Credentials','true')]
            return start_response(st,hd,ex)
        return app(env,_sr)
    return _mw
