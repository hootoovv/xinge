from fastapi import Depends, Query, FastAPI, HTTPException, status
from fastapi import WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.websockets import WebSocketState
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from pydantic import BaseModel
from typing import Annotated
import uvicorn
import uuid
import asyncio

from uvicorn.server import logger

app = FastAPI()

rooms = dict()  # room_id: room
users = dict()  # user_id: user
managers = dict()  # room_id: ConnectionManager

token_users = dict()  # token: user_id
user_tokens = dict()  # user_id: token

token_admins = dict()  # token: admin_id
admin_tokens = dict()  # admin_id: token

USERAPI_BASRPATH = "/api/user"
ADMINAPI_BASRPATH = "/api/admin"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


@app.get("/")
async def home():
    return {"message": "Puppet Server"}


# user api
def authenticate_user(username: str, password: str):
    if password != "123456":
        return ""
    return username


@app.post(USERAPI_BASRPATH + "/login")
async def user_login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_id = authenticate_user(form_data.username, form_data.password)
    if user_id == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = str(uuid.uuid4())
    user_tokens[user_id] = token
    token_users[token] = user_id
    users[user_id] = user_id

    return {"code": 200, "message": "Login success",
            "data": {"username": user_id, "token": token}}


async def get_user_from_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token not in token_users:
        raise credentials_exception

    return token_users[token]


@app.put(USERAPI_BASRPATH + "/me")
async def updateUser(user: dict, id: str = Depends(get_user_from_token)):
    if id not in users:
        return {"code": 404, "message": "User not found", "data": None}

    users[id] = user

    return {"code": 200, "message": "Update user success", "data": user}


@app.get(USERAPI_BASRPATH + "/me")
async def getUser(id: str = Depends(get_user_from_token)):
    if id not in users:
        return {"code": 404, "message": "User not found", "data": None}

    return {"code": 200, "message": "User found", "data": users[id]}


# admin api
def authenticate_admin(username: str, password: str):
    if not username.startswith("admin") or password != "123456":
        return ""

    return username


@app.post(ADMINAPI_BASRPATH + "/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    admin_id = authenticate_admin(form_data.username, form_data.password)
    if admin_id == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = str(uuid.uuid4())
    admin_tokens[admin_id] = token
    token_admins[token] = admin_id

    return {"code": 200, "message": "Login success",
            "data": {"username": admin_id, "token": token}}


async def get_admin_from_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token not in token_admins:
        raise credentials_exception

    return token_admins[token]


@app.post(ADMINAPI_BASRPATH + "/room/{room_id}")
async def createRoom(room_id: str, room: dict,
                     admin_id: str = Depends(get_admin_from_token)):
    for id, rm in rooms.items():
        if id == room_id:
            return {"code": 400, "message": "Room already exists", "data": rm}

    rooms[room_id] = room

    return {"code": 200, "message": "Create room success", "data": room}


@app.get(ADMINAPI_BASRPATH + "/room/{room_id}")
async def getRoom(room_id: str, admin_id: str = Depends(get_admin_from_token)):
    if room_id not in rooms:
        return {"code": 404, "message": "Room not found", "data": None}

    return {"code": 200, "message": "Room found",
            "data": {"id": room_id, "room": rooms[room_id]}}


@app.delete(ADMINAPI_BASRPATH + "/room/{room_id}")
async def deleteRoom(room_id: str,
                     admin_id: str = Depends(get_admin_from_token)):
    if room_id not in rooms:
        return {"code": 404, "message": "Room not found", "data": None}

    logger.info("Deleting Room: " + room_id)

    await managers[room_id].close_all_connections(room_id)

    managers[room_id] = None
    del managers[room_id]

    rooms[room_id] = None
    del rooms[room_id]

    return {"code": 200, "message": "Room deleted", "data": {"id": room_id}}


@app.get(ADMINAPI_BASRPATH + "/rooms")
async def getRooms(admin_id: str = Depends(get_admin_from_token)):
    room_list = []

    for id, rm in rooms.items():
        room_list.append({"id": id, "room": rm})

    return {"code": 200, "message": "Room list", "data": room_list}


@app.get(ADMINAPI_BASRPATH + "/users")
async def getUsers(admin_id: str = Depends(get_admin_from_token)):
    user_list = []

    for id, user in users.items():
        user_list.append({"id": id, "user": user})

    return {"code": 200, "message": "User list", "data": user_list}


@app.get(ADMINAPI_BASRPATH + "/sessions")
async def getSessions(admin_id: str = Depends(get_admin_from_token)):
    session_list = []

    for admin, token in admin_tokens.items():
        session_list.append({"id": admin, "token": token, "type": "admin"})

    for user, token in user_tokens.items():
        session_list.append({"id": user, "token": token, "type": "user"})

    return {"code": 200, "message": "Session list", "data": session_list}


class SendError(Exception):
    pass


# websocket
class ConnectionManager:
    def __init__(self):
        self.active_connections = dict()

    async def connect(self, user: str, ws: WebSocket):
        await ws.accept()
        self.active_connections[user] = ws

    async def send(self, data: dict, users: list):
        for user, ws in self.active_connections.items():
            if user in users:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(data)

    async def broadcast(self, data: dict, sender: str):
        for user, ws in self.active_connections.items():
            if user == sender:
                continue

            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_json(data)

    async def handle_close_exception(self, ws: WebSocket):
        try:
            await ws.close(status.WS_1000_NORMAL_CLOSURE,
                           "Room deleted")
        except RuntimeError:
            # print("Close Error")
            pass

    async def close_all_connections(self, room_id: str):
        for user, ws in self.active_connections.items():
            if ws.client_state == WebSocketState.CONNECTED:
                # print("send close to " + user)
                asyncio.create_task(self.handle_close_exception(ws))
            # else:
            #     print("User: " + user + " is already disconnected.")
            logger.info("Room[" + room_id + "]: " + user + " leaved.")

        self.active_connections.clear()


async def get_user(websocket: WebSocket,
                   token: Annotated[str | None, Query()] = None):
    if token is None:
        raise WebSocketException(code=status.HTTP_401_UNAUTHORIZED)

    if token in token_users.keys():
        return token_users[token]

    if token in token_admins.keys():
        return token_admins[token]

    raise WebSocketException(code=status.HTTP_401_UNAUTHORIZED)


@app.websocket("/ws/room/{room_id}")
async def websocket_endpoint(ws: WebSocket, room_id: str,
                             user: Annotated[str, Depends(get_user)]):
    if room_id not in rooms:
        raise WebSocketException(code=status.HTTP_403_FORBIDDEN)

    if room_id not in managers.keys():
        managers[room_id] = ConnectionManager()
        rooms[room_id]["users"] = []

    manager = managers[room_id]

    await manager.connect(user, ws)

    rooms[room_id]["users"].append(user)

    logger.info("Room[" + room_id + "]: " + user + " entered.")

    try:
        async for data in ws.iter_json():
            to_list = data["to"]

            payload = {"from": user, "data": data["data"]}

            # logger.info("Room[" + room_id + "]: " + user + "->" + data["data"])

            if to_list is None or len(to_list) == 0:
                await manager.broadcast(payload, sender=user)
            else:
                await manager.send(payload, to_list)
    except WebSocketDisconnect:
        # print(user + " disconnected")
        del manager.active_connections[user]
        if len(manager.active_connections) == 0:
            managers[room_id] = None
            del managers[room_id]


if __name__ == '__main__':
    try:
        uvicorn.run(app=app, host="127.0.0.1", port=8000)
    except KeyboardInterrupt:
        logger.info("Server stopped.")
