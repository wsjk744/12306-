import requests
import re
from datetime import datetime, timedelta
from tkinter import *
from tkinter import ttk, messagebox
import threading
import time
import webbrowser
import csv
import json
from pypinyin import pinyin, Style


class TicketMaster:
    def __init__(self, root):
        self.root = root
        self.root.title("🚄 12306 全国查票系统 · 终极版")
        self.root.geometry("1600x950")
        self.root.configure(bg='#0a0f1e')

        # 会话
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init'
        }

        # 全国车站数据
        self.all_stations = {}
        self.station_list = []
        self.station_pinyin = {}

        # 当前查询结果
        self.current_trains = []
        self.filtered_trains = []
        self.favorites = []

        # 全国查询相关
        self.nationwide_trains = []
        self.nationwide_index = 0
        self.nationwide_timer = None
        self.nationwide_loading = False
        self.screen_auto_refresh = False
        self.reminders = []
        self.reminder_thread_running = False
        self.screen_trains = []

        # 换乘结果缓存
        self.transfer_results = []

        # 12小时制转换标志
        self.time_format_12h = False

        # 全国主要城市列表
        self.major_cities = [
            '北京', '上海', '广州', '深圳', '杭州', '南京', '武汉', '西安',
            '成都', '重庆', '天津', '郑州', '长沙', '厦门', '青岛', '大连',
            '沈阳', '哈尔滨', '长春', '济南', '太原', '石家庄', '合肥',
            '南昌', '福州', '南宁', '贵阳', '昆明', '兰州', '西宁', '银川',
            '乌鲁木齐', '呼和浩特', '海口', '三亚', '苏州', '无锡', '宁波',
            '温州', '金华', '嘉兴', '湖州', '绍兴', '台州', '泉州', '漳州',
            '丰顺东', '广州东', '光明城', '珠海', '佛山', '东莞', '惠州',
            '中山', '江门', '肇庆', '汕头', '揭阳', '潮州', '梅州', '汕尾'
        ]

        # 加载车站
        self.load_stations()

        # 创建UI
        self.setup_ui()

    def load_stations(self):
        """加载全国车站并生成拼音"""
        try:
            url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9367"
            res = self.session.get(url, headers=self.headers, timeout=10)

            pattern = re.compile(r'\|([\u4e00-\u9fa5]+)\|([A-Z]+)\|')
            matches = pattern.findall(res.text)

            for name, code in matches:
                self.all_stations[name] = code
                self.station_list.append(name)

                try:
                    py_list = pinyin(name, style=Style.FIRST_LETTER)
                    pinyin_str = ''.join([item[0] for item in py_list])
                    self.station_pinyin[name] = pinyin_str
                except:
                    self.station_pinyin[name] = ''

            self.station_list.sort()
            print(f"✅ 加载 {len(self.all_stations)} 个车站")

        except Exception as e:
            print(f"加载失败: {e}")
            self.all_stations = {
                '北京': 'BJP', '北京西': 'BXP', '北京南': 'VNP',
                '上海': 'SHH', '上海虹桥': 'AOH',
                '广州': 'GZQ', '广州东': 'GGQ', '广州南': 'IZQ',
                '深圳': 'SZQ', '深圳北': 'IOQ',
                '杭州': 'HZH', '南京': 'NJH', '武汉': 'WHN',
                '西安': 'XAY', '成都': 'CDW', '重庆': 'CQW',
                '丰顺东': 'FDA', '广州东': 'GGQ', '光明城': 'IMQ'
            }
            self.station_list = list(self.all_stations.keys())

            for name in self.station_list:
                try:
                    py_list = pinyin(name, style=Style.FIRST_LETTER)
                    self.station_pinyin[name] = ''.join([item[0] for item in py_list])
                except:
                    self.station_pinyin[name] = ''

    def setup_ui(self):
        """创建UI"""
        top_frame = Frame(self.root, bg='#16213e', height=80)
        top_frame.pack(fill=X, padx=10, pady=10)

        Label(top_frame, text="🚆 12306 全国查票系统 · 终极版",
              bg='#16213e', fg='#00ff00', font=('Arial', 20, 'bold')).pack(pady=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=5)

        style = ttk.Style()
        style.configure('TNotebook.Tab', font=('Arial', 11, 'bold'), padding=[10, 5])

        # 创建9个功能页面
        self.create_page1()  # 🔍 自主查询
        self.create_page2()  # 🌍 全国查询
        self.create_page3()  # 🚅 车次查询
        self.create_page4()  # 🏢 车站大屏（简化版）
        self.create_page5()  # 📊 票价趋势
        self.create_page6()  # 🚉 车站车次
        self.create_page7()  # 📈 正晚点统计
        self.create_page8()  # 🔔 余票提醒
        self.create_page9()  # 🔄 智能换乘（官方接口）

        info_frame = Frame(self.root, bg='#16213e')
        info_frame.pack(fill=X, side=BOTTOM, padx=10, pady=5)

        self.stats_label = Label(info_frame, text="", bg='#16213e', fg='#00ff00',
                                 font=('Arial', 10), anchor=W)
        self.stats_label.pack(side=LEFT, padx=10)

        self.status_bar = Label(info_frame, text="就绪", bg='#16213e', fg='#00ff00',
                                font=('Arial', 10), anchor=E)
        self.status_bar.pack(side=RIGHT, padx=10)

        # 右键菜单
        self.context_menu = Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📅 查看时刻表", command=self.menu_timetable)
        self.context_menu.add_command(label="⭐ 添加到收藏", command=self.menu_add_favorite)
        self.context_menu.add_command(label="📋 复制车次号", command=self.menu_copy_train)
        self.context_menu.add_command(label="🌐 官网预订", command=self.menu_book_online)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="💰 票价详情", command=self.menu_price_detail)

    # ==================== 页面1：自主查询 ====================

    def create_page1(self):
        """页面1：自主查询"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🔍 自主查询')

        query_frame = Frame(page, bg='#16213e')
        query_frame.pack(fill=X, padx=10, pady=20)

        # 出发站
        Label(query_frame, text="出发站:", bg='#16213e', fg='white',
              font=('Arial', 11)).grid(row=0, column=0, padx=5, pady=10)

        self.from_var = StringVar()
        self.from_combo = ttk.Combobox(query_frame, textvariable=self.from_var,
                                       values=self.station_list, width=12, font=('Arial', 10))
        self.from_combo.grid(row=0, column=1, padx=5, pady=10)
        self.from_combo.bind('<KeyRelease>', self.suggest_from)
        self.from_combo.set('北京')

        # 到达站
        Label(query_frame, text="到达站:", bg='#16213e', fg='white',
              font=('Arial', 11)).grid(row=0, column=2, padx=5, pady=10)

        self.to_var = StringVar()
        self.to_combo = ttk.Combobox(query_frame, textvariable=self.to_var,
                                     values=self.station_list, width=12, font=('Arial', 10))
        self.to_combo.grid(row=0, column=3, padx=5, pady=10)
        self.to_combo.bind('<KeyRelease>', self.suggest_to)
        self.to_combo.set('上海')

        # 日期
        Label(query_frame, text="日期:", bg='#16213e', fg='white',
              font=('Arial', 11)).grid(row=0, column=4, padx=5, pady=10)

        self.date_entry = ttk.Entry(query_frame, width=12, font=('Arial', 10))
        self.date_entry.grid(row=0, column=5, padx=5, pady=10)
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # 查询按钮
        Button(query_frame, text="🔍 查询车次", command=self.start_query,
               bg='#0f3460', fg='white', font=('Arial', 11, 'bold'),
               padx=15, pady=3).grid(row=0, column=6, padx=10, pady=10)

        # 第二行：筛选条件
        row2 = Frame(query_frame, bg='#16213e')
        row2.grid(row=1, column=0, columnspan=7, pady=10, sticky='ew')

        Label(row2, text="车型筛选:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)
        self.train_type = StringVar(value="全部")
        types = ttk.Combobox(row2, textvariable=self.train_type,
                             values=['全部', '高铁(G)', '动车(D)', '城际(C)', '特快(T)', '快速(K)', '直达(Z)'],
                             width=12, state='readonly')
        types.pack(side=LEFT, padx=5)
        types.bind('<<ComboboxSelected>>', lambda e: self.apply_filter())

        Label(row2, text="时间段:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)
        self.time_range = StringVar(value="全部")
        times = ttk.Combobox(row2, textvariable=self.time_range,
                             values=['全部', '凌晨(00-06)', '上午(06-12)', '下午(12-18)', '晚上(18-24)'],
                             width=12, state='readonly')
        times.pack(side=LEFT, padx=5)
        times.bind('<<ComboboxSelected>>', lambda e: self.apply_filter())

        Label(row2, text="价格范围:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)
        self.min_price = ttk.Entry(row2, width=6)
        self.min_price.pack(side=LEFT, padx=2)
        self.min_price.insert(0, '0')
        Label(row2, text="-", bg='#16213e', fg='white').pack(side=LEFT)
        self.max_price = ttk.Entry(row2, width=6)
        self.max_price.pack(side=LEFT, padx=2)
        self.max_price.insert(0, '1000')
        Label(row2, text="元", bg='#16213e', fg='white').pack(side=LEFT)

        Button(row2, text="筛选", command=self.apply_filter,
               bg='#0f3460', fg='white', padx=15).pack(side=LEFT, padx=10)
        Button(row2, text="重置", command=self.reset_filter,
               bg='#8B0000', fg='white', padx=15).pack(side=LEFT, padx=5)

        # 第三行：排序和操作
        row3 = Frame(query_frame, bg='#16213e')
        row3.grid(row=2, column=0, columnspan=7, pady=10, sticky='ew')

        Label(row3, text="排序方式:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)
        self.sort_by = StringVar(value="默认")
        sorts = ttk.Combobox(row3, textvariable=self.sort_by,
                             values=['默认', '出发时间', '到达时间', '历时最短', '票价最低', '票价最高', '车次号'],
                             width=12, state='readonly')
        sorts.pack(side=LEFT, padx=5)
        sorts.bind('<<ComboboxSelected>>', lambda e: self.sort_trains())

        Button(row3, text="应用排序", command=self.sort_trains,
               bg='#0f3460', fg='white', padx=15).pack(side=LEFT, padx=10)

        Button(row3, text="🗑️ 一键删除", command=self.clear_current_trains,
               bg='#8B0000', fg='white', padx=15).pack(side=RIGHT, padx=5)
        Button(row3, text="⭐ 收藏", command=self.add_to_favorites,
               bg='#0f3460', fg='white', padx=15).pack(side=RIGHT, padx=5)

        # 结果表格
        columns = ('车次', '车型', '出发站', '到达站', '出发', '到达', '历时',
                   '商务座', '一等座', '二等座', '软卧', '硬卧', '硬座')

        self.tree = ttk.Treeview(page, columns=columns, show='headings', height=10)

        col_widths = [80, 60, 100, 100, 70, 70, 70, 70, 70, 70, 70, 70, 70]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor='center')

        self.tree.bind('<Double-1>', self.show_timetable)
        self.tree.bind('<Button-3>', self.show_context_menu)

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

    # ==================== 页面2：全国查询 ====================

    def create_page2(self):
        """页面2：全国查询"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🌍 全国查询')

        control_frame = Frame(page, bg='#16213e')
        control_frame.pack(fill=X, padx=10, pady=10)

        self.nationwide_btn = Button(control_frame, text="▶ 开始加载", command=self.start_nationwide_load,
                                     bg='#008000', fg='white', font=('Arial', 11, 'bold'),
                                     padx=15)
        self.nationwide_btn.pack(side=LEFT, padx=10)

        self.nationwide_stop_btn = Button(control_frame, text="⏸ 暂停", command=self.pause_nationwide_load,
                                          bg='#FFA500', fg='white', font=('Arial', 10, 'bold'),
                                          padx=15, state=DISABLED)
        self.nationwide_stop_btn.pack(side=LEFT, padx=5)

        self.nationwide_clear_btn = Button(control_frame, text="🗑️ 清空", command=self.clear_nationwide,
                                           bg='#8B0000', fg='white', font=('Arial', 10, 'bold'),
                                           padx=15)
        self.nationwide_clear_btn.pack(side=LEFT, padx=5)

        self.nationwide_progress = ttk.Progressbar(control_frame, length=300, mode='determinate')
        self.nationwide_progress.pack(side=LEFT, padx=10)

        self.nationwide_count_label = Label(control_frame, text="0/0", bg='#16213e', fg='#00ff00')
        self.nationwide_count_label.pack(side=LEFT, padx=5)

        columns = ('车次', '车型', '出发站', '到达站', '出发', '到达', '历时', '二等座')
        self.nationwide_tree = ttk.Treeview(page, columns=columns, show='headings', height=12)

        col_widths = [80, 60, 100, 100, 70, 70, 70, 70]
        for col, width in zip(columns, col_widths):
            self.nationwide_tree.heading(col, text=col)
            self.nationwide_tree.column(col, width=width, anchor='center')

        self.nationwide_tree.bind('<Double-1>', self.show_timetable)

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.nationwide_tree.yview)
        self.nationwide_tree.configure(yscrollcommand=scrollbar.set)

        self.nationwide_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

    # ==================== 页面3：车次查询 ====================

    def create_page3(self):
        """页面3：车次查询"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🚅 车次查询')

        query_frame = Frame(page, bg='#16213e')
        query_frame.pack(fill=X, padx=10, pady=20)

        Label(query_frame, text="车次号:", bg='#16213e', fg='white',
              font=('Arial', 11)).grid(row=0, column=0, padx=5, pady=10)

        self.train_no_var = StringVar()
        self.train_no_entry = ttk.Entry(query_frame, textvariable=self.train_no_var,
                                        width=15, font=('Arial', 11))
        self.train_no_entry.grid(row=0, column=1, padx=5, pady=10)
        self.train_no_entry.insert(0, 'G1')

        Label(query_frame, text="日期:", bg='#16213e', fg='white',
              font=('Arial', 11)).grid(row=0, column=2, padx=5, pady=10)

        self.train_date_entry = ttk.Entry(query_frame, width=12, font=('Arial', 10))
        self.train_date_entry.grid(row=0, column=3, padx=5, pady=10)
        self.train_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        Button(query_frame, text="🔍 查询时刻表", command=self.query_train_timetable,
               bg='#0f3460', fg='white', font=('Arial', 11, 'bold'),
               padx=15, pady=3).grid(row=0, column=4, padx=10, pady=10)

        hot_frame = Frame(query_frame, bg='#16213e')
        hot_frame.grid(row=1, column=0, columnspan=5, pady=10)

        for train in ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10']:
            btn = Button(hot_frame, text=train, bg='#0f3460', fg='white',
                         command=lambda t=train: self.set_train_no(t))
            btn.pack(side=LEFT, padx=2)

        columns = ('序号', '车站', '到达时间', '发车时间', '停留时间', '运行时间')
        self.timetable_tree = ttk.Treeview(page, columns=columns, show='headings', height=10)

        col_widths = [50, 150, 100, 100, 80, 100]
        for col, width in zip(columns, col_widths):
            self.timetable_tree.heading(col, text=col)
            self.timetable_tree.column(col, width=width, anchor='center')

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.timetable_tree.yview)
        self.timetable_tree.configure(yscrollcommand=scrollbar.set)

        self.timetable_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

    # ==================== 页面4：车站大屏（简化版）====================

    def create_page4(self):
        """页面4：车站大屏（简化版，无状态）"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🏢 车站大屏')

        # ========== 控制面板 ==========
        control_frame = Frame(page, bg='#16213e')
        control_frame.pack(fill=X, padx=10, pady=10)

        Label(control_frame, text="车站:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)

        self.screen_station_var = StringVar()
        self.screen_station_combo = ttk.Combobox(control_frame, textvariable=self.screen_station_var,
                                                 values=self.station_list, width=15)
        self.screen_station_combo.pack(side=LEFT, padx=5)
        self.screen_station_combo.set('北京南')
        self.screen_station_combo.bind('<KeyRelease>', self.suggest_screen_station)

        Label(control_frame, text="日期:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)

        self.screen_date_entry = ttk.Entry(control_frame, width=12)
        self.screen_date_entry.pack(side=LEFT, padx=5)
        self.screen_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        self.screen_btn = Button(control_frame, text="🔍 查询", command=self.query_station_screen,
                                 bg='#0f3460', fg='white', padx=15)
        self.screen_btn.pack(side=LEFT, padx=10)

        self.screen_auto_btn = Button(control_frame, text="🔄 自动刷新", command=self.toggle_screen_auto,
                                      bg='#008000', fg='white', padx=10)
        self.screen_auto_btn.pack(side=LEFT, padx=5)

        # ========== 大屏表格（无状态列，字体黑色）==========
        columns = ('车次', '始发站', '终点站', '本站到达', '本站发车')

        # 创建表格并设置样式
        style = ttk.Style()
        style.configure("Screen.Treeview",
                        background='white',
                        foreground='black',
                        fieldbackground='white',
                        font=('Arial', 10))
        style.configure("Screen.Treeview.Heading",
                        font=('Arial', 10, 'bold'),
                        background='#f0f0f0',
                        foreground='black')

        self.screen_tree = ttk.Treeview(page, columns=columns, show='headings',
                                        height=12, style="Screen.Treeview")

        col_widths = [80, 120, 120, 100, 100]
        for col, width in zip(columns, col_widths):
            self.screen_tree.heading(col, text=col)
            self.screen_tree.column(col, width=width, anchor='center')

        # 绑定双击事件
        self.screen_tree.bind('<Double-1>', self.show_timetable)

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.screen_tree.yview)
        self.screen_tree.configure(yscrollcommand=scrollbar.set)

        self.screen_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

        self.screen_update_label = Label(page, text="", bg='#0a0f1e', fg='#00ff00')
        self.screen_update_label.pack(pady=5)

    # ==================== 页面5：票价趋势 ====================

    def create_page5(self):
        """页面5：票价趋势"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='📊 票价趋势')

        query_frame = Frame(page, bg='#16213e')
        query_frame.pack(fill=X, padx=10, pady=20)

        Label(query_frame, text="车次号:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)

        self.price_train_var = StringVar()
        self.price_train_entry = ttk.Entry(query_frame, textvariable=self.price_train_var, width=15)
        self.price_train_entry.pack(side=LEFT, padx=5)
        self.price_train_entry.insert(0, 'G1')

        Label(query_frame, text="出发站:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)

        self.price_from_var = StringVar()
        self.price_from_combo = ttk.Combobox(query_frame, textvariable=self.price_from_var,
                                             values=self.station_list, width=12)
        self.price_from_combo.pack(side=LEFT, padx=5)
        self.price_from_combo.set('北京南')

        Label(query_frame, text="到达站:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)

        self.price_to_var = StringVar()
        self.price_to_combo = ttk.Combobox(query_frame, textvariable=self.price_to_var,
                                           values=self.station_list, width=12)
        self.price_to_combo.pack(side=LEFT, padx=5)
        self.price_to_combo.set('上海虹桥')

        Button(query_frame, text="📈 查看趋势", command=self.query_price_trend,
               bg='#0f3460', fg='white', padx=15).pack(side=LEFT, padx=10)

        columns = ('日期', '二等座', '一等座', '商务座', '软卧', '硬卧')
        self.price_tree = ttk.Treeview(page, columns=columns, show='headings', height=10)

        col_widths = [100, 80, 80, 80, 80, 80]
        for col, width in zip(columns, col_widths):
            self.price_tree.heading(col, text=col)
            self.price_tree.column(col, width=width, anchor='center')

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.price_tree.yview)
        self.price_tree.configure(yscrollcommand=scrollbar.set)

        self.price_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

    # ==================== 页面6：车站车次 ====================

    def create_page6(self):
        """页面6：车站车次"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🚉 车站车次')

        query_frame = Frame(page, bg='#16213e')
        query_frame.pack(fill=X, padx=10, pady=20)

        Label(query_frame, text="车站:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)

        self.station_trains_var = StringVar()
        self.station_trains_combo = ttk.Combobox(query_frame, textvariable=self.station_trains_var,
                                                 values=self.station_list, width=15)
        self.station_trains_combo.pack(side=LEFT, padx=5)
        self.station_trains_combo.set('北京南')
        self.station_trains_combo.bind('<KeyRelease>', self.suggest_station_trains)

        Label(query_frame, text="日期:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)

        self.station_trains_date = ttk.Entry(query_frame, width=12)
        self.station_trains_date.pack(side=LEFT, padx=5)
        self.station_trains_date.insert(0, datetime.now().strftime('%Y-%m-%d'))

        Button(query_frame, text="🔍 查询车次", command=self.query_station_trains,
               bg='#0f3460', fg='white', padx=15).pack(side=LEFT, padx=10)

        columns = ('车次', '始发站', '终点站', '到达本站', '离开本站', '运行区间')
        self.station_trains_tree = ttk.Treeview(page, columns=columns, show='headings', height=10)

        col_widths = [80, 100, 100, 90, 90, 150]
        for col, width in zip(columns, col_widths):
            self.station_trains_tree.heading(col, text=col)
            self.station_trains_tree.column(col, width=width, anchor='center')

        self.station_trains_tree.bind('<Double-1>', self.show_timetable)

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.station_trains_tree.yview)
        self.station_trains_tree.configure(yscrollcommand=scrollbar.set)

        self.station_trains_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

    # ==================== 页面7：正晚点统计 ====================

    def create_page7(self):
        """页面7：正晚点统计"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='📈 正晚点统计')

        query_frame = Frame(page, bg='#16213e')
        query_frame.pack(fill=X, padx=10, pady=20)

        Label(query_frame, text="车次号:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)

        self.delay_train_var = StringVar()
        self.delay_train_entry = ttk.Entry(query_frame, textvariable=self.delay_train_var, width=15)
        self.delay_train_entry.pack(side=LEFT, padx=5)
        self.delay_train_entry.insert(0, 'G1')

        Label(query_frame, text="查询月份:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)

        self.delay_month_var = StringVar(value=datetime.now().strftime('%Y-%m'))
        self.delay_month_entry = ttk.Entry(query_frame, textvariable=self.delay_month_var, width=10)
        self.delay_month_entry.pack(side=LEFT, padx=5)

        Button(query_frame, text="📊 查询统计", command=self.query_delay_stats,
               bg='#0f3460', fg='white', padx=15).pack(side=LEFT, padx=10)

        stats_frame = Frame(page, bg='#16213e')
        stats_frame.pack(fill=X, padx=10, pady=10)

        self.delay_stats_label = Label(stats_frame, text="", bg='#16213e', fg='#00ff00',
                                       font=('Arial', 12))
        self.delay_stats_label.pack(pady=10)

        columns = ('日期', '计划发车', '实际出发', '正晚点', '状态')
        self.delay_tree = ttk.Treeview(page, columns=columns, show='headings', height=10)

        col_widths = [100, 90, 90, 90, 100]
        for col, width in zip(columns, col_widths):
            self.delay_tree.heading(col, text=col)
            self.delay_tree.column(col, width=width, anchor='center')

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.delay_tree.yview)
        self.delay_tree.configure(yscrollcommand=scrollbar.set)

        self.delay_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

    # ==================== 页面8：余票提醒 ====================

    def create_page8(self):
        """页面8：余票提醒"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🔔 余票提醒')

        setting_frame = Frame(page, bg='#16213e')
        setting_frame.pack(fill=X, padx=10, pady=20)

        Label(setting_frame, text="车次号:", bg='#16213e', fg='white').grid(row=0, column=0, padx=5, pady=5)
        self.remind_train_var = StringVar()
        self.remind_train_entry = ttk.Entry(setting_frame, textvariable=self.remind_train_var, width=15)
        self.remind_train_entry.grid(row=0, column=1, padx=5, pady=5)
        self.remind_train_entry.insert(0, 'G1')

        Label(setting_frame, text="出发站:", bg='#16213e', fg='white').grid(row=0, column=2, padx=15, pady=5)
        self.remind_from_var = StringVar()
        self.remind_from_combo = ttk.Combobox(setting_frame, textvariable=self.remind_from_var,
                                              values=self.station_list, width=12)
        self.remind_from_combo.grid(row=0, column=3, padx=5, pady=5)
        self.remind_from_combo.set('北京南')

        Label(setting_frame, text="到达站:", bg='#16213e', fg='white').grid(row=0, column=4, padx=15, pady=5)
        self.remind_to_var = StringVar()
        self.remind_to_combo = ttk.Combobox(setting_frame, textvariable=self.remind_to_var,
                                            values=self.station_list, width=12)
        self.remind_to_combo.grid(row=0, column=5, padx=5, pady=5)
        self.remind_to_combo.set('上海虹桥')

        Label(setting_frame, text="席别:", bg='#16213e', fg='white').grid(row=1, column=0, padx=5, pady=5)
        self.remind_seat_var = StringVar(value="二等座")
        seat_combo = ttk.Combobox(setting_frame, textvariable=self.remind_seat_var,
                                  values=['二等座', '一等座', '商务座', '软卧', '硬卧'], width=10)
        seat_combo.grid(row=1, column=1, padx=5, pady=5)

        Label(setting_frame, text="提醒间隔:", bg='#16213e', fg='white').grid(row=1, column=2, padx=15, pady=5)
        self.remind_interval_var = StringVar(value="60")
        ttk.Entry(setting_frame, textvariable=self.remind_interval_var, width=8).grid(row=1, column=3, padx=5, pady=5)
        Label(setting_frame, text="秒", bg='#16213e', fg='white').grid(row=1, column=4, padx=2, pady=5)

        Button(setting_frame, text="➕ 添加提醒", command=self.add_reminder,
               bg='#008000', fg='white', padx=15).grid(row=1, column=5, padx=10, pady=5)

        list_frame = Frame(page, bg='#16213e')
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        Label(list_frame, text="当前提醒列表", bg='#16213e', fg='#00ff00',
              font=('Arial', 12)).pack(pady=5)

        columns = ('车次', '出发站', '到达站', '席别', '当前余票', '状态')
        self.remind_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)

        col_widths = [80, 100, 100, 80, 80, 100]
        for col, width in zip(columns, col_widths):
            self.remind_tree.heading(col, text=col)
            self.remind_tree.column(col, width=width, anchor='center')

        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.remind_tree.yview)
        self.remind_tree.configure(yscrollcommand=scrollbar.set)

        self.remind_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

        Button(list_frame, text="🗑️ 清空提醒", command=self.clear_reminders,
               bg='#8B0000', fg='white', padx=15).pack(pady=5)

    # ==================== 页面9：智能换乘（官方接口）====================

    def create_page9(self):
        """页面9：智能换乘（官方接口）"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🔄 智能换乘')

        # ========== 查询面板 ==========
        query_frame = Frame(page, bg='#16213e')
        query_frame.pack(fill=X, padx=10, pady=20)

        # 第一行：基本查询
        row1 = Frame(query_frame, bg='#16213e')
        row1.pack(pady=5, fill=X)

        Label(row1, text="出发站:", bg='#16213e', fg='white',
              font=('Arial', 11)).pack(side=LEFT, padx=5)

        self.transfer_from_var = StringVar()
        self.transfer_from_combo = ttk.Combobox(row1, textvariable=self.transfer_from_var,
                                                values=self.station_list, width=12, font=('Arial', 10))
        self.transfer_from_combo.pack(side=LEFT, padx=5)
        self.transfer_from_combo.bind('<KeyRelease>', self.suggest_transfer_from)
        self.transfer_from_combo.set('广州')

        Label(row1, text="到达站:", bg='#16213e', fg='white',
              font=('Arial', 11)).pack(side=LEFT, padx=15)

        self.transfer_to_var = StringVar()
        self.transfer_to_combo = ttk.Combobox(row1, textvariable=self.transfer_to_var,
                                              values=self.station_list, width=12, font=('Arial', 10))
        self.transfer_to_combo.pack(side=LEFT, padx=5)
        self.transfer_to_combo.bind('<KeyRelease>', self.suggest_transfer_to)
        self.transfer_to_combo.set('丰顺东')

        Label(row1, text="日期:", bg='#16213e', fg='white',
              font=('Arial', 11)).pack(side=LEFT, padx=15)

        self.transfer_date_entry = ttk.Entry(row1, width=12, font=('Arial', 10))
        self.transfer_date_entry.pack(side=LEFT, padx=5)
        self.transfer_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))

        # 12小时制开关
        self.time_12h_var = BooleanVar(value=False)
        Checkbutton(row1, text="12小时制", variable=self.time_12h_var,
                    bg='#16213e', fg='white', selectcolor='#16213e',
                    command=self.toggle_time_format).pack(side=LEFT, padx=10)

        self.transfer_btn = Button(row1, text="🔄 查询换乘", command=self.query_transfer_official,
                                   bg='#0f3460', fg='white', font=('Arial', 11, 'bold'),
                                   padx=15, pady=3)
        self.transfer_btn.pack(side=LEFT, padx=10)

        # 结果标题
        title = Label(page, text="=" * 30 + "  🔄 官方换乘方案  🔄  " + "=" * 30,
                      bg='#0a0f1e', fg='#00ff00', font=('Courier', 12, 'bold'))
        title.pack(pady=5)

        # 创建表格
        columns = ('方案', '第一程', '第二程', '总历时', '总票价', '等候时间', '操作')
        self.transfer_tree = ttk.Treeview(page, columns=columns, show='headings', height=12)

        col_widths = [60, 160, 160, 80, 80, 80, 80]
        for col, width in zip(columns, col_widths):
            self.transfer_tree.heading(col, text=col)
            self.transfer_tree.column(col, width=width, anchor='center')

        # 绑定双击事件
        self.transfer_tree.bind('<Double-1>', self.show_transfer_detail)
        self.transfer_tree.bind('<Button-3>', self.show_transfer_menu)

        scrollbar = ttk.Scrollbar(page, orient=VERTICAL, command=self.transfer_tree.yview)
        self.transfer_tree.configure(yscrollcommand=scrollbar.set)

        self.transfer_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=RIGHT, fill=Y, pady=5)

        # 底部说明
        info_frame = Frame(page, bg='#16213e')
        info_frame.pack(fill=X, padx=10, pady=5)

        Label(info_frame, text="💡 数据来自12306官方换乘接口 | 双击查看详情",
              bg='#16213e', fg='#00ff00').pack(side=LEFT, padx=10)

        self.transfer_status = Label(info_frame, text="就绪", bg='#16213e', fg='#00ff00')
        self.transfer_status.pack(side=RIGHT, padx=10)

    # ==================== 辅助方法 ====================

    def suggest_from(self, event):
        typed = self.from_var.get().lower()
        if typed:
            matches = []
            for station, py in self.station_pinyin.items():
                if typed in py:
                    matches.append(station)
            for station in self.station_list:
                if typed in station and station not in matches:
                    matches.append(station)
            self.from_combo['values'] = matches[:20]

    def suggest_to(self, event):
        typed = self.to_var.get().lower()
        if typed:
            matches = []
            for station, py in self.station_pinyin.items():
                if typed in py:
                    matches.append(station)
            for station in self.station_list:
                if typed in station and station not in matches:
                    matches.append(station)
            self.to_combo['values'] = matches[:20]

    def suggest_screen_station(self, event):
        typed = self.screen_station_var.get().lower()
        if typed:
            matches = []
            for station, py in self.station_pinyin.items():
                if typed in py:
                    matches.append(station)
            for station in self.station_list:
                if typed in station and station not in matches:
                    matches.append(station)
            self.screen_station_combo['values'] = matches[:20]

    def suggest_station_trains(self, event):
        typed = self.station_trains_var.get().lower()
        if typed:
            matches = []
            for station, py in self.station_pinyin.items():
                if typed in py:
                    matches.append(station)
            for station in self.station_list:
                if typed in station and station not in matches:
                    matches.append(station)
            self.station_trains_combo['values'] = matches[:20]

    def suggest_transfer_from(self, event):
        typed = self.transfer_from_var.get().lower()
        if typed:
            matches = []
            for station, py in self.station_pinyin.items():
                if typed in py:
                    matches.append(station)
            for station in self.station_list:
                if typed in station and station not in matches:
                    matches.append(station)
            self.transfer_from_combo['values'] = matches[:20]

    def suggest_transfer_to(self, event):
        typed = self.transfer_to_var.get().lower()
        if typed:
            matches = []
            for station, py in self.station_pinyin.items():
                if typed in py:
                    matches.append(station)
            for station in self.station_list:
                if typed in station and station not in matches:
                    matches.append(station)
            self.transfer_to_combo['values'] = matches[:20]

    def _price_format(self, p):
        if p and p != 'null' and p != '--' and p != '无':
            try:
                return f"{int(p) / 100:.0f}"
            except:
                return '无'
        return '无'

    def set_train_no(self, train_no):
        self.train_no_var.set(train_no)
        self.query_train_timetable()

    def toggle_time_format(self):
        """切换12/24小时制"""
        self.time_format_12h = self.time_12h_var.get()

    def format_time_12h(self, time_str):
        """将24小时制转换为12小时制"""
        if not time_str or time_str == '--':
            return time_str

        try:
            hour = int(time_str.split(':')[0])
            minute = time_str.split(':')[1]
            if hour < 12:
                return f"上午 {hour:02d}:{minute}"
            elif hour == 12:
                return f"下午 12:{minute}"
            else:
                return f"下午 {hour - 12:02d}:{minute}"
        except:
            return time_str

    # ==================== 自主查询方法 ====================

    def start_query(self):
        thread = threading.Thread(target=self.query_trains)
        thread.daemon = True
        thread.start()

    def query_trains(self):
        try:
            self.status_bar.config(text="查询中...")

            from_station = self.from_var.get()
            to_station = self.to_var.get()
            date = self.date_entry.get()

            if not from_station or not to_station:
                messagebox.showwarning("警告", "请填写出发站和到达站")
                return

            from_code = self.all_stations.get(from_station, '')
            to_code = self.all_stations.get(to_station, '')

            if not from_code or not to_code:
                messagebox.showwarning("警告", "车站代码不存在")
                return

            url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

            self.session.get("https://kyfw.12306.cn/otn", headers=self.headers, timeout=3)
            res = self.session.get(url, headers=self.headers, timeout=10)
            data = res.json()

            self.current_trains = []

            if data.get('data'):
                for item in data['data']:
                    train = item['queryLeftNewDTO']
                    train_code = train.get('station_train_code', '')

                    if train_code.startswith('G'):
                        train_type = '高铁'
                    elif train_code.startswith('D'):
                        train_type = '动车'
                    elif train_code.startswith('C'):
                        train_type = '城际'
                    elif train_code.startswith('T'):
                        train_type = '特快'
                    elif train_code.startswith('K'):
                        train_type = '快速'
                    else:
                        train_type = '普快'

                    train_info = {
                        'train_no': train_code,
                        'train_type': train_type,
                        'from_station': train.get('from_station_name', ''),
                        'to_station': train.get('to_station_name', ''),
                        'depart_time': train.get('start_time', ''),
                        'arrive_time': train.get('arrive_time', ''),
                        'duration': train.get('lishi', ''),
                        'business': self._price_format(train.get('swz_price', '')),
                        'first_class': self._price_format(train.get('zy_price', '')),
                        'second_class': self._price_format(train.get('ze_price', '')),
                        'soft_sleep': self._price_format(train.get('rw_price', '')),
                        'hard_sleep': self._price_format(train.get('yw_price', '')),
                        'hard_seat': self._price_format(train.get('yz_price', '')),
                        'full_no': train.get('train_no', '')
                    }
                    self.current_trains.append(train_info)

            self.filtered_trains = self.current_trains.copy()
            self._update_display()

            self.status_bar.config(text=f"✅ 找到 {len(self.current_trains)} 个车次")

        except Exception as e:
            self.status_bar.config(text=f"❌ 错误: {str(e)[:50]}")

    def _update_display(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for train in self.filtered_trains:
            values = (
                train['train_no'],
                train['train_type'],
                train['from_station'],
                train['to_station'],
                train['depart_time'],
                train['arrive_time'],
                train['duration'],
                train['business'],
                train['first_class'],
                train['second_class'],
                train['soft_sleep'],
                train['hard_sleep'],
                train['hard_seat']
            )
            self.tree.insert('', 'end', values=values)

    def apply_filter(self):
        if not self.current_trains:
            return

        filtered = []
        train_type = self.train_type.get()
        time_range = self.time_range.get()

        try:
            min_p = int(self.min_price.get()) if self.min_price.get() else 0
            max_p = int(self.max_price.get()) if self.max_price.get() else 9999
        except:
            min_p, max_p = 0, 9999

        for train in self.current_trains:
            if train_type != '全部':
                code = train['train_no'][0] if train['train_no'] else ''
                if train_type == '高铁(G)' and code != 'G':
                    continue
                if train_type == '动车(D)' and code != 'D':
                    continue
                if train_type == '城际(C)' and code != 'C':
                    continue
                if train_type == '特快(T)' and code != 'T':
                    continue
                if train_type == '快速(K)' and code != 'K':
                    continue

            if time_range != '全部':
                try:
                    hour = int(train['depart_time'].split(':')[0])
                    if time_range == '凌晨(00-06)' and not (0 <= hour < 6):
                        continue
                    if time_range == '上午(06-12)' and not (6 <= hour < 12):
                        continue
                    if time_range == '下午(12-18)' and not (12 <= hour < 18):
                        continue
                    if time_range == '晚上(18-24)' and not (18 <= hour < 24):
                        continue
                except:
                    pass

            try:
                if train['second_class'] != '无':
                    price = int(train['second_class'])
                    if price < min_p or price > max_p:
                        continue
            except:
                pass

            filtered.append(train)

        self.filtered_trains = filtered
        self._update_display()
        self.status_bar.config(text=f"筛选后 {len(filtered)} 个车次")

    def reset_filter(self):
        self.train_type.set('全部')
        self.time_range.set('全部')
        self.min_price.delete(0, END)
        self.min_price.insert(0, '0')
        self.max_price.delete(0, END)
        self.max_price.insert(0, '1000')
        self.sort_by.set('默认')
        self.filtered_trains = self.current_trains.copy()
        self._update_display()
        self.status_bar.config(text=f"已重置，共 {len(self.current_trains)} 个车次")

    def sort_trains(self):
        if not self.filtered_trains:
            return

        sort_method = self.sort_by.get()

        if sort_method == '出发时间':
            self.filtered_trains.sort(key=lambda x: x['depart_time'])
        elif sort_method == '到达时间':
            self.filtered_trains.sort(key=lambda x: x['arrive_time'])
        elif sort_method == '历时最短':
            self.filtered_trains.sort(key=lambda x: x['duration'])
        elif sort_method == '票价最低':
            self.filtered_trains.sort(key=lambda x: int(x['second_class']) if x['second_class'] != '无' else 9999)
        elif sort_method == '票价最高':
            self.filtered_trains.sort(key=lambda x: int(x['second_class']) if x['second_class'] != '无' else 0,
                                      reverse=True)
        elif sort_method == '车次号':
            self.filtered_trains.sort(key=lambda x: x['train_no'])

        self._update_display()
        self.status_bar.config(text=f"已按 {sort_method} 排序")

    def clear_current_trains(self):
        if not self.current_trains:
            messagebox.showinfo("提示", "当前没有数据可删除")
            return

        result = messagebox.askyesno("确认删除", f"确定要删除 {len(self.current_trains)} 个车次吗？")
        if result:
            self.current_trains = []
            self.filtered_trains = []
            self._update_display()
            self.status_bar.config(text="已清空所有查询结果")

    def add_to_favorites(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个车次")
            return

        item = self.tree.item(selection[0])
        train_no = item['values'][0]

        for train in self.current_trains:
            if train['train_no'] == train_no:
                if train_no not in [f['train_no'] for f in self.favorites]:
                    self.favorites.append(train)
                    self.status_bar.config(text=f"⭐ 已收藏 {train_no}")
                else:
                    self.status_bar.config(text=f"{train_no} 已在收藏中")
                break

    # ==================== 全国查询方法 ====================

    def start_nationwide_load(self):
        if self.nationwide_loading:
            return

        self.nationwide_loading = True
        self.nationwide_btn.config(state=DISABLED)
        self.nationwide_stop_btn.config(state=NORMAL)

        self.nationwide_trains = []
        self.nationwide_index = 0
        self.nationwide_tree.delete(*self.nationwide_tree.get_children())

        thread = threading.Thread(target=self._nationwide_load_thread)
        thread.daemon = True
        thread.start()

    def _nationwide_load_thread(self):
        try:
            date = self.date_entry.get()
            total_routes = len(self.major_cities) * len(self.major_cities)
            processed = 0

            for from_city in self.major_cities:
                if not self.nationwide_loading:
                    break

                for to_city in self.major_cities:
                    if not self.nationwide_loading:
                        break

                    if from_city == to_city:
                        processed += 1
                        continue

                    if from_city in self.all_stations and to_city in self.all_stations:
                        from_code = self.all_stations[from_city]
                        to_code = self.all_stations[to_city]

                        url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

                        try:
                            res = self.session.get(url, headers=self.headers, timeout=3)
                            data = res.json()

                            if data.get('data'):
                                for item in data['data']:
                                    train = item['queryLeftNewDTO']
                                    train_code = train.get('station_train_code', '')

                                    if train_code.startswith('G'):
                                        train_type = '高铁'
                                    elif train_code.startswith('D'):
                                        train_type = '动车'
                                    else:
                                        train_type = '其他'

                                    values = (
                                        train_code,
                                        train_type,
                                        train.get('from_station_name', ''),
                                        train.get('to_station_name', ''),
                                        train.get('start_time', ''),
                                        train.get('arrive_time', ''),
                                        train.get('lishi', ''),
                                        self._price_format(train.get('ze_price', ''))
                                    )

                                    self.root.after(0, lambda v=values:
                                    self.nationwide_tree.insert('', 'end', values=v))
                                    time.sleep(0.01)
                        except:
                            pass

                    processed += 1
                    progress = int(processed / total_routes * 100)
                    self.root.after(0, lambda p=progress, pr=processed, tr=total_routes:
                    self._update_nationwide_progress(p, pr, tr))

        finally:
            self.root.after(0, self._nationwide_load_complete)

    def _update_nationwide_progress(self, progress, processed, total):
        self.nationwide_progress['value'] = progress
        self.nationwide_count_label.config(text=f"{processed}/{total}")

    def _nationwide_load_complete(self):
        self.nationwide_loading = False
        self.nationwide_btn.config(state=NORMAL)
        self.nationwide_stop_btn.config(state=DISABLED)
        self.status_bar.config(text="全国查询加载完成")

    def pause_nationwide_load(self):
        self.nationwide_loading = False
        self.nationwide_btn.config(state=NORMAL)
        self.nationwide_stop_btn.config(state=DISABLED)
        self.status_bar.config(text="已暂停加载")

    def clear_nationwide(self):
        self.nationwide_tree.delete(*self.nationwide_tree.get_children())
        self.nationwide_progress['value'] = 0
        self.nationwide_count_label.config(text="0/0")
        self.status_bar.config(text="已清空")

    # ==================== 车次查询方法 ====================

    def query_train_timetable(self):
        train_no = self.train_no_var.get().upper()
        date = self.train_date_entry.get()

        self.status_bar.config(text=f"正在查询 {train_no} 时刻表...")

        thread = threading.Thread(target=self._fetch_train_timetable, args=(train_no, date))
        thread.daemon = True
        thread.start()

    def _fetch_train_timetable(self, train_no, date):
        try:
            full_no = None
            for from_city in self.major_cities[:15]:
                if full_no:
                    break
                for to_city in self.major_cities[:15]:
                    if from_city == to_city:
                        continue
                    if from_city in self.all_stations and to_city in self.all_stations:
                        from_code = self.all_stations[from_city]
                        to_code = self.all_stations[to_city]

                        url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

                        try:
                            res = self.session.get(url, headers=self.headers, timeout=3)
                            data = res.json()

                            if data.get('data'):
                                for item in data['data']:
                                    if item['queryLeftNewDTO'].get('station_train_code') == train_no:
                                        full_no = item['queryLeftNewDTO'].get('train_no')
                                        break
                        except:
                            continue

            if not full_no:
                self.root.after(0, lambda: messagebox.showinfo("提示", "未找到该车次"))
                return

            url = f"https://kyfw.12306.cn/otn/queryTrainInfo/query?leftTicketDTO.train_no={full_no}&leftTicketDTO.train_date={date}&rand_code="
            res = self.session.get(url, headers=self.headers, timeout=10)
            data = res.json()

            self.root.after(0, lambda: self.timetable_tree.delete(*self.timetable_tree.get_children()))

            if data.get('data') and data['data'].get('data'):
                stations = data['data']['data']
                for item in stations:
                    values = (
                        item['station_no'],
                        item['station_name'],
                        item['arrive_time'] if item['arrive_time'] != '----' else '始发',
                        item['start_time'] if item['start_time'] != '----' else '终到',
                        item.get('stopover_time', '--'),
                        item['running_time']
                    )
                    self.root.after(0, lambda v=values: self.timetable_tree.insert('', 'end', values=v))

                self.root.after(0, lambda: self.status_bar.config(
                    text=f"✅ {train_no} 时刻表加载完成，共 {len(stations)} 站"))
            else:
                self.root.after(0, lambda: messagebox.showinfo("提示", "暂无时刻表数据"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"查询失败: {str(e)}"))

    # ==================== 车站大屏方法 ====================

    def query_station_screen(self):
        station = self.screen_station_var.get()
        date = self.screen_date_entry.get()

        if not station:
            messagebox.showwarning("警告", "请选择车站")
            return

        if station not in self.all_stations:
            messagebox.showwarning("警告", "车站代码不存在")
            return

        self.status_bar.config(text=f"正在查询 {station} 大屏数据...")
        self.screen_btn.config(state=DISABLED, text="查询中...")

        thread = threading.Thread(target=self._fetch_station_screen, args=(station, date))
        thread.daemon = True
        thread.start()

    def _fetch_station_screen(self, station, date):
        try:
            self.root.after(0, lambda: self.screen_tree.delete(*self.screen_tree.get_children()))

            station_code = self.all_stations[station]
            all_trains = []

            for target_city in self.major_cities[:15]:
                if target_city == station:
                    continue

                if target_city in self.all_stations:
                    to_code = self.all_stations[target_city]

                    # 出发车次
                    url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={station_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

                    try:
                        res = self.session.get(url, headers=self.headers, timeout=5)
                        data = res.json()

                        if data.get('data'):
                            for item in data['data']:
                                train = item['queryLeftNewDTO']
                                train_code = train.get('station_train_code', '')

                                all_trains.append({
                                    'train_no': train_code,
                                    'start_station': station,
                                    'end_station': train.get('to_station_name', ''),
                                    'arrive_time': '--',
                                    'depart_time': train.get('start_time', '')
                                })
                    except:
                        pass

                    # 到达车次
                    url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={to_code}&leftTicketDTO.to_station={station_code}&purpose_codes=ADULT"

                    try:
                        res = self.session.get(url, headers=self.headers, timeout=5)
                        data = res.json()

                        if data.get('data'):
                            for item in data['data']:
                                train = item['queryLeftNewDTO']
                                train_code = train.get('station_train_code', '')

                                all_trains.append({
                                    'train_no': train_code,
                                    'start_station': train.get('from_station_name', ''),
                                    'end_station': station,
                                    'arrive_time': train.get('arrive_time', ''),
                                    'depart_time': '--'
                                })
                    except:
                        pass

            all_trains.sort(key=lambda x: x['depart_time'] if x['depart_time'] != '--' else x['arrive_time'])

            self.screen_trains = all_trains

            for train in all_trains:
                values = (
                    train['train_no'],
                    train['start_station'],
                    train['end_station'],
                    train['arrive_time'],
                    train['depart_time']
                )
                self.root.after(0, lambda v=values:
                self.screen_tree.insert('', 'end', values=v))
                time.sleep(0.02)

            self.root.after(0, lambda: self.screen_update_label.config(
                text=f"最后更新: {datetime.now().strftime('%H:%M:%S')} | 共 {len(all_trains)} 趟列车"))
            self.root.after(0, lambda: self.status_bar.config(
                text=f"{station} 大屏加载完成，共 {len(all_trains)} 趟列车"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"查询失败: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.screen_btn.config(state=NORMAL, text="🔍 查询"))

    def toggle_screen_auto(self):
        if not self.screen_auto_refresh:
            self.screen_auto_refresh = True
            self.screen_auto_btn.config(text="⏸ 停止刷新", bg='#8B0000')
            self._screen_auto_loop()
        else:
            self.screen_auto_refresh = False
            self.screen_auto_btn.config(text="🔄 自动刷新", bg='#008000')

    def _screen_auto_loop(self):
        if self.screen_auto_refresh:
            self.query_station_screen()
            self.root.after(30000, self._screen_auto_loop)

    # ==================== 票价趋势方法 ====================

    def query_price_trend(self):
        train_no = self.price_train_var.get().upper()
        from_station = self.price_from_var.get()
        to_station = self.price_to_var.get()

        if not train_no or not from_station or not to_station:
            messagebox.showwarning("警告", "请填写完整信息")
            return

        self.status_bar.config(text=f"正在查询 {train_no} 票价趋势...")

        thread = threading.Thread(target=self._fetch_price_trend,
                                  args=(train_no, from_station, to_station))
        thread.daemon = True
        thread.start()

    def _fetch_price_trend(self, train_no, from_station, to_station):
        try:
            self.root.after(0, lambda: self.price_tree.delete(*self.price_tree.get_children()))

            today = datetime.now()
            prices = []

            for i in range(7):
                date = (today + timedelta(days=i)).strftime('%Y-%m-%d')

                from_code = self.all_stations.get(from_station, '')
                to_code = self.all_stations.get(to_station, '')

                url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

                try:
                    res = self.session.get(url, headers=self.headers, timeout=5)
                    data = res.json()

                    if data.get('data'):
                        for item in data['data']:
                            if item['queryLeftNewDTO'].get('station_train_code') == train_no:
                                train = item['queryLeftNewDTO']
                                prices.append((
                                    date,
                                    self._price_format(train.get('ze_price', '')),
                                    self._price_format(train.get('zy_price', '')),
                                    self._price_format(train.get('swz_price', '')),
                                    self._price_format(train.get('rw_price', '')),
                                    self._price_format(train.get('yw_price', ''))
                                ))
                                break
                except:
                    continue

                time.sleep(0.5)

            for price in prices:
                self.root.after(0, lambda p=price: self.price_tree.insert('', 'end', values=p))

            self.root.after(0, lambda: self.status_bar.config(
                text=f"✅ {train_no} 票价趋势加载完成"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

    # ==================== 车站车次方法 ====================

    def query_station_trains(self):
        station = self.station_trains_var.get()
        date = self.station_trains_date.get()

        if not station:
            messagebox.showwarning("警告", "请选择车站")
            return

        self.status_bar.config(text=f"正在查询 {station} 所有车次...")

        thread = threading.Thread(target=self._fetch_station_trains, args=(station, date))
        thread.daemon = True
        thread.start()

    def _fetch_station_trains(self, station, date):
        try:
            self.root.after(0, lambda: self.station_trains_tree.delete(*self.station_trains_tree.get_children()))

            station_code = self.all_stations.get(station, '')
            all_trains = []

            for target_city in self.major_cities[:20]:
                if target_city == station:
                    continue

                if target_city in self.all_stations:
                    target_code = self.all_stations[target_city]

                    # 出发
                    url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={station_code}&leftTicketDTO.to_station={target_code}&purpose_codes=ADULT"

                    try:
                        res = self.session.get(url, headers=self.headers, timeout=3)
                        data = res.json()

                        if data.get('data'):
                            for item in data['data']:
                                train = item['queryLeftNewDTO']
                                all_trains.append({
                                    'train': train.get('station_train_code', ''),
                                    'start': station,
                                    'end': train.get('to_station_name', ''),
                                    'arrive': '--',
                                    'depart': train.get('start_time', ''),
                                    'route': f"{station} → {train.get('to_station_name', '')}"
                                })
                    except:
                        pass

                    # 到达
                    url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={target_code}&leftTicketDTO.to_station={station_code}&purpose_codes=ADULT"

                    try:
                        res = self.session.get(url, headers=self.headers, timeout=3)
                        data = res.json()

                        if data.get('data'):
                            for item in data['data']:
                                train = item['queryLeftNewDTO']
                                all_trains.append({
                                    'train': train.get('station_train_code', ''),
                                    'start': train.get('from_station_name', ''),
                                    'end': station,
                                    'arrive': train.get('arrive_time', ''),
                                    'depart': '--',
                                    'route': f"{train.get('from_station_name', '')} → {station}"
                                })
                    except:
                        pass

            all_trains.sort(key=lambda x: x['depart'] if x['depart'] != '--' else x['arrive'])

            for train in all_trains:
                values = (
                    train['train'],
                    train['start'],
                    train['end'],
                    train['arrive'],
                    train['depart'],
                    train['route']
                )
                self.root.after(0, lambda v=values: self.station_trains_tree.insert('', 'end', values=v))
                time.sleep(0.01)

            self.root.after(0, lambda: self.status_bar.config(
                text=f"✅ {station} 车次加载完成，共 {len(all_trains)} 趟"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

    # ==================== 正晚点统计方法 ====================

    def query_delay_stats(self):
        train_no = self.delay_train_var.get().upper()
        month = self.delay_month_var.get()

        if not train_no:
            messagebox.showwarning("警告", "请输入车次号")
            return

        self.status_bar.config(text=f"正在查询 {train_no} 正晚点统计...")

        thread = threading.Thread(target=self._fetch_delay_stats, args=(train_no, month))
        thread.daemon = True
        thread.start()

    def _fetch_delay_stats(self, train_no, month):
        try:
            self.root.after(0, lambda: self.delay_tree.delete(*self.delay_tree.get_children()))
            self.root.after(0, lambda: messagebox.showinfo("提示",
                                                           "正晚点统计需要历史数据接口\n目前仅支持模拟数据"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))

    # ==================== 余票提醒方法 ====================

    def add_reminder(self):
        train_no = self.remind_train_var.get().upper()
        from_station = self.remind_from_var.get()
        to_station = self.remind_to_var.get()
        seat = self.remind_seat_var.get()
        interval = int(self.remind_interval_var.get())

        if not train_no or not from_station or not to_station:
            messagebox.showwarning("警告", "请填写完整信息")
            return

        reminder = {
            'train_no': train_no,
            'from': from_station,
            'to': to_station,
            'seat': seat,
            'interval': interval,
            'last_check': None,
            'running': True
        }

        self.reminders.append(reminder)

        values = (train_no, from_station, to_station, seat, "待查询", "监控中")
        self.remind_tree.insert('', 'end', values=values)

        self.status_bar.config(text=f"✅ 已添加 {train_no} 余票提醒")

        if not self.reminder_thread_running:
            self.reminder_thread_running = True
            thread = threading.Thread(target=self._reminder_loop, daemon=True)
            thread.start()

    def _reminder_loop(self):
        while self.reminder_thread_running and self.reminders:
            for i, reminder in enumerate(self.reminders):
                if not reminder.get('running', True):
                    continue

                try:
                    from_code = self.all_stations.get(reminder['from'], '')
                    to_code = self.all_stations.get(reminder['to'], '')
                    date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

                    url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

                    res = self.session.get(url, headers=self.headers, timeout=5)
                    data = res.json()

                    ticket_count = "无"
                    if data.get('data'):
                        for item in data['data']:
                            train = item['queryLeftNewDTO']
                            if train.get('station_train_code') == reminder['train_no']:
                                if reminder['seat'] == '二等座':
                                    ticket_count = train.get('ze_price', '无')
                                elif reminder['seat'] == '一等座':
                                    ticket_count = train.get('zy_price', '无')
                                elif reminder['seat'] == '商务座':
                                    ticket_count = train.get('swz_price', '无')
                                break

                    self.root.after(0, lambda idx=i, count=ticket_count:
                    self.remind_tree.item(self.remind_tree.get_children()[idx],
                                          values=(reminder['train_no'], reminder['from'],
                                                  reminder['to'], reminder['seat'],
                                                  count, "监控中")))

                    if ticket_count != '无' and ticket_count != 'null' and ticket_count != '--':
                        self.root.after(0, lambda t=reminder['train_no'], s=reminder['seat']:
                        messagebox.showinfo("余票提醒", f"{t} {s} 有票了！"))

                except Exception as e:
                    print(f"提醒查询错误: {e}")

                time.sleep(reminder['interval'])

            time.sleep(5)

    def clear_reminders(self):
        self.reminders = []
        self.remind_tree.delete(*self.remind_tree.get_children())
        self.status_bar.config(text="已清空所有提醒")

    # ==================== 官方换乘接口方法 ====================

    def query_transfer_official(self):
        """使用12306官方联程查询接口"""
        from_station = self.transfer_from_var.get()
        to_station = self.transfer_to_var.get()
        date = self.transfer_date_entry.get()

        if not from_station or not to_station:
            messagebox.showwarning("警告", "请填写出发站和到达站")
            return

        from_code = self.all_stations.get(from_station, '')
        to_code = self.all_stations.get(to_station, '')

        if not from_code or not to_code:
            messagebox.showwarning("警告", "车站代码不存在")
            return

        self.transfer_btn.config(state=DISABLED, text="查询中...")
        self.transfer_status.config(text="正在查询官方换乘方案...")

        thread = threading.Thread(target=self._fetch_transfer_official,
                                  args=(from_code, to_code, date, from_station, to_station))
        thread.daemon = True
        thread.start()

    def _fetch_transfer_official(self, from_code, to_code, date, from_name, to_name):
        """获取官方换乘数据"""
        try:
            self.root.after(0, lambda: self.transfer_tree.delete(*self.transfer_tree.get_children()))

            url = "https://kyfw.12306.cn/lcquery/queryG"
            params = {
                'train_date': date,
                'from_station_telecode': from_code,
                'to_station_telecode': to_code,
                'middle_station': '',
                'result_index': 0,
                'can_query': 'Y',
                'isShowWZ': 'N',
                'purpose_codes': '00',
                'channel': 'E'
            }

            res = self.session.get(url, params=params, headers=self.headers, timeout=10)
            data = res.json()

            all_transfers = []

            if data.get('data') and data['data'].get('middleList'):
                for item in data['data']['middleList']:
                    first_leg = item['fullList'][0]
                    second_leg = item['fullList'][1] if len(item['fullList']) > 1 else None

                    # 计算总票价
                    total_price = 0
                    try:
                        price1 = int(first_leg.get('ze_price', 0)) / 100 if first_leg.get('ze_price') else 0
                        total_price += price1
                        if second_leg:
                            price2 = int(second_leg.get('ze_price', 0)) / 100 if second_leg.get('ze_price') else 0
                            total_price += price2
                    except:
                        pass

                    transfer = {
                        'type': '一次换乘',
                        'first_train': f"{first_leg['station_train_code']} {first_leg['from_station_name']}→{first_leg['to_station_name']}",
                        'second_train': f"{second_leg['station_train_code']} {second_leg['from_station_name']}→{second_leg['to_station_name']}" if second_leg else '--',
                        'total_duration': item['all_lishi'],
                        'total_price': f"{int(total_price)}",
                        'wait_time': item['wait_time'],
                        'first_depart': first_leg['start_time'],
                        'first_arrive': first_leg['arrive_time'],
                        'second_depart': second_leg['start_time'] if second_leg else '--',
                        'second_arrive': second_leg['arrive_time'] if second_leg else '--',
                        'middle_station': item['middle_station_name']
                    }
                    all_transfers.append(transfer)

            self.transfer_results = all_transfers
            self.root.after(0, lambda: self._display_transfer_official(all_transfers))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"查询失败: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.transfer_btn.config(state=NORMAL, text="🔄 查询换乘"))
            self.root.after(0, lambda: self.transfer_status.config(text="就绪"))

    def _display_transfer_official(self, transfers):
        """显示官方换乘方案"""
        for i, transfer in enumerate(transfers[:10]):
            # 时间格式转换
            first_text = transfer['first_train']
            if self.time_format_12h:
                first_text = f"{self.format_time_12h(transfer['first_depart'])} {first_text}"

            values = (
                f"方案{i + 1}",
                first_text,
                transfer['second_train'],
                transfer['total_duration'],
                transfer['total_price'],
                transfer['wait_time'],
                '查看详情'
            )
            self.transfer_tree.insert('', 'end', values=values)

        self.transfer_status.config(text=f"找到 {len(transfers)} 个官方换乘方案")

    def show_transfer_detail(self, event):
        """显示换乘详情"""
        selection = self.transfer_tree.selection()
        if not selection:
            return

        item = self.transfer_tree.item(selection[0])
        index = int(item['values'][0].replace('方案', '')) - 1

        if 0 <= index < len(self.transfer_results):
            transfer = self.transfer_results[index]

            detail = f"🚆 官方换乘方案\n"
            detail += "=" * 50 + "\n\n"
            detail += f"第一程: {transfer['first_train']}\n"
            detail += f"  出发: {transfer['first_depart']}  到达: {transfer['first_arrive']}\n\n"

            if transfer['second_train'] != '--':
                detail += f"第二程: {transfer['second_train']}\n"
                detail += f"  出发: {transfer['second_depart']}  到达: {transfer['second_arrive']}\n"
                detail += f"  中转站: {transfer['middle_station']}\n"
                detail += f"  等候时间: {transfer['wait_time']}\n\n"

            detail += f"总历时: {transfer['total_duration']}\n"
            detail += f"总票价: {transfer['total_price']}元"

            messagebox.showinfo("换乘详情", detail)

    def show_transfer_menu(self, event):
        """换乘右键菜单"""
        selection = self.transfer_tree.selection()
        if not selection:
            return

        menu = Menu(self.root, tearoff=0)
        menu.add_command(label="📅 查看详情", command=lambda: self.show_transfer_detail(event))
        menu.add_command(label="📋 复制方案", command=lambda: self.copy_transfer(event))
        menu.add_command(label="🌐 官网预订", command=self.menu_book_online)
        menu.post(event.x_root, event.y_root)

    def copy_transfer(self, event):
        """复制换乘方案"""
        selection = self.transfer_tree.selection()
        if selection:
            item = self.transfer_tree.item(selection[0])
            text = f"{item['values'][0]}: {item['values'][1]}"
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.transfer_status.config(text="已复制到剪贴板")

    # ==================== 时刻表方法 ====================

    def show_timetable(self, event):
        widget = event.widget
        selection = widget.selection()
        if not selection:
            return

        item = widget.item(selection[0])
        train_no = item['values'][0]

        if widget == self.screen_tree:
            date = self.screen_date_entry.get()
        elif widget == self.nationwide_tree:
            date = self.date_entry.get()
        else:
            date = self.date_entry.get()

        self.status_bar.config(text=f"正在查询 {train_no} 时刻表...")

        thread = threading.Thread(target=self._fetch_and_show_timetable,
                                  args=(train_no, date))
        thread.daemon = True
        thread.start()

    def _fetch_and_show_timetable(self, train_no, date):
        try:
            full_no = None
            for from_city in self.major_cities[:15]:
                if full_no:
                    break
                for to_city in self.major_cities[:15]:
                    if from_city == to_city:
                        continue
                    if from_city in self.all_stations and to_city in self.all_stations:
                        from_code = self.all_stations[from_city]
                        to_code = self.all_stations[to_city]

                        url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

                        try:
                            res = self.session.get(url, headers=self.headers, timeout=3)
                            data = res.json()

                            if data.get('data'):
                                for item in data['data']:
                                    if item['queryLeftNewDTO'].get('station_train_code') == train_no:
                                        full_no = item['queryLeftNewDTO'].get('train_no')
                                        break
                        except:
                            continue

            if not full_no:
                self.root.after(0, lambda: messagebox.showinfo("提示", "未找到该车次时刻表"))
                return

            url = f"https://kyfw.12306.cn/otn/queryTrainInfo/query?leftTicketDTO.train_no={full_no}&leftTicketDTO.train_date={date}&rand_code="
            res = self.session.get(url, headers=self.headers, timeout=10)
            data = res.json()

            self.root.after(0, lambda: self._show_timetable_window(train_no, date, data))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"查询失败: {str(e)}"))

    def _show_timetable_window(self, train_no, date, data):
        top = Toplevel(self.root)
        top.title(f"🚆 {train_no} 时刻表")
        top.geometry("700x500")
        top.configure(bg='#0a0f1e')

        Label(top, text=f"{train_no} 次列车时刻表 ({date})",
              bg='#0a0f1e', fg='#00ff00', font=('Arial', 14, 'bold')).pack(pady=10)

        frame = Frame(top, bg='#0a0f1e')
        frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        columns = ('序号', '车站', '到达时间', '发车时间', '停留时间', '运行时间')
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)

        col_widths = [50, 150, 100, 100, 80, 100]
        for col, width in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor='center')

        scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        if data.get('data') and data['data'].get('data'):
            stations = data['data']['data']
            for item in stations:
                values = (
                    item['station_no'],
                    item['station_name'],
                    item['arrive_time'] if item['arrive_time'] != '----' else '始发',
                    item['start_time'] if item['start_time'] != '----' else '终到',
                    item.get('stopover_time', '--'),
                    item['running_time']
                )
                tree.insert('', 'end', values=values)
        else:
            tree.insert('', 'end', values=('', '暂无数据', '', '', '', ''))

        Button(top, text="关闭", command=top.destroy,
               bg='#0f3460', fg='white', padx=20).pack(pady=10)

    # ==================== 右键菜单方法 ====================

    def show_context_menu(self, event):
        try:
            self.tree.selection_set(self.tree.identify_row(event.y))
            self.context_menu.post(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def menu_timetable(self):
        self.show_timetable(None)

    def menu_add_favorite(self):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            train_no = item['values'][0]
            self.status_bar.config(text=f"⭐ 已收藏 {train_no}")

    def menu_copy_train(self):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            train_no = item['values'][0]
            self.root.clipboard_clear()
            self.root.clipboard_append(train_no)
            self.status_bar.config(text=f"已复制 {train_no}")

    def menu_book_online(self):
        webbrowser.open("https://kyfw.12306.cn/otn/leftTicket/init")
        self.status_bar.config(text="已打开12306官网")

    def menu_price_detail(self):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            train_no = item['values'][0]

            for train in self.current_trains:
                if train['train_no'] == train_no:
                    details = f"""
车次: {train['train_no']}
车型: {train['train_type']}
路线: {train['from_station']} → {train['to_station']}
时间: {train['depart_time']} → {train['arrive_time']} ({train['duration']})

💰 票价详情:
商务座: {train['business']} 元
一等座: {train['first_class']} 元
二等座: {train['second_class']} 元
软卧: {train['soft_sleep']} 元
硬卧: {train['hard_sleep']} 元
硬座: {train['hard_seat']} 元
                    """
                    messagebox.showinfo("票价详情", details)
                    break


if __name__ == "__main__":
    root = Tk()
    app = TicketMaster(root)
    root.mainloop()