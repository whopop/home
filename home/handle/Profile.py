# -*- coding:utf-8 -*-

import uuid
import logging

from BaseHandle import BaseHandle
from utils.response_code import RET
from constants import AVATAR_URL
from utils.require_login import require_login


class Avator(BaseHandle):
    """上传头像处理"""
    @require_login
    def post(self):
        # # 接收上传的图像数据
        # files = self.request.files.get("avatar")
        # if not files:
        #     return self.write(dict(errcode=RET.PARAMERR, errmsg="未传图片"))
        # avatar = files[0]["body"]
        # img_url = '../static/media/'+uuid.uuid4().hex
        # try:
        #     file = open(img_url+'.jpg', "w+")
        #     file.write(avatar)
        #     file.close()
        # except Exception as e:
        #     logging.error(e)
        #     return self.write(dict(errcode=RET.THIRDERR, errmsg="上传失败"))
        # self.write(dict(errcode="0", data=img))

        image = self.request.files.get('avatar')
        img_url = './static/media/' + uuid.uuid4().hex
        try:
            try:
                pic = image[0]["body"]
                file = open(img_url + '.jpg', "w+")
                file.write(pic)
                file.close()
            except Exception as e:
                logging.error(e)
                return self.write(dict(errcode=RET.THIRDERR, errmsg="error"))
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.THIRDERR, errmsg="上传失败"))

        # image_url 地址
        img_url = img_url.lstrip(".")+'.jpg'
        img = img_url[-36:]

        # 取出用户id
        user_id = self.session.data["user_id"]
        try:
            sql = "update ih_user_profile set up_avatar=%(avatar)s where up_user_id=%(user_id)s"
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=user_id))
        # return self.write(dict(errcode=user_id))
        try:
            row_count = self.db.execute_rowcount(sql, avatar=img, user_id=user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="保存错误"))
        self.write(dict(errcode=RET.OK, errmsg="保存成功", data=img_url))


class Profile(BaseHandle):
    """个人主页"""
    @require_login
    def get(self):
        user_id = self.session.data['user_id']
        # 获取个人信息
        try:
            res = self.db.get("select up_name,up_mobile,up_avatar from ih_user_profile where up_user_id=%s", user_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="get data error"))
        # 判断是否有头像
        if res['up_avatar']:
            img_url = AVATAR_URL+res['up_avatar']
        else:
            img_url = None
        self.write({'errcode': RET.OK, 'errmsg': "ok",
                    "data":{"name": res['up_name'], "mobile": res['up_mobile'], "avatar": img_url}})


class ChangeName(BaseHandle):
    """修改昵称"""
    @require_login
    def post(self):
        # 接收数据
        name = self.json_args.get("name")
        # 用户id
        user_id = self.session.data["user_id"]
        # 简单过滤
        if name in (None, ""):
            return self.write({"errcode":RET.PARAMERR, "errmsg":"params error"})
        """
        未做注入过滤
        """
        try:
            self.db.execute_rowcount("update ih_user_profile set up_name=%s where up_user_id=%s", name, user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode": RET.DBERR, "errmsg": "name has exist"})

        # 修改保存在session中的name,并保存
        self.session.data["name"] = name
        try:
            self.session.save()
        except Exception as e:
            logging.error(e)

        self.write({"errcode":RET.OK, "errmsg":"OK"})


class Auth(BaseHandle):
    """真实身份认证"""
    @require_login
    def get(self):
        user_id = self.session.data['user_id']
        # 查询
        try:
            res = self.db.get("select up_real_name,up_id_card from ih_user_profile where up_user_id=%s", user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode":RET.DBERR, "errmsg":"get data failed"})
        # logging.debug(res)
        if not res:
            return self.write({"errcode":RET.NODATA, "errmsg":"no data"})

        self.write({"errcode":RET.OK, "errmsg":"OK", "data":{"real_name": res.get("up_real_name", ""), "id_card": res.get("up_id_card", "")}})

    @require_login
    def post(self):
        user_id = self.session.data['user_id']
        real_name = self.json_args.get('real_name')
        id_card = self.json_args.get('id_card')

        # 简单过滤检查
        if real_name in (None, "") or id_card in (None, ""):
            return self.write({"errcode": RET.PARAMERR, "errmsg": "params error"})

        try:
            self.db.execute_rowcount("update ih_user_profile set up_real_name=%s,up_id_card=%s where up_user_id=%s", real_name, id_card, user_id)
        except Exception as e:
            logging.error(e)
            return self.write({"errcode":RET.DBERR, "errmsg":"update failed"})
        self.write({"errcode":RET.OK, "errmsg":"OK"})









































