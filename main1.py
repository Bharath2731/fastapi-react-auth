from fastapi import FastAPI, Depends, HTTPException, Form
from authlib.integrations.starlette_client import OAuth
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.tokens import BearerToken
from authlib.common.security import generate_token
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_400_BAD_REQUEST
from werkzeug.security import gen_salt

app = FastAPI()

# In-memory storage for users and tokens (use a database in production)
users = {'user1': {'password': 'password1'}}
tokens = {}

class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        user = users.get(username)
        if user and user['password'] == password:
            return {'id': username}
        return None

class MyBearerToken(BearerToken):
    def __init__(self):
        super().__init__()
    
    def create_access_token(self, token, client, user, scope):
        token['access_token'] = generate_token(42)
        token['refresh_token'] = generate_token(48)
        tokens[token['access_token']] = user
        return token

oauth = OAuth()
oauth.register_grant(PasswordGrant)

@app.on_event("startup")
async def startup():
    oauth.init_app(app, MyBearerToken())

@app.post('/token')
async def issue_token(request: Request):
    return await oauth.create_token_response(request)

@app.post('/refresh')
async def refresh_token(request: Request):
    return await oauth.create_token_response(request)

@app.post('/oauth/token')
async def oauth_token(grant_type: str = Form(...), username: str = Form(None), password: str = Form(None), refresh_token: str = Form(None)):
    if grant_type == 'password':
        if not username or not password:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Missing username or password")
        user = users.get(username)
        if user and user['password'] == password:
            access_token = generate_token(42)
            refresh_token = generate_token(48)
            tokens[access_token] = user
            return JSONResponse({'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'Bearer'})
        else:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid username or password")
    elif grant_type == 'refresh_token':
        if not refresh_token:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Missing refresh token")
        for token, user in tokens.items():
            if token == refresh_token:
                new_access_token = generate_token(42)
                new_refresh_token = generate_token(48)
                tokens[new_access_token] = user
                return JSONResponse({'access_token': new_access_token, 'refresh_token': new_refresh_token, 'token_type': 'Bearer'})
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid refresh token")
    else:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Unsupported grant type")

if __name__ == '__main1__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
