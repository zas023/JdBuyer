# -*- coding: utf-8 -*-
import time

from config import global_config
from log import logger
from exception import JDException
from JdSession import Session
# from timer import Timer
from datetime import datetime
from utils import (
    save_image,
    convert_image,
    open_image,
    send_wechat
)


class Buyer(object):
    """
    京东买手
    """

    # 初始化
    def __init__(self):
        self.session = Session()
        # 微信推送
        self.enableWx = global_config.getboolean('messenger', 'enable')
        self.scKey = global_config.get('messenger', 'sckey')

    ############## 登录相关 #############
    # 二维码登录
    def loginByQrCode(self):
        if self.session.isLogin:
            logger.info('登录成功')
            return

        # download QR code
        qrCode = self.session.getQRcode()
        if not qrCode:
            raise JDException('二维码下载失败')

        fileName = 'QRcode.png'
        save_image(qrCode, fileName)
        new_file_name = 'QRcode.jpg'
        convert_image(fileName, new_file_name)
        logger.info('二维码获取成功，请打开京东APP扫描')
        
        open_image(new_file_name)

        # get QR code ticket
        ticket = None
        retryTimes = 85
        for i in range(retryTimes):
            ticket = self.session.getQRcodeTicket()
            if ticket:
                break
            time.sleep(2)
        else:
            raise JDException('二维码过期，请重新获取扫描')

        # validate QR code ticket
        if not self.session.validateQRcodeTicket(ticket):
            raise JDException('二维码信息校验失败')

        logger.info('二维码登录成功')
        self.session.isLogin = True
        self.session.saveCookies()

    ############## 外部方法 #############
    def buyItemInStock(
            self, skuId, areaId, end_time: datetime,
            skuNum=1, stockInterval=3, submitRetry=3, 
            submitInterval=5):
        """根据库存自动下单商品
        :skuId 商品sku
        :areaId 下单区域id
        :skuNum 购买数量
        :stockInterval 库存查询间隔（单位秒）
        :submitRetry 下单尝试次数
        :submitInterval 下单尝试间隔（单位秒）
        :buyTime 定时执行
        """
        
        # timer = Timer(start_time)
        # timer.start()

        while time.time() < time.mktime(end_time.timetuple()):
            try:
                if not self.session.getItemStock(skuId, skuNum, areaId):
                    logger.info('不满足下单条件，{0}s后进行下一次查询'.format(stockInterval))
                else:
                    logger.info('{0} 满足下单条件，开始执行'.format(skuId))
                    if self.session.trySubmitOrder(skuId, skuNum, areaId, submitRetry, submitInterval):
                        logger.info('下单成功')
                        if self.enableWx:
                            send_wechat(
                                message='JdBuyerApp', desp='您的商品已下单成功，请及时支付订单', sckey=self.scKey)
                        return
            except Exception as e:
                logger.error(e)
            time.sleep(stockInterval)


if __name__ == '__main__':
    
    from apscheduler.schedulers.background import BlockingScheduler
    import zoneinfo
    # 商品id,直接从详情页获取
    skuId = '100043960941'  # 准备抢4080公版
    # skuId = '100012700398'
    # 区域id(可根据工程 area_id 目录查找)
    areaId = '19_1601_3637'
    # 购买数量
    skuNum = 1
    # 查询库存间隔
    stockInterval = 1
    # 监听库存后尝试下单次数
    submitRetry = 3
    # 下单尝试间隔(秒)
    submitInterval = 1
    # 预约商品的购买时间，建议比开抢时间提前1分钟左右，否则会有延迟的
    start_time = '2022-12-05 13:59:00'
    end_time = '2022-12-05 14:02:00'

    # start_time = '2022-12-04 22:56:00'
    # end_time = '2022-12-04 22:56:15'

    # 创建定时任务
    scheduler = BlockingScheduler()
    zone = zoneinfo.ZoneInfo("Asia/Shanghai")
    start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=zone) 
    end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=zone) 
    print(f"程序预计开始时间：{start_time}, 预计结束时间：{end_time}")
    

    buyer = Buyer()
    # 登录京东账号
    buyer.loginByQrCode()
    # 获取商品信息
    buyer.session.fetchItemDetail(skuId)

    # 添加定时任务
    scheduler.add_job(
        buyer.buyItemInStock, 'date', run_date=start_time, 
        args=[skuId, areaId, end_time,
            skuNum, stockInterval, submitRetry, 
            submitInterval]
    )
    # 准备执行
    scheduler.start()

    # buyer.buyItemInStock(
    #     skuId, areaId, skuNum, stockInterval,
    #     submitRetry, submitInterval,
    #     start_time=start_time, end_time=end_time
    # )
