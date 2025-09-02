import json
import uuid
import requests
from board.models import User
import os
import dotenv

dotenv.load_dotenv()

APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")


def send(user: User, msg: str):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    payload = json.dumps(payload)
    response = json.loads(
        requests.request("POST", url, headers=headers, data=payload).text
    )
    tenant_access_token = response.get("tenant_access_token")
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": "open_id"}
    msgContent = {
        "text": msg,
    }
    req = {
        "receive_id": user.feishu_open_id,
        "msg_type": "text",
        "content": json.dumps(msgContent),
    }
    payload = json.dumps(req)
    headers = {
        "Authorization": "Bearer " + tenant_access_token,  # your access token
        "Content-Type": "application/json",
    }
    response = requests.request(
        "POST", url, params=params, headers=headers, data=payload
    )


def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    payload = json.dumps(payload)
    response = json.loads(
        requests.request("POST", url, headers=headers, data=payload).text
    )
    tenant_access_token = response.get("tenant_access_token")
    return tenant_access_token


def get_user_id(phone: str):
    tenant_access_token = get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
    params = {"user_id_type": "user_id"}
    headers = {
        "Authorization": "Bearer " + tenant_access_token,  # your access token
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {"mobiles": [phone]}
    payload = json.dumps(payload)
    response = json.loads(
        requests.request("POST", url, params=params, headers=headers, data=payload).text
    )
    return response["data"]["user_list"][0]["user_id"]


def send_approval_success(user: User, header: str, msg: str):
    user_id = get_user_id(user.feishu_phone)
    session_index = str(uuid.uuid4())
    session = session_index.replace("-", "")
    url = "https://www.feishu.cn/approval/openapi/v1/message/send"
    tenant_access_token = get_tenant_access_token()
    headers = {
        "Authorization": "Bearer " + tenant_access_token,  # your access token
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "template_id": "1005",
        "user_id": user_id,
        "uuid": session,
        "approval_name": "@i18n@1",
        "content": {"summaries": [{"summary": "@i18n@2"}]},
        "actions": [
            {
                "action_name": "DETAIL",
                "url": " http://okok-am-frontend-okok.app.secoder.net/login",
                "android_url": "http://okok-am-frontend-okok.app.secoder.net/login",
                "ios_url": "http://okok-am-frontend-okok.app.secoder.net/login",
                "pc_url": "http://okok-am-frontend-okok.app.secoder.net/login",
            }
        ],
        "i18n_resources": [
            {
                "locale": "zh-CN",
                "is_default": True,
                "texts": {
                    "@i18n@1": header,
                    "@i18n@2": msg,
                },
            }
        ],
    }
    payload = json.dumps(payload)
    response = json.loads(
        requests.request("POST", url, headers=headers, data=payload).text
    )
    message_id = response["data"]["message_id"]
    return message_id


def recieve_pending_approval(user: User, approval_type: str, initiator: User, msg: str):
    user_id = get_user_id(user.feishu_phone)
    initiator_user_id = get_user_id(initiator.feishu_phone)
    session_index = str(uuid.uuid4())
    session = session_index.replace("-", "")
    url = "https://www.feishu.cn/approval/openapi/v1/message/send"
    tenant_access_token = get_tenant_access_token()
    headers = {
        "Authorization": "Bearer " + tenant_access_token,  # your access token
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "template_id": "1008",
        "user_id": user_id,
        "uuid": session,
        "approval_name": "@i18n@1",
        "title_user_id": initiator_user_id,
        "title_user_id_type": "user_id",
        "content": {"summaries": [{"summary": "@i18n@2"}]},
        "actions": [
            {
                "action_name": "DETAIL",
                "url": " http://okok-am-frontend-okok.app.secoder.net/login",
                "android_url": "http://okok-am-frontend-okok.app.secoder.net/login",
                "ios_url": "http://okok-am-frontend-okok.app.secoder.net/login",
                "pc_url": "http://okok-am-frontend-okok.app.secoder.net/login",
            }
        ],
        "action_configs": [
            {
                "action_type": "APPROVE",
                "action_name": "@i18n@4",
                "is_need_reason": True,
                "is_reason_required": False,
                "is_need_attachment": False,
                "next_status": "APPROVED",
            },
            {
                "action_type": "REJECT",
                "action_name": "@i18n@5",
                "is_need_reason": True,
                "is_reason_required": False,
                "is_need_attachment": False,
                "next_status": "REJECTED",
            },
        ],
        "action_callback": {
            "action_callback_url": "http://okok-am-backend-okok.app.secoder.net/feishu_approval",
            "action_callback_token": "sdjkljkx9lsadf110",
            "action_context": "abaaba",
        },
        "i18n_resources": [
            {
                "locale": "zh-CN",
                "is_default": True,
                "texts": {
                    "@i18n@1": approval_type,
                    "@i18n@2": msg,
                    "@i18n@3": "DETAIL",
                    "@i18n@4": "同意",
                    "@i18n@5": "拒绝",
                },
            }
        ],
    }
    payload = json.dumps(payload)
    response = json.loads(
        requests.request("POST", url, headers=headers, data=payload).text
    )
    message_id = response["data"]["message_id"]
    return message_id


def update_pending_approval(message_id: str, type: any):
    url = "https://www.feishu.cn/approval/openapi/v1/message/update"
    tenant_access_token = get_tenant_access_token()
    headers = {
        "Authorization": "Bearer " + tenant_access_token,
        "Content-Type": "application/json; charset=utf-8",
    }
    if type == 1:
        payload = {
            "message_id": message_id,
            "status": "APPROVED",
        }
    elif type == 2:
        payload = {
            "message_id": message_id,
            "status": "REJECTED",
        }
    payload = json.dumps(payload)
    response = json.loads(
        requests.request("POST", url, headers=headers, data=payload).text
    )
    message_id = response["data"]["message_id"]
    return message_id


def get_user(phone: str):
    tenant_access_token = get_tenant_access_token()
    user_id = get_user_id(phone)
    url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}?department_id_type=open_department_id&user_id_type=user_id"
    payload = ""
    headers = {"Authorization": "Bearer " + tenant_access_token}
    response = json.loads(
        requests.request("GET", url, headers=headers, data=payload).text
    )
    return response["data"]["user"]["name"]


def get_entity_users():
    tenant_access_token = get_tenant_access_token()
    url = "https://open.feishu.cn/open-apis/contact/v3/users/find_by_department?department_id=0&department_id_type=open_department_id&page_size=10&user_id_type=open_id"
    payload = ""
    headers = {"Authorization": "Bearer " + tenant_access_token}
    response = json.loads(
        requests.request("GET", url, headers=headers, data=payload).text
    )
    users = []
    for i in response["data"]["items"]:
        users.append((i["name"], i["mobile"]))
    return users
