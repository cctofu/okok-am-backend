from datetime import date
from datetime import datetime, time, timedelta

# from pytz import timezone
# from time import sleep
# from datetime import datetime, time, timedelta
from django.test import TestCase, Client
from django.db.models import F
from django.urls import reverse
from board.models import (
    Entity,
    User,
    Department,
    PendingRequests,
    Asset,
    AssetTree,
    URL,
    Journal,
    AsyncTasks,
    AssetStatistics,
)
from django.utils import timezone
from . import feishu_test
import time

verify_check = [0]


def depreciation_job():
    # global signal
    all_valid_len = Asset.objects.count()
    start = 0
    end = 500
    while True:
        all_valid_assets = Asset.objects.all()[start:end]
        for valid_asset in all_valid_assets:
            if valid_asset.count > 0 and valid_asset.expire == 0:
                valid_asset.auto_depreciation()
        # print(f"Depreciation job ROUND [{end / 500}] done !")
        if end >= all_valid_len:
            break
        start += 500
        end += 500
        # sleep(1)

    # print(
    #     f"OK, all valid assets in the database have been depreciated automatically by Luca1K's ROBOT at :)"
    # )
    # signal = 1


def statistics_job():
    start = 0
    end = 100

    all_departments = Department.objects.all()
    cnt_dict_item = {f"{department.name}": 0 for department in all_departments}
    pri_dict_item = {f"{department.name}": 0.00 for department in all_departments}
    cnt_dict_amount = {f"{department.name}": 0 for department in all_departments}
    pri_dict_amount = {f"{department.name}": 0.00 for department in all_departments}

    tot_length = Asset.objects.count()
    start = 0
    end = 100

    while True:
        cur_round_assets = Asset.objects.all()[start:end]
        for a in cur_round_assets:
            if a.count == 0 or a.expire == 1:
                continue
            AssetStatistics.objects.create(
                asset=a,
                cur_department=a.department,
                cur_user=a.user,
                cur_price=a.price,
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=a.status if a.expire == 0 else 0,
                cur_count=a.count,
            )
            if a.assetClass == 0:
                # print(f"okokok={a.count};hahahah={a.price}")
                cnt_dict_item[a.department.name] += 1
                pri_dict_item[a.department.name] += float(a.price)
                # print(f"cnt_dict_item: {cnt_dict_item}")
                # print(f"pri_dict_item: {pri_dict_item}")
            else:
                # print(f"okokok={a.count};hahahah={a.price}")
                cnt_dict_amount[a.department.name] += a.count
                pri_dict_amount[a.department.name] += float(a.price) * float(a.count)
                # print(f"cnt_dict_amount: {cnt_dict_amount}")
                # print(f"pri_dict_amount: {pri_dict_amount}")

        # sleep(1)
        if end >= tot_length:
            break
        start += 100
        end += 100

    for dp in all_departments:
        dp_name = dp.name
        # print(dp_name)
        AssetStatistics.objects.create(
            asset=None,
            cur_department=dp,
            cur_user=None,
            cur_price=pri_dict_item[dp_name],
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=529113,
            cur_count=cnt_dict_item[dp_name],
        )
        AssetStatistics.objects.create(
            asset=None,
            cur_department=dp,
            cur_user=None,
            cur_price=pri_dict_amount[dp_name],
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=511529,
            cur_count=cnt_dict_amount[dp_name],
        )
        AssetStatistics.objects.create(
            asset=None,
            cur_department=dp,
            cur_user=None,
            cur_price=pri_dict_item[dp_name] + pri_dict_amount[dp_name],
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=501113,
            cur_count=cnt_dict_item[dp_name] + cnt_dict_amount[dp_name],
        )
    # print(
    #     f"OK, asset statistics have been made for all assets in the database automatically by Luca1K's ROBOT :)"
    # )
    # print(f"cnt_dict: {cnt_dict_amount}")
    # print(f"pri_dict: {pri_dict_amount}")


# time_zone = timezone("Asia/Shanghai")
# Life is hard, why not do something just for FUN ?
class TestForFun(TestCase):
    def setUp(self):
        self.client = Client()

    def test_okok_start(self):
        url = reverse("startup")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Congratulations! You have successfully installed the requirements. Go ahead!",
        )


class ModelTests(TestCase):
    def setUp(self):
        self.entity = Entity.objects.create(name="Mojang")
        self.department = Department.objects.create(
            entity=self.entity, name="RedstoneDepartment"
        )
        self.user = User.objects.create(
            name="Luca1K",
            password="05290113",
            entity=self.entity,
            department=self.department,
            character=4,
            lock=False,
            session="",
            email="luca1k@mails.thucst.cn",
        )
        self.asset = Asset.objects.create(
            name="DiamondSword",
            assetClass=1,
            user=self.user,
            price=5.0,
            description="A powerful weapon",
            position="Luca1K's bag",
            expire=0,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        )
        self.request = PendingRequests.objects.create(
            initiator=self.user,
            asset=self.asset,
            type=1,
            result=0,
            request_time=timezone.now(),
            review_time=timezone.now(),
        )
        self.journal = Journal.objects.create(
            user=self.user,
            time=timezone.now(),
            operation_type=1,
            object_type=1,
            object_name=self.user.name,
            message="",
        )

    def test_entity_model(self):
        entity = Entity.objects.get(id=self.entity.id)
        self.assertEqual(entity.name, "Mojang")

    def test_department_model(self):
        department = Department.objects.get(id=self.department.id)
        self.assertEqual(department.name, "RedstoneDepartment")
        self.assertEqual(department.entity.name, "Mojang")

    def test_user_model(self):
        user = User.objects.get(id=self.user.id)
        self.assertEqual(user.name, "Luca1K")
        self.assertEqual(user.password, "05290113")
        self.assertEqual(user.entity.name, "Mojang")
        self.assertEqual(user.department.name, "RedstoneDepartment")
        self.assertEqual(user.character, 4)
        self.assertEqual(user.lock, False)
        self.assertEqual(user.session, "")
        self.assertEqual(user.email, "luca1k@mails.thucst.cn")

    def test_asset_model(self):
        asset = Asset.objects.get(id=self.asset.id)
        self.assertEqual(asset.name, "DiamondSword")
        self.assertEqual(asset.assetClass, 1)
        self.assertEqual(asset.user.name, "Luca1K")
        self.assertEqual(asset.price, 5.0)
        self.assertEqual(asset.description, "A powerful weapon")
        self.assertEqual(asset.position, "Luca1K's bag")
        self.assertEqual(asset.expire, 0)

    def test_pending_requests_model(self):
        request = PendingRequests.objects.get(id=self.request.id)
        self.assertEqual(request.initiator.name, "Luca1K")
        self.assertEqual(request.asset.name, "DiamondSword")
        self.assertEqual(request.type, 1)
        self.assertEqual(request.result, 0)
        self.assertEqual(request.request_time.date(), timezone.now().date())
        self.assertEqual(request.review_time.date(), timezone.now().date())

    def test_journal(self):
        journal = Journal.objects.get(id=self.journal.id)
        self.assertEqual(journal.user.name, "Luca1K")
        self.assertEqual(journal.time.date(), timezone.now().date())
        self.assertEqual(journal.operation_type, 1)
        self.assertEqual(journal.object_type, 1)
        self.assertEqual(journal.object_name, "Luca1K")


class URLModelTest(TestCase):
    def setUp(self):
        self.entity = Entity.objects.create(name="Mojang")
        self.url = URL.objects.create(
            url="https://www.minecraft.net/",
            name="MineCraft",
            entity=self.entity,
        )

    def test_url_creation(self):
        self.assertEqual(self.url.url, "https://www.minecraft.net/")
        self.assertEqual(self.url.name, "MineCraft")
        self.assertEqual(self.url.authority_level, 1)
        self.assertEqual(self.url.entity, self.entity)

    def test_url_serialization(self):
        expected = {
            "id": self.url.id,
            "url": self.url.url,
            "name": self.url.name,
            "authority_level": self.url.authority_level,
            "entity": self.entity.name,
        }
        self.assertEqual(self.url.serialize(), expected)

    def test_url_string_representation(self):
        self.assertEqual(str(self.url), "MineCraft")


class MainTests(TestCase):
    # Initializer
    def setUp(self):
        entity1 = Entity(name="a")
        entity1.save()
        entity2 = Entity(name="gaybar")
        entity2.save()
        department1 = Department(name="b", entity=entity1, parent=None, userNumber=2)
        department1.save()
        user1 = User.objects.create(
            name="liusn",
            password="114514",
            entity=entity1,
            department=department1,
            character=1,
            lock=False,
            session="",
            email="",
        )
        user1.save()
        user2 = User.objects.create(
            name="manager",
            password="1919810",
            character=4,
            lock=False,
            session="",
            email="",
        )
        user2.save()
        user3 = User.objects.create(
            name="jinjin",
            password="bjzyydx",
            character=1,
            lock=False,
            session="",
            email="lqll@mails.cn",
            entity=entity1,
            department=department1,
        )
        user3.save()
        user4 = User.objects.create(
            name="xlx",
            password="sbop",
            character=3,
            lock=False,
            session="",
            email="mihoyo@sb.op",
            entity=entity2,
        )
        user4.save()

    # Utility functions
    def post_user(
        self,
        user_name,
        password,
        entity,
        department,
        character,
        lock,
        session_id,
        email,
        session,
    ):
        payload = {
            "name": user_name,
            "password": password,
            "entity": entity,
            "department": department,
            "character": character,
            "lock": lock,
            "session": session_id,
            "email": email,
        }
        return self.client.post(
            f"/user/{session}",
            data=payload,
            content_type="application/json",
        )

    def put_user(
        self,
        id,
        password,
        lock,
        session,
    ):
        payload = {
            "id": id,
            "password": password,
            "lock": lock,
        }
        return self.client.put(
            f"/user/{session}",
            data=payload,
            content_type="application/json",
        )

    def get_user_list(self, session, page):
        return self.client.get(f"/user_list_all/{session}/{page}")

    def user_login(self, identity, password):
        payload = {
            "identity": identity,
            "password": password,
        }
        return self.client.post(
            "/login",
            data=payload,
            content_type="application/json",
        )

    def user_logout(self, session):
        payload = {
            "session": session,
        }
        return self.client.put(
            "/logout",
            data=payload,
            content_type="application/json",
        )

    def user_character(self, session):
        return self.client.get(f"/character/{session}")

    def post_entity(self, session, name):
        payload = {
            "name": name,
        }
        return self.client.post(
            f"/entity/{session}",
            data=payload,
            content_type="application/json",
        )

    def get_entity(self, session):
        return self.client.get(f"/entity/{session}")

    def put_entity(self, session, id, name):
        payload = {
            "id": id,
            "name": name,
        }
        return self.client.put(
            f"/entity/{session}",
            data=payload,
            content_type="application/json",
        )

    def put_user_password(self, session, password, email):
        payload = {
            "oldpassword": password,
            "newpassword": email,
        }
        return self.client.put(
            f"/user_password/{session}",
            data=payload,
            content_type="application/json",
        )

    def put_user_email(self, session, password, email):
        payload = {
            "oldpassword": password,
            "email": email,
        }
        return self.client.put(
            f"/user_email/{session}",
            data=payload,
            content_type="application/json",
        )

    def get_user_entity(self, session, entity_name, page):
        return self.client.get(f"/user_entity/{session}/{entity_name}/{page}")

    def get_user_entity_2(self, session, page):
        return self.client.get(f"/user_entity4user/{session}/{page}")

    def get_user_department(self, session, department_name, page):
        return self.client.get(f"/user_department/{session}/{department_name}/{page}")

    def get_user_department_2(self, session, department_name):
        return self.client.get(f"/user_department_2/{session}/{department_name}")

    def post_department(self, entity_name, parent_name, name, session):
        payload = {
            "entity": entity_name,
            "parent": parent_name,
            "name": name,
        }
        return self.client.post(
            f"/department/{session}",
            data=payload,
            content_type="application/json",
        )

    def get_all_departments(self, session, entity_name):
        return self.client.get(
            f"/all_departments/{session}/{entity_name}",
            content_type="application/json",
        )

    def get_valid_parent_departments(self, session, department_name):
        return self.client.get(
            f"/valid_parent_departments/{session}/{department_name}",
            contenrt_type="application/json",
        )

    def put_department(self, parent_name, department_name, id, session):
        payload = {
            "parent": parent_name,
            "name": department_name,
            "id": id,
        }
        return self.client.put(
            f"/department/{session}",
            data=payload,
            content_type="application/json",
        )

    def get_department(self, session):
        return self.client.get(f"/department/{session}")

    def get_sub_department(self, session, department_name):
        return self.client.get(f"/sub_department/{session}/{department_name}")

    def get_cur_entity(self, session):
        return self.client.get(f"/cur_entity/{session}")

    def get_user_all(
        self, session, id, name, entity, department, character, lock, page
    ):
        payload = {
            "id": id,
            "name": name,
            "entity": entity,
            "department": department,
            "character": character,
            "lock": lock,
            "page": page,
        }
        return self.client.post(
            f"/get_user_all/{session}",
            data=payload,
            content_type="application/json",
        )

    def get_user_entity1(self, session, id, name, department, character, lock, page):
        payload = {
            "id": id,
            "name": name,
            "department": department,
            "character": character,
            "lock": lock,
            "page": page,
        }
        return self.client.post(
            f"/get_user_entity/{session}",
            data=payload,
            content_type="application/json",
        )

    def get_user_department1(self, session, id, name, character, lock, page):
        payload = {
            "id": id,
            "name": name,
            "character": character,
            "lock": lock,
            "page": page,
        }
        return self.client.post(
            f"/get_user_department/{session}",
            data=payload,
            content_type="application/json",
        )

    def post_logjournal1(self, session, entity_name, date, info, name, page):
        payload = {"date": date, "info": info, "name": name, "page": page}
        return self.client.post(
            f"/get_logjournal/{session}/{entity_name}",
            data=payload,
            content_type="application/json",
        )

    def post_operationjournal1(
        self, session, entity_name, date, info, change, name, page
    ):
        payload = {
            "date": date,
            "info": info,
            "change": change,
            "name": name,
            "page": page,
        }
        return self.client.post(
            f"/get_operationjournal/{session}/{entity_name}",
            data=payload,
            content_type="application/json",
        )

    def delete_department(self, session, department_name):
        return self.client.delete(f"/department/{session}/{department_name}")

    def get_logjournal(self, session, entity_name, page):
        return self.client.get(f"/logjournal/{session}/{entity_name}/{page}")

    def get_operationjournal(self, session, entity_name, page):
        return self.client.get(f"/operationjournal/{session}/{entity_name}/{page}")

    def put_feishu_name(self, session, feishu_name, feishu_phone):
        payload = {"feishu_name": feishu_name, "feishu_phone": feishu_phone}
        return self.client.put(
            f"/feishu_name/{session}",
            data=payload,
            content_type="application/json",
        )

    def feishu_users(self, session):
        payload = ""
        return self.client.post(
            f"/feishu_users/{session}",
            data=payload,
            content_type="application/json",
        )

    def test_get_valid_parent_departments(self):
        pokemon = Entity.objects.create(name="Pokemon")
        Kanto = Department.objects.create(
            name="Kanto", entity=pokemon, parent=None, userNumber=20020529
        )
        Johto = Department.objects.create(
            name="Johto", entity=pokemon, parent=Kanto, userNumber=20190501
        )
        Hoenn = Department.objects.create(
            name="Hoenn", entity=pokemon, parent=Johto, userNumber=20200708
        )
        Sinnoh = Department.objects.create(
            name="Sinnoh", entity=pokemon, parent=Hoenn, userNumber=20221226
        )
        Unova = Department.objects.create(
            name="Unova", entity=pokemon, parent=Sinnoh, userNumber=20230113
        )
        XiaoYue = User.objects.create(
            name="cutestYue",
            password="mysister",
            entity=pokemon,
            department=None,
            character=3,
            lock=False,
            session="",
            email="HeiFentz@pokemmo.com",
        )
        self.user_login("cutestYue", "mysister")
        XiaoYue.refresh_from_db()
        res = self.get_valid_parent_departments("XiaoYue", "Kanto")
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_valid_parent_departments(
            "XiaoYueYueXiaoYueYueXiaoYueYueOK", "Kanto"
        )
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_valid_parent_departments(XiaoYue.session, "XGD")
        self.assertEqual(
            res.json()["info"],
            "当前部门不存在",
        )
        res = self.get_valid_parent_departments(XiaoYue.session, "Kanto")
        self.assertEqual(
            res.json()["data"],
            [],
        )
        res = self.get_valid_parent_departments(XiaoYue.session, "Johto")
        self.assertEqual(
            res.json()["data"],
            [],
        )
        res = self.get_valid_parent_departments(XiaoYue.session, "Hoenn")
        self.assertEqual(
            res.json()["data"],
            [{"id": 2, "name": "Kanto"}],
        )
        res = self.get_valid_parent_departments(XiaoYue.session, "Sinnoh")
        self.assertEqual(
            res.json()["data"],
            [{"id": 2, "name": "Kanto"}, {"id": 3, "name": "Johto"}],
        )
        res = self.get_valid_parent_departments(XiaoYue.session, "Unova")
        self.assertEqual(
            res.json()["data"],
            [
                {"id": 2, "name": "Kanto"},
                {"id": 3, "name": "Johto"},
                {"id": 4, "name": "Hoenn"},
            ],
        )

    # Now start testcases.
    def test_post_logjournal1(self):
        entity1 = Entity.objects.filter(name="a").first()
        user5 = User.objects.create(
            name="lsn",
            password="114514",
            entity=entity1,
            character=3,
            lock=False,
            session="",
            email="",
        )
        user5.save()
        res = self.user_login("lsn", "114514")
        session = res.json()["data"]["session"]
        self.user_login("jinjin", "bjzyydx")
        self.user_login("liusn", "114514")
        res = self.post_logjournal1(session, "a", "", "", "", "")
        res = self.post_logjournal1(session, "a", "", "", "", "1")
        res = self.post_logjournal1(session, "a", "2023-05-17", "", "", "1")
        res = self.post_logjournal1(session, "a", "2023-05-17", "登录", "", "1")
        res = self.post_logjournal1(session, "a", "2023-05-17", "登录", "", "1")
        res = self.post_logjournal1(session, "a", "2023-05-17", "登录", "j", "1")

    def test_post_operationjournal1(self):
        entity1 = Entity.objects.filter(name="a").first()
        user5 = User.objects.create(
            name="lsn",
            password="114514",
            entity=entity1,
            character=3,
            lock=False,
            session="",
            email="",
        )
        user5.save()
        res = self.user_login("lsn", "114514")
        session = res.json()["data"]["session"]
        self.post_department("a", "", "cst", session)
        self.delete_department(session, "cst")
        self.post_department("a", "", "kon", session)
        self.delete_department(session, "kon")
        res = self.post_operationjournal1(session, "a", "", "", "", "", "")
        res = self.post_operationjournal1(session, "a", "", "", "", "", "1")
        self.assertEqual(len(res.json()["data"]), 4)
        res = self.post_operationjournal1(session, "a", "2023-05-17", "", "", "", "1")
        res = self.post_operationjournal1(session, "a", "2023-05-17", "创建", "", "", "1")
        res = self.post_operationjournal1(
            session, "a", "2023-05-17", "删除", "", "l", "1"
        )
        res = self.post_operationjournal1(
            session, "a", "2023-05-17", "删除", "cst", "l", "1"
        )

    def test_get_user_all(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.get_user_all(session, "", "", "", "", "", "", "1")
        self.assertEqual(len(res.json()["data"]), 4)
        res = self.get_user_all(session, "", "", "", "", "1", "", "1")
        self.assertEqual(len(res.json()["data"]), 2)
        res = self.get_user_all(session, "", "l", "", "", "1", "", "1")
        self.assertEqual(len(res.json()["data"]), 1)
        res = self.get_user_all(session, "", "", "a", "b", "", "0", "1")
        self.assertEqual(len(res.json()["data"]), 2)

    def test_get_user_entity1(self):
        entity1 = Entity.objects.filter(name="a").first()
        user5 = User.objects.create(
            name="lsn",
            password="114514",
            entity=entity1,
            character=3,
            lock=False,
            session="",
            email="",
        )
        user5.save()
        user5.refresh_from_db()
        res = self.user_login("lsn", "114514")
        session = res.json()["data"]["session"]
        res = self.get_user_entity1(session, "", "", "", "", "", "1")
        self.assertEqual(len(res.json()["data"]), 3)
        res = self.get_user_entity1(session, "", "", "", "1", "", "1")
        self.assertEqual(len(res.json()["data"]), 2)
        res = self.get_user_entity1(session, "", "j", "", "1", "", "1")
        self.assertEqual(len(res.json()["data"]), 1)
        res = self.get_user_entity1(session, "", "", "b", "", "0", "1")
        self.assertEqual(len(res.json()["data"]), 2)

    def test_get_user_department1(self):
        entity1 = Entity.objects.filter(name="a").first()
        department1 = Department.objects.filter(name="b").first()
        user5 = User.objects.create(
            name="lsn",
            password="114514",
            entity=entity1,
            department=department1,
            character=2,
            lock=False,
            session="",
            email="",
        )
        user5.save()
        res = self.user_login("lsn", "114514")
        session = res.json()["data"]["session"]
        res = self.get_user_department1(session, "", "", "", "", "1")
        self.assertEqual(len(res.json()["data"]), 3)
        res = self.get_user_department1(session, "", "", "1", "", "1")
        self.assertEqual(len(res.json()["data"]), 2)
        res = self.get_user_department1(session, "", "j", "1", "", "1")
        self.assertEqual(len(res.json()["data"]), 1)
        res = self.get_user_department1(session, "", "l", "", "0", "1")
        self.assertEqual(len(res.json()["data"]), 2)

    def test_log(self):
        res = self.user_login("liusn_gay", "gay")
        self.assertEqual(
            res.json()["info"],
            "用户名或密码错误",
        )
        res = self.user_login("liusn", "gay")
        self.assertEqual(
            res.json()["info"],
            "用户名或密码错误",
        )
        res = self.user_login("liusn", "114514")
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(res.status_code, 200)
        session_id = res.json()["data"]["session"]
        self.assertNotEqual(session_id, "")
        self.assertTrue(User.objects.filter(session=session_id).exists())  # test login
        user1 = User.objects.filter(name="liusn").first()
        session_id1 = user1.session
        self.assertNotEqual(session_id1, "")
        res1 = self.user_logout(session_id1)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.assertFalse(
            User.objects.filter(session=session_id1).exists()
        )  # test logout

    def test_change_information(self):
        res = self.user_login("liusn", "114514")
        session = res.json()["data"]["session"]
        res = self.user_login("manager", "1919810")
        session1 = res.json()["data"]["session"]
        user = User.objects.filter(session=session).first()
        user1 = User.objects.filter(session=session1).first()
        res = self.put_user_password(session, user.password, "abaaba")
        self.assertEqual(res.json()["code"], 0)
        user = User.objects.filter(session=session).first()
        self.assertEqual(user.password, "abaaba")
        res = self.put_user_password(session, "lalala", "abaaba")
        self.assertEqual(res.json()["code"], 2)
        res = self.put_user_email(session, user.password, "sb@1.com")
        self.assertEqual(res.json()["code"], 0)
        res = self.put_user_email(session1, user1.password, "sb@1.com")
        self.assertEqual(res.json()["code"], 5)

    def test_post_user(self):
        res = self.user_login("manager", "1919810")
        manager = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.user_login("xlx", "sbop")
        xlx_op = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_all_departments(manager.session, "a")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.get_all_departments(xlx_op.session, "b")
        self.assertEqual(
            res.json()["data"],
            [],
        )
        res = self.get_all_departments(jinjin.session, "b")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.post_user(
            "xupynantong",
            "gay",
            "a",
            "",
            3,
            False,
            "",
            "gaybar@vip.net",
            "Luca_Hacker",
        )
        self.assertEqual(res.json()["info"], "用户的会话标识符信息不正确")
        res = self.post_user(
            "xupynantong",
            "gay",
            "a",
            "",
            3,
            False,
            "",
            "gaybar@vip.net",
            "gggggggggggggggggggggggggggggggg",
        )
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.post_user(
            "xupynantong",
            "gay",
            "a",
            "",
            3,
            False,
            "",
            "gaybar@vip.net",
            jinjin.session,
        )
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.post_user(
            "xupysb",
            "zhubi",
            "a",
            "",
            3,
            False,
            "",
            "gaybar@vip.net",
            xlx_op.session,
        )
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.post_user(
            "阿",
            "1919810",
            "a",
            "",
            3,
            False,
            "",
            "satoshi@pikachu.poke",
            manager.session,
        )
        self.post_user(
            "阿巴",
            "1919810",
            "",
            "",
            4,
            False,
            "",
            "",
            manager.session,
        )
        res = self.post_user(
            "阿巴阿巴",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            manager.session,
        )
        self.assertEqual(res.json()["code"], 0)
        user = User.objects.filter(name="阿巴阿巴").first()
        self.assertNotEqual(user, None)
        self.assertEqual(user.password, "1919810")
        department = Department.objects.filter(name="b").first()
        self.assertEqual(department.userNumber, 3)
        entity2 = Entity(name="PKU")
        entity2.save()
        department2 = Department(name="cst", entity=entity2)
        department2.save()
        res = self.post_user(
            "bababa",
            "ababab",
            "PKU",
            "cst",
            1,
            False,
            "",
            "",
            manager.session,
        )
        self.assertEqual(res.json()["code"], 0)
        user = User.objects.filter(name="bababa").first()
        self.assertNotEqual(user, None)
        self.assertEqual(user.department.name, "cst")

    def test_get_user(self):
        res = self.user_login("manager", "1919810")
        manager = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_user_list(manager.session, 1)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["data"]), 4)
        self.assertEqual(res.json()["data"][0]["name"], "liusn")
        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_user_list(jinjin.session, 1)
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        res = self.user_login("xlx", "sbop")
        xlx_op = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_user_list(xlx_op.session, 1)
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        res = self.get_user_list(114514, 1)
        self.assertEqual(
            res.json()["info"],
            "用户的会话标识符信息不正确",
        )
        res = self.get_user_list("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh", 1)
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        self.post_user(
            "阿巴阿巴1",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            manager.session,
        )
        self.post_user(
            "阿巴阿巴2",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            manager.session,
        )
        self.post_user(
            "阿巴阿巴3",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            manager.session,
        )
        res = self.get_user_list(manager.session, 1)
        self.assertEqual(len(res.json()["data"]), 6)
        self.assertEqual(res.json()["pages"], 2)
        res = self.get_user_list(manager.session, 2)
        self.assertEqual(len(res.json()["data"]), 1)

    def test_put_user(self):
        res = self.user_login("manager", "1919810")
        manager = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.put_user(
            1,
            "sbgay",
            False,
            "ggg",
        )
        self.assertEqual(res.json()["info"], "用户的会话标识符信息不正确")
        res = self.put_user(
            1,
            "sbgay",
            False,
            "gggggggggggggggggggggggggggggggg",
        )
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.user_login("xlx", "sbop")
        xlx_op = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.put_user(
            1,
            "sbgay",
            False,
            jinjin.session,
        )
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.put_user(
            1,
            "sbgay",
            False,
            xlx_op.session,
        )
        self.assertEqual(res.json()["info"], "你无此权限")
        entity2 = Entity(name="tsinghua")
        entity2.save()
        res = self.put_user(
            1,
            "111111",
            False,
            manager.session,
        )
        self.assertEqual(res.json()["code"], 0)
        user = User.objects.filter(name="liusn").first()
        self.assertEqual(user.password, "111111")
        res = self.put_user(
            1,
            "",
            True,
            manager.session,
        )
        self.assertEqual(res.json()["code"], 0)
        user = User.objects.filter(name="liusn").first()
        self.assertEqual(user.lock, True)

    def test_character(self):
        res = self.user_login("manager", "1919810")
        user = User.objects.filter(session=res.json()["data"]["session"]).first()
        character = user.character
        res = self.user_character(user.session)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"]["character"], character)

    def test_post_entity(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.post_entity("aa", "mihoyo")
        self.assertEqual(res.json()["info"], "您给出的session ID是非法的。")
        res = self.post_entity("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "mihoyo")
        self.assertEqual(res.json()["info"], "您无此权限")
        res = self.user_login("jinjin", "bjzyydx")
        session1 = res.json()["data"]["session"]
        res = self.post_entity(session1, "mihoyo")
        self.assertEqual(res.json()["info"], "您无此权限")
        res = self.user_login("xlx", "sbop")
        session2 = res.json()["data"]["session"]
        res = self.post_entity(session2, "mihoyo")
        self.assertEqual(res.json()["info"], "您无此权限")
        res1 = self.post_entity(session, "b")
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(Entity.objects.filter(name="b").exists())
        res2 = self.post_entity(session, "a")
        self.assertEqual(res2.json()["code"], 2)
        self.assertEqual(res2.status_code, 400)

    def test_get_entity(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_entity(session, "b")
        self.post_entity(session, "abc")
        res1 = self.get_entity(session)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["data"][0]["name"], "a")
        self.assertEqual(res1.json()["data"][1]["name"], "gaybar")
        self.assertEqual(res1.json()["data"][2]["name"], "b")
        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_entity(jinjin.session)
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_entity(114514)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_entity("ssssssssssssssssssssssssssssssss")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

    def test_put_entity(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.put_entity("aa", 1, "a")
        self.assertEqual(res.json()["info"], "您给出的session ID是非法的。")
        res = self.put_entity("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1, "a")
        self.assertEqual(res.json()["info"], "您无此权限")
        res = self.user_login("jinjin", "bjzyydx")
        session1 = res.json()["data"]["session"]
        res = self.user_login("xlx", "sbop")
        session2 = res.json()["data"]["session"]
        res = self.put_entity(session1, 1, "a")
        self.assertEqual(res.json()["info"], "您无此权限")
        res = self.put_entity(session2, 1, "a")
        self.assertEqual(res.json()["info"], "您无此权限")
        res1 = self.put_entity(session, 1, "a")
        self.assertEqual(res1.json()["code"], 3)
        self.assertEqual(res1.status_code, 400)
        res2 = self.put_entity(session, 114515, "a")
        self.assertEqual(res2.json()["code"], 2)
        self.assertEqual(res2.status_code, 400)
        self.post_entity(session, "qwer")
        res3 = self.put_entity(session, 3, "tsinghua")
        self.assertEqual(res3.json()["code"], 0)
        self.assertEqual(res3.status_code, 200)
        self.assertFalse(Entity.objects.filter(name="qwer").exists())
        self.assertTrue(Entity.objects.filter(name="tsinghua").exists())

    def test_user_entity(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_user(
            "lyq",
            "1919810",
            "a",
            "",
            3,
            False,
            "",
            "",
            session,
        )
        res2 = self.get_user_entity(session, "a", 1)
        self.assertEqual(res2.json()["code"], 0)
        self.assertEqual(res2.status_code, 200)
        user_list1 = res2.json()["data"]
        self.assertEqual(user_list1[0]["name"], "liusn")
        self.assertEqual(user_list1[1]["name"], "jinjin")
        self.post_entity(session, "tsinghua")
        entity1 = Entity.objects.filter(name="tsinghua").first()
        department1 = Department(name="cst", entity=entity1, parent=None)
        department1.save()
        res = self.post_user(
            "xupy",
            "abaaba",
            "tsinghua",
            "",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq1",
            "1919810",
            "a",
            "",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq2",
            "1919810",
            "a",
            "",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq3",
            "1919810",
            "a",
            "",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq4",
            "1919810",
            "a",
            "",
            3,
            False,
            "",
            "",
            session,
        )
        res3 = self.get_user_entity(session, "a", 1)
        res4 = self.get_user_entity(session, "tsinghua", 1)
        self.assertEqual(len(res3.json()["data"]), 6)
        self.assertEqual(res3.json()["pages"], 2)
        self.assertEqual(len(res4.json()["data"]), 1)
        res3 = self.get_user_entity(session, "a", 2)
        self.assertEqual(len(res3.json()["data"]), 1)
        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_user_entity(jinjin.session, "a", 1)
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_user_entity(114514, "a", 1)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_user_entity("ssssssssssssssssssssssssssssssss", "a", 1)
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

    def test_user_entity2(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_user(
            "lyq",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            session,
        )
        user_session = self.user_login("lyq", "1919810").json()["data"]["session"]
        res = self.get_user_entity_2(user_session, 1)
        self.assertEqual(len(res.json()["data"]), 3)
        self.post_user(
            "lyq1",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            session,
        )
        res = self.post_user(
            "lyq2",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            session,
        )
        res = self.post_user(
            "lyq3",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            session,
        )
        res = self.post_user(
            "lyq4",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            session,
        )
        res = self.get_user_entity_2(user_session, 1)
        self.assertEqual(len(res.json()["data"]), 7)

    def test_user_department(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_user(
            "lyq",
            "1919810",
            "a",
            "b",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq1",
            "1919810",
            "a",
            "b",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq2",
            "1919810",
            "a",
            "b",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq3",
            "1919810",
            "a",
            "b",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "lyq4",
            "1919810",
            "a",
            "b",
            3,
            False,
            "",
            "",
            session,
        )
        res2 = self.get_user_department(session, "b", 1)
        self.assertEqual(res2.json()["code"], 0)
        self.assertEqual(res2.status_code, 200)
        user_list1 = res2.json()["data"]
        self.assertEqual(user_list1[0]["name"], "liusn")
        self.assertEqual(user_list1[1]["name"], "jinjin")
        self.assertEqual(len(res2.json()["data"]), 6)
        self.assertEqual(res2.json()["pages"], 2)
        res2 = self.get_user_department(session, "b", 2)
        self.assertEqual(len(res2.json()["data"]), 1)
        entity1 = Entity.objects.filter(name="a").first()
        department1 = Department(name="cst", entity=entity1, parent=None)
        department1.save()
        self.post_user(
            "xupy",
            "abaaba",
            "a",
            "",
            3,
            False,
            "",
            "",
            session,
        )
        self.post_user(
            "xpy21",
            "abaaba",
            "a",
            "cst",
            2,
            False,
            "",
            "",
            session,
        )
        res3 = self.get_user_department(session, "b", 1)
        res4 = self.get_user_department(session, "cst", 1)
        self.assertEqual(len(res3.json()["data"]), 6)
        self.assertEqual(len(res4.json()["data"]), 1)
        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_user_department(jinjin.session, "cst", 1)
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_user_department(114514, "cst", 1)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_user_department("ssssssssssssssssssssssssssssssss", "cst", 1)
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.user_login("jinjin", "bjzyydx")
        session = res.json()["data"]["session"]
        res = self.get_user_department_2("jinjin", "b")
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_user_department_2("xiaoyuechoumeimeihuaimeimeiLOVEU", "b")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_user_department_2(session, "cst")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_user_department_2(session, "b")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

    def test_post_department(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res1 = self.post_department("a", "b", "tsinghua", session)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)  # test post_department succeed
        department = Department.objects.filter(name="b").first()
        self.assertEqual(department.subDepartmentNumber, 1)
        res1 = self.post_department("a", "b", "PKU", session)
        assetTree = AssetTree.objects.filter(name="默认分类", department="PKU").first()
        self.assertNotEqual(assetTree, None)
        assetTree = AssetTree.objects.filter(name="条目型资产", department="PKU").first()
        self.assertNotEqual(assetTree, None)
        assetTree = AssetTree.objects.filter(name="数量型资产", department="PKU").first()
        self.assertNotEqual(assetTree, None)
        res1 = self.post_department(
            "a",
            "b",
            "UCLA",
            session,
        )
        res1 = self.post_department(
            "a",
            "b",
            "MIT",
            session,
        )
        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.post_department(
            "a",
            "b",
            "MIT",
            114514,
        )
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.post_department(
            "a",
            "b",
            "MIT",
            "ssssssssssssssssssssssssssssssss",
        )
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.post_department(
            "a",
            "b",
            "MIT",
            jinjin.session,
        )
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.post_department(
            "aa",
            "b",
            "MIT",
            session,
        )
        self.assertEqual(
            res.json()["info"],
            "给出的业务实体未找到。",
        )
        res = self.post_department(
            "a",
            "bb",
            "UCB",
            session,
        )
        self.assertEqual(
            res.json()["info"],
            "给定的父部门不存在",
        )
        res = self.post_department(
            "a",
            "b",
            "UCLA",
            session,
        )
        self.assertEqual(
            res.json()["info"],
            "已存在同名的业务实体",
        )
        res1 = self.post_department(
            "a",
            "MIT",
            "MIT_cst",
            session,
        )
        res1 = self.post_department(
            "a",
            "tsinghua",
            "tsinghua_cst",
            session,
        )
        res1 = self.post_department(
            "a",
            "tsinghua_cst",
            "grade_1",
            session,
        )
        department = Department.objects.filter(name="b").first()
        self.assertEqual(department.subDepartmentNumber, 7)
        department = Department.objects.filter(name="tsinghua").first()
        self.assertEqual(department.subDepartmentNumber, 2)
        department = Department.objects.filter(name="MIT").first()
        self.assertEqual(department.subDepartmentNumber, 1)
        department = Department.objects.filter(name="UCLA").first()
        self.assertEqual(department.subDepartmentNumber, 0)
        res = self.user_login("liusn", "114514")
        session1 = res.json()["data"]["session"]
        res2 = self.post_department(
            "a",
            "",
            "tsinghua1",
            session1,
        )
        self.assertEqual(res2.json()["code"], 1)
        self.assertEqual(
            res2.status_code, 400
        )  # test post_department failed because the user's character is 1
        self.post_entity(session, "b")
        self.post_department("b", "", "tsinghua2", session)
        self.post_user(
            "lyq",
            "123456",
            "b",
            "tsinghua2",
            2,
            False,
            "",
            "",
            session,
        )
        res = self.user_login("lyq", "123456")
        session2 = res.json()["data"]["session"]
        res3 = self.post_department(
            "a",
            "",
            "tsinghua3",
            session2,
        )
        self.assertEqual(res3.json()["code"], 1)
        self.assertEqual(
            res3.status_code, 400
        )  # test post_department failed because the user's character is 3 but he trys to create a department that is not under his business entity

    def test_put_department(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res1 = self.put_department("", "c", 1, session)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(
            res1.status_code, 200
        )  # test put_department succeed(modify name)
        self.post_department("a", "", "tsinghua", session)
        res2 = self.put_department("c", "tsinghua1", 2, session)
        self.assertEqual(res2.json()["code"], 0)
        self.assertEqual(
            res2.status_code, 200
        )  # test put_department succeed(modify parent)
        self.post_entity(session, "b")
        self.post_department("b", "", "tsinghua2", session)
        res3 = self.put_department("tsinghua2", "tsinghua3", 2, session)
        self.assertEqual(res3.json()["code"], 2)
        self.assertEqual(
            res3.status_code, 400
        )  # test put_department failed because this department is different from the business entity in which the parent department is located
        res4 = self.put_department("tsinghua3", "d", 1, session)
        self.assertEqual(res4.json()["code"], 2)
        self.assertEqual(
            res4.status_code, 400
        )  # test put_department failed because you set a child department as new parent department

    def test_put_department_2(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.post_department("a", "b", "tsinghua", session)
        asset_tree_node = AssetTree.objects.filter(
            name="默认分类", department="tsinghua"
        ).first()
        self.assertNotEqual(asset_tree_node, None)
        res = self.put_department("b", "tsinghua1", 2, session)
        asset_tree_node = AssetTree.objects.filter(
            name="默认分类", department="tsinghua"
        ).first()
        self.assertEqual(asset_tree_node, None)
        asset_tree_node = AssetTree.objects.filter(
            name="默认分类", department="tsinghua1"
        ).first()
        self.assertNotEqual(asset_tree_node, None)
        res = self.put_department("b", "tsinghua", 2, session)
        self.post_department(
            "a",
            "b",
            "PKU",
            session,
        )
        self.post_department(
            "a",
            "b",
            "UCLA",
            session,
        )
        self.post_department(
            "a",
            "b",
            "MIT",
            session,
        )
        self.post_department(
            "a",
            "MIT",
            "MIT_cst",
            session,
        )
        self.post_department("a", "tsinghua", "tsinghua_cst", session)
        self.post_department("a", "tsinghua_cst", "grade_1", session)
        res = self.put_department(
            "",
            "tsinghua",
            2,
            session,
        )
        department = Department.objects.filter(name="b").first()
        self.assertEqual(department.subDepartmentNumber, 4)
        department = Department.objects.filter(name="tsinghua").first()
        self.assertEqual(department.subDepartmentNumber, 2)
        self.put_department("UCLA", "PKU", 3, session)
        department = Department.objects.filter(name="b").first()
        self.assertEqual(department.subDepartmentNumber, 4)
        department = Department.objects.filter(name="UCLA").first()
        self.assertEqual(department.subDepartmentNumber, 1)
        department = Department.objects.filter(name="PKU").first()
        self.assertEqual(department.subDepartmentNumber, 0)

    def test_get_department(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_department("a", "", "tsinghua1", session)
        self.post_department("a", "", "tsinghua2", session)
        self.post_department("a", "", "tsinghua3", session)
        self.post_entity(session, "b")
        self.post_department("b", "", "tsinghua4", session)
        self.post_department("b", "", "tsinghua5", session)
        self.post_department("b", "tsinghua4", "tsinghua6", session)
        self.post_department("a", "tsinghua1", "tsinghua7", session)
        res1 = self.get_department(session)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.json()["data"]), 6)
        self.assertEqual(res1.json()["data"][1]["subDepartmentNumber"], 1)
        res = self.user_login("liusn", "114514")
        session1 = res.json()["data"]["session"]
        res2 = self.get_department(session1)
        self.assertEqual(res2.json()["code"], 0)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(res2.json()["data"]), 4)
        self.post_user(
            "lyq",
            "123456",
            "b",
            "tsinghua4",
            2,
            False,
            "",
            "",
            session,
        )
        res = self.user_login("lyq", "123456")
        session2 = res.json()["data"]["session"]
        res3 = self.get_department(session2)
        self.assertEqual(res3.json()["code"], 0)
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(len(res3.json()["data"]), 2)
        self.post_department("b", "", "tsinghu11", session)
        res4 = self.get_department(session2)
        self.assertEqual(len(res4.json()["data"]), 3)
        res = self.user_login("jinjin", "bjzyydx")
        res = self.get_department(114514)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_department("ssssssssssssssssssssssssssssssss")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

    def test_get_sub_department(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_department("a", "b", "tsinghua1", session)
        self.post_department("a", "b", "tsinghua2", session)
        self.post_department("a", "tsinghua1", "tsinghua3", session)
        self.post_department("a", "tsinghua1", "tsinghua4", session)
        self.post_department("a", "tsinghua1", "tsinghua5", session)
        res1 = self.get_sub_department(session, "b")
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.json()["data"]), 2)
        self.assertEqual(res1.json()["data"][0]["subDepartmentNumber"], 3)
        res2 = self.get_sub_department(session, "tsinghua1")
        self.assertEqual(len(res2.json()["data"]), 3)
        self.post_entity(session, "b")
        self.post_department("b", "", "tsinghua14", session)
        self.post_user(
            "lyq",
            "123456",
            "b",
            "tsinghua14",
            2,
            False,
            "",
            "",
            session,
        )
        res = self.user_login("lyq", "123456")
        session1 = res.json()["data"]["session"]
        res3 = self.get_sub_department(session1, "b")
        self.assertEqual(res3.json()["code"], 1)
        self.assertEqual(res3.status_code, 400)

        res = self.user_login("jinjin", "bjzyydx")
        jinjin = User.objects.filter(session=res.json()["data"]["session"]).first()
        res = self.get_sub_department(jinjin.session, "cst")
        self.assertEqual(
            res.json()["info"],
            "给定的父部门不存在",
        )
        res = self.get_sub_department(jinjin.session, "b")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.get_sub_department(114514, "cst")
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_sub_department("ssssssssssssssssssssssssssssssss", "cst")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

    def test_get_cur_entity(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_entity(session, "Mihoyo")
        res1 = self.get_cur_entity(session)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()["data"]["name"], "manager")
        session_err = "114514"
        res2 = self.get_cur_entity(session_err)
        self.assertEqual(res2.json()["code"], 1)
        self.assertEqual(res2.status_code, 400)
        session_none = "20020529201905012022122620230113"
        res3 = self.get_cur_entity(session_none)
        self.assertEqual(res3.json()["code"], 2)
        self.assertEqual(res3.status_code, 400)
        self.post_user(
            "xlxsb",
            "chusheng",
            "a",
            "b",
            1,
            True,
            "",
            "",
            session,
        )
        res4 = self.user_login("xlxsb", "chusheng")
        self.assertEqual(res4.json()["code"], 3)

    def test_delete_department(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_department("a", "b", "pku1", session)
        asset_root = AssetTree.objects.filter(name="默认分类", department="pku1").first()
        self.assertNotEqual(asset_root, None)
        asset_root = AssetTree.objects.filter(name="数量型资产", department="pku1").first()
        self.assertNotEqual(asset_root, None)
        asset_root = AssetTree.objects.filter(name="条目型资产", department="pku1").first()
        self.assertNotEqual(asset_root, None)
        res = self.delete_department(session, "pku1")
        asset_root = AssetTree.objects.filter(name="默认分类", department="pku1").first()
        self.assertEqual(asset_root, None)
        asset_root = AssetTree.objects.filter(name="数量型资产", department="pku1").first()
        self.assertEqual(asset_root, None)
        asset_root = AssetTree.objects.filter(name="条目型资产", department="pku1").first()
        self.assertEqual(asset_root, None)
        entity1 = Entity.objects.filter(name="a").first()
        department1 = Department.objects.filter(name="b").first()
        department2 = Department(name="cst", entity=entity1, parent=department1)
        department2.save()
        department3 = Department(name="se", entity=entity1, parent=department1)
        department3.save()
        new_user = User(
            name="xupy", password="111111", entity=entity1, department=department2
        )
        new_user.save()
        res = self.delete_department("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "b")
        self.assertEqual(res.json()["code"], 1)
        res = self.delete_department(session, "cst")
        self.assertEqual(res.json()["info"], "不可以删除有用户的部门")
        res = self.delete_department(session, "se")
        self.assertEqual(res.json()["code"], 0)
        department = Department.objects.filter(name="se").first()
        self.assertEqual(department, None)
        res = self.user_login("liusn", "114514")
        session = res.json()["data"]["session"]
        res = self.delete_department(session, "b")
        self.assertEqual(res.json()["info"], "您无此权限")

    def test_get_logjournal(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res2 = self.user_login("liusn", "114514")
        liusn_session = res2.json()["data"]["session"]
        res = self.get_logjournal("xymm", "a", 1)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_logjournal("xymmhggznzttyqdhykjdlkkhggwyyazn", "a", 1)
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res1 = self.get_logjournal(session, "a", 1)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.post_user(
            "abaaba",
            "1919810",
            "a",
            "b",
            1,
            False,
            "",
            "",
            session,
        )
        res3 = self.user_login("abaaba", "1919810")
        abaaba_session = res3.json()["data"]["session"]
        self.user_logout(liusn_session)
        self.user_logout(abaaba_session)
        entity = Entity.objects.filter(name="a").first()
        res = self.user_login("abaaba", "1919810")
        self.user_logout(res.json()["data"]["session"])
        res = self.user_login("abaaba", "1919810")
        self.user_logout(res.json()["data"]["session"])
        res = self.user_login("abaaba", "1919810")
        self.user_logout(res.json()["data"]["session"])
        res4 = self.get_logjournal(session, "a", 2)
        self.assertEqual(len(res4.json()["data"]), 2)
        res4 = self.get_logjournal(session, "a", 1)
        self.assertEqual(len(res4.json()["data"]), 8)

    def test_get_operationjournal_department(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        self.post_department("a", "b", "tsinghua", session)
        self.post_department("a", "b", "PKU", session)
        self.post_department("a", "b", "UCLA", session)
        self.post_department("a", "b", "MIT", session)
        self.post_department("a", "MIT", "MIT_cst", session)
        self.post_department("a", "tsinghua", "tsinghua_cst", session)
        self.post_department("a", "tsinghua_cst", "grade_1", session)
        self.put_department("", "tsinghua", 2, session)
        self.put_department("b", "pku1", 3, session)
        self.delete_department(session, "MIT_cst")
        self.delete_department(session, "grade_1")
        res1 = self.get_operationjournal(session, "a", 1)
        self.assertEqual(res1.json()["code"], 0)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.json()["data"]), 8)
        res1 = self.get_operationjournal(session, "a", 2)
        self.assertEqual(len(res1.json()["data"]), 3)
        res = self.get_operationjournal("xymm", "a", 1)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_operationjournal("xymmhggznzttyqdhykjdlkkhggwyyazn", "a", 1)
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

    def test_put_feishu_name(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.put_feishu_name("aa", "b", "11")
        self.assertEqual(res.json()["info"], "用户的会话标识符信息不正确")
        res = self.put_feishu_name("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "a", "1")
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.put_feishu_name(session, "a", "18852569598")
        self.assertEqual(res.json()["code"], 11)
        res = self.put_feishu_name(session, "徐沛阳", "18852569598")
        self.assertEqual(res.json()["code"], 0)
        user = User.objects.filter(feishu_name="徐沛阳").first()
        self.assertNotEqual(user, None)
        res = self.user_login("liusn", "114514")
        session = res.json()["data"]["session"]
        res = self.put_feishu_name(session, "徐沛阳", "18852569578")
        self.assertEqual(res.json()["info"], "该飞书用户名对应的用户已经存在")

    def test_feishu_users(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.feishu_users("aa")
        self.assertEqual(res.json()["info"], "用户的会话标识符信息不正确")
        res = self.feishu_users("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.feishu_users(session)
        self.assertEqual(res.json()["info"], "你无此权限")
        res = self.user_login("xlx", "sbop")
        session = res.json()["data"]["session"]
        res = self.feishu_users(session)
        self.assertEqual(res.json()["info"], "管理员尚未绑定飞书用户")
        user = User.objects.filter(name="xlx").first()
        user.feishu_name = "徐沛阳"
        user.feishu_phone = "18852569598"
        user.save()
        cur_user = User.objects.filter(name="张凯文").first()
        self.assertEqual(cur_user, None)
        res = self.user_login("xlx", "sbop")
        session = res.json()["data"]["session"]
        res = self.feishu_users(session)
        self.assertEqual(res.json()["code"], 0)
        cur_user = User.objects.filter(name="zkw").first()
        self.assertNotEqual(cur_user, None)
        dep = Department.objects.filter(name="gaybar_feishu").first()
        self.assertNotEqual(dep, None)


class AssetTests(TestCase):
    def setUp(self):
        entity1 = Entity(name="a")
        entity1.save()
        department1 = Department(
            name="b",
            entity=entity1,
            parent=None,
            userNumber=1,
        )
        department1.save()
        department2 = Department(
            name="cst",
            entity=entity1,
            parent=None,
            userNumber=1,
        )
        department2.save()
        user1 = User(
            name="manager",
            password="1919810",
            character=4,
            lock=False,
            session="",
            email="",
        )
        user1.save()
        user2 = User(
            name="steve",
            password="minecraft",
            department=department1,
            entity=entity1,
            character=1,
            lock=False,
            session="",
            email="",
        )
        user2.save()
        user3 = User(
            name="asset_manager",
            password="minecraft",
            department=department1,
            entity=entity1,
            character=2,
            lock=False,
            session="",
            email="",
        )
        user3.save()
        user4 = User(
            name="green",
            password="minecraft",
            department=department2,
            entity=entity1,
            character=2,
            lock=False,
            session="",
            email="",
        )
        user4.save()
        user5 = User(
            name="poole",
            password="minecraft",
            department=department1,
            entity=entity1,
            character=2,
            lock=False,
            session="",
            email="",
        )
        user5.save()
        user6 = User(
            name="tom",
            password="minecraft",
            department=department2,
            entity=entity1,
            character=1,
            lock=False,
            session="",
            email="",
        )
        user6.save()
        user7 = User(
            name="kyrie",
            password="minecraft",
            department=department1,
            entity=entity1,
            character=1,
            lock=False,
            session="",
            email="KyrieIrving@cleverland",
        )
        user7.save()
        user8 = User(
            name="cutestYue",
            password="mysister",
            department=department1,
            entity=entity1,
            character=3,
            lock=False,
            session="",
            email="",
        )
        user8.save()
        user9 = User(
            name="yueyue",
            password="yueyue",
            department=department2,
            entity=entity1,
            character=1,
            lock=False,
            session="",
            email="",
        )
        user9.save()
        user10 = User(
            name="haohao",
            password="haohao",
            department=department1,
            entity=entity1,
            character=1,
            lock=False,
            session="",
            email="",
        )
        user10.save()
        user11 = User(
            name="LYiQian",
            password="luca1k",
            department=department2,
            entity=entity1,
            character=2,
            lock=False,
            session="",
            email="",
        )
        user11.save()
        root_node = AssetTree(name="默认分类", department="b")
        root_node.save()
        node1 = AssetTree(name="条目型资产", parent=root_node, department="b")
        node1.save()
        node2 = AssetTree(name="数量型资产", parent=root_node, department="b")
        node2.save()
        root_node2 = AssetTree(name="默认分类", department="cst")
        root_node2.save()
        node3 = AssetTree(name="条目型资产", parent=root_node2, department="cst")
        node3.save()
        node4 = AssetTree(name="数量型资产", parent=root_node2, department="cst")
        node4.save()
        asset1 = Asset(
            name="DiamondSword",
            assetClass=1,
            user=user2,
            price=5.0,
            description="A powerful weapon",
            position="steve's bag",
            expire=0,
            assetTree=root_node,
            department=department1,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
            count=2,
        )
        asset1.save()
        asset2 = Asset(
            name="chair",
            assetClass=1,
            user=user2,
            price=5.0,
            description="",
            position="steve's bag",
            expire=0,
            assetTree=root_node,
            department=department1,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        )
        asset2.save()
        asset3 = Asset(
            name="goldaxe",
            assetClass=1,
            user=user2,
            price=5.0,
            description="A powerful weapon",
            position="",
            expire=0,
            assetTree=root_node,
            department=department1,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        )
        asset3.save()
        asset4 = Asset(
            name="bed",
            assetClass=1,
            user=user2,
            price=5.0,
            description="",
            position="steve's bag",
            expire=0,
            assetTree=root_node,
            department=department1,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        )
        asset4.save()
        # asset5 = Asset(
        #     name="Wool",
        #     assetClass=1,
        #     user=user2,
        #     price=5.0,
        #     description="An userful material in MineCraft",
        #     position="",
        #     expire=0,
        #     assetTree=root_node,
        #     department=department1,
        #     create_time=timezone.now().date(),
        #     initial_price=5.0,
        #     deadline=9,
        #     count=64,
        # )
        # asset5.save()

    # Utility functions
    def user_login(self, identity, password):
        payload = {
            "identity": identity,
            "password": password,
        }
        return self.client.post("/login", data=payload, content_type="application/json")

    def post_export_task(self, session, body: list):
        payload = body
        return self.client.post(
            f"/export_task/{session}", data=payload, content_type="application/json"
        )

    def get_export_task(self, session, id):
        return self.client.get(
            f"/export_task/{session}/{id}", content_type="application/json"
        )

    def post_pending_request(
        self, session, initiator, participant, target, asset_id, type, count
    ):
        payload = {
            "initiator": initiator,
            "participant": participant,
            "target": target,
            "asset_id": asset_id,
            "type": type,
            "count": count,
        }
        return self.client.post(
            f"/pending_request/{session}",
            data=payload,
            content_type="application/json",
        )

    def all_item_assets(self, session, asset_id):
        return self.client.get(
            f"/all_item_assets/{session}/{asset_id}",
            content_type="application/json",
        )

    def get_pending_request_list(self, session, asset_manager_name):
        return self.client.get(
            f"/pending_request_list/{session}/{asset_manager_name}",
            content_type="application/json",
        )

    def put_return_pending_request(self, session, id, result):
        payload = {
            "id": id,
            "result": result,
        }
        return self.client.put(
            f"/return_pending_request/{session}",
            data=payload,
            content_type="application/json",
        )

    def count_department_asset(self, session):
        return self.client.get(
            f"/count_department_asset/{session}",
        )

    def count_status_asset(self, session):
        return self.client.get(
            f"/count_status_asset/{session}",
        )

    def info_curve(self, session, asset_id, visible_type):
        return self.client.get(
            f"/info_curve/{session}/{asset_id}/{visible_type}",
        )

    def count_price_curve(self, session, visible_type):
        return self.client.get(
            f"/count_price_curve/{session}/{visible_type}",
        )

    def get_maintain_list(self, session):
        return self.client.get(
            f"/get_maintain_list/{session}",
        )

    def put_asset(
        self,
        session,
        id,
        parent,
        name,
        assetClass,
        user,
        price,
        description,
        position,
        expire,
        count,
        assetTree,
        department,
    ):
        payload = {
            "id": id,
            "parent": parent,
            "name": name,
            "assetClass": assetClass,
            "user": user,
            "price": price,
            "description": description,
            "position": position,
            "expire": expire,
            "count": count,
            "assetTree": assetTree,
            "department": department,
        }
        return self.client.put(
            f"/asset/{session}", data=payload, content_type="application/json"
        )

    def post_asset(
        self,
        session,
        parent,
        name,
        assetClass,
        user,
        price,
        description,
        position,
        expire,
        count,
        assetTree,
        department,
        deadline,
    ):
        payload = [
            {
                "parent": parent,
                "name": name,
                "assetClass": assetClass,
                "user": user,
                "price": price,
                "description": description,
                "position": position,
                "expire": expire,
                "count": count,
                "assetTree": assetTree,
                "department": department,
                "deadline": deadline,
            }
        ]
        return self.client.post(
            f"/post_asset/{session}", data=payload, content_type="application/json"
        )

    def get_asset_tree_node(self, session, asset_tree_node_name, page, expire):
        return self.client.get(
            f"/asset_tree_node/{session}/{asset_tree_node_name}/{page}/{expire}",
            content_type="application/json",
        )

    def get_picture_link(self, session, id):
        return self.client.get(
            f"/picture/{session}/{id}",
            content_type="application/json",
        )

    def put_picture_link(self, session, id, links: list, richtxt: str):
        payload = {"links": links, "richtxt": richtxt}
        return self.client.put(
            f"/picture/{session}/{id}",
            content_type="application/json",
            data=payload,
        )

    def get_asset_user(self, session, user_name, page):
        return self.client.get(
            f"/asset/{session}/{user_name}/{page}",
            content_type="application/json",
        )

    def get_history_list(self, session, id, history_type):
        return self.client.get(
            f"/asset_query/{session}/{id}/{history_type}",
            content_type="application/json",
        )

    def get_asset_manager_entity(self, session, entity_name):
        return self.client.get(
            f"/asset_manager_entity/{session}/{entity_name}",
            content_type="application/json",
        )

    def get_asset_manager(self, session, department_name):
        return self.client.get(
            f"/asset_manager/{session}/{department_name}",
            content_type="application/json",
        )

    def get_asset(self, session, page):
        return self.client.get(
            f"/asset_user_list/{session}/{page}",
            content_type="application/json",
        )

    def allot_asset(self, session, id, name, count):
        payload = {
            "id": id,
            "name": name,
            "count": count,
        }
        return self.client.put(
            f"/allot_asset/{session}",
            data=payload,
            content_type="application/json",
        )

    def transfer_asset(self, session, id, sender, target, count):
        payload = {
            "id": id,
            "sender": sender,
            "target": target,
            "count": count,
            "request_id": 1,
        }
        return self.client.put(
            f"/transfer_asset/{session}",
            data=payload,
            content_type="application/json",
        )

    def maintain_asset(self, session, id, name, new_deadline, new_price, count):
        payload = {
            "id": id,
            # "request_id": request_id,
            "name": name,
            "new_deadline": new_deadline,
            "new_price": new_price,
            "count": count,
            # "request_id": 1,
        }
        return self.client.put(
            f"/maintain_asset/{session}",
            data=payload,
            content_type="application/json",
        )

    def receive_asset(self, session, id, name, count):
        payload = {
            "id": id,
            "name": name,
            "count": count,
            "request_id": 1,
        }
        return self.client.put(
            f"/receive_asset/{session}", data=payload, content_type="application/json"
        )

    def return_asset(self, session, id, name, count):
        payload = {
            "id": id,
            "name": name,
            "count": count,
            "request_id": 1,
        }
        return self.client.put(
            f"/return_asset/{session}", data=payload, content_type="application/json"
        )

    def get_asset_tree_root(self, session, department_name):
        return self.client.get(
            f"/asset_tree_root/{session}/{department_name}",
            content_type="application/json",
        )

    def get_operationjournal(self, session, entity_name, page):
        return self.client.get(f"/operationjournal/{session}/{entity_name}/{page}")

    def get_sub_asset_tree(self, session, asset_tree_node_name):
        return self.client.get(
            f"/sub_asset_tree/{session}/{asset_tree_node_name}",
            content_type="application/json",
        )

    def delete_sub_asset_tree(self, session, asset_tree_node_name):
        return self.client.delete(
            f"/sub_asset_tree/{session}/{asset_tree_node_name}",
            content_type="application/json",
        )

    def post_asset_tree(self, session, name, parent, department):
        payload = {
            "name": name,
            "parent": parent,
            "department": department,
        }
        return self.client.post(
            f"/asset_tree/{session}",
            data=payload,
            content_type="application/json",
        )

    def search_assets(
        self,
        session,
        asset_tree_node,
        id,
        name,
        price_inf,
        price_sup,
        description,
        owner_name,
        status,
        page,
        asset_class,
    ):
        payload = {
            "asset_tree_node": asset_tree_node,
            "id": id,
            "name": name,
            "price_inf": price_inf,
            "price_sup": price_sup,
            "asset_class": asset_class,
            "description": description,
            "owner_name": owner_name,
            "status": status,
            "page": page,
        }
        return self.client.post(
            f"/search_assets/{session}",
            data=payload,
            content_type="application/json",
        )

    def search_unallocated_assets(
        self,
        session,
        asset_tree_node,
        name,
        price_inf,
        price_sup,
        description,
        page,
        asset_class,
        manager_name,
        id,
    ):
        payload = {
            "asset_tree_node": asset_tree_node,
            "id": id,
            "name": name,
            "price_inf": price_inf,
            "price_sup": price_sup,
            "asset_class": asset_class,
            "description": description,
            "page": page,
        }
        return self.client.post(
            f"/search_unallocated_assets/{session}/{manager_name}",
            data=payload,
            content_type="application/json",
        )

    def search_personal_assets(
        self,
        session,
        asset_tree_node,
        name,
        price_inf,
        price_sup,
        description,
        page,
        asset_class,
        id,
    ):
        payload = {
            "id": id,
            "asset_tree_node": asset_tree_node,
            "name": name,
            "price_inf": price_inf,
            "price_sup": price_sup,
            "asset_class": asset_class,
            "description": description,
            "page": page,
        }
        return self.client.post(
            f"/search_personal_assets/{session}",
            data=payload,
            content_type="application/json",
        )

    def expire_asset(self, session, id, count):
        payload = {
            "id": id,
            "count": count,
        }
        return self.client.put(
            f"/expire_asset/{session}", data=payload, content_type="application/json"
        )

    def get_unallocated_asset(self, session, asset_manager_name, page):
        return self.client.get(
            f"/unallocated_asset/{session}/{asset_manager_name}/{page}",
            content_type="application/json",
        )

    def put_warning(self, session, date, amount, id):
        payload = {
            "date": date,
            "amount": amount,
            "id": id,
        }
        return self.client.put(
            f"/warning/{session}", data=payload, content_type="application/json"
        )

    def get_warning(self, session, page):
        return self.client.get(
            f"/warning_get/{session}/{page}", content_type="application/json"
        )

    def get_warning_list(self, session):
        return self.client.get(
            f"/warning_list/{session}", content_type="application/json"
        )

    def feishu_approval(self, message_id, action_type):
        payload = {"action_type": action_type, "message_id": message_id}
        return self.client.post(
            f"/feishu_approval",
            data=payload,
            content_type="application/json",
        )

    def feishu_asset(self, session, id):
        payload = {
            "id": id,
        }
        return self.client.post(
            f"/feishu_asset/{session}",
            data=payload,
            content_type="application/json",
        )

    def post_asset_async(
        self,
        session,
        body: list,
    ):
        payload = body
        return self.client.post(
            f"/asset/{session}", data=payload, content_type="application/json"
        )

    def get_asset_async(self, session):
        return self.client.get(
            f"/async_task/{session}", content_type="application/json"
        )

    def get_failed_task(self, session, id):
        return self.client.get(
            f"/failed_task/{session}/{id}", content_type="application/json"
        )

    def put_failed_task(self, session, id, body: list):
        payload = body
        return self.client.put(
            f"/failed_task/{session}/{id}",
            data=payload,
            content_type="application/json",
        )

    def get_all_departments(self, session, entity_name):
        return self.client.get(
            f"/all_departments/{session}/{entity_name}",
            content_type="application/json",
        )

    def get_all_departments(self, session, entity_name):
        return self.client.get(
            f"/all_departments/{session}/{entity_name}",
            content_type="application/json",
        )

    # Now start test cases
    def test_search_assets(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.search_assets(
            session,
            "默认分类",
            "1",
            "DiamondSword",
            "1",
            "10",
            "A powerful weapon",
            "s",
            "1",
            "1",
            "1",
        )
        self.assertEqual(
            len(res.json()["data"]),
            1,
        )

    def test_search_unallocated_assets(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.search_unallocated_assets(
            session,
            "默认分类",
            "DiamondSword",
            "1",
            "10",
            "A powerful weapon",
            "1",
            "1",
            "asset_manager",
            "",
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        session_1 = self.user_login("yueyue", "yueyue").json()["data"]["session"]
        res = self.search_unallocated_assets(
            session_1,
            "默认分类",
            "DiamondSword",
            "1",
            "10",
            "A powerful weapon",
            "1",
            "1",
            "xiaoyue",
            "",
        )
        self.assertEqual(
            res.json()["info"],
            "所选资产管理员非法",
        )
        res = self.search_unallocated_assets(
            session_1,
            "默认分类",
            "DiamondSword",
            "1",
            "10",
            "A powerful weapon",
            "1",
            "1",
            "asset_manager",
            "",
        )
        self.assertEqual(
            res.json()["info"],
            "所选资产管理员非法",
        )
        res = self.search_unallocated_assets(
            session_1,
            "默认分类",
            "DiamondSword",
            "1",
            "10",
            "A powerful weapon",
            "1",
            "1",
            "green",
            "",
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

    def test_search_personal_assets(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.search_personal_assets(
            session,
            "默认分类",
            "DiamondSword",
            "1",
            "10",
            "A powerful weapon",
            "1",
            "1",
            "",
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        session_1 = self.user_login("yueyue", "yueyue").json()["data"]["session"]
        res = self.search_personal_assets(
            session_1,
            "默认分类",
            "DiamondSword",
            "1",
            "10",
            "A powerful weapon",
            "1",
            "1",
            "",
        )
        self.assertEqual(
            res.json()["data"],
            [],
        )
        yueyue = User.objects.filter(name="yueyue").first()
        Asset.objects.create(
            name="DiamondSword",
            assetClass=1,
            user=yueyue,
            price=5.0,
            department=yueyue.department,
            status=2,
            description="A powerful weapon",
            position="yueyue's bag",
            expire=0,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        )
        res = self.search_personal_assets(
            session_1, "", "DiamondSword", "5", "10", "A powerful weapon", "1", "1", ""
        )
        self.assertEqual(
            len(res.json()["data"]),
            1,
        )

    def test_post_asset_async(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        body = [
            {
                "parent": 0,
                "name": "Trident1",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident2",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident3",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident4",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident5",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": -1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident6",
                "assetClass": 0,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 2,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident7",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "bc",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident8",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类1",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident9",
                "assetClass": 1,
                "user": "steve1",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "name": "Trident10",
                "assetClass": 1,
                "user": "steve1",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident12",
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident13",
                "assetClass": 1,
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident14",
                "assetClass": 1,
                "user": "steve",
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident15",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident16",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident17",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident18",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident19",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident20",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident21",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
            },
            {
                "parent": 0,
                "name": "Trident22",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "条目型资产",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": "abc",
                "name": "Trident23",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident24",
                "assetClass": "abc",
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident25",
                "assetClass": 1,
                "user": "steve",
                "price": "abc",
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident26",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": "abc",
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident27",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": "abc",
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident28",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": "abc",
            },
        ]
        res = self.post_asset_async(session, body)
        self.assertEqual(res.json()["code"], 0)
        async_task = AsyncTasks.objects.filter(id=1).first()
        self.assertEqual(async_task.number_need, 28)
        self.assertEqual(async_task.number_succeed, 4)
        manager = User.objects.filter(session=session).first()
        manager.character = 3
        manager.save()
        res = self.get_asset_async(session)
        self.assertTrue(res.json()["data"][0]["finish"] == 2)
        res = self.get_failed_task(session, 1)
        self.assertEqual(len(res.json()["data"]), 24)
        body = [
            {
                "parent": 0,
                "name": "Trident5",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": -1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident6",
                "assetClass": 0,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 2,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident7",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "bc",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident8",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类1",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident9",
                "assetClass": 1,
                "user": "steve1",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "name": "Trident10",
                "assetClass": 1,
                "user": "steve1",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident12",
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident13",
                "assetClass": 1,
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident14",
                "assetClass": 1,
                "user": "steve",
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident15",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident16",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident17",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident18",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident19",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident20",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident21",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
            },
            {
                "parent": 0,
                "name": "Trident22",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "条目型资产",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": "abc",
                "name": "Trident23",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident24",
                "assetClass": "abc",
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident25",
                "assetClass": 1,
                "user": "steve",
                "price": "abc",
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident26",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": "abc",
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident27",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": "abc",
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident28",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": "abc",
            },
        ]
        res = self.put_failed_task(session, 1, body)
        self.assertEqual(res.json()["code"], 0)
        async_task = AsyncTasks.objects.filter(id=1).first()
        self.assertEqual(async_task.number_succeed, 4)
        self.assertEqual(async_task.finish, 2)
        body = [
            {
                "parent": 0,
                "name": "Trident5",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident6",
                "assetClass": 0,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident7",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident8",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident9",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident10",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident11",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident12",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident13",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident14",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident15",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident16",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident17",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident18",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident19",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident20",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident21",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident22",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident23",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident24",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident25",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident26",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident27",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
            {
                "parent": 0,
                "name": "Trident28",
                "assetClass": 1,
                "user": "steve",
                "price": 50.0,
                "description": "",
                "position": "",
                "expire": 0,
                "count": 1,
                "assetTree": "默认分类",
                "department": "b",
                "deadline": 1,
            },
        ]
        res = self.put_failed_task(session, 1, body)
        self.assertEqual(res.json()["code"], 0)
        async_task = AsyncTasks.objects.filter(id=1).first()
        self.assertEqual(async_task.number_succeed, 28)
        self.assertEqual(async_task.finish, 1)

    def test_picture_link(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.put_picture_link(
            session, 1, ["https://pornhub.com", "https://baidu.com"], ""
        )
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(Asset.objects.filter(id=1).first().picture_link), 2)
        res = self.put_picture_link(
            "abc", 1, ["https://pornhub.com", "https://baidu.com"], ""
        )
        self.assertEqual(res.json()["code"], 2)
        res = self.put_picture_link(
            session, 10085, ["https://pornhub.com", "https://baidu.com"], ""
        )
        self.assertEqual(res.json()["code"], 3)
        res = self.get_picture_link("abc", 1)
        self.assertEqual(res.json()["code"], 2)
        res = self.get_picture_link(session, 1)
        self.assertEqual(len(res.json()["links"]), 2)
        res = self.get_picture_link(session, 10086)
        self.assertEqual(res.json()["code"], 3)
        user = User.objects.filter(name="asset_manager").first()
        user.lock = True
        user.save()
        res = self.get_picture_link(session, 1)
        self.assertEqual(res.json()["code"], 4)
        res = self.put_picture_link(
            session, 1, ["https://pornhub.com", "https://baidu.com"], ""
        )
        self.assertEqual(res.json()["code"], 4)

    def test_post_asset_tree_node(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.post_asset_tree(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "电子产品",
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 1)
        res = self.post_asset_tree(session, "电子产品", "b_all_", "b")
        self.assertEqual(res.json()["code"], 2)
        res = self.post_asset_tree(session, "电子产品", "默认分类", "bb")
        self.assertEqual(res.json()["code"], 2)
        res = self.post_asset_tree(session, "电子产品", "默认分类", "b")
        self.assertEqual(res.json()["info"], "无法在此处创建一个资产分类")
        res = self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.assertEqual(res.json()["code"], 0)
        res = self.post_asset_tree(session, "电子产品", "电子产品", "b")
        self.assertEqual(res.json()["code"], 2)
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        asset_node = AssetTree.objects.filter(name="电子产品").first()
        self.assertEqual(asset_node.parent.name, "数量型资产")
        asset_node = AssetTree.objects.filter(name="电脑").first()
        self.assertEqual(asset_node.parent.name, "电子产品")
        self.assertEqual(asset_node.department, "b")
        res = self.user_login("steve", "minecraft")
        session = res.json()["data"]["session"]
        res = self.post_asset_tree(session, "lsn", "电子产品", "b")
        self.assertEqual(res.json()["info"], "您无此权限")

        # YueYue = User.objects.filter(name="manager").first()
        # all_departments = Department.objects.all()
        # for dp in all_departments:
        #     cur_dp_assets = Asset.objects.filter(department=dp, count__gt=0).all()
        #     tot_cnt_item = 0
        #     tot_cnt_amount = 0
        #     tot_cnt = 0
        #     tot_price_item = 0.00
        #     tot_price_amount = 0.00
        #     tot_price = 0.00
        #     for a in cur_dp_assets:
        #         AssetStatistics.objects.create(
        #         asset=a,
        #         cur_department=a.department,
        #         cur_user=a.user,
        #         cur_price=a.price,
        #         cur_time=timezone.now() + timezone.timedelta(hours=8),
        #         cur_status=a.status if a.expire == 0 else 0,
        #         cur_count=a.count,
        #     )
        #         if a.assetClass == 0:
        #             tot_cnt_item += a.count
        #             tot_price_item += float(a.price)
        #         else:
        #             tot_cnt_amount += a.count
        #             tot_price_amount += float(a.price) * float(a.count)
        #     tot_cnt = tot_cnt_item + tot_cnt_amount
        #     tot_price = tot_price_item + tot_price_amount
        #     AssetStatistics.objects.create(
        #         asset=None,
        #         cur_department=dp,
        #         cur_user=None,
        #         cur_price=tot_price_item,
        #         cur_time=timezone.now() + timezone.timedelta(hours=8),
        #         cur_status=529113,
        #         cur_count=tot_cnt_item,
        #     )
        #     AssetStatistics.objects.create(
        #         asset=None,
        #         cur_department=dp,
        #         cur_user=None,
        #         cur_price=tot_price_amount,
        #         cur_time=timezone.now() + timezone.timedelta(hours=8),
        #         cur_status=511529,
        #         cur_count=tot_cnt_amount,
        #     )
        #     AssetStatistics.objects.create(
        #         asset=None,
        #         cur_department=dp,
        #         cur_user=None,
        #         cur_price=tot_price,
        #         cur_time=timezone.now() + timezone.timedelta(hours=8),
        #         cur_status=501113,
        #         cur_count=tot_cnt,
        #     )
        # print(
        #     f"OK, asset statistics have been made for all assets in the database automatically by Luca1K's ROBOT at {datetime.now()} :)"
        # )
        # # print(list(AssetStatistics.objects.all()))
        depreciation_job()
        statistics_job()
        # for Ass in AssetStatistics.objects.all():
        #     print(Ass.cur_count)
        #     print(Ass.cur_price)
        #     print(Ass.cur_status)
        #     print(Ass.cur_time)

    def test_get_asset_user_list(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset(
            session,
            0,
            "Trident",
            1,
            "steve",
            50.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )
        user_session = self.user_login("steve", "minecraft").json()["data"]["session"]
        self.post_asset(
            session,
            0,
            "Trident1",
            1,
            "steve",
            50.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )
        self.post_asset(
            session,
            0,
            "Trident2",
            1,
            "steve",
            50.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )

        self.post_asset(
            session,
            0,
            "Trident3",
            1,
            "steve",
            50.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )
        res = self.get_asset(user_session, 1)
        self.assertEqual(len(res.json()["data"]), 6)
        self.assertEqual(res.json()["pages"], 2)
        res = self.get_asset(user_session, 2)
        self.assertEqual(len(res.json()["data"]), 2)

    def test_get_sub_asset_tree(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.get_sub_asset_tree("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "电子产品")
        self.assertEqual(res.json()["code"], 1)
        res = self.get_sub_asset_tree(session, "b_all_")
        self.assertEqual(res.json()["code"], 2)
        res = self.get_sub_asset_tree(session, "默认分类")
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 2)
        self.assertEqual(res.json()["data"][0]["name"], "条目型资产")
        res = self.get_sub_asset_tree(session, "木制品")
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 2)
        self.assertEqual(res.json()["data"][0]["name"], "椅子")
        res = self.user_login("steve", "minecraft")
        session = res.json()["data"]["session"]
        res = self.get_sub_asset_tree(session, "木制品")
        self.assertEqual(res.json()["info"], "Succeed")

    def test_delete_sub_asset_tree(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]

        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.delete_sub_asset_tree("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "cst")
        self.assertEqual(res.json()["code"], 1)
        res = self.delete_sub_asset_tree(session, "b_all")
        self.assertEqual(res.json()["code"], 2)
        res = self.delete_sub_asset_tree(session, "电子产品")
        self.assertEqual(res.json()["code"], 2)
        res = self.delete_sub_asset_tree(session, "椅子")
        self.assertEqual(res.json()["code"], 0)
        deleted_node = AssetTree.objects.filter(name="椅子").first()
        self.assertEqual(deleted_node, None)
        res = self.user_login("steve", "minecraft")
        session = res.json()["data"]["session"]
        res = self.delete_sub_asset_tree(session, "木制品")
        self.assertEqual(res.json()["info"], "您无此权限")

    def test_get_asset_tree_root(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.get_asset_tree_root("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "b")
        self.assertEqual(res.json()["code"], 1)
        res = self.get_asset_tree_root(session, "b_all")
        self.assertEqual(res.json()["code"], 2)
        entity1 = Entity(name="mit")
        entity1.save()
        department1 = Department(name="c", entity=entity1)
        department1.save()
        res = self.get_asset_tree_root(session, "c")
        self.assertEqual(res.json()["info"], "资产分类不存在")
        res = self.get_asset_tree_root(session, "b")
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(res.json()["data"]["name"], "默认分类")
        res = self.user_login("steve", "minecraft")
        session = res.json()["data"]["session"]
        res = self.get_asset_tree_root(session, "b")
        self.assertEqual(res.json()["info"], "Succeed")

    def test_post_asset_logic(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")

        res = self.post_asset(
            session,
            0,
            "DiamondSword",
            1,
            "green",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "指定资产挂账人不处于当前部门(错误序号：[0])",
        )

        res = self.post_asset(
            session,
            0,
            "StoneSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "fuck 默认分类",
            "b",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "未找到指定层级分类(错误序号：[0])",
        )

        res = self.post_asset(
            session,
            0,
            "StoneSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "fuck",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "对应部门不存在(错误序号：[0])",
        )

        res = self.post_asset(
            session,
            0,
            "StoneSword",
            1,
            "jinjin",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "未找到该资产挂账人(错误序号：[0])",
        )

        res = self.post_asset(
            session,
            0,
            "StoneSword",
            1,
            "tom",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "指定资产挂账人不处于当前部门(错误序号：[0])",
        )

        res = self.post_asset(
            session,
            0,
            "Sword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        self.assertEqual(res.json()["code"], 0)
        res = self.post_asset(
            session,
            0,
            "Swordnewnew",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "木制品",
            "b",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "资产类别与层级分类不匹配(错误序号：[0])",
        )

    def test_post_pending_request(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        res = self.user_login("green", "minecraft")
        session2 = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")

        res = self.post_asset(
            session,
            0,
            "GoldSword",
            1,
            "asset_manager",
            10.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

        res = self.post_pending_request(
            "sbxlx",
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "用户的会话标识符信息不正确",
        )
        res = self.post_pending_request(
            "sbopxlxsbopxlxsbopxlxsbopxlxsbop",
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        res = self.post_pending_request(
            session1,
            "steven",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "提交请求的用户不存在",
        )
        res = self.post_pending_request(
            session2,
            "green",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "提交请求的用户的角色不合法",
        )
        res = self.post_pending_request(
            session2,
            "green",
            "sb_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "提交请求的用户的角色不合法",
        )
        res = self.post_pending_request(
            session2,
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Hacker detected!",
        )
        res = self.post_pending_request(
            session1,
            "steve",
            "green",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "所涉及的资产不存在",
        )
        res = self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            5,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "申请类型不合法",
        )
        res = self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        self.user_login("yueyue", "yueyue")
        # self.user_login("haohao", "haohao")
        yueyue = User.objects.filter(name="yueyue").first()
        # haohao = User.objects.filter(name="haohao").first()
        # print(Asset.objects.filter(id=5).first().count)
        res = self.post_pending_request(
            yueyue.session,
            "yueyue",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        self.put_return_pending_request(session, 1, 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        # print(Asset.objects.filter(id=5).first().count)
        ta = Asset.objects.filter(id=5).first()
        self.receive_asset(session, 5, "steve", 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        ta.refresh_from_db()
        # print(ta.count)
        res = self.get_pending_request_list(session, "asset_manager")
        # print(res.json()["data"])
        res = self.get_pending_request_list(yueyue.session, "asset_manager")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        pr = PendingRequests.objects.filter(id=2).first()
        # print(pr.valid)
        res = self.put_return_pending_request(session, 2, 1)
        self.assertEqual(
            res.json()["info"],
            "该审批单已失效，无法通过此申请",
        )

    def test_pending_request_list(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        res = self.user_login("green", "minecraft")
        res = self.user_login("cutestYue", "mysister")
        session3 = res.json()["data"]["session"]
        res = self.get_pending_request_list(session, "green")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.get_pending_request_list(session3, "green")
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        res = self.get_pending_request_list("sbxlx", "green")
        self.assertEqual(
            res.json()["info"],
            "用户的会话标识符信息不正确",
        )
        res = self.post_asset(
            session,
            0,
            "Trident",
            1,
            "asset_manager",
            50.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.post_asset(
            session,
            0,
            "Trident",
            0,
            "asset_manager",
            50.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )

        self.assertEqual(
            res.json()["info"],
            "资产类别错误(错误序号：[0])",
        )

        res = self.post_asset(
            session,
            0,
            "Boat",
            0,
            "asset_manager",
            500.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        boad_id = Asset.objects.filter(name="Boat").first().id
        res = self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            boad_id,
            1,
            2,
        )
        self.assertEqual(
            res.json()["info"],
            "资产Boat不是数量型资产，请重新检查",
        )
        res = self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            1,
            2,
        )
        self.assertEqual(
            res.json()["info"],
            "资产Trident数量不足",
        )
        res = self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.get_pending_request_list(session, "asset_manager")
        self.assertEqual(
            res.json()["data"][0]["initiatorName"],
            "steve",
        )
        self.assertEqual(
            res.json()["data"][0]["assetID"],
            5,
        )

    def test_return_pending_request(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        res = self.user_login("green", "minecraft")
        session2 = res.json()["data"]["session"]
        res = self.post_asset(
            session,
            0,
            "Trident",
            1,
            "asset_manager",
            50.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.put_return_pending_request(
            "cutestYue",
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "用户的会话标识符信息不正确",
        )
        res = self.put_return_pending_request(
            "HeiFentzHeiFentzHeiFentzHeiFentz",
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        res = self.put_return_pending_request(
            session,
            2,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "资产管理员下的该请求不存在",
        )
        res = self.put_return_pending_request(
            session,
            1,
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

    def test_maintain_related(self):
        global verify_check
        verify_check[0] = 1
        yueyue = User.objects.filter(name="yueyue").first()
        manager = User.objects.filter(name="LYiQian").first()
        # res = self.get_all_departments(yueyue.session, "b")
        # self.assertEqual(
        #     res.json()["info"],
        #     "Succeed",
        # )
        res = self.user_login("LYiQian", "luca1k")
        session = res.json()["data"]["session"]
        res = self.post_asset(
            session,
            0,
            "Love",
            1,
            "yueyue",
            999999.98,
            "",
            "",
            0,
            529,
            "默认分类",
            "cst",
            1353,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        love = Asset.objects.filter(name="Love").first()
        PendingRequests.objects.create(
            initiator=yueyue,
            participant=manager,
            target=None,
            asset=love,
            type=3,
            result=0,
            request_time=timezone.now(),
            review_time=timezone.now(),
            count=9,
        )
        req_id = PendingRequests.objects.filter(initiator=yueyue, result=0).first().id
        res = self.put_return_pending_request(session, req_id, 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        self.assertEqual(
            love.user,
            yueyue,
        )
        love.refresh_from_db()
        maintain_love = Asset.objects.filter(name="Love", user=manager).first()
        self.assertEqual(
            love.count,
            520,
        )
        self.assertEqual(
            maintain_love.count,
            9,
        )
        PendingRequests.objects.create(
            initiator=yueyue,
            participant=manager,
            target=None,
            asset=love,
            type=3,
            result=0,
            request_time=timezone.now(),
            review_time=timezone.now(),
            count=20,
        )
        req_id = PendingRequests.objects.filter(count=20, type=3).first().id
        res = self.put_return_pending_request(session, req_id, 1)
        love.refresh_from_db()
        maintain_love = Asset.objects.filter(name="Love", user=manager).all()[1]
        self.assertEqual(
            love.count,
            500,
        )
        self.assertEqual(
            maintain_love.count,
            20,
        )
        len_maintain_love = len(Asset.objects.filter(user=manager).all())
        self.assertEqual(
            len_maintain_love,
            2,
        )
        res = self.post_asset(
            session,
            0,
            "Friendship",
            0,
            "yueyue",
            999999.98,
            "",
            "",
            0,
            1,
            "默认分类",
            "cst",
            1353,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.all_item_assets(session, 0)
        self.assertEqual(
            res.json()["data"],
            [],
        )
        friendship = Asset.objects.filter(name="Friendship").first()
        friendship.user = manager
        friendship.save()
        res = self.all_item_assets(session, 0)
        self.assertEqual(
            res.json()["data"],
            [{"id": 8, "name": "Friendship"}],
        )
        res = self.all_item_assets(session, love.id)
        # print(love.id)
        # print(love.department)
        # print(love.name)
        # print(love.user)
        # print(manager.department)
        self.assertEqual(
            res.json()["data"],
            [],
        )
        friendship.user = yueyue
        friendship.save()
        res = self.all_item_assets(session, love.id)
        self.assertEqual(
            res.json()["data"],
            [{"id": 8, "name": "Friendship"}],
        )
        PendingRequests.objects.create(
            initiator=yueyue,
            participant=manager,
            target=None,
            asset=friendship,
            type=3,
            result=0,
            request_time=timezone.now(),
            review_time=timezone.now(),
            count=1,
        )
        self.assertEqual(
            friendship.status,
            1,
        )
        req_id = PendingRequests.objects.filter(asset=friendship, type=3).first().id
        res = self.put_return_pending_request(session, req_id, 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        friendship.refresh_from_db()
        self.assertEqual(
            friendship.user.name,
            "LYiQian",
        )
        self.assertEqual(
            friendship.status,
            3,
        )
        res = self.get_maintain_list(session)
        # self.assertEqual(
        #     res.json()["info"],
        #     "okok"
        # )
        self.assertEqual(
            len(res.json()["data"]),
            3,
        )
        res = self.maintain_asset(session, 6, "yueyue", 99999, 529113, 9)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        yueyue_asset = Asset.objects.filter(user=yueyue).all()
        res = self.maintain_asset(session, 7, "yueyue", 99999, 529113, 20)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        yueyue_asset = Asset.objects.filter(user=yueyue, name="Love").all()
        self.assertEqual(
            yueyue_asset[1].count,
            29,
        )
        res = self.maintain_asset(session, 8, "yueyue", 99999, 529113, 20)
        self.assertEqual(
            res.json()["info"],
            "资产Friendship数量错误",
        )
        res = self.maintain_asset(session, 8, "yueyue", 99999, 529113, 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        yueyue_asset = Asset.objects.filter(name="Friendship").all()
        self.assertEqual(
            yueyue_asset[0].price,
            529113,
        )

    def test_post_asset_permissions(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.post_asset(
            "GTA6",
            0,
            "AK47",
            1,
            "green",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )

        res = self.post_asset(
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            0,
            "M4A1",
            1,
            "green",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

        res = self.post_asset(
            session1,
            0,
            "Shit",
            1,
            "green",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

        res = self.post_asset(
            session,
            0,
            "RedStone",
            1,
            "tom",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "cst",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )

        res = self.post_asset(
            session,
            0,
            "GoldBlock",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.post_asset(
            session,
            0,
            "GoldBlock",
            0,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "资产类别错误(错误序号：[0])",
        )

        res = self.post_asset(
            session,
            0,
            "GoldBlock",
            1,
            "steve",
            10.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )

        self.assertEqual(
            res.json()["info"],
            "GoldBlock的初始价格应当为：1.00(错误序号：[0])",
        )

    def test_put_asset(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.put_asset(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            1,
            0,
            "DiamondSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 1)
        res = self.put_asset(
            session,
            7,
            0,
            "DiamondSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["info"], "指定ID的资产不存在")
        res = self.put_asset(
            session,
            1,
            0,
            "DiamondSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "b_all",
            "b",
        )
        self.assertEqual(
            res.json()["info"],
            "该部门下不存在该名称的资产分类",
        )
        res = self.put_asset(
            session,
            1,
            0,
            "DiamondSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "电子产品",
            "b",
        )
        self.assertEqual(res.json()["code"], 0)
        asset = Asset.objects.filter(id=1).first()
        self.assertEqual(asset.assetTree.name, "电子产品")
        res = self.put_asset(
            session,
            2,
            0,
            "chair",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "木制品",
            "b",
        )
        self.assertEqual(
            res.json()["info"],
            "资产类型(条目型/数量型)与所选层级分类不匹配",
        )
        res = self.put_asset(
            session,
            2,
            0,
            "chair",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "钢铁制品",
            "b",
        )
        asset = Asset.objects.filter(id=2).first()
        self.assertEqual(asset.assetTree.name, "钢铁制品")
        asset_tree = AssetTree.objects.filter(name="默认分类").first()
        assets = Asset.objects.filter(assetTree=asset_tree).all()
        self.assertEqual(len(assets), 2)
        res = self.user_login("steve", "minecraft")
        session = res.json()["data"]["session"]
        res = self.put_asset(
            session,
            2,
            0,
            "chair",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "桌子",
            "b",
        )
        self.assertEqual(res.json()["info"], "您无此权限")

    def test_put_asset2(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "默认分类", "b")
        self.post_asset_tree(session, "木制品", "默认分类", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "默认分类", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.put_asset(
            session,
            1,
            0,
            "GoldSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 0)
        asset = Asset.objects.filter(id=1).first()
        self.assertEqual(asset.name, "GoldSword")
        res = self.put_asset(
            session,
            1,
            0,
            "GoldSword",
            0,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 2)
        res = self.put_asset(
            session,
            1,
            0,
            "GoldSword",
            1,
            "asset_manager",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["info"], "无法在维护资产信息中修改资产所有者")
        res = self.put_asset(
            session,
            1,
            0,
            "bed",
            1,
            "asset_manager",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 2)
        asset = Asset.objects.filter(id=1).first()
        self.assertEqual(asset.user.name, "steve")
        res = self.put_asset(
            session,
            1,
            0,
            "GoldSword",
            1,
            "green",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 2)
        res = self.put_asset(
            session,
            1,
            0,
            "GoldSword",
            1,
            "steve",
            100.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 0)
        res = self.count_department_asset(session)
        self.assertEqual(
            res.json()["data"][0]["count_amount"],
            4,
        )
        res = self.count_status_asset(session)
        self.assertEqual(
            res.json()["data"][0]["type"],
            "expire",
        )
        res = self.info_curve(session, 1, 1)
        self.assertEqual(
            res.json()["data"],
            [],
        )
        res = self.count_price_curve(session, 1)
        self.assertEqual(
            res.json()["data_item"],
            [],
        )
        res = self.count_price_curve(session, 2)
        self.assertEqual(
            res.json()["data_item"],
            [],
        )
        manager = User.objects.filter(name="asset_manager").first()
        gs = Asset.objects.filter(name="GoldSword").first()
        AssetStatistics.objects.create(
            asset=None,
            cur_department=manager.department,
            cur_user=None,
            cur_price=2002.529 + float(gs.price) * float(gs.count),
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=529113,
            cur_count=529113,
        )
        test_decimal = 0.00
        test_decimal = float(gs.price) + float(gs.price)
        AssetStatistics.objects.create(
            asset=None,
            cur_department=manager.department,
            cur_user=manager,
            cur_price=2019.501 + test_decimal,
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=511529,
            cur_count=511529,
        )
        AssetStatistics.objects.create(
            asset=None,
            cur_department=manager.department,
            cur_user=manager,
            cur_price=2023.113,
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=501113,
            cur_count=501113,
        )
        res = self.count_price_curve(session, 1)
        self.assertEqual(
            res.json()["data_item"][0]["cur_count"],
            529113,
        )
        self.assertEqual(
            res.json()["data_amount"][0]["cur_count"],
            511529,
        )
        self.assertEqual(
            res.json()["data_total"][0]["cur_count"],
            501113,
        )
        self.assertEqual(
            res.json()["data_item"][0]["cur_price"],
            "2102.53",
        )
        self.assertEqual(
            res.json()["data_amount"][0]["cur_price"],
            "2219.50",
        )
        self.assertEqual(
            res.json()["data_total"][0]["cur_price"],
            "2023.11",
        )
        asset = Asset.objects.filter(id=1).first()
        self.assertEqual(asset.price, 100.0)
        res = self.put_asset(
            session,
            1,
            0,
            "GoldSword",
            1,
            "steve",
            100.0,
            "",
            "",
            1,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(res.json()["code"], 2)

    def test_get_asset_tree_node(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.post_asset(
            session,
            0,
            "Shit",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.post_asset(
            session,
            0,
            "Shit1",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.post_asset(
            session,
            0,
            "Shit2",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.post_asset(
            session,
            0,
            "Shit3",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.post_asset(
            session,
            0,
            "Shit4",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.get_asset_tree_node("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "默认分类", 1, 0)
        self.assertEqual(res.json()["code"], 1)
        res = self.get_asset_tree_node(session, "b_all", 1, 0)
        res = self.get_asset_tree_node(session, "默认分类", 1, 0)
        self.assertEqual(res.json()["info"], "Succeed")
        self.assertEqual(len(res.json()["data"]), 6)
        res = self.get_asset_tree_node(session, "默认分类", 2, 0)
        self.assertEqual(len(res.json()["data"]), 3)
        self.put_asset(
            session,
            1,
            0,
            "DiamondSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "电子产品",
            "b",
        )
        self.put_asset(
            session,
            2,
            0,
            "chair",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "木制品",
            "b",
        )
        self.put_asset(
            session,
            3,
            0,
            "goldaxe",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "椅子",
            "b",
        )
        res = self.put_asset(
            session,
            4,
            0,
            "bed",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "电子产品",
            "b",
        )
        res = self.get_asset_tree_node(session, "电子产品", 1, 0)
        self.assertEqual(len(res.json()["data"]), 2)
        self.put_asset(
            session,
            3,
            0,
            "goldaxe",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "电子产品",
            "b",
        )
        res = self.get_asset_tree_node(session, "电子产品", 1, 0)
        self.assertEqual(len(res.json()["data"]), 3)
        res = self.get_asset_tree_node(session, "桌子", 1, 0)
        self.assertEqual(len(res.json()["data"]), 0)
        res = self.user_login("steve", "minecraft")
        session = res.json()["data"]["session"]
        res = self.get_asset_tree_node(session, "电子产品", 1, 0)
        self.assertEqual(res.json()["info"], "您无此权限")

    def test_get_operationjournal_asset(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset_tree(session, "电子产品", "数量型资产", "b")
        self.post_asset_tree(session, "木制品", "条目型资产", "b")
        self.post_asset_tree(session, "电脑", "电子产品", "b")
        self.post_asset_tree(session, "钢铁制品", "数量型资产", "b")
        self.post_asset_tree(session, "椅子", "木制品", "b")
        self.post_asset_tree(session, "桌子", "木制品", "b")
        res = self.user_login("cutestYue", "mysister")
        session = res.json()["data"]["session"]
        res1 = self.get_operationjournal(session, "a", 1)
        self.assertTrue(len(res1.json()["data"]) == 6)
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.put_asset(
            session,
            1,
            0,
            "DiamondSword",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "电子产品",
            "b",
        )
        self.put_asset(
            session,
            2,
            0,
            "chair",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "钢铁制品",
            "b",
        )
        res = self.user_login("cutestYue", "mysister")
        session = res.json()["data"]["session"]
        res2 = self.get_operationjournal(session, "a", 1)
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        # for a in res2.json()["data"]:
        #     print(a["message"])
        res = self.put_asset(
            session,
            2,
            0,
            "chair",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "钢铁制品",
            "b",
        )
        self.assertEqual(
            res.json()["info"],
            "没有作修改 :)",
        )
        res = self.user_login("cutestYue", "mysister")
        session = res.json()["data"]["session"]
        self.assertEqual(len(res2.json()["data"]), 8)
        res2 = self.get_operationjournal(session, "a", 2)
        self.assertEqual(len(res2.json()["data"]), 6)
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.delete_sub_asset_tree(session, "椅子")
        self.delete_sub_asset_tree(
            session,
            "电脑",
        )
        res = self.user_login("cutestYue", "mysister")
        session = res.json()["data"]["session"]
        res3 = self.get_operationjournal(session, "a", 2)
        self.assertEqual(len(res3.json()["data"]), 8)
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.put_asset(
            session,
            2,
            0,
            "chairs",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "钢铁制品",
            "b",
        )
        res = self.user_login("cutestYue", "mysister")
        session = res.json()["data"]["session"]
        res3 = self.get_operationjournal(session, "a", 1)
        self.assertEqual(res3.json()["pages"], 3)

    def test_get_asset_user(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.get_asset_user("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "steve", 1)
        self.assertEqual(res.json()["code"], 1)
        res = self.get_asset_user(session, 1, 1)
        self.assertEqual(res.json()["code"], 2)
        self.assertEqual(
            res.json()["info"],
            "指定名称的用户不存在",
        )
        res = self.get_asset_user("Luca1K's sons——lsn,xpy,xlx,zkw", 1, 1)
        self.assertEqual(res.json()["code"], 2)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_asset_user(session, "steve", 1)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 4)
        res = self.put_asset(
            session,
            1,
            0,
            "DiamondSword",
            1,
            "asset_manager",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
        )
        self.assertEqual(
            res.json()["info"],
            "无法在维护资产信息中修改资产所有者",
        )
        res = self.get_asset_user(session, "steve", 1)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 4)
        res = self.get_asset_user(session, "asset_manager", 1)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 0)
        res = self.post_asset(
            session,
            0,
            "Shit3",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.post_asset(
            session,
            0,
            "Shit4",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.post_asset(
            session,
            0,
            "Shit5",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.post_asset(
            session,
            0,
            "Shit6",
            1,
            "steve",
            1.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.get_asset_user(session, "steve", 1)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 6)
        self.assertEqual(res.json()["pages"], 2)
        res = self.get_asset_user(session, "steve", 2)
        self.assertEqual(len(res.json()["data"]), 2)

    def test_allot_asset(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.allot_asset("aa", 1, "asset_manager", 1)
        self.assertEqual(res.json()["code"], 2)
        res = self.allot_asset("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1, "steve", 1)
        self.assertEqual(res.json()["code"], 1)
        res = self.allot_asset(session, 1, "steve", 1)
        self.assertEqual(res.json()["info"], "你只能调拨资产给资产管理员")
        res = self.allot_asset(session, 1, "poole", 3)
        self.assertEqual(
            res.json()["info"],
            "资产 DiamondSword 数量不足",
        )
        res = self.allot_asset(session, 1, "poole", 1)
        self.assertEqual(res.json()["code"], 0)
        poole = User.objects.filter(name="poole").first()
        pid = Asset.objects.filter(user=poole).first().id
        res = self.allot_asset(session, pid, "poole", 1)
        self.assertEqual(
            res.json()["info"],
            "没有作资产的调拨",
        )
        res = self.allot_asset(session, 1, "green", 1)
        self.assertEqual(res.json()["code"], 0)
        user = User.objects.filter(name="steve").first()
        assets = Asset.objects.filter(user=user, expire=0, count__gt=0).all()
        self.assertEqual(len(assets), 3)
        asset = Asset.objects.filter(id=6).first()
        self.assertEqual(asset.department.name, "cst")
        self.assertEqual(asset.assetTree.name, "默认分类")
        self.assertEqual(asset.user.name, "green")
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.allot_asset(session, 1, "green", 1)
        self.assertEqual(res.json()["code"], 1)

    def test_return_asset(self):
        global verify_check
        verify_check[0] = 1
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.return_asset("aa", 1, "asset_manager", 1)
        self.assertEqual(res.json()["code"], 2)
        res = self.return_asset(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1, "asset_manager", 1
        )
        self.assertEqual(res.json()["code"], 1)
        res = self.return_asset(session, 1, "asset_manager", 1)
        self.assertEqual(res.json()["info"], "只有用户可以退库资产")
        res = self.return_asset(session, 1, "lsn", 1)
        self.assertEqual(res.json()["code"], 2)
        res = self.return_asset(session, 1, "steve", 1)
        self.assertEqual(res.json()["code"], 0)
        asset = Asset.objects.filter(id=5).first()
        self.assertEqual(asset.user.name, "asset_manager")
        user = User.objects.filter(name="steve").first()
        assets = Asset.objects.filter(user=user).all()
        self.assertEqual(len(assets), 4)
        res = self.return_asset(session, 1, "tom", 1)
        self.assertEqual(
            res.json()["info"],
            "退库者和资产管理员不在一个部门下.",
        )
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.return_asset(session, 1, "steve", 1)
        self.assertEqual(res.json()["code"], 1)

    def test_receive_asset(self):
        global verify_check
        verify_check[0] = 1
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.receive_asset("aa", 1, "asset_manager", 1)
        self.assertEqual(res.json()["code"], 2)
        res = self.receive_asset(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1, "asset_manager", 1
        )
        self.assertEqual(res.json()["code"], 1)
        res = self.receive_asset(session, 1, "asset_manager", 1)
        self.assertEqual(res.json()["info"], "只有用户可以领用资产")
        self.return_asset(session, 1, "steve", 1)
        asset = Asset.objects.filter(id=5).first()
        self.assertEqual(asset.user.name, "asset_manager")
        res = self.receive_asset(session, 1, "lsn", 1)
        self.assertEqual(res.json()["code"], 2)
        res = self.receive_asset(session, 1, "steve", 3)
        self.assertEqual(
            res.json()["info"],
            "资产 DiamondSword 数量不足",
        )
        res = self.receive_asset(session, 1, "steve", 0)
        self.assertEqual(
            res.json()["info"],
            "请不要浪费时间 :)",
        )
        res = self.receive_asset(session, 1, "steve", 1)
        self.assertEqual(res.json()["code"], 0)
        asset = Asset.objects.filter(id=5).first()
        self.assertEqual(asset.user.name, "asset_manager")
        res = self.return_asset(session, 5, "tom", 1)
        self.assertEqual(
            res.json()["info"],
            "退库者和资产管理员不在一个部门下.",
        )
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.receive_asset(session, 1, "steve", 1)
        self.assertEqual(res.json()["code"], 1)

    def test_transfer_asset(self):
        global verify_check
        verify_check[0] = 1
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.post_asset(
            session,
            0,
            "Love",
            0,
            "haohao",
            999999.98,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            999999,
        )
        res = self.post_asset(
            session,
            5,
            "Love2",
            0,
            "haohao",
            999999.98,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            999999,
        )
        res = self.post_asset(
            session,
            6,
            "Love3",
            0,
            "haohao",
            999999.98,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            999999,
        )
        res = self.transfer_asset("aa", 1, "haohao", "yueyue", 1)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.transfer_asset(
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1, "haohao", "yueyue", 1
        )
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        love = Asset.objects.filter(name="Love").first().id
        res = self.transfer_asset(session, love, "haohao", "yueyue", 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.get_history_list(session, love, 1)
        self.assertEqual(res.json()["data"][0]["message"], "资产转移到了 cst 的 yueyue")
        yueyue = User.objects.filter(name="yueyue").first()
        haohao = User.objects.filter(name="haohao").first()
        self.assertEqual(
            len(list(Asset.objects.filter(user=yueyue).all())),
            3,
        )
        self.assertEqual(
            Asset.objects.filter(user=yueyue).first().department.name,
            "cst",
        )
        res = self.post_asset(
            session,
            0,
            "qlove",
            1,
            "haohao",
            999999.98,
            "",
            "",
            0,
            520,
            "默认分类",
            "b",
            999999,
        )
        res = self.post_asset(
            session,
            0,
            "qqlove",
            1,
            "haohao",
            999999.98,
            "",
            "",
            0,
            520,
            "默认分类",
            "b",
            999999,
        )
        res = self.user_login("green", "minecraft")
        session_1 = res.json()["data"]["session"]
        res = self.post_asset(
            session_1,
            0,
            "qlove",
            1,
            "yueyue",
            999999.98,
            "",
            "",
            0,
            520,
            "默认分类",
            "cst",
            999999,
        )
        love = Asset.objects.filter(user=haohao, name="qlove").first()
        love.status = 2
        love.save()
        love2 = Asset.objects.filter(user=yueyue, name="qlove").first()
        love2.status = 2
        love2.save()
        res = self.transfer_asset(session, love.id, "haohao", "yueyue", 520)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.assertEqual(
            Asset.objects.filter(name="qlove", user=yueyue).first().count,
            1040,
        )
        res = self.assertEqual(
            Asset.objects.filter(name="qlove", user=haohao).first().count,
            0,
        )
        love = Asset.objects.filter(user=haohao, name="qqlove").first().id
        res = self.transfer_asset(session, love, "haohao", "yueyue", 320)
        res = self.assertEqual(
            Asset.objects.filter(name="qqlove", user=yueyue).first().count,
            320,
        )
        res = self.assertEqual(
            Asset.objects.filter(name="qqlove", user=haohao).first().count,
            200,
        )
        res = self.post_asset(
            session,
            0,
            "grass",
            1,
            "haohao",
            999999.98,
            "",
            "",
            0,
            64,
            "默认分类",
            "b",
            999999,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        grass = Asset.objects.filter(name="grass").first().id
        res = self.transfer_asset(session, grass, "haohao", "steve", 63)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.transfer_asset(session, grass, "haohao", "steve", 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.post_asset(
            session,
            0,
            "grassitem",
            0,
            "haohao",
            999999.98,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            999999,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        grassitem = Asset.objects.filter(name="grassitem").first().id
        res = self.transfer_asset(session, grassitem, "haohao", "steve", 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

    def test_asset_expire(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res1 = self.expire_asset(session, 1, 3)
        self.assertEqual(
            res1.json()["info"],
            "资产 DiamondSword 数量不足",
        )
        res1 = self.expire_asset(20190501, 1, 1)
        self.assertEqual(
            res1.json()["info"],
            "您给出的session ID是非法的。",
        )
        res1 = self.expire_asset("20190501201905012019050120190501", 1, 1)
        self.assertEqual(
            res1.json()["info"],
            "您无此权限",
        )
        res1 = self.expire_asset(session, 1, -1)
        self.assertEqual(
            res1.json()["info"],
            "请不要浪费时间",
        )
        res1 = self.expire_asset(session, 1, 1)
        self.assertEqual(res1.json()["code"], 0)
        asset1 = Asset.objects.filter(id=1).first()
        self.assertEqual(asset1.expire, 0)
        self.assertEqual(asset1.price, 5.00)
        self.expire_asset(session, 2, 1)
        self.expire_asset(session, 3, 1)
        self.expire_asset(session, 4, 1)
        asset2 = Asset.objects.filter(id=2).first()
        asset3 = Asset.objects.filter(id=3).first()
        asset4 = Asset.objects.filter(id=4).first()
        self.assertEqual(asset2.count, 0)
        self.assertEqual(asset3.count, 0)
        self.assertEqual(asset4.count, 0)

    def test_asset_manager_entity(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res1 = self.user_login("steve", "minecraft")
        session1 = res1.json()["data"]["session"]
        res = self.get_asset_manager_entity("Hacker", "a")
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_asset_manager_entity("mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm", "a")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_asset_manager_entity(session1, "a")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_asset_manager_entity(session, "pokemmo")
        self.assertEqual(
            res.json()["info"],
            "未发现目标业务实体",
        )
        res = self.get_asset_manager_entity(session, "a")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

    def test_get_asset_manager(self):
        res = self.user_login("manager", "1919810")
        session = res.json()["data"]["session"]
        res = self.get_asset_manager("Hacker", "b")
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res1 = self.user_login("steve", "minecraft")
        session1 = res1.json()["data"]["session"]
        res = self.get_asset_manager(session1, "cst")
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_asset_manager(session1, "sb")
        self.assertEqual(
            res.json()["info"],
            "未找到目标部门",
        )
        res = self.get_asset_manager(session, "b")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.get_asset_manager(session1, "b")
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        self.assertEqual(
            res.json()["data"],
            [
                {
                    "id": 3,
                    "name": "asset_manager",
                },
                {
                    "id": 5,
                    "name": "poole",
                },
            ],
        )

    def test_get_unallocated_asset(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res1 = self.user_login("steve", "minecraft")
        session1 = res1.json()["data"]["session"]
        res = self.get_unallocated_asset("GengarQ", "asset_manager", 1)
        self.assertEqual(
            res.json()["info"],
            "您给出的session ID是非法的。",
        )
        res = self.get_unallocated_asset(
            "dddddddddddddddddddddddddddddddd", "asset_manager", 1
        )
        self.assertEqual(
            res.json()["info"],
            "您无此权限",
        )
        res = self.get_unallocated_asset(session1, "XinYue", 1)
        self.assertEqual(
            res.json()["info"],
            "未找到目标资产管理员",
        )
        res = self.get_unallocated_asset(session1, "green", 1)
        self.assertEqual(
            res.json()["info"],
            "不要向非自己部门的资产管理员请求领用资产 :(",
        )
        res = self.get_unallocated_asset(session1, "kyrie", 1)
        self.assertEqual(
            res.json()["info"],
            "目标不是资产管理员 :(",
        )
        res = self.get_unallocated_asset(session1, "asset_manager", 1)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        self.assertEqual(
            res.json()["data"],
            [],
        )
        manager = User.objects.filter(name="asset_manager").first()
        btree = AssetTree.objects.filter(name="默认分类").first()
        db = Department.objects.filter(name="b").first()
        asset5 = Asset(
            name="Beef",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        )
        asset5.save()
        Asset(
            name="Beef1",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        ).save()
        Asset(
            name="Beef2",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        ).save()
        Asset(
            name="Beef4",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        ).save()
        Asset(
            name="Beef5",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        ).save()
        Asset(
            name="Beef6",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        ).save()
        Asset(
            name="Beef7",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        ).save()
        Asset(
            name="Beef8",
            assetClass=1,
            user=manager,
            price=5.0,
            description="",
            position="manager's box",
            expire=0,
            assetTree=btree,
            department=db,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        ).save()
        res = self.get_unallocated_asset(session1, "asset_manager", 1)
        self.assertEqual(len(res.json()["data"]), 6)
        self.assertEqual(res.json()["pages"], 2)
        res = self.get_unallocated_asset(session1, "asset_manager", 2)
        self.assertEqual(len(res.json()["data"]), 2)

    def test_put_warning(self):
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        bed = Asset.objects.filter(name="bed").first()
        res = self.put_warning(session, 1, 4, bed.id if bed else 0)
        self.assertEqual(res.json()["info"], "Succeed")
        chair = Asset.objects.filter(name="chair").first()
        res = self.put_warning(session, 2, 5, chair.id if chair else 0)
        self.assertEqual(res.json()["code"], 0)
        self.post_asset(
            session,
            0,
            "table",
            0,
            "steve",
            11.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        table = Asset.objects.filter(name="table").first()
        res = self.put_warning(session, 2, 10, table.id if table else 0)
        self.assertEqual(res.json()["code"], 3)
        res = self.get_warning(session, 1)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 5)
        self.assertEqual(res.json()["data"][1]["warning_date"], 2)
        self.assertEqual(res.json()["data"][3]["warning_date"], 1)

    def test_get_warning_list(self):
        user2 = User.objects.filter(name="steve").first()
        department1 = Department.objects.filter(name="b").first()
        root_node = AssetTree.objects.filter(name="默认分类").first()
        test_asset1 = Asset(
            name="shit",
            assetClass=1,
            user=user2,
            count=10,
            price=5.0,
            description="",
            position="steve's bag",
            expire=0,
            assetTree=root_node,
            department=department1,
            create_time=timezone.now().date() - timezone.timedelta(days=8),
            initial_price=5.0,
            deadline=9,
            warning_date=2,
            warning_amount=5,
        )
        test_asset1.save()
        test_asset2 = Asset(
            name="shit2",
            assetClass=1,
            user=user2,
            count=10,
            price=5.0,
            description="",
            position="steve's bag",
            expire=0,
            assetTree=root_node,
            department=department1,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
            warning_date=2,
            warning_amount=20,
        )
        test_asset2.save()
        test_asset3 = Asset(
            name="shit3",
            assetClass=1,
            user=user2,
            count=10,
            price=5.0,
            description="",
            position="steve's bag",
            expire=0,
            assetTree=root_node,
            department=department1,
            create_time=timezone.now().date(),
            initial_price=5.0,
            deadline=9,
        )
        test_asset3.save()
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        res = self.get_warning_list("aa")
        self.assertEqual(res.json()["code"], 2)
        res = self.get_warning_list("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        self.assertEqual(res.json()["code"], 1)
        res = self.get_warning_list(session)
        self.assertEqual(res.json()["info"], "Succeed")
        # print(list(res.json()["data"]))
        self.assertEqual(len(res.json()["data"]), 2)
        self.assertEqual(res.json()["data"][0]["name"], "shit")
        self.assertEqual(res.json()["data"][1]["name"], "shit2")
        res = self.get_warning_list(session)
        self.assertEqual(res.json()["code"], 0)
        self.assertEqual(len(res.json()["data"]), 2)
        self.assertEqual(res.json()["data"][0]["name"], "shit")
        self.assertEqual(res.json()["data"][1]["name"], "shit2")

    def test_feishu_approval(self):
        manager = User.objects.filter(name="asset_manager").first()
        user = User.objects.filter(name="steve").first()
        user.feishu_name = "刘晟男"
        user.feishu_open_id = "ou_e00cda55b73cada4baf96df40a6fb34b"
        user.feishu_phone = "15948224559"
        manager.feishu_name = "徐沛阳"
        manager.feishu_phone = "18852569598"
        message_id = feishu_test.recieve_pending_approval(
            manager, "lalala", user, "abaaba"
        )
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset(
            session,
            0,
            "GoldSword",
            1,
            "asset_manager",
            10.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        pending = PendingRequests.objects.filter(id=1).first()
        pending.feishu_message_id = message_id
        pending.save()
        res = self.feishu_approval(message_id, "APPROVE")

    def test_feishu_approval1(self):
        manager = User.objects.filter(name="asset_manager").first()
        user = User.objects.filter(name="steve").first()
        user.feishu_name = "刘晟男"
        user.feishu_open_id = "ou_e00cda55b73cada4baf96df40a6fb34b"
        user.feishu_phone = "15948224559"
        manager.feishu_name = "徐沛阳"
        manager.feishu_phone = "18852569598"
        message_id = feishu_test.recieve_pending_approval(
            manager, "lalala", user, "abaaba"
        )
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset(
            session,
            0,
            "GoldSword",
            1,
            "asset_manager",
            10.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            1,
            1,
        )
        pending = PendingRequests.objects.filter(id=1).first()
        pending.feishu_message_id = message_id
        pending.save()
        res = self.feishu_approval(message_id, "REJECT")

    def test_feishu_approval2(self):
        manager = User.objects.filter(name="asset_manager").first()
        user = User.objects.filter(name="steve").first()
        user.feishu_name = "刘晟男"
        user.feishu_open_id = "ou_e00cda55b73cada4baf96df40a6fb34b"
        user.feishu_phone = "15948224559"
        manager.feishu_name = "徐沛阳"
        manager.feishu_phone = "18852569598"
        message_id = feishu_test.recieve_pending_approval(
            manager, "lalala", user, "abaaba"
        )
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset(
            session,
            0,
            "GoldSword",
            1,
            "steve",
            10.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            2,
            1,
        )
        pending = PendingRequests.objects.filter(id=1).first()
        pending.feishu_message_id = message_id
        pending.save()
        res = self.feishu_approval(message_id, "APPROVE")

    def test_feishu_approval3(self):
        manager = User.objects.filter(name="asset_manager").first()
        user = User.objects.filter(name="steve").first()
        user.feishu_name = "刘晟男"
        user.feishu_open_id = "ou_e00cda55b73cada4baf96df40a6fb34b"
        user.feishu_phone = "15948224559"
        manager.feishu_name = "徐沛阳"
        manager.feishu_phone = "18852569598"
        message_id = feishu_test.recieve_pending_approval(
            manager, "lalala", user, "abaaba"
        )
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset(
            session,
            0,
            "GoldSword",
            1,
            "steve",
            10.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "",
            5,
            3,
            1,
        )
        pending = PendingRequests.objects.filter(id=1).first()
        pending.feishu_message_id = message_id
        pending.save()
        res = self.feishu_approval(message_id, "APPROVE")

    def test_feishu_approval4(self):
        manager = User.objects.filter(name="asset_manager").first()
        user = User.objects.filter(name="steve").first()
        user.feishu_name = "刘晟男"
        user.feishu_open_id = "ou_e00cda55b73cada4baf96df40a6fb34b"
        user.feishu_phone = "15948224559"
        manager.feishu_name = "徐沛阳"
        manager.feishu_phone = "18852569598"
        message_id = feishu_test.recieve_pending_approval(
            manager, "lalala", user, "abaaba"
        )
        res = self.user_login("asset_manager", "minecraft")
        session = res.json()["data"]["session"]
        self.post_asset(
            session,
            0,
            "GoldSword",
            1,
            "steve",
            10.0,
            "",
            "",
            0,
            1,
            "默认分类",
            "b",
            10,
        )
        res = self.user_login("steve", "minecraft")
        session1 = res.json()["data"]["session"]
        self.post_pending_request(
            session1,
            "steve",
            "asset_manager",
            "kyrie",
            5,
            4,
            1,
        )
        pending = PendingRequests.objects.filter(id=1).first()
        pending.feishu_message_id = message_id
        pending.save()
        res = self.feishu_approval(message_id, "APPROVE")


class UrlTests(TestCase):
    def post_entity(self, session, name):
        payload = {
            "name": name,
        }
        return self.client.post(
            f"/entity/{session}", data=payload, content_type="application/json"
        )

    def user_login(self, identity, password):
        payload = {
            "identity": identity,
            "password": password,
        }
        return self.client.post("/login", data=payload, content_type="application/json")

    def setUp(self):
        user1 = User(
            name="Luca1K",
            password="pokemon",
            character=4,
            lock=False,
            session="",
            email="",
        )
        user1.save()
        res = self.user_login("Luca1K", "pokemon")
        session = res.json()["data"]["session"]
        self.post_entity(session, "Pokemon")
        entity1 = Entity.objects.filter(name="Pokemon").first()
        self.post_entity(session, "Zelda")
        entity2 = Entity.objects.filter(name="Zelda").first()
        department1 = Department(
            name="Kanto",
            entity=entity1,
            parent=None,
            userNumber=1,
        )
        department1.save()
        department2 = Department(
            name="Unova",
            entity=entity1,
            parent=None,
            userNumber=1,
        )
        department2.save()
        department3 = Department(
            name="SuperSB",
            entity=entity2,
            parent=None,
            userNumber=1,
        )
        department3.save()

        user2 = User(
            name="NoahArk",
            password="pokemon",
            department=department2,
            entity=entity1,
            character=2,
            lock=False,
            session="",
            email="",
        )
        user2.save()
        user3 = User(
            name="YouAna",
            password="pokemon",
            department=department2,
            entity=entity1,
            character=1,
            lock=False,
            session="",
            email="",
        )
        user3.save()
        user4 = User(
            name="cutestYue",
            password="pokemon",
            department=department1,
            entity=entity1,
            character=3,
            lock=False,
            session="",
            email="",
        )
        user4.save()
        user5 = User(
            name="SB",
            password="zelda",
            department=department3,
            entity=entity2,
            character=3,
            lock=False,
            session="",
            email="",
        )
        user5.save()

    # Utility functions
    def user_login(self, identity, password):
        payload = {
            "identity": identity,
            "password": password,
        }
        return self.client.post("/login", data=payload, content_type="application/json")

    def put_url(
        self,
        session,
        entity,
        url1,
        name1,
        character1,
        url2,
        name2,
        character2,
        url3,
        name3,
        character3,
        url4,
        name4,
        character4,
        url5,
        name5,
        character5,
    ):
        payload = [
            {
                "entity": entity,
                "url": url1,
                "name": name1,
                "character": character1,
            },
            {
                "entity": entity,
                "url": url2,
                "name": name2,
                "character": character2,
            },
            {
                "entity": entity,
                "url": url3,
                "name": name3,
                "character": character3,
            },
            {
                "entity": entity,
                "url": url4,
                "name": name4,
                "character": character4,
            },
            {
                "entity": entity,
                "url": url5,
                "name": name5,
                "character": character5,
            },
        ]
        return self.client.put(
            f"/url/{session}", data=payload, content_type="application/json"
        )

    def get_url(self, session):
        return self.client.get(f"/url/{session}")

    def test_url_put_permissions(self):
        Luca1K = User.objects.filter(name="Luca1K").first()
        res2 = self.user_login("NoahArk", "pokemon")
        res3 = self.user_login("YouAna", "pokemon")
        res4 = self.user_login("cutestYue", "pokemon")
        res5 = self.user_login("SB", "zelda")
        session1 = Luca1K.session  # Luca1K
        session2 = res2.json()["data"]["session"]  # NoahArk
        session3 = res3.json()["data"]["session"]  # YouAna
        session4 = res4.json()["data"]["session"]  # cutestYue
        session5 = res5.json()["data"]["session"]  # SB

        res = self.put_url(
            "PumpKing",
            "Pokemon",
            "pokemonwiki.net",
            "PokemonWiki",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "用户的会话标识符信息不正确",
        )

        res = self.put_url(
            "yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
            "Pokemon",
            "pokemonwiki.net",
            "PokemonWiki",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )

        res = self.put_url(
            session2,
            "Pokemon",
            "pokemonwiki.net",
            "PokemonWiki",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )

        res = self.put_url(
            session3,
            "Pokemon",
            "pokemonwiki.net",
            "PokemonWiki",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )

        res = self.put_url(
            session5,
            "Pokemon",
            "pokemonwiki.net",
            "PokemonWiki",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )

        res = self.put_url(
            session1,
            "Pokemon",
            "1pokemonwiki.net",
            "1PokemonWiki",
            1,
            "1pokemonshowdown.net",
            "1PokemonShowdown",
            1,
            "1PMGBA.net",
            "1PMGBA",
            1,
            "1PokeDex.net",
            "1PokeDex",
            1,
            "1https://pokemmo.com/",
            "1PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

        res = self.put_url(
            session4,
            "Pokemon",
            "2pokemonwiki.net",
            "2PokemonWiki",
            1,
            "2pokemonshowdown.net",
            "2PokemonShowdown",
            1,
            "2PMGBA.net",
            "2PMGBA",
            1,
            "2PokeDex.net",
            "2PokeDex",
            1,
            "2https://pokemmo.com/",
            "2PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )

    def test_url_put_logic(self):
        Luca1K = User.objects.filter(name="Luca1K").first()
        res2 = self.user_login("NoahArk", "pokemon")
        res3 = self.user_login("YouAna", "pokemon")
        res4 = self.user_login("cutestYue", "pokemon")
        res5 = self.user_login("SB", "zelda")
        session1 = Luca1K.session  # Luca1K
        session2 = res2.json()["data"]["session"]  # NoahArk
        session3 = res3.json()["data"]["session"]  # YouAna
        session4 = res4.json()["data"]["session"]  # cutestYue
        session5 = res5.json()["data"]["session"]  # SB

        res = self.put_url(
            session4,
            "Pokemon",
            "https://pokemmo.com/",
            "Pokemmo",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "检测到冲突url",
        )

        res = self.put_url(
            session4,
            "Pokemon",
            "https://pokemmo.com/",
            "PokeMMO",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pornhub.com",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "检测到冲突url",
        )

        res = self.put_url(
            session4,
            "Pokemmo",
            "pokemonwiki.net",
            "PokemonWiki",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "给出的业务实体不存在",
        )

        res = self.put_url(
            session4,
            "Pokemon",
            "pokemonwiki.net",
            "PokemonWiki",
            1,
            "pokemonshowdown.net",
            "PokemonShowdown",
            1,
            "PMGBA.net",
            "PMGBA",
            1,
            "PokeDex.net",
            "PokeDex",
            1,
            "https://pokemmo.com/",
            "PokeMMO",
            1,
        )
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        pokemon_entity = Entity.objects.filter(name="Pokemon").first()
        url_list = (
            URL.objects.filter(entity=pokemon_entity, authority_level=1)
            .all()
            .order_by("id")
        )
        self.assertEqual(
            url_list[4].name,
            "PokeMMO",
        )
        self.assertEqual(
            url_list[4].url,
            "https://pokemmo.com/",
        )

    def test_url_get_permissions(self):
        Luca1K = User.objects.filter(name="Luca1K").first()
        res2 = self.user_login("NoahArk", "pokemon")
        res3 = self.user_login("YouAna", "pokemon")
        res4 = self.user_login("cutestYue", "pokemon")
        res5 = self.user_login("SB", "zelda")
        session1 = Luca1K.session  # Luca1K
        session2 = res2.json()["data"]["session"]  # NoahArk
        session3 = res3.json()["data"]["session"]  # YouAna
        session4 = res4.json()["data"]["session"]  # cutestYue
        session5 = res5.json()["data"]["session"]  # SB
        res = self.get_url("Hacker")
        self.assertEqual(
            res.json()["info"],
            "用户的会话标识符信息不正确",
        )
        res = self.get_url(session1)
        self.assertEqual(
            res.json()["info"],
            "超级管理员不能得到URL列表",
        )
        res = self.get_url("cccccccccccccccccccccccccccccccc")
        self.assertEqual(
            res.json()["info"],
            "你无此权限",
        )
        res = self.get_url(session4)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )
        res = self.get_url(session2)
        self.assertEqual(
            res.json()["info"],
            "Succeed",
        )


class TestBadMethod(TestCase):
    def test_bad_method(self):
        session = "a"
        page = "1"
        entity_name = "a"
        self.client.delete(f"/login", content_type="application/json")
        self.client.delete(f"/user/{session}", content_type="application/json")
        self.client.delete(f"/logout", content_type="application/json")
        self.client.delete(f"/character/{session}", content_type="application/json")
        self.client.delete(
            f"/user_list_all/{session}/{page}", content_type="application/json"
        )
        self.client.delete(f"/user_password/{session}", content_type="application/json")
        self.client.delete(f"/user_email/{session}", content_type="application/json")
        self.client.delete(f"/entity/{session}", content_type="application/json")
        self.client.delete(
            f"/user_entity/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(f"/user_entity_2/{session}", content_type="application/json")
        self.client.delete(f"/cur_entity/{session}", content_type="application/json")
        self.client.delete(f"/async_task/{session}", content_type="application/json")
        self.client.delete(
            f"/user_department/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(
            f"/user_department_2/{session}/{entity_name}",
            content_type="application/json",
        )
        self.client.delete(
            f"/all_departments/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(
            f"/sub_department/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(
            f"/department/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(f"/asset_tree/{session}", content_type="application/json")
        self.client.delete(
            f"/sub_asset_tree/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(
            f"/asset_tree_root/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(
            f"/asset_tree_node/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(f"/asset/{session}", content_type="application/json")
        self.client.delete(
            f"/asset_user_list/{session}/{page}", content_type="application/json"
        )
        self.client.delete(
            f"/asset_manager/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(
            f"/unallocated_asset/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(f"/allot_asset/{session}", content_type="application/json")
        self.client.delete(
            f"/transfer_asset/{session}", content_type="application/json"
        )
        self.client.delete(
            f"/maintain_asset/{session}", content_type="application/json"
        )
        self.client.delete(f"/expire_asset/{session}", content_type="application/json")
        self.client.delete(f"/receive_asset/{session}", content_type="application/json")
        self.client.delete(f"/return_asset/{session}", content_type="application/json")
        self.client.delete(
            f"/asset_manager_entity/{session}/{entity_name}",
            content_type="application/json",
        )
        self.client.delete(
            f"/asset/{session}/{entity_name}/{page}", content_type="application/json"
        )
        self.client.delete(
            f"/get_maintain_list/{session}", content_type="application/json"
        )
        self.client.delete(
            f"/asset_query/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(
            f"/picture/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(f"/url/{session}", content_type="application/json")
        self.client.delete(
            f"/logjournal/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(
            f"/operationjournal/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(
            f"/pending_request/{session}", content_type="application/json"
        )
        self.client.delete(
            f"/return_pending_request/{session}", content_type="application/json"
        )
        self.client.delete(
            f"/pending_request_list/{session}/{entity_name}",
            content_type="application/json",
        )
        self.client.delete(f"/warning/{session}", content_type="application/json")
        self.client.delete(
            f"/warning_get/{session}/{page}", content_type="application/json"
        )
        self.client.delete(f"/warning_list/{session}", content_type="application/json")
        self.client.delete(
            f"/count_department_asset/{session}", content_type="application/json"
        )
        self.client.delete(
            f"/count_status_asset/{session}",
            content_type="application/json",
        )
        self.client.delete(
            f"/info_curve/{session}/{entity_name}/{page}",
            content_type="application/json",
        )
        self.client.delete(
            f"/count_price_curve/{session}/{entity_name}",
            content_type="application/json",
        )
        self.client.delete(f"qrLogin", content_type="application/json")
        self.client.delete(f"feishu_name/{session}", content_type="application/json")
        self.client.delete(f"feishu_users/{session}", content_type="application/json")
        self.client.delete(f"feishu_get_event", content_type="application/json")
        self.client.delete(f"feishu_approval", content_type="application/json")
        self.client.delete(
            f"failed_task/{session}/{page}", content_type="application/json"
        )
        self.client.delete(f"post_asset/{session}", content_type="application/json")
        self.client.delete(f"get_user_all/{session}", content_type="application/json")
        self.client.delete(
            f"get_user_department/{session}", content_type="application/json"
        )
        self.client.delete(
            f"get_user_entity/{session}", content_type="application/json"
        )
        self.client.delete(
            f"get_logjournal/{session}/{entity_name}", content_type="application/json"
        )
        self.client.delete(
            f"get_operationjournal/{session}/{entity_name}",
            content_type="application/json",
        )
        self.client.delete(
            f"get_asset_tree_node/{session}/{entity_name}",
            content_type="application/json",
        )
        self.client.delete(
            f"get_unallocated_asset/{session}/{entity_name}",
            content_type="application/json",
        )
        self.client.delete(
            f"get_asset_user_list/{session}", content_type="application/json"
        )
        self.client.delete(f"get_asset/{session}", content_type="application/json")
        self.client.delete(
            f"all_item_assets/{session}", content_type="application/json"
        )
        self.client.delete(f"add_user", content_type="application/json")
