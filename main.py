from fastapi import FastAPI,HTTPException,Response,Depends,Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import datetime
import socketio
import jwt
# Create a new FastAPI app
app = FastAPI()

# CORS settings
origins = ["http://localhost:3000","*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=['http://localhost:3000',"*"])
app.mount('/socket.io', socketio.ASGIApp(sio, static_files={'/': './public/'}))




# Basic endpoint to check if the server is running
@app.get('/')
def root():
    return {'message': 'server is running'}

# Global data for checklist
globalData = [
    {"name": "one", 'ischecked': True}, 
    {"name": "two", 'ischecked': False},
    {"name": 'three', 'ischecked': False},
    {"name": 'four', 'ischecked': False},
    {"name": 'five', 'ischecked': False},
]
roomAData = [
    {"name": "one", 'ischecked': True},
    {"name": "two", 'ischecked': False},
    {"name": 'three', 'ischecked': False},
    {"name": 'four', 'ischecked': False},
    {"name": 'five', 'ischecked': False},
]
roomBData = [
    {"name": "one", 'ischecked': True},
    {"name": "two", 'ischecked': False},
    {"name": 'three', 'ischecked': False},
    {"name": 'four', 'ischecked': False},
    {"name": 'five', 'ischecked': False},
]

# Endpoint to get the checklist
@app.get('/checklist')
async def checklist():
    return {'globalData':globalData,
            'roomAData':roomAData,
            'roomBData':roomBData,}

# Pydantic model for checklist item
class Subobj(BaseModel):
    name: str
    ischecked: bool

# Endpoint to update the checklist
@app.post('/checklist')
async def addchecklist(checklists: list[Subobj]):
    global globalData
    objects = checklists
    dicts = [obj.dict() for obj in objects]
    globalData = dicts
    print("after", globalData)
    await sio.emit('update_checklist', globalData)
    return checklists

usersData = [
    {'name':'bharath','password':'123456'},
    {'name':'sahil','password':'123456'},
    {'name':'vishnu','password':'123456'},
    {'name':'sai','password':'123456'},
    {'name':'siva','password':'123456'},
]
SECRET_KEY = 'testkey'
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
class LoginForm(BaseModel):
    name: str
    password: str
    exp: str


@app.post('/login')
async def login(form_data: LoginForm,response:Response):
    # create access token
    for user in usersData:
        if user['name'] == form_data.name and user['password'] == form_data.password:
            access_token = create_access_token(data=form_data)
            refresh_token = create_refresh_token(data={"sub": user['name']})
             # Set cookies in the response
            response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,secure=True,samesite="None")
            response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,secure=True,samesite="None")
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }   
    raise HTTPException(status_code=401, detail="Invalid username or password")

def create_access_token(data: LoginForm):
    to_encode = data.dict().copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@app.get('/home')
async def homeName(request:Request): 
    decodedValue = verify_token(request.cookies.get('access_token'))
    print(decodedValue['name'])
    return {"name":decodedValue['name']}

@app.get('/checkauth')
async def isUserAuthorized(request:Request):
    decodedValue = verify_token(request.cookies.get('access_token'))
    if(decodedValue is not None):
        print(decodedValue)
        return {'message':'user authorized','isauth':True}
    return{'message':'user not authorized','isauth':False}

@app.post('/checklist/A')
async def addchecklista(checklists: list[Subobj]):
    global roomAData
    objects = checklists
    dicts = [obj.dict() for obj in objects]
    roomAData = dicts
    print("after roomA \n", roomAData)
    await sio.emit('update_checklist_roomA', roomAData, room="roomA")
    print('emited to room ')
    return checklists

@app.post('/checklist/B')
async def addchecklista(checklists: list[Subobj]):
    global roomBData
    objects = checklists
    dicts = [obj.dict() for obj in objects]
    roomBData = dicts
    print("after roomB \n", roomBData)
    await sio.emit('update_checklist_roomB', roomBData, room="roomB")
    print('emited to roomB ')
    return checklists

# Define Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")
    await sio.emit('message', 'Hello from the server!', to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client {sid} disconnected")

@sio.event
async def join_room(sid, room):
    await sio.enter_room(sid, room)
    rooms = sio.rooms(sid)
    print(rooms,room)
    if room in rooms:
        print(f"Client {sid} joined room {room}")
    else:
        print(f"Client {sid} failed to join room {room}")


@sio.event
async def leave_room(sid, room):
    await sio.leave_room(sid, room)
    print(f"Client {sid} left room {room}")

    # Remove the client from the room tracking
    if room in room_clients:
        room_clients[room].discard(sid)
        # If the room is empty, remove it from tracking
        if not room_clients[room]:
            del room_clients[room]
            print(f"Room {room} is now empty and has been deleted.")
    
    print(f"Current clients in {room}: {room_clients.get(room, set())}")


# Run the application with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
