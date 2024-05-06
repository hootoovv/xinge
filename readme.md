# FastAPI Websocket sample

This sample can use to build as part of video chat room or a command center.

Admin user can use fastapi restful api to login then create room, then join the room via websocket and broadcast message to all users in the room.

Normal user can use login api login then, join the room via websocket and message to others in the room.

It is just an simple sample of fastapi/websocket for implementation of chat room.

When admin delete the room via restful api and there is users in the room. The code shows how to disconnect the users in the room then remove the room from the memory. (server side disconnect)

It also can handle client side disconnect

Note. in client.py send_message function, change loop range from 15 (client disconnect) to 35 (server disconnect) to see the difference.

So far it is only a simple demo code, admin account must start with admin, and all password should be 123456. you can change it to test the auth failed case. later can add sqllit + orm to handle a more real user login process.
