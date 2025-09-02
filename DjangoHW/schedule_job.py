# import schedule
import pytz
from time import sleep
from datetime import datetime, time, timedelta
from django.utils import timezone

time_zone = pytz.timezone("Asia/Shanghai")

# print(datetime.now(tz=time_zone))

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


# signal = 0
# print(time(14, 45, tzinfo=time_zone))
# print(datetime.now(time_zone).time())
# print((datetime.now() + timedelta(hours=8)).date())
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
        if end >= all_valid_len:
            break
        start += 500
        end += 500
        sleep(1)
        print(f"Depreciation job ROUND [{end / 500}] done !")

    print(
        f"OK, all valid assets in the database have been depreciated automatically by Luca1K's ROBOT at :)"
    )
    # signal = 1


def statistics_job():
    # global signal
    # YueYue = User.objects.filter(name="manager").first()

    start = 0
    end = 100

    all_departments = Department.objects.all()
    template_dict_cnt = {department.name: 0 for department in all_departments}
    template_dict_pri = {department.name: 0.00 for department in all_departments}
    cnt_dict_item = template_dict_cnt.copy()
    pri_dict_item = template_dict_pri.copy()
    cnt_dict_amount = template_dict_cnt.copy()
    pri_dict_amount = template_dict_pri.copy()

    cnt_dict_item_idle = template_dict_cnt.copy()
    cnt_dict_item_use = template_dict_cnt.copy()
    cnt_dict_item_maintain = template_dict_cnt.copy()

    cnt_dict_amount_idle = template_dict_cnt.copy()
    cnt_dict_amount_use = template_dict_cnt.copy()
    cnt_dict_amount_maintain = template_dict_cnt.copy()

    cnt_dict_item_expire = template_dict_cnt.copy()
    cnt_dict_amount_expire = template_dict_cnt.copy()

    tot_length = Asset.objects.count()
    start = 0
    end = 100

    while True:
        cur_round_assets = Asset.objects.all()[start:end]
        for a in cur_round_assets:
            if a.count <= 0:
                continue

            dp_name = a.department.name

            if a.expire == 1:
                if a.assetClass == 0:
                    cnt_dict_item_expire[dp_name] += 1
                else:
                    cnt_dict_amount_expire[dp_name] += 1
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
            if a.status == 1:
                cnt_dict_item_idle[dp_name] += 1
            if a.status == 2:
                cnt_dict_item_use[dp_name] += 1
            else:
                cnt_dict_item_maintain[dp_name] += 1
            if a.assetClass == 0:
                cnt_dict_item[dp_name] += 1
                pri_dict_item[dp_name] += float(a.price)
                if a.status == 1:
                    cnt_dict_item_idle[dp_name] += 1
                if a.status == 2:
                    cnt_dict_item_use[dp_name] += 1
                else:
                    cnt_dict_item_maintain[dp_name] += 1
            else:
                cnt_dict_amount[dp_name] += a.count
                pri_dict_amount[dp_name] += float(a.price) * float(a.count)
                if a.status == 1:
                    cnt_dict_amount_idle[dp_name] += a.count
                if a.status == 2:
                    cnt_dict_amount_use[dp_name] += a.count
                else:
                    cnt_dict_amount_maintain[dp_name] += a.count

        sleep(1)
        if end >= tot_length:
            break
        start += 100
        end += 100

    for dp in all_departments:
        dp_name = dp.name
        AssetStatistics.objects.create(
            asset=None,
            cur_department=dp,
            cur_user=None,
            cur_price=0.00,
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=44,
            cur_count=cnt_dict_item_expire[dp_name],
        )
        AssetStatistics.objects.create(
            asset=None,
            cur_department=dp,
            cur_user=None,
            cur_price=0.00,
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=444,
            cur_count=cnt_dict_amount_expire[dp_name],
        )
        if cnt_dict_item[dp_name] == 0 and cnt_dict_amount[dp_name] == 0:
            continue
        if cnt_dict_item[dp_name] != 0:
            AssetStatistics.objects.create(
                asset=None,
                cur_department=dp,
                cur_user=None,
                cur_price=0.00,
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=11,
                cur_count=cnt_dict_item_idle[dp_name],
            )
            AssetStatistics.objects.create(
                asset=None,
                cur_department=dp,
                cur_user=None,
                cur_price=0.00,
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=22,
                cur_count=cnt_dict_item_use[dp_name],
            )
            AssetStatistics.objects.create(
                asset=None,
                cur_department=dp,
                cur_user=None,
                cur_price=0.00,
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=33,
                cur_count=cnt_dict_item_maintain[dp_name],
            )
            AssetStatistics.objects.create(
                asset=None,
                cur_department=dp,
                cur_user=None,
                cur_price=pri_dict_item[dp_name],
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=529113,
                cur_count=cnt_dict_item[dp_name],
            )
        if cnt_dict_amount[dp_name] != 0:
            AssetStatistics.objects.create(
                asset=None,
                cur_department=dp,
                cur_user=None,
                cur_price=0.00,
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=111,
                cur_count=cnt_dict_amount_idle[dp_name],
            )
            AssetStatistics.objects.create(
                asset=None,
                cur_department=dp,
                cur_user=None,
                cur_price=0.00,
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=222,
                cur_count=cnt_dict_amount_use[dp_name],
            )
            AssetStatistics.objects.create(
                asset=None,
                cur_department=dp,
                cur_user=None,
                cur_price=0.00,
                cur_time=timezone.now() + timezone.timedelta(hours=8),
                cur_status=333,
                cur_count=cnt_dict_amount_maintain[dp_name],
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
        # total
        AssetStatistics.objects.create(
            asset=None,
            cur_department=dp,
            cur_user=None,
            cur_price=pri_dict_item[dp_name] + pri_dict_amount[dp_name],
            cur_time=timezone.now() + timezone.timedelta(hours=8),
            cur_status=501113,
            cur_count=cnt_dict_item[dp_name] + cnt_dict_amount[dp_name],
        )
        sleep(0.1)
    # for dp in all_departments:
    #     cur_length = Asset.objects.filter(department=dp, count__gt=0, expire=0).count()
    #     start = 0
    #     end = 100
    #     tot_cnt_item = 0
    #     tot_cnt_amount = 0
    #     tot_cnt = 0
    #     tot_price_item = 0.00
    #     tot_price_amount = 0.00
    #     tot_price = 0.00
    #     while(end < cur_length):
    #         cur_dp_assets = Asset.objects.filter(department=dp, count__gt=0, expire=0)[start:end]
    #         for a in cur_dp_assets:
    #             AssetStatistics.objects.create(
    #                 asset=a,
    #                 cur_department=a.department,
    #                 cur_user=a.user,
    #                 cur_price=a.price,
    #                 cur_time=timezone.now() + timezone.timedelta(hours=8),
    #                 cur_status=a.status if a.expire == 0 else 0,
    #                 cur_count=a.count,
    #             )
    #             if a.assetClass == 0:
    #                 tot_cnt_item += a.count
    #                 tot_price_item += float(a.price)
    #             else:
    #                 tot_cnt_amount += a.count
    #                 tot_price_amount += float(a.price) * float(a.count)
    #         start += 100
    #         end += 100
    #         sleep(1)

    #     tot_cnt = tot_cnt_item + tot_cnt_amount
    #     tot_price = tot_price_item + tot_price_amount

    #     print(f"Department: {dp.name} statistics DONE")

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
    print(
        f"OK, asset statistics have been made for all assets in the database automatically by Luca1K's ROBOT :)"
    )


# def check_job():
#     global signal
#     if signal == 1:
#         sleep(80000)
#         signal = 0
#     return


# # schedule.every(1).days.do(depreciation_job)
# schedule.every().day.at(time(14, 45, tzinfo=time_zone)).do(depreciation_job)
# # schedule.every().day.at(time(0, 0, tzinfo=time_zone)).do(statistics_job)
# # schedule.every().day.at(datetime.now(time_zone).replace(hour=0, minute=0)).do(depreciation_job)
# # schedule.every().day.at(datetime.now(time_zone).replace(hour=0, minute=0)).do(statistics_job)
# # schedule.every(5).minutes.do(depreciation_job)

while True:
    # signal = 0
    # schedule.run_pending()
    # check_job()
    # sleep(10)
    nw = datetime.now(time_zone)
    if (
        time(0, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(0, 0, 59, 999999, tzinfo=time_zone)
    ):
        depreciation_job()
        statistics_job()
        sleep_time = 529
    elif (
        time(4, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(4, 0, 59, 999999, tzinfo=time_zone)
    ):
        depreciation_job()
        statistics_job()
        sleep_time = 529
    elif (
        time(8, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(8, 0, 59, 999999, tzinfo=time_zone)
    ):
        depreciation_job()
        statistics_job()
        sleep_time = 529
    elif (
        time(12, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(12, 0, 59, 999999, tzinfo=time_zone)
    ):
        depreciation_job()
        statistics_job()
        sleep_time = 529
    elif (
        time(16, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(16, 0, 59, 999999, tzinfo=time_zone)
    ):
        depreciation_job()
        statistics_job()
        sleep_time = 529
    elif (
        time(20, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(20, 0, 59, 999999, tzinfo=time_zone)
    ):
        depreciation_job()
        statistics_job()
        sleep_time = 529
    if (
        time(2, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(2, 0, 59, 999999, tzinfo=time_zone)
    ):
        statistics_job()
        sleep_time = 529
    elif (
        time(6, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(6, 0, 59, 999999, tzinfo=time_zone)
    ):
        statistics_job()
        sleep_time = 529
    elif (
        time(10, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(10, 0, 59, 999999, tzinfo=time_zone)
    ):
        statistics_job()
        sleep_time = 529
    elif (
        time(14, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(14, 0, 59, 999999, tzinfo=time_zone)
    ):
        statistics_job()
        sleep_time = 529
    elif (
        time(18, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(18, 0, 59, 999999, tzinfo=time_zone)
    ):
        statistics_job()
        sleep_time = 529
    elif (
        time(22, 0, 0, 0, tzinfo=time_zone)
        <= nw.time()
        <= time(22, 0, 59, 999999, tzinfo=time_zone)
    ):
        statistics_job()
        sleep_time = 529
    else:
        sleep_time = 29
    sleep(sleep_time)
    # schedule.run_pending()
