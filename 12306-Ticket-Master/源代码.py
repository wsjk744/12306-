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
from collections import deque
from pypinyin import pinyin, Style


class TicketMaster:
    def __init__(self, root):
        self.root = root
        self.root.title("🚄 12306 全国查票系统 · V3.0版")
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

        # 查询缓存（提高速度）
        self.query_cache = {}

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

        # 换乘枢纽站
        self.transfer_hubs = ['北京', '上海', '广州', '武汉', '郑州', '西安', '南京', '杭州', '济南', '沈阳', '成都',
                              '长沙']

        # 全国所有省份的车站映射
        self.province_stations = {
            '北京': ['北京', '北京西', '北京南', '北京北', '北京东', '北京朝阳', '北京大兴', '北京丰台'],
            '上海': ['上海', '上海虹桥', '上海南', '上海西', '上海松江', '安亭北', '金山北'],
            '天津': ['天津', '天津西', '天津南', '天津北', '滨海', '滨海西', '滨海北', '军粮城北'],
            '重庆': ['重庆', '重庆北', '重庆西', '重庆南', '沙坪坝', '永川东', '荣昌北', '大足南', '綦江东'],

            '广东': ['广州', '广州东', '广州南', '广州北', '广州白云', '深圳', '深圳北', '深圳东', '深圳西',
                     '深圳坪山', '深圳机场', '珠海', '珠海北', '珠海长隆', '佛山', '佛山西', '东莞', '东莞东',
                     '东莞南', '虎门', '虎门北', '惠州', '惠州南', '惠州北', '中山', '中山北', '中山站',
                     '江门', '江门东', '肇庆', '肇庆东', '汕头', '汕头北', '揭阳', '揭阳机场', '揭阳南',
                     '潮州', '潮汕', '潮阳', '梅州', '梅州西', '梅州东', '汕尾', '陆丰', '丰顺东', '普宁',
                     '清远', '清远西', '韶关', '韶关东', '乐昌', '乐昌东', '阳江', '阳春', '茂名', '茂名西',
                     '茂名东', '湛江', '湛江西', '湛江南', '云浮', '云浮东', '罗定', '河源', '河源东',
                     '龙川', '和平', '连平', '紫金', '惠来', '惠东', '博罗', '龙门', '仁化', '始兴',
                     '翁源', '新丰', '乳源', '乐昌', '南雄', '曲江', '浈江', '武江'],

            '江苏': ['南京', '南京南', '南京站', '苏州', '苏州北', '苏州园区', '苏州新区', '无锡', '无锡东',
                     '无锡新区', '常州', '常州北', '徐州', '徐州东', '徐州站', '扬州', '扬州东', '镇江',
                     '镇江南', '镇江站', '南通', '南通西', '海安', '如皋', '启东', '连云港', '连云港东',
                     '淮安', '淮安东', '盐城', '盐城北', '泰州', '泰兴', '靖江', '兴化', '宿迁', '沭阳',
                     '泗阳', '泗洪', '常熟', '张家港', '昆山', '昆山南', '太仓', '吴江', '宜兴', '江阴',
                     '溧阳', '金坛', '高邮', '宝应', '仪征', '句容', '丹阳', '丹阳北', '扬中', '新沂',
                     '邳州', '睢宁', '沛县', '丰县', '赣榆', '东海', '灌云', '灌南', '涟水', '洪泽',
                     '盱眙', '金湖', '阜宁', '射阳', '建湖', '大丰', '东台'],

            '浙江': ['杭州', '杭州东', '杭州南', '杭州西', '宁波', '宁波东', '温州', '温州南', '温州北',
                     '金华', '金华站', '义乌', '义乌西', '绍兴', '绍兴北', '绍兴东', '嘉兴', '嘉兴南',
                     '湖州', '湖州站', '台州', '台州西', '台州南', '丽水', '丽水站', '衢州', '衢州站',
                     '舟山', '舟山西', '诸暨', '余姚', '余姚北', '慈溪', '奉化', '宁海', '象山', '石浦',
                     '临海', '温岭', '玉环', '三门', '天台', '仙居', '黄岩', '路桥', '椒江', '永嘉',
                     '乐清', '乐清北', '瑞安', '瑞安东', '平阳', '苍南', '龙港', '文成', '泰顺', '洞头',
                     '嵊州', '新昌', '诸暨', '上虞', '嵊泗', '岱山', '普陀', '定海'],

            '湖北': ['武汉', '汉口', '武昌', '武汉东', '武汉西', '宜昌', '宜昌东', '襄阳', '襄阳东',
                     '荆州', '荆州站', '黄石', '黄石北', '十堰', '十堰东', '恩施', '恩施站', '随州',
                     '孝感', '孝感北', '咸宁', '咸宁北', '黄冈', '黄冈东', '鄂州', '鄂州站', '荆门',
                     '仙桃', '潜江', '天门', '神农架', '秭归', '兴山', '巴东', '建始', '利川', '宣恩',
                     '咸丰', '来凤', '鹤峰', '丹江口', '老河口', '枣阳', '宜城', '南漳', '保康', '谷城'],

            '湖南': ['长沙', '长沙南', '长沙站', '株洲', '株洲西', '湘潭', '湘潭北', '衡阳', '衡阳东',
                     '邵阳', '邵阳北', '岳阳', '岳阳东', '常德', '常德站', '张家界', '张家界西', '益阳',
                     '郴州', '郴州西', '永州', '永州站', '怀化', '怀化南', '娄底', '娄底南', '湘西州',
                     '吉首', '凤凰', '花垣', '保靖', '古丈', '永顺', '龙山', '泸溪', '新晃', '芷江',
                     '会同', '靖州', '通道', '洪江', '沅陵', '辰溪', '溆浦', '中方', '麻阳', '新化'],

            '福建': ['福州', '福州南', '福州站', '厦门', '厦门北', '厦门站', '泉州', '泉州站', '泉州东',
                     '漳州', '漳州东', '龙岩', '龙岩站', '三明', '三明北', '南平', '南平北', '宁德',
                     '莆田', '莆田站', '武夷山', '武夷山东', '建瓯', '建阳', '邵武', '光泽', '松溪',
                     '政和', '浦城', '顺昌', '将乐', '泰宁', '建宁', '宁化', '清流', '明溪', '永安'],

            '山东': ['济南', '济南西', '济南东', '青岛', '青岛北', '青岛西', '烟台', '烟台南', '威海',
                     '威海站', '潍坊', '潍坊北', '淄博', '淄博站', '临沂', '临沂北', '济宁', '济宁北',
                     '泰安', '泰安站', '聊城', '聊城西', '德州', '德州东', '滨州', '滨州站', '东营',
                     '菏泽', '菏泽东', '枣庄', '枣庄西', '日照', '日照西', '莱芜', '钢城', '新泰'],

            '四川': ['成都', '成都东', '成都南', '成都西', '绵阳', '绵阳站', '德阳', '德阳站', '宜宾',
                     '宜宾西', '泸州', '泸州站', '南充', '南充北', '达州', '达州站', '内江', '内江北',
                     '自贡', '自贡东', '攀枝花', '攀枝花南', '乐山', '乐山站', '眉山', '眉山东',
                     '广元', '广元站', '遂宁', '遂宁站', '资阳', '资阳北', '巴中', '巴中站', '雅安',
                     '阿坝', '甘孜', '凉山', '西昌', '西昌西', '会理', '会东', '宁南', '普格', '布拖'],

            '河南': ['郑州', '郑州东', '郑州站', '洛阳', '洛阳龙门', '南阳', '南阳东', '新乡', '新乡东',
                     '商丘', '商丘站', '信阳', '信阳东', '驻马店', '驻马店西', '周口', '周口东',
                     '平顶山', '平顶山西', '开封', '开封北', '安阳', '安阳东', '鹤壁', '鹤壁东',
                     '焦作', '焦作站', '濮阳', '濮阳东', '许昌', '许昌东', '漯河', '漯河西', '三门峡'],

            '河北': ['石家庄', '石家庄站', '保定', '保定东', '唐山', '唐山站', '邯郸', '邯郸东',
                     '秦皇岛', '秦皇岛站', '邢台', '邢台东', '沧州', '沧州西', '廊坊', '廊坊站',
                     '承德', '承德南', '张家口', '张家口站', '衡水', '衡水北', '辛集', '定州'],

            '陕西': ['西安', '西安北', '西安站', '宝鸡', '宝鸡南', '咸阳', '咸阳西', '渭南', '渭南北',
                     '铜川', '铜川东', '延安', '延安站', '榆林', '榆林站', '汉中', '汉中站', '安康',
                     '商洛', '商洛站', '杨凌', '兴平', '韩城', '华阴', '华州', '潼关', '大荔'],

            '辽宁': ['沈阳', '沈阳北', '沈阳南', '大连', '大连北', '鞍山', '鞍山西', '抚顺', '抚顺北',
                     '本溪', '本溪站', '丹东', '丹东站', '锦州', '锦州南', '营口', '营口东', '阜新',
                     '辽阳', '辽阳站', '盘锦', '盘锦站', '铁岭', '铁岭西', '朝阳', '葫芦岛'],

            '黑龙江': ['哈尔滨', '哈尔滨西', '哈尔滨东', '齐齐哈尔', '齐齐哈尔南', '牡丹江', '牡丹江站',
                       '佳木斯', '佳木斯站', '大庆', '大庆东', '大庆西', '绥化', '绥化站', '黑河',
                       '鸡西', '双鸭山', '伊春', '七台河', '鹤岗', '大兴安岭', '加格达奇'],

            '吉林': ['长春', '长春西', '长春站', '吉林', '吉林站', '四平', '四平东', '辽源', '通化',
                     '白山', '松原', '白城', '延边', '延吉', '延吉西', '珲春', '敦化', '图们'],

            '山西': ['太原', '太原南', '大同', '大同南', '阳泉', '阳泉北', '长治', '长治北', '晋城',
                     '朔州', '晋中', '运城', '运城北', '忻州', '临汾', '临汾西', '吕梁', '孝义'],

            '江西': ['南昌', '南昌西', '南昌站', '九江', '九江站', '赣州', '赣州西', '上饶', '上饶站',
                     '宜春', '宜春站', '吉安', '吉安西', '抚州', '抚州站', '景德镇', '萍乡', '新余',
                     '鹰潭', '鹰潭北', '丰城', '樟树', '高安', '瑞金', '龙南', '定南'],

            '安徽': ['合肥', '合肥南', '合肥站', '芜湖', '芜湖站', '蚌埠', '蚌埠南', '淮南', '淮南东',
                     '马鞍山', '马鞍山东', '淮北', '淮北北', '铜陵', '铜陵北', '安庆', '安庆站',
                     '黄山', '黄山北', '滁州', '滁州北', '阜阳', '阜阳西', '宿州', '宿州东', '六安',
                     '亳州', '池州', '宣城', '宁国', '桐城', '天长', '明光', '界首'],

            '广西': ['南宁', '南宁东', '南宁站', '柳州', '柳州站', '桂林', '桂林北', '梧州', '梧州南',
                     '北海', '北海站', '防城港', '防城港北', '钦州', '钦州东', '贵港', '贵港站',
                     '玉林', '玉林站', '百色', '百色站', '贺州', '贺州站', '河池', '来宾', '崇左'],

            '云南': ['昆明', '昆明南', '昆明站', '曲靖', '曲靖北', '玉溪', '玉溪站', '保山', '昭通',
                     '丽江', '丽江站', '普洱', '临沧', '楚雄', '红河', '蒙自', '个旧', '开远',
                     '文山', '西双版纳', '景洪', '大理', '大理站', '德宏', '芒市', '怒江', '迪庆'],

            '贵州': ['贵阳', '贵阳北', '贵阳东', '遵义', '遵义站', '安顺', '安顺西', '六盘水',
                     '毕节', '毕节站', '铜仁', '铜仁站', '黔东南', '凯里', '黔南', '都匀',
                     '黔西南', '兴义', '仁怀', '赤水', '福泉', '清镇'],

            '甘肃': ['兰州', '兰州西', '兰州站', '嘉峪关', '嘉峪关南', '金昌', '白银', '天水',
                     '天水南', '武威', '张掖', '张掖西', '平凉', '酒泉', '庆阳', '定西',
                     '陇南', '临夏', '甘南', '合作'],

            '青海': ['西宁', '西宁站', '海东', '海北', '黄南', '海南', '果洛', '玉树', '海西', '格尔木'],

            '宁夏': ['银川', '银川站', '石嘴山', '吴忠', '固原', '中卫', '中卫南', '青铜峡', '灵武'],

            '新疆': ['乌鲁木齐', '乌鲁木齐南', '乌鲁木齐站', '克拉玛依', '吐鲁番', '哈密', '昌吉',
                     '博尔塔拉', '巴音郭楞', '库尔勒', '阿克苏', '克孜勒苏', '喀什', '和田',
                     '伊犁', '伊宁', '塔城', '阿勒泰', '石河子', '阿拉尔', '图木舒克', '五家渠'],

            '内蒙古': ['呼和浩特', '呼和浩特东', '包头', '包头东', '乌海', '赤峰', '通辽', '鄂尔多斯',
                       '呼伦贝尔', '海拉尔', '巴彦淖尔', '乌兰察布', '兴安盟', '乌兰浩特',
                       '锡林郭勒', '锡林浩特', '阿拉善', '巴彦浩特'],

            '海南': ['海口', '海口东', '三亚', '三亚站', '三沙', '儋州', '文昌', '琼海', '万宁',
                     '东方', '五指山', '乐东', '澄迈', '临高', '定安', '屯昌', '陵水', '昌江',
                     '保亭', '琼中', '白沙'],

            '西藏': ['拉萨', '拉萨站', '日喀则', '昌都', '林芝', '山南', '那曲', '阿里', '噶尔'],
            '香港': ['香港西九龙', '香港红磡'],
            '澳门': ['澳门'],
            '台湾': ['台北', '台中', '高雄', '基隆', '新竹', '嘉义', '台南', '花莲', '台东']
        }

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

    def get_province_by_station(self, station_name):
        """根据车站名查找所属省份"""
        for province, stations in self.province_stations.items():
            if station_name in stations:
                return province
        return '其他'

    def get_stations_by_province(self, province):
        """获取某省份的所有车站"""
        return self.province_stations.get(province, [])

    def setup_ui(self):
        """创建UI"""
        top_frame = Frame(self.root, bg='#16213e', height=80)
        top_frame.pack(fill=X, padx=10, pady=10)

        Label(top_frame, text="🚆 12306 全国查票系统 · V3.0版",
              bg='#16213e', fg='#00ff00', font=('Arial', 20, 'bold')).pack(pady=10)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=5)

        style = ttk.Style()
        style.configure('TNotebook.Tab', font=('Arial', 11, 'bold'), padding=[10, 5])

        # 创建9个功能页面
        self.create_page1()  # 🔍 自主查询
        self.create_page2()  # 🌍 全国查询
        self.create_page3()  # 🚅 车次查询
        self.create_page4()  # 🏢 车站大屏
        self.create_page5()  # 📊 票价趋势
        self.create_page6()  # 🚉 车站车次
        self.create_page7()  # 📈 正晚点统计
        self.create_page8()  # 🔔 余票提醒
        self.create_page9()  # 🔄 智能换乘（带地域优先算法）

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

    # ==================== 页面4：车站大屏 ====================

    def create_page4(self):
        """页面4：车站大屏"""
        page = Frame(self.notebook, bg='#0a0f1e')
        self.notebook.add(page, text='🏢 车站大屏')

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

        self.screen_btn = Button(control_frame, text="🔍 查询大屏", command=self.query_station_screen,
                                 bg='#0f3460', fg='white', padx=15)
        self.screen_btn.pack(side=LEFT, padx=10)

        self.screen_auto_btn = Button(control_frame, text="🔄 自动刷新", command=self.toggle_screen_auto,
                                      bg='#008000', fg='white', padx=10)
        self.screen_auto_btn.pack(side=LEFT, padx=5)

        status_frame = Frame(control_frame, bg='#16213e')
        status_frame.pack(side=RIGHT, padx=10)

        Label(status_frame, text="🟢 已发车  🟡 计划中  ⚪ 已到达  🔴 停运",
              bg='#16213e', fg='white').pack()

        columns = ('车次', '始发站', '终点站', '本站到达', '本站发车', '状态')
        self.screen_tree = ttk.Treeview(page, columns=columns, show='headings', height=12)

        col_widths = [80, 100, 100, 90, 90, 100]
        for col, width in zip(columns, col_widths):
            self.screen_tree.heading(col, text=col)
            self.screen_tree.column(col, width=width, anchor='center')

        self.screen_tree.tag_configure('departed', foreground='#00ff00')
        self.screen_tree.tag_configure('waiting', foreground='#ffff00')
        self.screen_tree.tag_configure('arrived', foreground='#888888')
        self.screen_tree.tag_configure('cancelled', foreground='#ff4444')

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

    # ==================== 页面9：智能换乘（带地域优先算法）====================

    def create_page9(self):
        """页面9：智能换乘（带地域优先算法）"""
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

        self.transfer_btn = Button(row1, text="🔄 查询换乘", command=self.query_transfer,
                                   bg='#0f3460', fg='white', font=('Arial', 11, 'bold'),
                                   padx=15, pady=3)
        self.transfer_btn.pack(side=LEFT, padx=10)

        # 第二行：时间段筛选（12小时制）
        row2 = Frame(query_frame, bg='#16213e')
        row2.pack(pady=5, fill=X)

        Label(row2, text="出发时间:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)

        # 上午/下午选择
        self.time_ampm_var = StringVar(value="上午")
        ampm_combo = ttk.Combobox(row2, textvariable=self.time_ampm_var,
                                  values=['上午', '下午'], width=5, state='readonly')
        ampm_combo.pack(side=LEFT, padx=2)

        # 小时选择
        self.time_hour_var = StringVar(value="")
        hour_combo = ttk.Combobox(row2, textvariable=self.time_hour_var,
                                  values=['', '12', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11'],
                                  width=3)
        hour_combo.pack(side=LEFT, padx=2)

        Label(row2, text="点", bg='#16213e', fg='white').pack(side=LEFT, padx=2)

        # 分钟选择
        self.time_min_var = StringVar(value="")
        min_combo = ttk.Combobox(row2, textvariable=self.time_min_var,
                                 values=['', '00', '05', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55'],
                                 width=3)
        min_combo.pack(side=LEFT, padx=2)

        Label(row2, text="分", bg='#16213e', fg='white').pack(side=LEFT, padx=2)

        Label(row2, text="(不填则不限制)", bg='#16213e', fg='#888888').pack(side=LEFT, padx=10)

        # 第三行：筛选选项
        row3 = Frame(query_frame, bg='#16213e')
        row3.pack(pady=5, fill=X)

        Label(row3, text="最多换乘:", bg='#16213e', fg='white').pack(side=LEFT, padx=5)
        self.max_transfer_var = StringVar(value="2")
        ttk.Combobox(row3, textvariable=self.max_transfer_var,
                     values=['1', '2', '3'], width=5, state='readonly').pack(side=LEFT, padx=5)

        Label(row3, text="最少等候:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)
        self.min_wait_var = StringVar(value="20")
        ttk.Entry(row3, textvariable=self.min_wait_var, width=5).pack(side=LEFT, padx=5)
        Label(row3, text="分钟", bg='#16213e', fg='white').pack(side=LEFT, padx=2)

        Label(row3, text="最多等候:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)
        self.max_wait_var = StringVar(value="180")
        ttk.Entry(row3, textvariable=self.max_wait_var, width=5).pack(side=LEFT, padx=5)
        Label(row3, text="分钟", bg='#16213e', fg='white').pack(side=LEFT, padx=2)

        Label(row3, text="排序方式:", bg='#16213e', fg='white').pack(side=LEFT, padx=15)
        self.transfer_sort_var = StringVar(value="推荐")
        ttk.Combobox(row3, textvariable=self.transfer_sort_var,
                     values=['推荐', '总时长', '总票价', '等候时间'], width=8, state='readonly').pack(side=LEFT, padx=5)

        # 第四行：地域优先选项
        row4 = Frame(query_frame, bg='#16213e')
        row4.pack(pady=5, fill=X)

        self.priority_province_var = BooleanVar(value=True)
        Checkbutton(row4, text="优先同省份换乘", variable=self.priority_province_var,
                    bg='#16213e', fg='white', selectcolor='#16213e').pack(side=LEFT, padx=5)

        Label(row4, text="当前出发站省份:", bg='#16213e', fg='#00ff00').pack(side=LEFT, padx=20)
        self.from_province_label = Label(row4, text="广东", bg='#16213e', fg='#ffff00')
        self.from_province_label.pack(side=LEFT, padx=2)

        Label(row4, text="到达站省份:", bg='#16213e', fg='#00ff00').pack(side=LEFT, padx=10)
        self.to_province_label = Label(row4, text="广东", bg='#16213e', fg='#ffff00')
        self.to_province_label.pack(side=LEFT, padx=2)

        # 绑定车站变化事件
        self.transfer_from_combo.bind('<<ComboboxSelected>>', self.update_province_labels)
        self.transfer_to_combo.bind('<<ComboboxSelected>>', self.update_province_labels)

        # 结果标题
        title = Label(page, text="=" * 30 + "  🔄 智能换乘方案（全国范围） 🔄  " + "=" * 30,
                      bg='#0a0f1e', fg='#00ff00', font=('Courier', 12, 'bold'))
        title.pack(pady=5)

        # 创建表格
        columns = ('方案', '第一程', '第二程', '第三程', '总时长', '总票价', '等候时间', '操作')
        self.transfer_tree = ttk.Treeview(page, columns=columns, show='headings', height=12)

        col_widths = [60, 140, 140, 140, 80, 80, 80, 80]
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

        Label(info_frame, text="💡 双击方案查看详情 | 右键查看更多操作 | 优先搜索同省份车站，再扩大到全国",
              bg='#16213e', fg='#00ff00').pack(side=LEFT, padx=10)

        self.transfer_status = Label(info_frame, text="就绪", bg='#16213e', fg='#00ff00')
        self.transfer_status.pack(side=RIGHT, padx=10)

    def toggle_time_format(self):
        """切换12/24小时制"""
        self.time_format_12h = self.time_12h_var.get()

    def update_province_labels(self, event=None):
        """更新省份显示"""
        from_station = self.transfer_from_var.get()
        to_station = self.transfer_to_var.get()

        if from_station:
            from_province = self.get_province_by_station(from_station)
            self.from_province_label.config(text=from_province)

        if to_station:
            to_province = self.get_province_by_station(to_station)
            self.to_province_label.config(text=to_province)

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

    def apply_time_filter(self, trains):
        """应用时间筛选"""
        hour = self.time_hour_var.get()
        ampm = self.time_ampm_var.get()

        if not hour:
            return trains

        try:
            # 转换为24小时制
            target_hour = int(hour)
            if ampm == '下午' and target_hour != 12:
                target_hour += 12
            elif ampm == '上午' and target_hour == 12:
                target_hour = 0

            target_min = int(self.time_min_var.get()) if self.time_min_var.get() else 0
            target_time = target_hour * 60 + target_min

            filtered = []
            for train in trains:
                depart_time = train.get('depart', '00:00')
                if depart_time == '--':
                    continue
                try:
                    t_hour = int(depart_time.split(':')[0])
                    t_min = int(depart_time.split(':')[1])
                    t_total = t_hour * 60 + t_min

                    # 允许前后30分钟偏差
                    if abs(t_total - target_time) <= 30:
                        filtered.append(train)
                except:
                    continue
            return filtered
        except:
            return trains

    def query_direct_trains(self, from_station, to_station, date):
        """查询直达车次"""
        cache_key = f"{from_station}_{to_station}_{date}"
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]

        if from_station not in self.all_stations or to_station not in self.all_stations:
            return []

        from_code = self.all_stations[from_station]
        to_code = self.all_stations[to_station]

        url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={from_code}&leftTicketDTO.to_station={to_code}&purpose_codes=ADULT"

        try:
            res = self.session.get(url, headers=self.headers, timeout=5)
            data = res.json()

            trains = []
            if data.get('data'):
                for item in data['data']:
                    train = item['queryLeftNewDTO']
                    train_code = train.get('station_train_code', '')
                    price = self._price_format(train.get('ze_price', ''))

                    trains.append({
                        'train': train_code,
                        'from': from_station,
                        'to': to_station,
                        'depart': train.get('start_time', ''),
                        'arrive': train.get('arrive_time', ''),
                        'duration': train.get('lishi', ''),
                        'price': price,
                        'full_no': train.get('train_no', '')
                    })

            self.query_cache[cache_key] = trains
            return trains
        except:
            return []

    def find_transfers_bfs(self, from_station, to_station, date, max_depth=2):
        """
        广度优先搜索找换乘方案
        优先搜索同省份车站，再扩大到全国
        """
        from_province = self.get_province_by_station(from_station)
        to_province = self.get_province_by_station(to_station)

        results = []
        queue = deque()
        visited = set()

        # 初始状态：从出发站开始
        queue.append({
            'current': from_station,
            'path': [],
            'depth': 0
        })

        while queue and len(results) < 20:  # 最多找20个方案
            state = queue.popleft()

            if state['depth'] >= max_depth:
                continue

            # 确定下一站搜索范围
            next_stations = []

            # 优先搜索同省份的车站
            if self.priority_province_var.get() and from_province == to_province:
                # 同省份内，优先搜省内车站
                province_stations = self.get_stations_by_province(from_province)
                for s in province_stations:
                    if s != state['current'] and s not in visited:
                        next_stations.append(s)

            # 再搜索热门城市
            for city in self.major_cities[:30]:
                if city != state['current'] and city not in visited and city not in next_stations:
                    next_stations.append(city)

            # 限制每次搜索的车站数量，避免太慢
            for next_station in next_stations[:15]:
                if next_station in visited:
                    continue

                # 查询当前站到下一站的直达车
                trains = self.query_direct_trains(state['current'], next_station, date)
                if not trains:
                    continue

                # 应用时间筛选
                trains = self.apply_time_filter(trains)
                if not trains:
                    continue

                for train in trains[:2]:  # 每段只取前2个车次
                    new_path = state['path'] + [train]

                    # 如果到达目标站，记录方案
                    if next_station == to_station:
                        # 计算总时长和票价
                        total_minutes = 0
                        total_price = 0
                        wait_times = []

                        for i, seg in enumerate(new_path):
                            # 计算运行时间（分钟）
                            try:
                                h, m = map(int, seg['duration'].split(':'))
                                total_minutes += h * 60 + m
                            except:
                                pass

                            # 累加票价
                            try:
                                total_price += int(seg['price']) if seg['price'] != '无' else 0
                            except:
                                pass

                            # 计算换乘等候时间
                            if i < len(new_path) - 1:
                                wait = self.calc_wait_time(seg['arrive'], new_path[i + 1]['depart'])
                                wait_times.append(wait)

                        hours = total_minutes // 60
                        mins = total_minutes % 60
                        total_duration = f"{hours:02d}:{mins:02d}"

                        results.append({
                            'type': f"{len(new_path)}次换乘",
                            'segments': new_path,
                            'total_duration': total_duration,
                            'total_price': str(total_price),
                            'wait_times': wait_times,
                            'max_wait': max(wait_times) if wait_times else 0,
                            'min_wait': min(wait_times) if wait_times else 0
                        })
                    else:
                        # 继续搜索
                        visited.add(next_station)
                        queue.append({
                            'current': next_station,
                            'path': new_path,
                            'depth': state['depth'] + 1
                        })

        return results

    def calc_wait_time(self, arrive_time, depart_time):
        """计算换乘等候时间（分钟）"""
        try:
            date = self.transfer_date_entry.get()
            arrive = datetime.strptime(f"{date} {arrive_time}", '%Y-%m-%d %H:%M')
            depart = datetime.strptime(f"{date} {depart_time}", '%Y-%m-%d %H:%M')
            wait_minutes = int((depart - arrive).seconds / 60)
            return wait_minutes
        except:
            return 999

    def query_transfer(self):
        """查询换乘方案"""
        from_station = self.transfer_from_var.get()
        to_station = self.transfer_to_var.get()
        date = self.transfer_date_entry.get()

        if not from_station or not to_station:
            messagebox.showwarning("警告", "请填写出发站和到达站")
            return

        self.transfer_btn.config(state=DISABLED, text="查询中...")
        self.transfer_status.config(text="正在计算换乘方案（全国范围搜索）...")

        thread = threading.Thread(target=self._fetch_transfer_bfs,
                                  args=(from_station, to_station, date))
        thread.daemon = True
        thread.start()

    def _fetch_transfer_bfs(self, from_station, to_station, date):
        """BFS搜索换乘方案"""
        try:
            self.root.after(0, lambda: self.transfer_tree.delete(*self.transfer_tree.get_children()))

            max_transfer = int(self.max_transfer_var.get())
            min_wait = int(self.min_wait_var.get())
            max_wait = int(self.max_wait_var.get())

            # 1. 先查直达
            direct_trains = self.query_direct_trains(from_station, to_station, date)
            direct_trains = self.apply_time_filter(direct_trains)

            all_transfers = []

            for train in direct_trains[:5]:
                all_transfers.append({
                    'type': '直达',
                    'segments': [train],
                    'total_duration': train['duration'],
                    'total_price': train['price'],
                    'wait_times': []
                })

            # 2. 如果直达不够，用BFS找换乘
            if len(direct_trains) < 3:
                bfs_results = self.find_transfers_bfs(from_station, to_station, date, max_transfer)
                all_transfers.extend(bfs_results)

            # 3. 过滤等候时间
            filtered = []
            for t in all_transfers:
                if t['type'] == '直达':
                    filtered.append(t)
                else:
                    if t['wait_times']:
                        max_wait_time = max(t['wait_times'])
                        min_wait_time = min(t['wait_times'])
                        if min_wait_time >= min_wait and max_wait_time <= max_wait:
                            filtered.append(t)

            # 4. 排序
            sort_by = self.transfer_sort_var.get()
            if sort_by == '总时长':
                filtered.sort(key=lambda x: x['total_duration'])
            elif sort_by == '总票价':
                filtered.sort(key=lambda x: int(x['total_price']) if x['total_price'] != '无' else 9999)
            elif sort_by == '等候时间':
                filtered.sort(key=lambda x: max(x['wait_times']) if x['wait_times'] else 0)
            else:
                # 推荐排序：优先直达，其次总时长
                filtered.sort(key=lambda x: (0 if x['type'] == '直达' else 1, x['total_duration']))

            self.transfer_results = filtered
            self.root.after(0, lambda: self._display_transfers(filtered))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"查询失败: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.transfer_btn.config(state=NORMAL, text="🔄 查询换乘"))
            self.root.after(0, lambda: self.transfer_status.config(text="就绪"))

    def _display_transfers(self, transfers):
        """显示换乘方案"""
        for i, transfer in enumerate(transfers[:15]):  # 只显示前15个
            if transfer['type'] == '直达':
                seg_text = transfer['segments'][0]['train']
                second_text = '--'
                third_text = '--'
                wait_time = '--'
            else:
                segs = transfer['segments']
                seg_text = f"{segs[0]['train']}→{segs[0]['to']}"
                second_text = segs[1]['train'] if len(segs) > 1 else '--'
                third_text = segs[2]['train'] if len(segs) > 2 else '--'
                wait_time = f"{min(transfer['wait_times'])}-{max(transfer['wait_times'])}分"

            # 时间格式转换
            if self.time_format_12h:
                if transfer['type'] == '直达':
                    seg_text = f"{self.format_time_12h(transfer['segments'][0]['depart'])} {seg_text}"
                else:
                    seg_text = f"{self.format_time_12h(transfer['segments'][0]['depart'])} {seg_text}"

            values = (
                f"方案{i + 1}",
                seg_text,
                second_text,
                third_text,
                transfer['total_duration'],
                transfer['total_price'],
                wait_time,
                '查看详情'
            )
            self.transfer_tree.insert('', 'end', values=values)

        self.transfer_status.config(text=f"找到 {len(transfers)} 个换乘方案（全国范围）")

    def show_transfer_detail(self, event):
        """显示换乘详情"""
        selection = self.transfer_tree.selection()
        if not selection:
            return

        item = self.transfer_tree.item(selection[0])
        index = int(item['values'][0].replace('方案', '')) - 1

        if 0 <= index < len(self.transfer_results):
            transfer = self.transfer_results[index]

            detail = f"🚆 换乘方案详情\n"
            detail += "=" * 50 + "\n"

            for i, seg in enumerate(transfer['segments'], 1):
                depart_time = seg['depart']
                arrive_time = seg['arrive']

                if self.time_format_12h:
                    depart_time = self.format_time_12h(depart_time)
                    arrive_time = self.format_time_12h(arrive_time)

                detail += f"\n第{i}程: {seg['train']}\n"
                detail += f"  {seg['from']} {depart_time} → {seg['to']} {arrive_time}\n"
                detail += f"  历时: {seg['duration']} | 票价: {seg['price']}元\n"

                if i < len(transfer['segments']):
                    wait = transfer['wait_times'][i - 1] if i - 1 < len(transfer['wait_times']) else '?'
                    detail += f"  换乘等候: {wait}分钟\n"

            detail += f"\n总时长: {transfer['total_duration']}"
            detail += f"\n总票价: {transfer['total_price']}元"

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

                                status, tag = self._get_train_status(train_code, date, station,
                                                                     train.get('start_time', ''),
                                                                     is_departure=True)

                                all_trains.append({
                                    'train_no': train_code,
                                    'start_station': station,
                                    'end_station': train.get('to_station_name', ''),
                                    'arrive_time': '--',
                                    'depart_time': train.get('start_time', ''),
                                    'status': status,
                                    'tag': tag
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

                                status, tag = self._get_train_status(train_code, date, station,
                                                                     train.get('arrive_time', ''),
                                                                     is_departure=False)

                                all_trains.append({
                                    'train_no': train_code,
                                    'start_station': train.get('from_station_name', ''),
                                    'end_station': station,
                                    'arrive_time': train.get('arrive_time', ''),
                                    'depart_time': '--',
                                    'status': status,
                                    'tag': tag
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
                    train['depart_time'],
                    train['status']
                )
                self.root.after(0, lambda v=values, tag=train['tag']:
                self.screen_tree.insert('', 'end', values=v, tags=(tag,)))
                time.sleep(0.02)

            self.root.after(0, lambda: self.screen_update_label.config(
                text=f"最后更新: {datetime.now().strftime('%H:%M:%S')} | 共 {len(all_trains)} 趟列车"))
            self.root.after(0, lambda: self.status_bar.config(
                text=f"{station} 大屏加载完成，共 {len(all_trains)} 趟列车"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"查询失败: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.screen_btn.config(state=NORMAL, text="🔍 查询大屏"))

    def _get_train_status(self, train_no, date, station, time_str, is_departure=True):
        try:
            now = datetime.now()
            plan_time = datetime.strptime(f"{date} {time_str}", '%Y-%m-%d %H:%M')

            url = f"https://kyfw.12306.cn/otn/leftTicketPrice/queryAllPublicPrice?leftTicketDTO.train_date={date}&leftTicketDTO.from_station={self.all_stations.get(station, 'BJP')}&leftTicketDTO.to_station={self.all_stations.get('上海', 'SHH')}&purpose_codes=ADULT"

            try:
                res = self.session.get(url, headers=self.headers, timeout=3)
                data = res.json()

                has_ticket = False
                if data.get('data'):
                    for item in data['data']:
                        if item['queryLeftNewDTO'].get('station_train_code') == train_no:
                            has_ticket = True
                            break

                if not has_ticket:
                    return "停运", 'cancelled'
            except:
                pass

            if now > plan_time + timedelta(minutes=10):
                return ("已发车" if is_departure else "已到达"), 'departed' if is_departure else 'arrived'
            elif now > plan_time - timedelta(minutes=30):
                return "即将发车" if is_departure else "即将到达", 'waiting'
            else:
                return "计划中", 'waiting'

        except:
            return "--", 'waiting'

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