# -*-coding:utf-8-*-

import logging
import random
import re
from BaseHandle import BaseHandle
from utils.response_code import RET
from utils.captcha.captcha import captcha
from constants import PIC_CODE_EXPIRES_SECONDS, SMS_CODE_EXPIRES_SECONDS
from libs.yuntongxun.SendTemplateSMS import ccp


class PicCode(BaseHandle):
    """验证码"""
    def get(self):
        # 接收验证码id
        pre_code_id = self.get_argument("pre", "")  # 前验证码id
        cur_code_id = self.get_argument("cur")  # 现验证码id

        # 生成验证码
        name, text, pic = captcha.generate_captcha()
        # 判断pre_code_id
        try:
            if pre_code_id:
                self.redis.delete("pic_code_%s"%pre_code_id)
            self.redis.setex("pic_code_%s" % cur_code_id, PIC_CODE_EXPIRES_SECONDS, text)
        except Exception as e:
            logging.error(e)
            self.write("")
        else:
            self.set_header("Content-Type", "image/jpg")
            self.write(pic)


class SmsCode(BaseHandle):
    """发送手机验证码"""
    def post(self):
        # 接收参数
        mobile = self.json_args.get("mobile")
        pic_code = self.json_args.get("pic_code")
        pic_code_id = self.json.args.get("pic_code_id")

        if not all((mobile, pic_code, pic_code_id)):
            return self.write(dict(errcode=RET.PARAMERR, errmsg="参数缺失"))

        # 检查手机号
        if not re.match(r"^1\d{10}$", mobile):
            return self.write(dict(errcode=RET.PARAMERR, errmsg="手机号格式错误"))

        sql = "select count(*) counts from ih_user_profile where up_mobile=%s"
        try:
            res = self.db.get(sql, mobile)
        except Exception as e:
            logging.error(e)
        else:
            if 0 != res["counts"]:
                return self.write(dict(errcode=RET.DATAEXIST, errmsg="手机号已注册"))

        # 检验验证码
        try:
            real_pic_code = self.redis.get("pic_code_%s"%pic_code_id)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="查询验证码错误"))
        if not real_pic_code:
            return self.write(dict(errcode=RET.NODATA, errmsg="验证码过期"))

        # 删除redis 中保存的验证码
        try:
            self.redis.delete("pic_code_%s"%pic_code_id)
        except Exception as e:
            logging.error(e)

        if real_pic_code.lower() != pic_code.lower():
            return self.write(dict(errcode=RET.DATAERR, errmsg="验证码错误"))

        # 产生随机短信验证码
        sms_code = "%06d" % random.randint(1, 1000000)
        try:
            self.redis.setex("sms_code_%s" % mobile, SMS_CODE_EXPIRES_SECONDS, sms_code)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.DBERR, errmsg="数据库出错"))

        # 发送短信验证码
        try:
            result = ccp.sendTemplateSMS(mobile, [sms_code, SMS_CODE_EXPIRES_SECONDS / 60], 1)
        except Exception as e:
            logging.error(e)
            return self.write(dict(errcode=RET.THIRDERR, errmsg="发送短信失败"))
        if result:
            self.write(dict(errcode=RET.OK, errmsg="发送成功"))
        else:
            self.write(dict(errcode=RET.UNKOWNERR, errmsg="发送失败"))











