"""Loopback-only, read-only BFF. Engine credentials never reach the browser."""
import argparse
import hmac
import os
import secrets
import ssl
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

ASSETS=Path(__file__).resolve().parent/'web/observatory'


def create_app(engine_url, token, *, ca_file=None, transport=None):
    if not token or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError('PRIVATE_OPERATOR_TOKEN_REQUIRED')
    parsed=urlparse(engine_url)
    if parsed.scheme!='https' or parsed.hostname not in ('127.0.0.1','localhost','control') or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('LOCAL_TLS_ENGINE_REQUIRED')
    verify=ssl.create_default_context(cafile=str(ca_file)) if ca_file else True
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    session=secrets.token_urlsafe(32)

    @app.middleware('http')
    async def boundary(request, call_next):
        host=request.headers.get('host','')
        local=request.url.hostname in ('127.0.0.1','localhost') and len(request.headers.getlist('host'))==1
        origin=request.headers.getlist('origin')
        valid_origin=not origin or len(origin)==1 and origin[0]==str(request.url.scheme)+'://'+host
        same_site=request.headers.get('sec-fetch-site','none') in ('none','same-origin')
        if not local or not valid_origin or not same_site:
            response=JSONResponse({'error':{'code':'LOCAL_BOUNDARY_REJECTED','retryable':False}},403)
        elif request.url.path.startswith('/dashboard/') and not hmac.compare_digest(request.cookies.get('wh_dashboard',''),session):
            response=JSONResponse({'error':{'code':'DASHBOARD_AUTH_REQUIRED','retryable':False}},401)
        else:
            response=await call_next(request)
            if request.url.path=='/' and response.status_code==200:
                response.set_cookie('wh_dashboard',session,httponly=True,samesite='strict',path='/')
        for name,value in {'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
                           'X-Frame-Options':'DENY','Permissions-Policy':'camera=(), microphone=(), geolocation=()',
                           'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}.items():
            response.headers[name]=value
        return response

    @app.get('/')
    async def index():
        return FileResponse(ASSETS/'index.html',media_type='text/html')

    @app.get('/app.js')
    async def javascript():
        return FileResponse(ASSETS/'app.js',media_type='text/javascript')

    @app.get('/styles.css')
    async def stylesheet():
        return FileResponse(ASSETS/'styles.css',media_type='text/css')

    @app.get('/dashboard/v1/{path:path}')
    async def proxy(path:str,request:Request):
        import re
        if path not in ('status','summary','events','security') and not re.fullmatch(r'events/[a-f0-9]{64}',path):
            return JSONResponse({'error':{'code':'NOT_FOUND','retryable':False}},404)
        # Only explicit read routes. No caller URL, engine write, auth/ASK nonce or
        # user headers/cookies are forwarded to Control. No automatic HTTP retry.
        try:
            async with httpx.AsyncClient(verify=verify,trust_env=False,follow_redirects=False,timeout=8,transport=transport) as client:
                response=await client.get(engine_url.rstrip('/')+'/dashboard/v1/'+path,
                                          params=list(request.query_params.multi_items()),headers={'Authorization':'Bearer '+token})
            if response.status_code==200:
                if len(response.content)>2097152:
                    raise ValueError()
                data=response.json()
                if path=='status':
                    data['relay']={'state':'ONLINE','engine_url':engine_url,'observed_at':time.time()}
                return JSONResponse(data)
            status=response.status_code if response.status_code in (400,401,403,404,409,429,503,504) else 503
            data=response.json() if response.headers.get('content-type','').startswith('application/json') else {}
            code=(data.get('error') or {}).get('code') or {401:'PERMISSION_DENIED',403:'PERMISSION_DENIED',404:'API_NOT_IMPLEMENTED',429:'RATE_LIMITED'}.get(status,'ENGINE_UNAVAILABLE')
            headers={'Retry-After':response.headers.get('Retry-After','15')} if status==429 else {}
            return JSONResponse({'error':{'code':code,'retryable':status>=500 or status==429}},status,headers=headers)
        except (httpx.HTTPError,ValueError,TypeError):
            return JSONResponse({'error':{'code':'ENGINE_UNAVAILABLE','message':'엔진 TLS·기동·API 설정을 확인하세요.','retryable':True}},503)

    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials',type=Path,required=True)
    parser.add_argument('--engine-url',default='https://127.0.0.1:8130')
    parser.add_argument('--port',type=int,default=8150)
    args=parser.parse_args()
    try:
        root=args.credentials.absolute()
        if any(p.is_symlink() for p in (root,*root.parents)) or not 1024<=args.port<=65535:
            raise ValueError()
        key=root/'human.token'
        ca=root/'ca.pem'
        if key.is_symlink() or ca.is_symlink() or key.stat().st_size>4096:
            raise ValueError()
        app=create_app(args.engine_url,key.read_text(encoding='ascii').strip(),ca_file=ca)
    except (ValueError,OSError):
        raise SystemExit('LOCAL_DASHBOARD_CONFIGURATION_REQUIRED') from None
    print('Local dashboard: http://127.0.0.1:'+str(args.port),flush=True)
    host='0.0.0.0' if os.environ.get('WITH_HUMAN_CONTAINER_BOUNDARY')=='loopback-published' else '127.0.0.1'
    uvicorn.run(app,host=host,port=args.port,access_log=False,proxy_headers=False,log_level='warning')


if __name__=='__main__':
    main()
