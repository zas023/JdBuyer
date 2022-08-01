import json
import os
import sys
import pickle
import random
import time
import requests

from lxml import etree

DEFAULT_TIMEOUT = 10
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'

if getattr(sys, 'frozen', False):
    absPath = os.path.dirname(os.path.abspath(sys.executable))
elif __file__:
    absPath = os.path.dirname(os.path.abspath(__file__))


class Session(object):
    """
    京东买手
    """

    # 初始化
    def __init__(self):
        self.user_agent = DEFAULT_USER_AGENT
        self.headers = {'User-Agent': self.user_agent}
        self.timeout = DEFAULT_TIMEOUT
        self.item_details = dict()  # 商品信息：分类id、商家id
        self.username = 'jd'
        self.is_login = False
        self.password = None
        self.sess = requests.session()
        try:
            self.load_cookies()
        except Exception:
            pass

    ############## 登录相关 #############
    # 保存 cookie
    def _save_cookies(self):
        cookies_file = os.path.join(
            absPath, './cookies/{0}.cookies'.format(self.username))
        directory = os.path.dirname(cookies_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(cookies_file, 'wb') as f:
            pickle.dump(self.sess.cookies, f)

    # 加载 cookie
    def load_cookies(self):
        cookies_file = os.path.join(
            absPath, './cookies/{0}.cookies'.format(self.username))
        with open(cookies_file, 'rb') as f:
            local_cookies = pickle.load(f)
        self.sess.cookies.update(local_cookies)
        self.is_login = self._validate_cookies()

    # 验证 cookie
    def _validate_cookies(self):
        """
        通过访问用户订单列表页进行判断：若未登录，将会重定向到登陆页面。
        :return: cookies是否有效 True/False
        """
        url = 'https://order.jd.com/center/list.action'
        payload = {
            'rid': str(int(time.time() * 1000)),
        }
        try:
            resp = self.sess.get(url=url, params=payload,
                                 allow_redirects=False)
            if self.response_status(resp):
                return True
        except Exception as e:
            return False

        self.sess = requests.session()
        return False

    # 获取登录页
    def _get_login_page(self):
        url = "https://passport.jd.com/new/login.aspx"
        page = self.sess.get(url, headers=self.headers)
        return page

    # 获取登录二维码
    def get_QRcode(self):
        url = 'https://qr.m.jd.com/show'
        payload = {
            'appid': 133,
            'size': 147,
            't': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        resp = self.sess.get(url=url, headers=headers, params=payload)

        if not self.response_status(resp):
            return None

        return resp.content

    # 获取Ticket
    def _get_QRcode_ticket(self):
        url = 'https://qr.m.jd.com/check'
        payload = {
            'appid': '133',
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'token': self.sess.cookies.get('wlfstk_smdl'),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        resp = self.sess.get(url=url, headers=headers, params=payload)

        if not self.response_status(resp):
            return False

        resp_json = self.parse_json(resp.text)
        if resp_json['code'] != 200:
            return None
        else:
            return resp_json['ticket']

    # 验证Ticket
    def _validate_QRcode_ticket(self, ticket):
        url = 'https://passport.jd.com/uc/qrCodeTicketValidation'
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://passport.jd.com/uc/login?ltype=logout',
        }
        resp = self.sess.get(url=url, headers=headers, params={'t': ticket})

        if not self.response_status(resp):
            return False

        resp_json = json.loads(resp.text)
        if resp_json['returnCode'] == 0:
            return True
        else:
            return False

    ############## 商品方法 #############
    # 获取商品详情信息
    def _get_item_detail(self, sku_id):
        '''
        :param sku_id
        :return 商品信息
        '''
        url = 'https://item.jd.com/{}.html'.format(sku_id)
        page = requests.get(url=url, headers=self.headers)

        html = etree.HTML(page.text)
        vender = html.xpath(
            '//div[@class="follow J-follow-shop"]/@data-vid')[0]
        cat = html.xpath('//a[@clstag="shangpin|keycount|product|mbNav-3"]/@href')[
            0].replace('//list.jd.com/list.html?cat=', '')

        detail = dict(cat_id=cat, vender_id=vender)
        return detail

    ############## 库存方法 #############
    # 获取单个商品库存状态
    def _get_item_stock(self, sku_id, num, area_id):
        """
        :param sku_id: 商品id
        :param num: 商品数量
        :param area_id: 地区id
        :return: 商品是否有货 True/False
        """

        item = self.item_details.get(sku_id)

        if not item:
            return False

        url = 'https://c0.3.cn/stock'
        payload = {
            'skuId': sku_id,
            'buyNum': num,
            'area': area_id,
            'ch': 1,
            '_': str(int(time.time() * 1000)),
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            # get error stock state without this param
            'extraParam': '{"originid":"1"}',
            # get 403 Forbidden without this param (obtained from the detail page)
            'cat': item.get('cat_id'),
            # return seller information with this param (can't be ignored)
            'venderId': item.get('vender_id')
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://item.jd.com/{}.html'.format(sku_id),
        }

        resp_text = ''
        try:
            resp_text = requests.get(
                url=url, params=payload, headers=headers, timeout=self.timeout).text
            resp_json = self.parse_json(resp_text)
            stock_info = resp_json.get('stock')
            sku_state = stock_info.get('skuState')  # 商品是否上架
            # 商品库存状态：33 -- 现货  0,34 -- 无货  36 -- 采购中  40 -- 可配货
            stock_state = stock_info.get('StockState')
            return sku_state == 1 and stock_state in (33, 40)
        except Exception as e:
            return False

    ############## 购物车相关 #############

    def uncheckCartAll(self):
        """ 取消所有选中商品
        return 购物车信息
        """
        url = 'https://api.m.jd.com/api'

        headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/x-www-form-urlencoded',
            'origin': 'https://cart.jd.com',
            'referer': 'https://cart.jd.com'
        }

        data = {
            'functionId': 'pcCart_jc_cartUnCheckAll',
            'appid': 'JDC_mall_cart',
            'body': '{"serInfo":{"area":"","user-key":""}}',
            'loginType': 3
        }

        resp = self.sess.post(url=url, headers=headers, data=data)

        # return self.response_status(resp) and resp.json()['success']
        return resp

    def addCartSku(self, skuId, skuNum):
        """ 加入购入车
        skuId 商品sku
        skuNum 购买数量
        retrun 是否成功
        """
        url = 'https://api.m.jd.com/api'

        headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/x-www-form-urlencoded',
            'origin': 'https://cart.jd.com',
            'referer': 'https://cart.jd.com'
        }

        data = {
            'functionId': 'pcCart_jc_cartAdd',
            'appid': 'JDC_mall_cart',
            'body': '{\"operations\":[{\"carttype\":1,\"TheSkus\":[{\"Id\":\"' + skuId + '\",\"num\":' + str(skuNum) + '}]}]}',
            'loginType': 3
        }

        resp = self.sess.post(url=url, headers=headers, data=data)

        return self.response_status(resp) and resp.json()['success']

    def changeCartSkuCount(self, skuId, skuUid, skuNum, areaId):
        """ 修改购物车商品数量
        skuId 商品sku
        skuUid 商品用户关系
        skuNum 购买数量
        retrun 是否成功
        """
        url = 'https://api.m.jd.com/api'

        headers = {
            'User-Agent': self.user_agent,
            'Content-Type': 'application/x-www-form-urlencoded',
            'origin': 'https://cart.jd.com',
            'referer': 'https://cart.jd.com'
        }

        body = '{\"operations\":[{\"TheSkus\":[{\"Id\":\"'+skuId+'\",\"num\":'+str(
            skuNum)+',\"skuUuid\":\"'+skuUid+'\",\"useUuid\":false}]}],\"serInfo\":{\"area\":\"'+areaId+'\"}}'
        data = {
            'functionId': 'pcCart_jc_changeSkuNum',
            'appid': 'JDC_mall_cart',
            'body': body,
            'loginType': 3
        }

        resp = self.sess.post(url=url, headers=headers, data=data)

        return self.response_status(resp) and resp.json()['success']

    def prepareCart(self, skuId, skuNum, areaId):
        """ 下单前准备购物车
        1 取消全部勾选（返回购物车信息）
        2 已在购物车则修改商品数量
        3 不在购物车则加入购物车
        skuId 商品sku
        skuNum 商品数量
        return True/False
        """
        resp = self.uncheckCartAll()
        respObj = resp.json()
        if not self.response_status(resp) or not respObj['success']:
            raise Exception('购物车取消勾选失败')

        # 检查商品是否已在购物车
        cartInfo = respObj['resultData']['cartInfo']
        if not cartInfo:
            # 购物车为空 直接加入
            return self.addCartSku(skuId, skuNum)

        venders = cartInfo['vendors']

        for vender in venders:
            # if str(vender['vendorId']) != self.item_details[skuId]['vender_id']:
            #     continue
            items = vender['sorted']
            for item in items:
                if str(item['item']['Id']) == skuId:
                    # 在购物车中 修改数量
                    return self.changeCartSkuCount(skuId, item['item']['skuUuid'], skuNum, areaId)
        # 不在购物车中
        return self.addCartSku(skuId, skuNum)

    ############## 订单相关 #############

    def submit_order_with_retry(self, retry=3, interval=4):
        """提交订单，并且带有重试功能
        :param retry: 重试次数
        :param interval: 重试间隔
        :return: 订单提交结果 True/False
        """
        for i in range(1, retry + 1):
            self.get_checkout_page()
            if self.submit_order():
                return True
            else:
                if i < retry:
                    time.sleep(interval)
        return False

    def get_checkout_page(self):
        """获取订单结算页面信息
        :return: 结算信息 dict
        """
        url = 'http://trade.jd.com/shopping/order/getOrderInfo.action'
        # url = 'https://cart.jd.com/gotoOrder.action'
        payload = {
            'rid': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://cart.jd.com/cart',
        }
        try:
            resp = self.sess.get(url=url, params=payload, headers=headers)
            if not self.response_status(resp):
                return

            html = etree.HTML(resp.text)
            self.eid = html.xpath("//input[@id='eid']/@value")
            self.fp = html.xpath("//input[@id='fp']/@value")
            self.risk_control = html.xpath("//input[@id='riskControl']/@value")
            self.track_id = html.xpath("//input[@id='TrackID']/@value")

            order_detail = {
                # remove '寄送至： ' from the begin
                'address': html.xpath("//span[@id='sendAddr']")[0].text[5:],
                # remove '收件人:' from the begin
                'receiver':  html.xpath("//span[@id='sendMobile']")[0].text[4:],
                # remove '￥' from the begin
                'total_price':  html.xpath("//span[@id='sumPayPriceId']")[0].text[1:],
                'items': []
            }
            return order_detail
        except Exception as e:
            return

    def submit_order(self):
        """提交订单
        :return: True/False 订单提交结果
        """
        url = 'https://trade.jd.com/shopping/order/submitOrder.action'
        # js function of submit order is included in https://trade.jd.com/shopping/misc/js/order.js?r=2018070403091

        data = {
            'overseaPurchaseCookies': '',
            'vendorRemarks': '[]',
            'submitOrderParam.sopNotPutInvoice': 'false',
            'submitOrderParam.trackID': 'TestTrackId',
            'submitOrderParam.ignorePriceChange': '0',
            'submitOrderParam.btSupport': '0',
            'riskControl': self.risk_control,
            'submitOrderParam.isBestCoupon': 1,
            'submitOrderParam.jxj': 1,
            'submitOrderParam.trackId': self.track_id,
            'submitOrderParam.eid': self.eid,
            'submitOrderParam.fp': self.fp,
            'submitOrderParam.needCheck': 1,
        }

        # add payment password when necessary
        payment_pwd = self.password
        if payment_pwd:
            data['submitOrderParam.payPassword'] = ''.join(
                ['u3' + x for x in payment_pwd])

        headers = {
            'User-Agent': self.user_agent,
            'Host': 'trade.jd.com',
            'Referer': 'http://trade.jd.com/shopping/order/getOrderInfo.action',
        }

        try:
            resp = self.sess.post(url=url, data=data, headers=headers)
            resp_json = json.loads(resp.text)

            if resp_json.get('success'):
                order_id = resp_json.get('orderId')
                return True
            else:
                message, result_code = resp_json.get(
                    'message'), resp_json.get('resultCode')
                if result_code == 0:
                    self._save_invoice()
                    message = message + '(下单商品可能为第三方商品，将切换为普通发票进行尝试)'
                elif result_code == 60077:
                    message = message + '(可能是购物车为空 或 未勾选购物车中商品)'
                elif result_code == 60123:
                    message = message + '(需要在config.ini文件中配置支付密码)'
                return False
        except Exception as e:
            return False

    def _save_invoice(self):
        """下单第三方商品时如果未设置发票，将从电子发票切换为普通发票
        http://jos.jd.com/api/complexTemplate.htm?webPamer=invoice&groupName=%E5%BC%80%E6%99%AE%E5%8B%92%E5%85%A5%E9%A9%BB%E6%A8%A1%E5%BC%8FAPI&id=566&restName=jd.kepler.trade.submit&isMulti=true
        :return:
        """
        url = 'https://trade.jd.com/shopping/dynamic/invoice/saveInvoice.action'
        data = {
            "invoiceParam.selectedInvoiceType": 1,
            "invoiceParam.companyName": "个人",
            "invoiceParam.invoicePutType": 0,
            "invoiceParam.selectInvoiceTitle": 4,
            "invoiceParam.selectBookInvoiceContent": "",
            "invoiceParam.selectNormalInvoiceContent": 1,
            "invoiceParam.vatCompanyName": "",
            "invoiceParam.code": "",
            "invoiceParam.regAddr": "",
            "invoiceParam.regPhone": "",
            "invoiceParam.regBank": "",
            "invoiceParam.regBankAccount": "",
            "invoiceParam.hasCommon": "true",
            "invoiceParam.hasBook": "false",
            "invoiceParam.consigneeName": "",
            "invoiceParam.consigneePhone": "",
            "invoiceParam.consigneeAddress": "",
            "invoiceParam.consigneeProvince": "请选择：",
            "invoiceParam.consigneeProvinceId": "NaN",
            "invoiceParam.consigneeCity": "请选择",
            "invoiceParam.consigneeCityId": "NaN",
            "invoiceParam.consigneeCounty": "请选择",
            "invoiceParam.consigneeCountyId": "NaN",
            "invoiceParam.consigneeTown": "请选择",
            "invoiceParam.consigneeTownId": 0,
            "invoiceParam.sendSeparate": "false",
            "invoiceParam.usualInvoiceId": "",
            "invoiceParam.selectElectroTitle": 4,
            "invoiceParam.electroCompanyName": "undefined",
            "invoiceParam.electroInvoiceEmail": "",
            "invoiceParam.electroInvoicePhone": "",
            "invokeInvoiceBasicService": "true",
            "invoice_ceshi1": "",
            "invoiceParam.showInvoiceSeparate": "false",
            "invoiceParam.invoiceSeparateSwitch": 1,
            "invoiceParam.invoiceCode": "",
            "invoiceParam.saveInvoiceFlag": 1
        }
        headers = {
            'User-Agent': self.user_agent,
            'Referer': 'https://trade.jd.com/shopping/dynamic/invoice/saveInvoice.action',
        }
        self.sess.post(url=url, data=data, headers=headers)

    def parse_json(self, s):
        begin = s.find('{')
        end = s.rfind('}') + 1
        return json.loads(s[begin:end])

    def response_status(self, resp):
        if resp.status_code != requests.codes.OK:
            return False
        return True
