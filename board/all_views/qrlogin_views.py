import os
import json
import requests
import uuid
from django.utils import timezone
from urllib import parse
from django.http import JsonResponse
from utils.utils_request import (
    BAD_METHOD,
    request_failed,
    request_success,
    return_field,
)
from board.models import (
    User,
    Journal,
)
from . import feishu_utli
import dotenv

dotenv.load_dotenv()

# get env
APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
LARK_PASSPORT_HOST = "https://passport.feishu.cn/suite/passport/oauth/"


def qr_login(request):
    request_body = request.body
    # init config
    qrLogin = QrLogin(APP_ID, APP_SECRET, LARK_PASSPORT_HOST)

    # get token
    tokenInfo = qrLogin.get_token_info(json_param=json.loads(request_body.decode()))

    # get user
    qrUserInfo = qrLogin.get_user_info()

    if not tokenInfo and qrUserInfo:
        response = {"code": -1, "msg": "扫描二维码获取用户信息"}
        return JsonResponse(response, safe=False)
    # response = {"code": 0, "msg": "get userinfo success", "tokenInfo": tokenInfo,
    #                 "qrUserInfo": qrUserInfo}

    # return JsonResponse(response, safe=False)
    feishu_name = qrUserInfo["name"]
    user = User.objects.filter(feishu_name=feishu_name).first()
    # check if the user exists
    if not user:
        return request_failed(
            2,
            "提供的飞书用户未绑定用户",
            status_code=400,
        )
    if user.lock == True:
        return request_failed(
            3,
            "您已被锁定",
            status_code=400,
        )
    while True:
        session_index = str(uuid.uuid4())
        conflictUser = User.objects.filter(
            session=session_index.replace("-", "")
        ).first()
        if not conflictUser:
            break
    user.session = session_index.replace("-", "")
    user.feishu_open_id = qrUserInfo["openId"]
    user.save()
    return_data = {"data": return_field(user.serialize(), ["session", "character"])}
    if user.feishu_name != "":
        feishu_utli.send(user, "您刚刚登录了启源资产管理系统!")
    time = timezone.now()
    prefix = ""
    if user.character == 1:
        prefix = "用户"
    elif user.character == 2:
        prefix = "资产管理员"
    elif user.character == 3:
        prefix = "系统管理员"
    elif user.character == 4:
        prefix = "尊贵的超级管理员"
    message = f"{prefix} [{str(user.name)}] 登录了启源资产管理系统"
    journal = Journal(
        time=time + timezone.timedelta(hours=8),
        user=user,
        operation_type=1,
        object_type=1,
        object_name=user.name,
        message=message,
        entity=user.entity,
    )
    journal.save()
    user.entity.add_log_journal(journal.serialize())
    return request_success(return_data)


class QrLogin(object):
    def __init__(self, app_id, app_secret, lark_passport_host):
        self.lark_passport_host = lark_passport_host
        self.app_id = app_id
        self.app_secret = app_secret
        self._token_info = {}
        self._user_info = {}

    def get_token_info(self, json_param):
        authcode = json_param.get("code", 0)
        if authcode == 0:
            return {}

        headers = {"Content-Type": "application/json"}

        param = {
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": json_param.get("redirect_uri", 0),
            "code": authcode,
        }

        token_res = json.loads(
            requests.post(self._gen_url(uri="token"), param, headers).text
        )

        tokenInfo = {
            "accessToken": token_res.get("access_token"),
            "refreshToken": token_res.get("refresh_token"),
            "tokenType": token_res.get("token_type"),
        }

        self._token_info = tokenInfo
        return tokenInfo

    def get_user_info(self):
        header = {}
        qrUserInfo = {}

        header["Content-Type"] = "application/json;charset=UTF-8"
        header["Authorization"] = "%s %s" % (
            self._token_info.get("tokenType"),
            self._token_info.get("accessToken"),
        )
        try:
            qr_login_user = requests.get(
                url=self._gen_url(uri="userinfo"), headers=header
            ).text
        except Exception as e:
            print(e)
            return {}
        userInfoObj = json.loads(qr_login_user)
        qrUserInfo["name"] = userInfoObj.get("name")
        qrUserInfo["openId"] = userInfoObj.get("open_id")
        qrUserInfo["userId"] = userInfoObj.get("user_id")
        qrUserInfo["tenantKey"] = userInfoObj.get("tenant_key")
        qrUserInfo["avatarUrl"] = userInfoObj.get("avatar_url")
        qrUserInfo["picture"] = userInfoObj.get("picture")

        self._user_info = qrUserInfo
        return qrUserInfo

    def _gen_url(self, uri):
        return "{}{}".format(self.lark_passport_host, uri)
