import time
import wx
from threading import Thread
from JdBuyer import Buyer

class JdBuyerApp(wx.Frame):
    def __init__(self, parent, title):
        super(JdBuyerApp, self).__init__(parent, title=title)
        self.buyer = Buyer()
        self.initApp()
        self.startFlag = False
    
    def initApp(self):
        """ 初始化界面
        """
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # 商品SUK输入框
        hboxSku = wx.BoxSizer(wx.HORIZONTAL)
        textSku = wx.StaticText(panel, -1, "商品SKU")
        hboxSku.Add(textSku, 1, wx.EXPAND|wx.ALL, 5)
        self.tcSku = wx.TextCtrl(panel, -1, value='100015253061')
        hboxSku.Add(self.tcSku, 1, wx.EXPAND|wx.ALL, 5)
        self.tcSku.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
        vbox.Add(hboxSku) 

        # 购买地区输入框
        hboxArea = wx.BoxSizer(wx.HORIZONTAL)
        textArea = wx.StaticText(panel, -1, "购买地区")
        hboxArea.Add(textArea, 1, wx.EXPAND|wx.ALL, 5)
        self.tcArea = wx.TextCtrl(panel, -1, value='1_2901_4135')
        hboxArea.Add(self.tcArea, 1, wx.EXPAND|wx.ALL, 5)
        vbox.Add(hboxArea)
        self.tcArea.Bind(wx.EVT_TEXT,self.OnKeyTyped)

        # 购买数量
        hboxNum = wx.BoxSizer(wx.HORIZONTAL)
        textNum = wx.StaticText(panel, -1, "购买数量")
        hboxNum.Add(textNum, 1, wx.EXPAND|wx.ALL, 5)
        self.spinNum = wx.SpinCtrl(panel, min=1, max=10, initial=1)
        hboxNum.Add(self.spinNum, 1, wx.EXPAND|wx.ALL, 5)
        vbox.Add(hboxNum)

        # 控制按钮
        hboxBtn = wx.BoxSizer(wx.HORIZONTAL)
        self.endBtn = wx.Button(panel, -1, "结束")
        hboxBtn.Add(self.endBtn, 1, wx.EXPAND|wx.ALL, 5)
        self.endBtn.Bind(wx.EVT_BUTTON, self.OnClicked) 
        self.startBtn = wx.Button(panel, -1, "开始")
        hboxBtn.Add(self.startBtn, 1, wx.EXPAND|wx.ALL, 5)
        self.startBtn.Bind(wx.EVT_BUTTON, self.OnClicked) 
        vbox.Add(hboxBtn)

        # 日志信息
        hboxLog = wx.BoxSizer(wx.HORIZONTAL)
        self.log_info = ''
        self.textLog = wx.StaticText(panel)
        hboxLog.Add(self.textLog, 1, wx.ALIGN_LEFT|wx.ALL, 5)
        vbox.Add(hboxLog)

        self.update_log()

        panel.SetSizer(vbox)

        self.Centre()
        self.Show()
        self.Fit()

    def update_log(self):
        self.textLog.SetLabel(self.log_info)
        wx.CallLater(1000, self.update_log)

    def OnKeyTyped(self, event):
        content = event.GetString()
        print(content)

    def OnClicked(self, event):
        """Button点击事件监听
        """
        btn = event.GetEventObject().GetLabel() 
        if(btn == '开始'):
            self.startFlag = True
             # 登陆
            if not self.buyer.is_login:
                self.login()
            self.thread = Thread(target=self.start)
            self.thread.start()
        if(btn == '结束'):
            if not self.startFlag:
                return
            self.startFlag = False
            self.thread.join()
    
    def start(self):
        """ 开始执行
        """
        self.buyer.login_by_QRcode()
        sku_id = self.tcSku.GetValue()
        area_id = self.tcArea.GetValue()
        count = self.spinNum.GetValue()

        self.buyer.item_details[sku_id] = self.buyer._get_item_detail(sku_id)
        stock_interval = 3
        submit_retry = 3
        submit_interval = 5
        while True:
            if not self.startFlag:
                self.log_info=('{0} 已结束'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
                break
            if not self.buyer._get_item_stock(sku_id=sku_id, num=1, area_id=area_id):
                self.log_info=('{0} 不满足下单条件，{1}s后进行下一次查询'.format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), stock_interval))
            else:
                self.textLog.SetLabel('{0} 满足下单条件，开始执行'.format(sku_id))
                self.buyer.clear_cart()
                self.buyer.add_item_to_cart(sku_id, count)
                if self.buyer.submit_order_with_retry(submit_retry, submit_interval):
                    self.textLog.SetLabel('下单成功')
                    return
            time.sleep(stock_interval)

    def checkTicket(self):
        # get QR code ticket
        ticket = None
        retry_times = 85
        for _ in range(retry_times):
            ticket = self.buyer._get_QRcode_ticket()
            if ticket:
                break
            time.sleep(2)
        else:
            self.log_info = '二维码过期，请重新获取扫描'
            return

        # validate QR code ticket
        if not self.buyer._validate_QRcode_ticket(ticket):
            self.log_info = '二维码信息校验失败'
            return

        self.is_login = True
        self.buyer._save_cookies()
        self.dialog.Destroy()
    
    def login(self):
        self.buyer._get_QRcode()
        thread = Thread(target=self.checkTicket)
        thread.start()
        self.dialog = QrDialog(None, title='请打开京东扫码二维码')
        self.dialog.ShowModal()
        thread.join()

class QrDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        super(QrDialog, self).__init__(*args, **kw)

        self.InitUI()
        self.SetSize((250, 200))

    def InitUI(self):

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.HORIZONTAL)

        qrcode = wx.Image('QRcode.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        bmp = wx.StaticBitmap(panel, -1, qrcode)
        vbox.Add(bmp, 1, wx.Center, 5)

		
if __name__ == '__main__':
    app = wx.App() 
    JdBuyerApp(None, '京东小猪手')
    app.MainLoop()