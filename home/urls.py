# coding:utf-8
import os
from handle.BaseHandle import StaticFileBaseHandler as StaticFileHandler
from handle import UserHandle, VerifyCode, Profile, House, Orders
urls = [
    (r"^/api/check_login$", UserHandle.CheckLogin),  # 检验登入状态
    (r"^/api/piccode$", VerifyCode.PicCode),  # 验证码
    (r"^/api/smscode$", VerifyCode.SmsCode),  # 发送手机验证码
    (r"^/api/register$", UserHandle.Register),  # 注册
    (r"^/api/login$", UserHandle.Login),  # 登入
    (r"^/api/logout$", UserHandle.Logout), #登出
    (r"^/api/profile/avatar$", Profile.Avator), #头像上传处理
    (r"^/api/profile$", Profile.Profile),  # 个人主页个人信息
    (r"^/api/profile/name$", Profile.ChangeName),  # 修改昵称
    (r"^/api/profile/auth$", Profile.Auth),  # 认证
    (r"^/api/house/area$", House.AreaInfo),  # 所在城区
    (r"^/api/house/my$", House.MyHouse),  # 我的房源
    (r"^/api/house/info$", House.HouseInfo),  # house info
    (r"^/api/house/image$", House.HouseImage),  # 房屋图片
    (r"^/api/house/index$", House.Index),  # 首页
    (r'^/api/house/list2$', House.HouseList),  # 房屋过滤列表数据
    (r'^/api/order$', Orders.Order),  # 下单
    (r'^/api/order/my$', Orders.MyOrder), # 我的订单，作为房客和房东同时适用
    (r'^/api/order/accept$', Orders.AcceptOrder), # 接单
    (r'^/api/order/reject$', Orders.RejectOrder), # 拒单
    (r'^/api/order/comment$', Orders.OrderComment), #评论
    (r"^/(.*)$", StaticFileHandler, dict(path=os.path.join(os.path.dirname(__file__), "html"), default_filename="index.html")) 
]
