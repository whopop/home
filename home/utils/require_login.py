# -*-coding:utf-8-*-

import functools
from utils.response_code import RET


def require_login(fun):
    """ 检验是否登入的装饰器"""
    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        if not self.get_current_user():
            return self.write(dict(errcode=RET.SESSIONERR, errmsg="用户未登录"))
        else:
            fun(self, *args, **kwargs)
    return wrapper
