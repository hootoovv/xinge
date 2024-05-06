import requests
import websocket
import threading
import time
import json

url = "http://127.0.0.1:8000"
wsurl = "ws://127.0.0.1:8000"

completes = dict()


def login(route, payload=None):
    # send form data
    response = requests.post(url + route, data=payload)

    if response.status_code == 200:
        json = response.json()
        if json["code"] == 200:
            # print(json["data"]["session_id"])
            token = json["data"]["token"]
        else:
            print("Error: " + str(json["code"]) + " - " + json["message"])
            return ""
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)
        return ""

    return token


def user_put(route, token=None):
    headers = {"Authorization": "Bearer " + token}
    payload = {"username": "kevin",
               "name": "Kevin Wu",
               "selfie": "kevin.jpg",
               "orgnization": "ZKTR"}
    response = requests.put(url + route, headers=headers, json=payload)
    if response.status_code == 200:
        json = response.json()
        print(json)
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)
        return ""


def user_get(route, token=None):
    headers = {"Authorization": "Bearer " + token}
    response = requests.get(url + route, headers=headers)
    if response.status_code == 200:
        json = response.json()
        print(json)
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)


def admin_get(route, token=None):
    headers = {"Authorization": "Bearer " + token}
    response = requests.get(url + route, headers=headers)
    if response.status_code == 200:
        json = response.json()
        print(json)
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)


def get(route, token=None):
    headers = {"Authorization": "Bearer " + token}
    response = requests.get(url + route, headers=headers)
    if response.status_code == 200:
        json = response.json()
        print(json)
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)


def post(route, token=None, payload=None):
    headers = {"Authorization": "Bearer " + token}
    response = requests.post(url + route, headers=headers, json=payload)
    if response.status_code == 200:
        json = response.json()
        print(json)
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)


def delete(route, token=None):
    headers = {"Authorization": "Bearer " + token}
    response = requests.delete(url + route, headers=headers)
    if response.status_code == 200:
        json = response.json()
        print(json)
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)


def home():
    response = requests.get(url)
    json = response.json()
    if response.status_code == 200:
        print(json)
    else:
        print("Error: " + str(response.status_code) + " - " + response.reason)


def send_message(ws, sender, to=None):
    time.sleep(2)
    for i in range(15):

        if to is None or len(to) == 0:
            data = {"to": "", "data": "to_all_" + str(i)}
        else:
            data = {"to": to,
                    "data": sender + "_to_" + ''.join(to) + "_" + str(i)}

        try:
            ws.send(json.dumps(data))
        except websocket.WebSocketConnectionClosedException:
            print("connection closed.")
            break

        time.sleep(0.25)

    print(sender + " send message done.")
    ws.close()
    completes[sender] = True


def on_user_open(ws):
    t = threading.Thread(target=send_message, args=[ws, "kevin", ["admin"]])
    t.start()


def on_admin_open(ws):
    t = threading.Thread(target=send_message, args=[ws, "admin"])
    t.start()


def on_message(ws, message):
    data = json.loads(message)
    print("From [" + data["from"] + "]: " + data["data"])


def on_close(ws, close_status_code, close_msg):
    print("on_close: " + str(close_status_code) + " - " + close_msg)


# def on_error(ws, error):
#     print("on_error")


def user_thread(route, token):
    ws = websocket.WebSocketApp(wsurl + route + "?token=" + token,
                                on_open=on_user_open,
                                on_message=on_message,
                                # on_error=on_error,
                                on_close=on_close)
    ws.run_forever()


def admin_thread(route, token):
    ws = websocket.WebSocketApp(wsurl + route + "?token=" + token,
                                on_open=on_admin_open,
                                on_message=on_message,
                                # on_error=on_error,
                                on_close=on_close)
    ws.run_forever()


if __name__ == '__main__':
    home()

    login_payload = {"username": "kevin", "password": "123456"}
    user_token = login("/api/user/login", login_payload)

    print("Token: " + user_token)

    user_put("/api/user/me", user_token)
    user_get("/api/user/me", user_token)

    admin_payload = {"username": "admin", "password": "123456"}
    admin_token = login("/api/admin/login", admin_payload)

    admin_get("/api/admin/users", admin_token)
    admin_get("/api/admin/sessions", admin_token)

    room = "kevin_room"
    admin_post_payload = {"name": room,
                          "creator": "kevin"}

    post("/api/admin/room/%s" % room, admin_token, admin_post_payload)

    get("/api/admin/rooms", admin_token)

    completes["kevin"] = False
    threading.Thread(target=user_thread, args=["/ws/room/%s" % room,
                                               user_token]).start()

    time.sleep(1)

    completes["admin"] = False
    threading.Thread(target=admin_thread, args=["/ws/room/%s" % room,
                                                admin_token]).start()

    time.sleep(7)
    delete("/api/admin/room/%s" % room, admin_token)

    while not completes["kevin"] or not completes["admin"]:
        # get("/api/admin/rooms", admin_token)
        get("/api/admin/room/%s" % room, admin_token)
        time.sleep(1)

    # delete("/api/admin/room/%s" % room, admin_token)
    get("/api/admin/rooms", admin_token)
    print("Done.")
