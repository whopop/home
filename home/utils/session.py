# -*-coding:utf-8-*-
import uuid
import json
import logging
from constants import *


class Session(object):
    """自定义session"""
    def __init__(self, request_handle_obj):

        # 先判断用户是否已经有了session_id
        self._request_handle = request_handle_obj
        self.session_id = request_handle_obj.get_secure_cookie("session_id")
        # 诺不存在则生成
        if not self.session_id:
            self.session_id = uuid.uuid4().hex
            self.data = {}
            request_handle_obj.set_secure_cookie("session_id", self.session_id)
        # 诺存在则取出值data
        else:
            try:
                json_data = request_handle_obj.redis.get("sess_%s" % self.session_id)
            except Exception as e:
                logging.error(e)
                raise e
            if not json_data:
                self.data = {}
            else:
                self.data = json.loads(json_data)

    def save(self):
        json_data = json.dumps(self.data)
        try:
            self._request_handle.redis.setex("sess_%s" % self.session_id,
                                             SESSION_EXPIRES_SECONDS, json_data)
        except Exception as e:
            logging.error(e)
            raise e

    def clear(self):
        try:
            self._request_handle.redis.delete("sess_%s" % self.session_id)
        except Exception as e:
            logging.error(e)
        self._request_handle.clear_cookie("session_id")
