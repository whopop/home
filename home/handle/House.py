# -*- coding:utf-8 -*-

import logging
import redis
import uuid
import json
import math
import constants
from constants import AVATAR_URL, REDIS_AREA_INFO_EXPIRES_SECONDES, HOME_PAGE_MAX_HOUSES, HOME_PAGE_DATA_REDIS_EXPIRE_SECOND, REDIS_HOUSE_INFO_EXPIRES_SECONDES
from .BaseHandle import BaseHandle
from utils.require_login import require_login
from utils.response_code import RET
from utils.session import Session

class MyHouse(BaseHandle):
    """我的房源"""
    @require_login
    def get(self):
        user_id = self.session.data['user_id']
        # 获取房源数据
        try:
            sql = "select a.hi_house_id,a.hi_title,a.hi_price,a.hi_ctime,b.ai_name,a.hi_index_image_url " \
                  "from ih_house_info a inner join ih_area_info b on a.hi_area_id=b.ai_area_id where a.hi_user_id=%s;"
            ret = self.db.query(sql, user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.DBERR, "errmsg": "get data error"})

        houses = []
        if ret:
            for h in ret:
                house = {
                    "house_id": h['hi_house_id'],
                    "title": h['hi_title'],
                    "price": h['hi_price'],
                    "ctime": h['hi_ctime'].strftime("%Y-%m-%d"),
                    "area_name": h["ai_name"],
                    "img_url": AVATAR_URL + h["hi_index_image_url"] if h["hi_index_image_url"] else ""
                }
                houses.append(house)
        self.write({"errcode":RET.OK, "errmsg":"OK", "houses": houses})


class AreaInfo(BaseHandle):
    """城区"""
    def get(self):
        # 先到缓存redis中找,诺有直接返回数据,没有再到数据库中找
        try:
            res = self.redis.get("area_info")
        except Exception as e:
            logging.error(e)
            res = None
        if res:
            logging.info("hit redis area_info")
            response = '{"errcode":"0","errmsg":"ok", "data":%s}' % res
            return self.write(response)

        # 数据库
        sql = "select ai_area_id,ai_name from ih_area_info;"
        try:
            res = self.db.query(sql)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="数据库查询出错"))
        if not res:
            return self.write(dict(errcode=RET.NODATA, errmsg="没有数据"))

        data = []
        for row in res:
            area = {
                "area_id":row['ai_area_id'],
                "name":row['ai_name']
            }
            data.append(area)
        data_json = json.dumps(data)

        # 保存到redis中,方便下次读取
        try:
            self.redis.setex("area_info", REDIS_AREA_INFO_EXPIRES_SECONDES, data_json)
        except Exception as e:
            logging.error(e)

        self.write(dict(errcode=RET.OK, errmsg='ok',data=data))


class HouseInfo(BaseHandle):
    """处理发布房源信息"""
    @require_login
    def post(self):
        user_id = self.session.data.get("user_id")
        title = self.json_args.get("title")
        price = self.json_args.get("price")
        area_id = self.json_args.get("area_id")
        address = self.json_args.get("address")
        room_count = self.json_args.get("room_count")
        acreage = self.json_args.get("acreage")
        unit = self.json_args.get("unit")
        capacity = self.json_args.get("capacity")
        beds = self.json_args.get("beds")
        deposit = self.json_args.get("deposit")
        min_days = self.json_args.get("min_days")
        max_days = self.json_args.get("max_days")
        facility = self.json_args.get("facility")  # 一个房屋的设施，是列表类型

        if not all((title, price, area_id, address, room_count, acreage, unit, capacity, beds, deposit, min_days,
                    max_days)):
            return self.write(dict(errcode=RET.PARAMERR, errmsg="缺少参数"))
        try:
            price = int(price) * 100
            deposit = int(deposit) * 100
        except Exception as e:
            return self.write(dict(errcode=RET.PARAMERR, errmsg="参数错误"))

        # 未过滤
        # 数据
        try:
            sql = "insert into ih_house_info(hi_user_id,hi_title,hi_price,hi_area_id,hi_address,hi_room_count," \
                  "hi_acreage,hi_house_unit,hi_capacity,hi_beds,hi_deposit,hi_min_days,hi_max_days) " \
                  "values(%(user_id)s,%(title)s,%(price)s,%(area_id)s,%(address)s,%(room_count)s,%(acreage)s," \
                  "%(house_unit)s,%(capacity)s,%(beds)s,%(deposit)s,%(min_days)s,%(max_days)s)"
            # 对于insert语句，execute方法会返回最后一个自增id
            house_id = self.db.execute(sql, user_id=user_id, title=title, price=price, area_id=area_id,
                                       address=address,
                                       room_count=room_count, acreage=acreage, house_unit=unit, capacity=capacity,
                                       beds=beds, deposit=deposit, min_days=min_days, max_days=max_days)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="save data error"))

        # 保存房屋设施
        try:
            sql = "insert into ih_house_facility(hf_house_id,hf_facility_id) values"
            sql_val = []
            val = []
            for facility_id in facility:
                sql_val.append("(%s,%s)")
                val.append(house_id)
                val.append(facility_id)
            sql += ",".join(sql_val)
            val = tuple(val)
            self.db.execute(sql, *val)
        except Exception as e:
            logging.error(e)
            try:
                self.db.execute("delete from ih_house_info where hi_house_id=%s", house_id)
            except Exception as e:
                logging.error(e)
                return self.write(dict(errcode=RET.DBERR, errmsg="delete fail"))
            else:
                return self.write(dict(errcode=RET.DBERR, errmsg="no data save"))
        # 返回
        self.write(dict(errcode=RET.OK, errmsg="OK", house_id=house_id))

    def get(self):
        """获取房屋信息"""
        session = Session(self)
        user_id = session.data.get('user_id', "-1")
        house_id = self.get_argument('house_id')

        if not house_id:
            return self.write(dict(errcode=RET.PARAMERR, errmsg="缺少参数"))

        # 试从redis中获取房屋数据
        try:
            res = self.redis.get('house_info_%s', house_id)
        except Exception as e:
            logging.error(e)
            res = None
        if res:
           response = '{"errcode":"0", "errmsg":"OK", "data":%s, "user_id":%s}' % (res, user_id)
           return self.write(response)

         # 数据库取
        sql = "select hi_title,hi_price,hi_address,hi_room_count,hi_acreage,hi_house_unit,hi_capacity,hi_beds," \
              "hi_deposit,hi_min_days,hi_max_days,up_name,up_avatar,hi_user_id " \
              "from ih_house_info inner join ih_user_profile on hi_user_id=up_user_id where hi_house_id=%s"
        try:
            res = self.db.get(sql, house_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="查询错误"))
        if not res:
            return self.write(dict(errcode=RET.NODATA, errmsg="查无此房"))

        # 信息
        data = {
            "hid": house_id,
            "user_id": res["hi_user_id"],
            "title": res["hi_title"],
            "price": res["hi_price"],
            "address": res["hi_address"],
            "room_count": res["hi_room_count"],
            "acreage": res["hi_acreage"],
            "unit": res["hi_house_unit"],
            "capacity": res["hi_capacity"],
            "beds": res["hi_beds"],
            "deposit": res["hi_deposit"],
            "min_days": res["hi_min_days"],
            "max_days": res["hi_max_days"],
            "user_name": res["up_name"],
            "user_avatar": AVATAR_URL + res["up_avatar"] if res.get("up_avatar") else ""
        }

        # 房屋图片
        sql = "select hi_url from ih_house_image where hi_house_id=%s"
        try:
            res = self.db.query(sql, house_id)
        except Exception as e:
            logging.error(e)
            res = None

        images = []
        if res:
            for image in res:
                images.append(AVATAR_URL+image['hi_url'])
        data["images"] = images

        # 查询房屋的基本设施
        sql = "select hf_facility_id from ih_house_facility where hf_house_id=%s"
        try:
            res = self.db.query(sql, house_id)
        except Exception as e:
            logging.error(e)
            res = None

        # 如果查询到设施
        facilities = []
        if res:
            for facility in res:
                facilities.append(facility["hf_facility_id"])
        data["facilities"] = facilities

        # 查询评论信息
        sql = "select oi_comment,up_name,oi_utime,up_mobile from ih_order_info inner join ih_user_profile " \
              "on oi_user_id=up_user_id where oi_house_id=%s and oi_status=4 and oi_comment is not null"

        try:
            res = self.db.query(sql, house_id)
        except Exception as e:
            logging.error(e)
            res = None
        comments = []
        if res:
            for comment in res:
                comments.append(dict(
                    user_name=comment["up_name"] if comment["up_name"] != comment["up_mobile"] else "匿名用户",
                    content=comment["oi_comment"],
                    ctime=comment["oi_utime"].strftime("%Y-%m-%d %H:%M:%S")
                ))
        data["comments"] = comments

        # 存放到redis
        json_data = json.dumps(data)
        try:
            self.redis.setex("house_info_%s" % house_id, REDIS_HOUSE_INFO_EXPIRES_SECONDES,
                             json_data)
        except Exception as e:
            logging.error(e)

        response = '{"errcode":"0", "errmsg":"ok", "data":%s, "user_id":%s}' % (json_data, user_id)
        self.write(response)


class HouseImage(BaseHandle):
    """房源照片"""
    def post(self):
        house_id = self.get_argument("house_id")
        house_img = self.request.files['house_image'][0]['body']
        try:
            img_url = './static/media/' + uuid.uuid4().hex
            file = open(img_url + '.jpg', "w")
            file.write(house_img)
            file.close()
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.THIRDERR, errmsg="上传失败"))

        # image_url 地址
        img_url = img_url.lstrip(".") + '.jpg'
        img = img_url[-36:]

        # 保存导数据库
        try:
            sql = "insert into ih_house_image(hi_house_id,hi_url) values(%s,%s);" \
                  "update ih_house_info set hi_index_image_url=%s " \
                  "where hi_house_id=%s and hi_index_image_url is null;"
            self.db.execute(sql, house_id, img, img, house_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode":RET.DBERR, "errmsg":"upload failed"})
        # img_url = AVATAR_URL + img
        self.write({"errcode":RET.OK, "errmsg":"ok", "url":img_url})


class Index(BaseHandle):
    """主页信息"""
    def get(self):
        # 获取房子信息
        try:
            res = self.redis.get("home_page_data")
        except Exception as e:
            logging.error(e)
            res = None
        if res:
            json_data = res
        else:
            # 从数据库中获取房子数据
            try:
                house_res = self.db.query("select hi_house_id,hi_title,hi_order_count,hi_index_image_url from ih_house_info " \
                                          "order by hi_order_count desc limit %s;" % HOME_PAGE_MAX_HOUSES)
            except Exception as e:
                logging.error(e)
                return self.write({"errcode": RET.DBERR, "errmsg": "get data error"})
            if not house_res:
                return self.write({"errcode":RET.NODATA, "errmsg":"get data error"})
            houses = []
            for h in house_res:
                if not h['hi_index_image_url']:
                    continue
                house = {
                    "house_id": h['hi_house_id'],
                    "title": h['hi_title'],
                    "img_url": AVATAR_URL + h['hi_index_image_url']
                }
                houses.append(house)
            json_data = json.dumps(houses)
            #  保存到redis
            try:
                self.redis.setex("home_page_data", HOME_PAGE_DATA_REDIS_EXPIRE_SECOND, json_data)
            except Exception as e:
                logging.error(e)

        # 获取地区信息
        try:
            res = self.redis.get("area_info")
        except Exception as e:
            logging.error(e)
            res = None
        if res:
            json_area_data = res
        else:
            try:
                area_res = self.db.query("select ai_area_id,ai_name from ih_area_info")
            except Exception as e:
                logging.error(e)
                area_res = None

            areas = []
            if area_res:
                for a in area_res:
                    area = {
                        "area_id":a['ai_area_id'],
                        "name":a['ai_name']
                    }
                    areas.append(area)
            json_area_data = json.dumps(areas)

            try:
                self.redis.setex("area_info", REDIS_AREA_INFO_EXPIRES_SECONDES, json_area_data)
            except Exception as e:
                logging.error(e)
        response = '{"errcode":"0", "errmsg":"ok", "houses":%s, "areas":%s}' % (json_data, json_area_data)
        self.write(response)


class HouseList(BaseHandle):
    """查询房屋redis缓存版"""
    def get(self):
        # 获取参数
        start_date = self.get_argument("sd", "")
        end_date = self.get_argument("ed", "")
        area_id = self.get_argument("aid", "")
        sort_key = self.get_argument("sk", "new")
        page = self.get_argument("p", "1")

        try:
            redis_key = "houses_%s_%s_%s_%s" % (start_date, end_date, area_id, sort_key)
            ret = self.redis.hget(redis_key, page)
        except Exception as e:
            logging.error(e)
            ret = None
        if ret:
            logging.info("hit redis")
            return self.write(ret)

        # 数据库
        # 数据
        sql = "select distinct hi_title,hi_house_id,hi_price,hi_room_count,hi_address,hi_order_count,up_avatar,hi_index_image_url,hi_ctime" \
              " from ih_house_info inner join ih_user_profile on hi_user_id=up_user_id left join ih_order_info" \
              " on hi_house_id=oi_house_id"
        # 总条目查询语句
        sql_total_count = "select count(distinct hi_house_id) count from ih_house_info inner join ih_user_profile on hi_user_id=up_user_id " \
                          "left join ih_order_info on hi_house_id=oi_house_id"

        sql_where = []
        sql_params = {}

        if start_date and end_date:
            sql_part = "((oi_begin_date>%(end_date)s or oi_end_date<%(start_date)s) " \
                       "or (oi_begin_date is null and oi_end_date is null))"
            sql_where.append(sql_part)
            sql_params["start_date"] = start_date
            sql_params["end_date"] = end_date
        elif start_date:
            sql_part = "(oi_end_date<%(start_date)s or (oi_begin_date is null and oi_end_date is null))"
            sql_where.append(sql_part)
            sql_params["start_date"] = start_date
        elif end_date:
            sql_part = "(oi_begin_date>%(end_date)s or (oi_begin_date is null and oi_end_date is null))"
            sql_where.append(sql_part)
            sql_params["end_date"] = end_date

        if area_id:
            sql_part = "hi_area_id=%(area_id)s"
            sql_where.append(sql_part)
            sql_params["area_id"] = area_id

        if sql_where:
            sql += " where "
            sql += " and ".join(sql_where)

        # 查询总条数
        try:
            ret = self.db.get(sql_total_count, **sql_params)
        except Exception as e:
            logging.error(e)
            total_page = "-1"
        else:
            total_page = int(math.ceil(ret['count'] / float(constants.HOUSE_LIST_PAGE_CAPACITY)))
            page = int(page)
            if page > total_page:
                return self.write(dict(errcode=RET.OK, errmsg="OK", data=[], total_page=total_page))

        # 排序
        if "new" == sort_key: # 按最新上传时间排序
            sql += " order by hi_ctime desc"
        elif "booking" == sort_key: # 最受欢迎
            sql += " order by hi_order_count desc"
        elif "price-inc" == sort_key: # 价格由低到高
            sql += " order by hi_price asc"
        elif "price-des" == sort_key: # 价格由高到低
            sql += " order by hi_price desc"

        # 分页
        if 1 == page:
            sql += " limit %s" % (constants.HOUSE_LIST_PAGE_CAPACITY * constants.HOUSE_LIST_PAGE_CACHE_NUM)
        else:
            sql += " limit %s,%s" % ((page - 1) * constants.HOUSE_LIST_PAGE_CAPACITY,
                                     constants.HOUSE_LIST_PAGE_CAPACITY * constants.HOUSE_LIST_PAGE_CACHE_NUM)

        logging.debug(sql)
        try:
            ret = self.db.query(sql, **sql_params)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="查询出错"))
        data = []
        if ret:
            for l in ret:
                house = dict(
                    house_id=l["hi_house_id"],
                    title=l["hi_title"],
                    price=l["hi_price"],
                    room_count=l["hi_room_count"],
                    address=l["hi_address"],
                    order_count=l["hi_order_count"],
                    avatar=constants.AVATAR_URL + l["up_avatar"] if l.get("up_avatar") else "",
                    image_url=constants.AVATAR_URL + l["hi_index_image_url"] if l.get(
                        "hi_index_image_url") else ""
                )
                data.append(house)

        # 对与返回的多页面数据进行分页处理
        # 首先取出用户想要获取的page页的数据
        current_page_data = data[:constants.HOUSE_LIST_PAGE_CAPACITY]
        house_data = {}
        house_data[page] = json.dumps(
            dict(errcode=RET.OK, errmsg="OK", data=current_page_data, total_page=total_page))
        # 将多取出来的数据分页
        i = 1
        while 1:
            page_data = data[i * constants.HOUSE_LIST_PAGE_CAPACITY: (i + 1) * constants.HOUSE_LIST_PAGE_CAPACITY]
            if not page_data:
                break
            house_data[page + i] = json.dumps(
                dict(errcode=RET.OK, errmsg="OK", data=page_data, total_page=total_page))
            i += 1
        try:
            redis_key = "houses_%s_%s_%s_%s" % (start_date, end_date, area_id, sort_key)
            self.redis.hmset(redis_key, house_data)
            self.redis.expire(redis_key, constants.REDIS_HOUSE_LIST_EXPIRES_SECONDS)
        except Exception as e:
            logging.error(e)

        self.write(house_data[page])

