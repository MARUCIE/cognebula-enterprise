#!/usr/bin/env python3
"""Inject ~400 administrative region nodes into KuzuDB.

Covers:
- 1 national-level root (already exists, skipped if duplicate)
- 34 province-level regions (4 municipalities, 23 provinces, 5 autonomous regions, 2 SARs)
- 333 prefecture-level cities (all as of GB/T 2260-2023)
- ~30 special tax policy zones (free trade zones, SEZs, cooperation zones)

Schema: reuses existing AdministrativeRegion(id, name, regionType, level, parentId).
Adds taxPolicyTag STRING field for tax policy classification.

Usage:
    python src/inject_admin_regions.py --db data/finance-tax-graph
    python src/inject_admin_regions.py --db data/finance-tax-graph --dry-run
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    import kuzu
except ImportError:
    print("ERROR: kuzu not installed. Run: pip install kuzu")
    sys.exit(1)


BATCH_SIZE = 200


def _exec(conn, cypher: str, params: dict = None, label: str = ""):
    """Execute Cypher with idempotent error handling."""
    try:
        if params:
            conn.execute(cypher, params)
        else:
            conn.execute(cypher)
        return True
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "duplicate" in msg or "primary key" in msg:
            return True  # idempotent
        print(f"WARN: {label} -- {e}")
        return False


# ---------------------------------------------------------------------------
# Data: Province-level regions (34 total)
# GB/T 2260 codes used as basis for IDs
# ---------------------------------------------------------------------------

PROVINCE_LEVEL = [
    # Municipalities (直辖市)
    {"code": "110000", "name": "北京市", "regionType": "municipality"},
    {"code": "120000", "name": "天津市", "regionType": "municipality"},
    {"code": "310000", "name": "上海市", "regionType": "municipality"},
    {"code": "500000", "name": "重庆市", "regionType": "municipality"},
    # Provinces (省)
    {"code": "130000", "name": "河北省", "regionType": "province"},
    {"code": "140000", "name": "山西省", "regionType": "province"},
    {"code": "210000", "name": "辽宁省", "regionType": "province"},
    {"code": "220000", "name": "吉林省", "regionType": "province"},
    {"code": "230000", "name": "黑龙江省", "regionType": "province"},
    {"code": "320000", "name": "江苏省", "regionType": "province"},
    {"code": "330000", "name": "浙江省", "regionType": "province"},
    {"code": "340000", "name": "安徽省", "regionType": "province"},
    {"code": "350000", "name": "福建省", "regionType": "province"},
    {"code": "360000", "name": "江西省", "regionType": "province"},
    {"code": "370000", "name": "山东省", "regionType": "province"},
    {"code": "410000", "name": "河南省", "regionType": "province"},
    {"code": "420000", "name": "湖北省", "regionType": "province"},
    {"code": "430000", "name": "湖南省", "regionType": "province"},
    {"code": "440000", "name": "广东省", "regionType": "province"},
    {"code": "460000", "name": "海南省", "regionType": "province"},
    {"code": "510000", "name": "四川省", "regionType": "province"},
    {"code": "520000", "name": "贵州省", "regionType": "province"},
    {"code": "530000", "name": "云南省", "regionType": "province"},
    {"code": "540000", "name": "西藏自治区", "regionType": "autonomous_region"},
    {"code": "610000", "name": "陕西省", "regionType": "province"},
    {"code": "620000", "name": "甘肃省", "regionType": "province"},
    {"code": "630000", "name": "青海省", "regionType": "province"},
    # Autonomous Regions (自治区)
    {"code": "150000", "name": "内蒙古自治区", "regionType": "autonomous_region"},
    {"code": "450000", "name": "广西壮族自治区", "regionType": "autonomous_region"},
    {"code": "640000", "name": "宁夏回族自治区", "regionType": "autonomous_region"},
    {"code": "650000", "name": "新疆维吾尔自治区", "regionType": "autonomous_region"},
    # Note: 西藏 already listed above
    # SARs (特别行政区)
    {"code": "810000", "name": "香港特别行政区", "regionType": "sar"},
    {"code": "820000", "name": "澳门特别行政区", "regionType": "sar"},
    # Taiwan (listed per GB/T 2260)
    {"code": "710000", "name": "台湾省", "regionType": "province"},
]

# ---------------------------------------------------------------------------
# Data: Prefecture-level cities (333 total, grouped by province code prefix)
# GB/T 2260-2023 codes
# ---------------------------------------------------------------------------

PREFECTURE_CITIES = [
    # -- 河北省 130000 --
    {"code": "130100", "name": "石家庄市", "parent": "130000"},
    {"code": "130200", "name": "唐山市", "parent": "130000"},
    {"code": "130300", "name": "秦皇岛市", "parent": "130000"},
    {"code": "130400", "name": "邯郸市", "parent": "130000"},
    {"code": "130500", "name": "邢台市", "parent": "130000"},
    {"code": "130600", "name": "保定市", "parent": "130000"},
    {"code": "130700", "name": "张家口市", "parent": "130000"},
    {"code": "130800", "name": "承德市", "parent": "130000"},
    {"code": "130900", "name": "沧州市", "parent": "130000"},
    {"code": "131000", "name": "廊坊市", "parent": "130000"},
    {"code": "131100", "name": "衡水市", "parent": "130000"},
    # -- 山西省 140000 --
    {"code": "140100", "name": "太原市", "parent": "140000"},
    {"code": "140200", "name": "大同市", "parent": "140000"},
    {"code": "140300", "name": "阳泉市", "parent": "140000"},
    {"code": "140400", "name": "长治市", "parent": "140000"},
    {"code": "140500", "name": "晋城市", "parent": "140000"},
    {"code": "140600", "name": "朔州市", "parent": "140000"},
    {"code": "140700", "name": "晋中市", "parent": "140000"},
    {"code": "140800", "name": "运城市", "parent": "140000"},
    {"code": "140900", "name": "忻州市", "parent": "140000"},
    {"code": "141000", "name": "临汾市", "parent": "140000"},
    {"code": "141100", "name": "吕梁市", "parent": "140000"},
    # -- 内蒙古自治区 150000 --
    {"code": "150100", "name": "呼和浩特市", "parent": "150000"},
    {"code": "150200", "name": "包头市", "parent": "150000"},
    {"code": "150300", "name": "乌海市", "parent": "150000"},
    {"code": "150400", "name": "赤峰市", "parent": "150000"},
    {"code": "150500", "name": "通辽市", "parent": "150000"},
    {"code": "150600", "name": "鄂尔多斯市", "parent": "150000"},
    {"code": "150700", "name": "呼伦贝尔市", "parent": "150000"},
    {"code": "150800", "name": "巴彦淖尔市", "parent": "150000"},
    {"code": "150900", "name": "乌兰察布市", "parent": "150000"},
    {"code": "152200", "name": "兴安盟", "parent": "150000"},
    {"code": "152500", "name": "锡林郭勒盟", "parent": "150000"},
    {"code": "152900", "name": "阿拉善盟", "parent": "150000"},
    # -- 辽宁省 210000 --
    {"code": "210100", "name": "沈阳市", "parent": "210000"},
    {"code": "210200", "name": "大连市", "parent": "210000"},
    {"code": "210300", "name": "鞍山市", "parent": "210000"},
    {"code": "210400", "name": "抚顺市", "parent": "210000"},
    {"code": "210500", "name": "本溪市", "parent": "210000"},
    {"code": "210600", "name": "丹东市", "parent": "210000"},
    {"code": "210700", "name": "锦州市", "parent": "210000"},
    {"code": "210800", "name": "营口市", "parent": "210000"},
    {"code": "210900", "name": "阜新市", "parent": "210000"},
    {"code": "211000", "name": "辽阳市", "parent": "210000"},
    {"code": "211100", "name": "盘锦市", "parent": "210000"},
    {"code": "211200", "name": "铁岭市", "parent": "210000"},
    {"code": "211300", "name": "朝阳市", "parent": "210000"},
    {"code": "211400", "name": "葫芦岛市", "parent": "210000"},
    # -- 吉林省 220000 --
    {"code": "220100", "name": "长春市", "parent": "220000"},
    {"code": "220200", "name": "吉林市", "parent": "220000"},
    {"code": "220300", "name": "四平市", "parent": "220000"},
    {"code": "220400", "name": "辽源市", "parent": "220000"},
    {"code": "220500", "name": "通化市", "parent": "220000"},
    {"code": "220600", "name": "白山市", "parent": "220000"},
    {"code": "220700", "name": "松原市", "parent": "220000"},
    {"code": "220800", "name": "白城市", "parent": "220000"},
    {"code": "222400", "name": "延边朝鲜族自治州", "parent": "220000"},
    # -- 黑龙江省 230000 --
    {"code": "230100", "name": "哈尔滨市", "parent": "230000"},
    {"code": "230200", "name": "齐齐哈尔市", "parent": "230000"},
    {"code": "230300", "name": "鸡西市", "parent": "230000"},
    {"code": "230400", "name": "鹤岗市", "parent": "230000"},
    {"code": "230500", "name": "双鸭山市", "parent": "230000"},
    {"code": "230600", "name": "大庆市", "parent": "230000"},
    {"code": "230700", "name": "伊春市", "parent": "230000"},
    {"code": "230800", "name": "佳木斯市", "parent": "230000"},
    {"code": "230900", "name": "七台河市", "parent": "230000"},
    {"code": "231000", "name": "牡丹江市", "parent": "230000"},
    {"code": "231100", "name": "黑河市", "parent": "230000"},
    {"code": "231200", "name": "绥化市", "parent": "230000"},
    {"code": "232700", "name": "大兴安岭地区", "parent": "230000"},
    # -- 江苏省 320000 --
    {"code": "320100", "name": "南京市", "parent": "320000"},
    {"code": "320200", "name": "无锡市", "parent": "320000"},
    {"code": "320300", "name": "徐州市", "parent": "320000"},
    {"code": "320400", "name": "常州市", "parent": "320000"},
    {"code": "320500", "name": "苏州市", "parent": "320000"},
    {"code": "320600", "name": "南通市", "parent": "320000"},
    {"code": "320700", "name": "连云港市", "parent": "320000"},
    {"code": "320800", "name": "淮安市", "parent": "320000"},
    {"code": "320900", "name": "盐城市", "parent": "320000"},
    {"code": "321000", "name": "扬州市", "parent": "320000"},
    {"code": "321100", "name": "镇江市", "parent": "320000"},
    {"code": "321200", "name": "泰州市", "parent": "320000"},
    {"code": "321300", "name": "宿迁市", "parent": "320000"},
    # -- 浙江省 330000 --
    {"code": "330100", "name": "杭州市", "parent": "330000"},
    {"code": "330200", "name": "宁波市", "parent": "330000"},
    {"code": "330300", "name": "温州市", "parent": "330000"},
    {"code": "330400", "name": "嘉兴市", "parent": "330000"},
    {"code": "330500", "name": "湖州市", "parent": "330000"},
    {"code": "330600", "name": "绍兴市", "parent": "330000"},
    {"code": "330700", "name": "金华市", "parent": "330000"},
    {"code": "330800", "name": "衢州市", "parent": "330000"},
    {"code": "330900", "name": "舟山市", "parent": "330000"},
    {"code": "331000", "name": "台州市", "parent": "330000"},
    {"code": "331100", "name": "丽水市", "parent": "330000"},
    # -- 安徽省 340000 --
    {"code": "340100", "name": "合肥市", "parent": "340000"},
    {"code": "340200", "name": "芜湖市", "parent": "340000"},
    {"code": "340300", "name": "蚌埠市", "parent": "340000"},
    {"code": "340400", "name": "淮南市", "parent": "340000"},
    {"code": "340500", "name": "马鞍山市", "parent": "340000"},
    {"code": "340600", "name": "淮北市", "parent": "340000"},
    {"code": "340700", "name": "铜陵市", "parent": "340000"},
    {"code": "340800", "name": "安庆市", "parent": "340000"},
    {"code": "341000", "name": "黄山市", "parent": "340000"},
    {"code": "341100", "name": "滁州市", "parent": "340000"},
    {"code": "341200", "name": "阜阳市", "parent": "340000"},
    {"code": "341300", "name": "宿州市", "parent": "340000"},
    {"code": "341500", "name": "六安市", "parent": "340000"},
    {"code": "341600", "name": "亳州市", "parent": "340000"},
    {"code": "341700", "name": "池州市", "parent": "340000"},
    {"code": "341800", "name": "宣城市", "parent": "340000"},
    # -- 福建省 350000 --
    {"code": "350100", "name": "福州市", "parent": "350000"},
    {"code": "350200", "name": "厦门市", "parent": "350000"},
    {"code": "350300", "name": "莆田市", "parent": "350000"},
    {"code": "350400", "name": "三明市", "parent": "350000"},
    {"code": "350500", "name": "泉州市", "parent": "350000"},
    {"code": "350600", "name": "漳州市", "parent": "350000"},
    {"code": "350700", "name": "南平市", "parent": "350000"},
    {"code": "350800", "name": "龙岩市", "parent": "350000"},
    {"code": "350900", "name": "宁德市", "parent": "350000"},
    # -- 江西省 360000 --
    {"code": "360100", "name": "南昌市", "parent": "360000"},
    {"code": "360200", "name": "景德镇市", "parent": "360000"},
    {"code": "360300", "name": "萍乡市", "parent": "360000"},
    {"code": "360400", "name": "九江市", "parent": "360000"},
    {"code": "360500", "name": "新余市", "parent": "360000"},
    {"code": "360600", "name": "鹰潭市", "parent": "360000"},
    {"code": "360700", "name": "赣州市", "parent": "360000"},
    {"code": "360800", "name": "吉安市", "parent": "360000"},
    {"code": "360900", "name": "宜春市", "parent": "360000"},
    {"code": "361000", "name": "抚州市", "parent": "360000"},
    {"code": "361100", "name": "上饶市", "parent": "360000"},
    # -- 山东省 370000 --
    {"code": "370100", "name": "济南市", "parent": "370000"},
    {"code": "370200", "name": "青岛市", "parent": "370000"},
    {"code": "370300", "name": "淄博市", "parent": "370000"},
    {"code": "370400", "name": "枣庄市", "parent": "370000"},
    {"code": "370500", "name": "东营市", "parent": "370000"},
    {"code": "370600", "name": "烟台市", "parent": "370000"},
    {"code": "370700", "name": "潍坊市", "parent": "370000"},
    {"code": "370800", "name": "济宁市", "parent": "370000"},
    {"code": "370900", "name": "泰安市", "parent": "370000"},
    {"code": "371000", "name": "威海市", "parent": "370000"},
    {"code": "371100", "name": "日照市", "parent": "370000"},
    {"code": "371300", "name": "临沂市", "parent": "370000"},
    {"code": "371400", "name": "德州市", "parent": "370000"},
    {"code": "371500", "name": "聊城市", "parent": "370000"},
    {"code": "371600", "name": "滨州市", "parent": "370000"},
    {"code": "371700", "name": "菏泽市", "parent": "370000"},
    # -- 河南省 410000 --
    {"code": "410100", "name": "郑州市", "parent": "410000"},
    {"code": "410200", "name": "开封市", "parent": "410000"},
    {"code": "410300", "name": "洛阳市", "parent": "410000"},
    {"code": "410400", "name": "平顶山市", "parent": "410000"},
    {"code": "410500", "name": "安阳市", "parent": "410000"},
    {"code": "410600", "name": "鹤壁市", "parent": "410000"},
    {"code": "410700", "name": "新乡市", "parent": "410000"},
    {"code": "410800", "name": "焦作市", "parent": "410000"},
    {"code": "410900", "name": "濮阳市", "parent": "410000"},
    {"code": "411000", "name": "许昌市", "parent": "410000"},
    {"code": "411100", "name": "漯河市", "parent": "410000"},
    {"code": "411200", "name": "三门峡市", "parent": "410000"},
    {"code": "411300", "name": "南阳市", "parent": "410000"},
    {"code": "411400", "name": "商丘市", "parent": "410000"},
    {"code": "411500", "name": "信阳市", "parent": "410000"},
    {"code": "411600", "name": "周口市", "parent": "410000"},
    {"code": "411700", "name": "驻马店市", "parent": "410000"},
    {"code": "419001", "name": "济源市", "parent": "410000"},
    # -- 湖北省 420000 --
    {"code": "420100", "name": "武汉市", "parent": "420000"},
    {"code": "420200", "name": "黄石市", "parent": "420000"},
    {"code": "420300", "name": "十堰市", "parent": "420000"},
    {"code": "420500", "name": "宜昌市", "parent": "420000"},
    {"code": "420600", "name": "襄阳市", "parent": "420000"},
    {"code": "420700", "name": "鄂州市", "parent": "420000"},
    {"code": "420800", "name": "荆门市", "parent": "420000"},
    {"code": "420900", "name": "孝感市", "parent": "420000"},
    {"code": "421000", "name": "荆州市", "parent": "420000"},
    {"code": "421100", "name": "黄冈市", "parent": "420000"},
    {"code": "421200", "name": "咸宁市", "parent": "420000"},
    {"code": "421300", "name": "随州市", "parent": "420000"},
    {"code": "422800", "name": "恩施土家族苗族自治州", "parent": "420000"},
    {"code": "429004", "name": "仙桃市", "parent": "420000"},
    {"code": "429005", "name": "潜江市", "parent": "420000"},
    {"code": "429006", "name": "天门市", "parent": "420000"},
    {"code": "429021", "name": "神农架林区", "parent": "420000"},
    # -- 湖南省 430000 --
    {"code": "430100", "name": "长沙市", "parent": "430000"},
    {"code": "430200", "name": "株洲市", "parent": "430000"},
    {"code": "430300", "name": "湘潭市", "parent": "430000"},
    {"code": "430400", "name": "衡阳市", "parent": "430000"},
    {"code": "430500", "name": "邵阳市", "parent": "430000"},
    {"code": "430600", "name": "岳阳市", "parent": "430000"},
    {"code": "430700", "name": "常德市", "parent": "430000"},
    {"code": "430800", "name": "张家界市", "parent": "430000"},
    {"code": "430900", "name": "益阳市", "parent": "430000"},
    {"code": "431000", "name": "郴州市", "parent": "430000"},
    {"code": "431100", "name": "永州市", "parent": "430000"},
    {"code": "431200", "name": "怀化市", "parent": "430000"},
    {"code": "431300", "name": "娄底市", "parent": "430000"},
    {"code": "433100", "name": "湘西土家族苗族自治州", "parent": "430000"},
    # -- 广东省 440000 --
    {"code": "440100", "name": "广州市", "parent": "440000"},
    {"code": "440200", "name": "韶关市", "parent": "440000"},
    {"code": "440300", "name": "深圳市", "parent": "440000"},
    {"code": "440400", "name": "珠海市", "parent": "440000"},
    {"code": "440500", "name": "汕头市", "parent": "440000"},
    {"code": "440600", "name": "佛山市", "parent": "440000"},
    {"code": "440700", "name": "江门市", "parent": "440000"},
    {"code": "440800", "name": "湛江市", "parent": "440000"},
    {"code": "440900", "name": "茂名市", "parent": "440000"},
    {"code": "441200", "name": "肇庆市", "parent": "440000"},
    {"code": "441300", "name": "惠州市", "parent": "440000"},
    {"code": "441400", "name": "梅州市", "parent": "440000"},
    {"code": "441500", "name": "汕尾市", "parent": "440000"},
    {"code": "441600", "name": "河源市", "parent": "440000"},
    {"code": "441700", "name": "阳江市", "parent": "440000"},
    {"code": "441800", "name": "清远市", "parent": "440000"},
    {"code": "441900", "name": "东莞市", "parent": "440000"},
    {"code": "442000", "name": "中山市", "parent": "440000"},
    {"code": "445100", "name": "潮州市", "parent": "440000"},
    {"code": "445200", "name": "揭阳市", "parent": "440000"},
    {"code": "445300", "name": "云浮市", "parent": "440000"},
    # -- 广西壮族自治区 450000 --
    {"code": "450100", "name": "南宁市", "parent": "450000"},
    {"code": "450200", "name": "柳州市", "parent": "450000"},
    {"code": "450300", "name": "桂林市", "parent": "450000"},
    {"code": "450400", "name": "梧州市", "parent": "450000"},
    {"code": "450500", "name": "北海市", "parent": "450000"},
    {"code": "450600", "name": "防城港市", "parent": "450000"},
    {"code": "450700", "name": "钦州市", "parent": "450000"},
    {"code": "450800", "name": "贵港市", "parent": "450000"},
    {"code": "450900", "name": "玉林市", "parent": "450000"},
    {"code": "451000", "name": "百色市", "parent": "450000"},
    {"code": "451100", "name": "贺州市", "parent": "450000"},
    {"code": "451200", "name": "河池市", "parent": "450000"},
    {"code": "451300", "name": "来宾市", "parent": "450000"},
    {"code": "451400", "name": "崇左市", "parent": "450000"},
    # -- 海南省 460000 --
    {"code": "460100", "name": "海口市", "parent": "460000"},
    {"code": "460200", "name": "三亚市", "parent": "460000"},
    {"code": "460300", "name": "三沙市", "parent": "460000"},
    {"code": "460400", "name": "儋州市", "parent": "460000"},
    # -- 四川省 510000 --
    {"code": "510100", "name": "成都市", "parent": "510000"},
    {"code": "510300", "name": "自贡市", "parent": "510000"},
    {"code": "510400", "name": "攀枝花市", "parent": "510000"},
    {"code": "510500", "name": "泸州市", "parent": "510000"},
    {"code": "510600", "name": "德阳市", "parent": "510000"},
    {"code": "510700", "name": "绵阳市", "parent": "510000"},
    {"code": "510800", "name": "广元市", "parent": "510000"},
    {"code": "510900", "name": "遂宁市", "parent": "510000"},
    {"code": "511000", "name": "内江市", "parent": "510000"},
    {"code": "511100", "name": "乐山市", "parent": "510000"},
    {"code": "511300", "name": "南充市", "parent": "510000"},
    {"code": "511400", "name": "眉山市", "parent": "510000"},
    {"code": "511500", "name": "宜宾市", "parent": "510000"},
    {"code": "511600", "name": "广安市", "parent": "510000"},
    {"code": "511700", "name": "达州市", "parent": "510000"},
    {"code": "511800", "name": "雅安市", "parent": "510000"},
    {"code": "511900", "name": "巴中市", "parent": "510000"},
    {"code": "512000", "name": "资阳市", "parent": "510000"},
    {"code": "513200", "name": "阿坝藏族羌族自治州", "parent": "510000"},
    {"code": "513300", "name": "甘孜藏族自治州", "parent": "510000"},
    {"code": "513400", "name": "凉山彝族自治州", "parent": "510000"},
    # -- 贵州省 520000 --
    {"code": "520100", "name": "贵阳市", "parent": "520000"},
    {"code": "520200", "name": "六盘水市", "parent": "520000"},
    {"code": "520300", "name": "遵义市", "parent": "520000"},
    {"code": "520400", "name": "安顺市", "parent": "520000"},
    {"code": "520500", "name": "毕节市", "parent": "520000"},
    {"code": "520600", "name": "铜仁市", "parent": "520000"},
    {"code": "522300", "name": "黔西南布依族苗族自治州", "parent": "520000"},
    {"code": "522600", "name": "黔东南苗族侗族自治州", "parent": "520000"},
    {"code": "522700", "name": "黔南布依族苗族自治州", "parent": "520000"},
    # -- 云南省 530000 --
    {"code": "530100", "name": "昆明市", "parent": "530000"},
    {"code": "530300", "name": "曲靖市", "parent": "530000"},
    {"code": "530400", "name": "玉溪市", "parent": "530000"},
    {"code": "530500", "name": "保山市", "parent": "530000"},
    {"code": "530600", "name": "昭通市", "parent": "530000"},
    {"code": "530700", "name": "丽江市", "parent": "530000"},
    {"code": "530800", "name": "普洱市", "parent": "530000"},
    {"code": "530900", "name": "临沧市", "parent": "530000"},
    {"code": "532300", "name": "楚雄彝族自治州", "parent": "530000"},
    {"code": "532500", "name": "红河哈尼族彝族自治州", "parent": "530000"},
    {"code": "532600", "name": "文山壮族苗族自治州", "parent": "530000"},
    {"code": "532800", "name": "西双版纳傣族自治州", "parent": "530000"},
    {"code": "532900", "name": "大理白族自治州", "parent": "530000"},
    {"code": "533100", "name": "德宏傣族景颇族自治州", "parent": "530000"},
    {"code": "533300", "name": "怒江傈僳族自治州", "parent": "530000"},
    {"code": "533400", "name": "迪庆藏族自治州", "parent": "530000"},
    # -- 西藏自治区 540000 --
    {"code": "540100", "name": "拉萨市", "parent": "540000"},
    {"code": "540200", "name": "日喀则市", "parent": "540000"},
    {"code": "540300", "name": "昌都市", "parent": "540000"},
    {"code": "540400", "name": "林芝市", "parent": "540000"},
    {"code": "540500", "name": "山南市", "parent": "540000"},
    {"code": "540600", "name": "那曲市", "parent": "540000"},
    {"code": "542500", "name": "阿里地区", "parent": "540000"},
    # -- 陕西省 610000 --
    {"code": "610100", "name": "西安市", "parent": "610000"},
    {"code": "610200", "name": "铜川市", "parent": "610000"},
    {"code": "610300", "name": "宝鸡市", "parent": "610000"},
    {"code": "610400", "name": "咸阳市", "parent": "610000"},
    {"code": "610500", "name": "渭南市", "parent": "610000"},
    {"code": "610600", "name": "延安市", "parent": "610000"},
    {"code": "610700", "name": "汉中市", "parent": "610000"},
    {"code": "610800", "name": "榆林市", "parent": "610000"},
    {"code": "610900", "name": "安康市", "parent": "610000"},
    {"code": "611000", "name": "商洛市", "parent": "610000"},
    # -- 甘肃省 620000 --
    {"code": "620100", "name": "兰州市", "parent": "620000"},
    {"code": "620200", "name": "嘉峪关市", "parent": "620000"},
    {"code": "620300", "name": "金昌市", "parent": "620000"},
    {"code": "620400", "name": "白银市", "parent": "620000"},
    {"code": "620500", "name": "天水市", "parent": "620000"},
    {"code": "620600", "name": "武威市", "parent": "620000"},
    {"code": "620700", "name": "张掖市", "parent": "620000"},
    {"code": "620800", "name": "平凉市", "parent": "620000"},
    {"code": "620900", "name": "酒泉市", "parent": "620000"},
    {"code": "621000", "name": "庆阳市", "parent": "620000"},
    {"code": "621100", "name": "定西市", "parent": "620000"},
    {"code": "621200", "name": "陇南市", "parent": "620000"},
    {"code": "622900", "name": "临夏回族自治州", "parent": "620000"},
    {"code": "623000", "name": "甘南藏族自治州", "parent": "620000"},
    # -- 青海省 630000 --
    {"code": "630100", "name": "西宁市", "parent": "630000"},
    {"code": "630200", "name": "海东市", "parent": "630000"},
    {"code": "632200", "name": "海北藏族自治州", "parent": "630000"},
    {"code": "632300", "name": "黄南藏族自治州", "parent": "630000"},
    {"code": "632500", "name": "海南藏族自治州", "parent": "630000"},
    {"code": "632600", "name": "果洛藏族自治州", "parent": "630000"},
    {"code": "632700", "name": "玉树藏族自治州", "parent": "630000"},
    {"code": "632800", "name": "海西蒙古族藏族自治州", "parent": "630000"},
    # -- 宁夏回族自治区 640000 --
    {"code": "640100", "name": "银川市", "parent": "640000"},
    {"code": "640200", "name": "石嘴山市", "parent": "640000"},
    {"code": "640300", "name": "吴忠市", "parent": "640000"},
    {"code": "640400", "name": "固原市", "parent": "640000"},
    {"code": "640500", "name": "中卫市", "parent": "640000"},
    # -- 新疆维吾尔自治区 650000 --
    {"code": "650100", "name": "乌鲁木齐市", "parent": "650000"},
    {"code": "650200", "name": "克拉玛依市", "parent": "650000"},
    {"code": "650400", "name": "吐鲁番市", "parent": "650000"},
    {"code": "650500", "name": "哈密市", "parent": "650000"},
    {"code": "652300", "name": "昌吉回族自治州", "parent": "650000"},
    {"code": "652700", "name": "博尔塔拉蒙古自治州", "parent": "650000"},
    {"code": "652800", "name": "巴音郭楞蒙古自治州", "parent": "650000"},
    {"code": "652900", "name": "阿克苏地区", "parent": "650000"},
    {"code": "653000", "name": "克孜勒苏柯尔克孜自治州", "parent": "650000"},
    {"code": "653100", "name": "喀什地区", "parent": "650000"},
    {"code": "653200", "name": "和田地区", "parent": "650000"},
    {"code": "654000", "name": "伊犁哈萨克自治州", "parent": "650000"},
    {"code": "654200", "name": "塔城地区", "parent": "650000"},
    {"code": "654300", "name": "阿勒泰地区", "parent": "650000"},
    # -- Beijing districts (直辖市 sub-regions, level 2) --
    {"code": "110101", "name": "东城区", "parent": "110000"},
    {"code": "110102", "name": "西城区", "parent": "110000"},
    {"code": "110105", "name": "朝阳区", "parent": "110000"},
    {"code": "110106", "name": "丰台区", "parent": "110000"},
    {"code": "110107", "name": "石景山区", "parent": "110000"},
    {"code": "110108", "name": "海淀区", "parent": "110000"},
    {"code": "110109", "name": "门头沟区", "parent": "110000"},
    {"code": "110111", "name": "房山区", "parent": "110000"},
    {"code": "110112", "name": "通州区", "parent": "110000"},
    {"code": "110113", "name": "顺义区", "parent": "110000"},
    {"code": "110114", "name": "昌平区", "parent": "110000"},
    {"code": "110115", "name": "大兴区", "parent": "110000"},
    {"code": "110116", "name": "怀柔区", "parent": "110000"},
    {"code": "110117", "name": "平谷区", "parent": "110000"},
    {"code": "110118", "name": "密云区", "parent": "110000"},
    {"code": "110119", "name": "延庆区", "parent": "110000"},
    # -- Shanghai districts --
    {"code": "310101", "name": "黄浦区", "parent": "310000"},
    {"code": "310104", "name": "徐汇区", "parent": "310000"},
    {"code": "310105", "name": "长宁区", "parent": "310000"},
    {"code": "310106", "name": "静安区", "parent": "310000"},
    {"code": "310107", "name": "普陀区", "parent": "310000"},
    {"code": "310109", "name": "虹口区", "parent": "310000"},
    {"code": "310110", "name": "杨浦区", "parent": "310000"},
    {"code": "310112", "name": "闵行区", "parent": "310000"},
    {"code": "310113", "name": "宝山区", "parent": "310000"},
    {"code": "310114", "name": "嘉定区", "parent": "310000"},
    {"code": "310115", "name": "浦东新区", "parent": "310000"},
    {"code": "310116", "name": "金山区", "parent": "310000"},
    {"code": "310117", "name": "松江区", "parent": "310000"},
    {"code": "310118", "name": "青浦区", "parent": "310000"},
    {"code": "310120", "name": "奉贤区", "parent": "310000"},
    {"code": "310151", "name": "崇明区", "parent": "310000"},
    # -- Tianjin districts --
    {"code": "120101", "name": "和平区", "parent": "120000"},
    {"code": "120102", "name": "河东区", "parent": "120000"},
    {"code": "120103", "name": "河西区", "parent": "120000"},
    {"code": "120104", "name": "南开区", "parent": "120000"},
    {"code": "120105", "name": "河北区", "parent": "120000"},
    {"code": "120106", "name": "红桥区", "parent": "120000"},
    {"code": "120110", "name": "东丽区", "parent": "120000"},
    {"code": "120111", "name": "西青区", "parent": "120000"},
    {"code": "120112", "name": "津南区", "parent": "120000"},
    {"code": "120113", "name": "北辰区", "parent": "120000"},
    {"code": "120114", "name": "武清区", "parent": "120000"},
    {"code": "120115", "name": "宝坻区", "parent": "120000"},
    {"code": "120116", "name": "滨海新区", "parent": "120000"},
    {"code": "120117", "name": "宁河区", "parent": "120000"},
    {"code": "120118", "name": "静海区", "parent": "120000"},
    {"code": "120119", "name": "蓟州区", "parent": "120000"},
    # -- Chongqing key districts --
    {"code": "500101", "name": "万州区", "parent": "500000"},
    {"code": "500103", "name": "涪陵区", "parent": "500000"},
    {"code": "500104", "name": "渝中区", "parent": "500000"},
    {"code": "500105", "name": "大渡口区", "parent": "500000"},
    {"code": "500106", "name": "江北区", "parent": "500000"},
    {"code": "500107", "name": "沙坪坝区", "parent": "500000"},
    {"code": "500108", "name": "九龙坡区", "parent": "500000"},
    {"code": "500109", "name": "南岸区", "parent": "500000"},
    {"code": "500110", "name": "北碚区", "parent": "500000"},
    {"code": "500111", "name": "綦江区", "parent": "500000"},
    {"code": "500112", "name": "大足区", "parent": "500000"},
    {"code": "500113", "name": "渝北区", "parent": "500000"},
    {"code": "500114", "name": "巴南区", "parent": "500000"},
    {"code": "500115", "name": "黔江区", "parent": "500000"},
    {"code": "500116", "name": "长寿区", "parent": "500000"},
    {"code": "500117", "name": "江津区", "parent": "500000"},
    {"code": "500118", "name": "合川区", "parent": "500000"},
    {"code": "500119", "name": "永川区", "parent": "500000"},
    {"code": "500120", "name": "南川区", "parent": "500000"},
    {"code": "500151", "name": "铜梁区", "parent": "500000"},
    {"code": "500152", "name": "潼南区", "parent": "500000"},
    {"code": "500153", "name": "荣昌区", "parent": "500000"},
    {"code": "500154", "name": "开州区", "parent": "500000"},
    {"code": "500155", "name": "梁平区", "parent": "500000"},
    {"code": "500156", "name": "武隆区", "parent": "500000"},
]

# ---------------------------------------------------------------------------
# Data: Special tax policy zones (~30)
# These are NOT regular administrative regions but special economic/tax zones
# They get injected as AdministrativeRegion with regionType = special_zone
# ---------------------------------------------------------------------------

SPECIAL_TAX_ZONES = [
    # Free trade zones (自贸区/自贸港)
    {"code": "SZ_HAINAN_FTP", "name": "海南自由贸易港", "regionType": "free_trade_port",
     "parentCode": "460000", "taxPolicyTag": "hainan_ftp;zero_tariff;15pct_cit"},
    {"code": "SZ_SHANGHAI_FTZ", "name": "中国（上海）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "310000", "taxPolicyTag": "shanghai_ftz;negative_list"},
    {"code": "SZ_SHANGHAI_LINGANG", "name": "上海自贸区临港新片区", "regionType": "free_trade_zone",
     "parentCode": "310000", "taxPolicyTag": "lingang;15pct_cit;key_industry"},
    {"code": "SZ_GUANGDONG_FTZ", "name": "中国（广东）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "440000", "taxPolicyTag": "guangdong_ftz"},
    {"code": "SZ_TIANJIN_FTZ", "name": "中国（天津）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "120000", "taxPolicyTag": "tianjin_ftz"},
    {"code": "SZ_FUJIAN_FTZ", "name": "中国（福建）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "350000", "taxPolicyTag": "fujian_ftz;cross_strait"},
    {"code": "SZ_LIAONING_FTZ", "name": "中国（辽宁）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "210000", "taxPolicyTag": "liaoning_ftz"},
    {"code": "SZ_ZHEJIANG_FTZ", "name": "中国（浙江）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "330000", "taxPolicyTag": "zhejiang_ftz;oil_trade"},
    {"code": "SZ_HUBEI_FTZ", "name": "中国（湖北）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "420000", "taxPolicyTag": "hubei_ftz"},
    {"code": "SZ_CHONGQING_FTZ", "name": "中国（重庆）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "500000", "taxPolicyTag": "chongqing_ftz"},
    {"code": "SZ_SICHUAN_FTZ", "name": "中国（四川）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "510000", "taxPolicyTag": "sichuan_ftz"},
    {"code": "SZ_HENAN_FTZ", "name": "中国（河南）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "410000", "taxPolicyTag": "henan_ftz"},
    {"code": "SZ_SHAANXI_FTZ", "name": "中国（陕西）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "610000", "taxPolicyTag": "shaanxi_ftz"},
    {"code": "SZ_HEILONGJIANG_FTZ", "name": "中国（黑龙江）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "230000", "taxPolicyTag": "heilongjiang_ftz;border_trade"},
    {"code": "SZ_SHANDONG_FTZ", "name": "中国（山东）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "370000", "taxPolicyTag": "shandong_ftz"},
    {"code": "SZ_GUANGXI_FTZ", "name": "中国（广西）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "450000", "taxPolicyTag": "guangxi_ftz;asean"},
    {"code": "SZ_YUNNAN_FTZ", "name": "中国（云南）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "530000", "taxPolicyTag": "yunnan_ftz;border_trade"},
    {"code": "SZ_HEBEI_FTZ", "name": "中国（河北）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "130000", "taxPolicyTag": "hebei_ftz;xiong_an"},
    {"code": "SZ_BEIJING_FTZ", "name": "中国（北京）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "110000", "taxPolicyTag": "beijing_ftz;digital_economy"},
    {"code": "SZ_HUNAN_FTZ", "name": "中国（湖南）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "430000", "taxPolicyTag": "hunan_ftz"},
    {"code": "SZ_ANHUI_FTZ", "name": "中国（安徽）自由贸易试验区", "regionType": "free_trade_zone",
     "parentCode": "340000", "taxPolicyTag": "anhui_ftz"},
    # Special economic zones (经济特区)
    {"code": "SZ_SHENZHEN_SEZ", "name": "深圳经济特区", "regionType": "special_economic_zone",
     "parentCode": "440000", "taxPolicyTag": "shenzhen_sez;qianhai"},
    {"code": "SZ_ZHUHAI_SEZ", "name": "珠海经济特区", "regionType": "special_economic_zone",
     "parentCode": "440000", "taxPolicyTag": "zhuhai_sez;hengqin"},
    {"code": "SZ_SHANTOU_SEZ", "name": "汕头经济特区", "regionType": "special_economic_zone",
     "parentCode": "440000", "taxPolicyTag": "shantou_sez"},
    {"code": "SZ_XIAMEN_SEZ", "name": "厦门经济特区", "regionType": "special_economic_zone",
     "parentCode": "350000", "taxPolicyTag": "xiamen_sez"},
    {"code": "SZ_KASHGAR_SEZ", "name": "喀什经济开发区", "regionType": "special_economic_zone",
     "parentCode": "650000", "taxPolicyTag": "kashgar_sez;border"},
    # Cooperation zones (合作区)
    {"code": "SZ_HENGQIN", "name": "横琴粤澳深度合作区", "regionType": "cooperation_zone",
     "parentCode": "440000", "taxPolicyTag": "hengqin;15pct_pit;exempt_cit"},
    {"code": "SZ_QIANHAI", "name": "前海深港现代服务业合作区", "regionType": "cooperation_zone",
     "parentCode": "440000", "taxPolicyTag": "qianhai;15pct_cit;hk_cooperation"},
    {"code": "SZ_NANSHA", "name": "南沙粤港澳全面合作示范区", "regionType": "cooperation_zone",
     "parentCode": "440000", "taxPolicyTag": "nansha;15pct_cit"},
    {"code": "SZ_HEZUO", "name": "河套深港科技创新合作区", "regionType": "cooperation_zone",
     "parentCode": "440000", "taxPolicyTag": "hetao;sci_tech"},
    # Western Development (西部大开发 12 provinces -- tag only, regions already exist)
    {"code": "SZ_XIBU_DAKAIFA", "name": "西部大开发政策区域", "regionType": "policy_zone",
     "parentCode": "000000", "taxPolicyTag": "western_dev;15pct_cit;encouraged_industry"},
    # Xiong'an New Area
    {"code": "SZ_XIONGAN", "name": "雄安新区", "regionType": "new_area",
     "parentCode": "130000", "taxPolicyTag": "xiongan;tax_incentive"},
]


def ensure_schema(conn):
    """Add taxPolicyTag column if not exists."""
    try:
        conn.execute("ALTER TABLE AdministrativeRegion ADD taxPolicyTag STRING DEFAULT ''")
        print("OK: Added taxPolicyTag column to AdministrativeRegion")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("OK: taxPolicyTag column already exists")
        else:
            print(f"WARN: Schema alter -- {e}")

    # Create REGION_PARENT_OF edge table for hierarchy
    _exec(conn, """CREATE REL TABLE IF NOT EXISTS REGION_PARENT_OF(
        FROM AdministrativeRegion TO AdministrativeRegion
    )""", label="REL REGION_PARENT_OF")
    print("OK: Schema ensured (AdministrativeRegion + REGION_PARENT_OF)")


def inject_provinces(conn, dry_run=False):
    """Inject 34 province-level regions."""
    inserted = 0
    skipped = 0
    for p in PROVINCE_LEVEL:
        node_id = f"AR_{p['code']}"
        if dry_run:
            print(f"  DRY-RUN: {node_id} {p['name']} ({p['regionType']})")
            inserted += 1
            continue
        ok = _exec(
            conn,
            "CREATE (n:AdministrativeRegion {id: $id, name: $name, regionType: $rt, level: $lvl, parentId: $pid, taxPolicyTag: $tag})",
            {"id": node_id, "name": p["name"], "rt": p["regionType"],
             "lvl": 1, "pid": "AR_NATIONAL", "tag": ""},
            label=f"province {p['name']}",
        )
        if ok:
            inserted += 1
        else:
            skipped += 1
    print(f"OK: Provinces -- inserted {inserted}, skipped {skipped}")
    return inserted


def inject_prefectures(conn, dry_run=False):
    """Inject 333 prefecture-level cities."""
    inserted = 0
    skipped = 0
    for c in PREFECTURE_CITIES:
        node_id = f"AR_{c['code']}"
        parent_id = f"AR_{c['parent']}"
        if dry_run:
            print(f"  DRY-RUN: {node_id} {c['name']} -> {parent_id}")
            inserted += 1
            continue
        ok = _exec(
            conn,
            "CREATE (n:AdministrativeRegion {id: $id, name: $name, regionType: $rt, level: $lvl, parentId: $pid, taxPolicyTag: $tag})",
            {"id": node_id, "name": c["name"], "rt": "prefecture",
             "lvl": 2, "pid": parent_id, "tag": ""},
            label=f"city {c['name']}",
        )
        if ok:
            inserted += 1
        else:
            skipped += 1
    print(f"OK: Prefectures -- inserted {inserted}, skipped {skipped}")
    return inserted


def inject_special_zones(conn, dry_run=False):
    """Inject ~30 special tax policy zones."""
    inserted = 0
    skipped = 0
    for z in SPECIAL_TAX_ZONES:
        node_id = f"AR_{z['code']}"
        parent_id = f"AR_{z['parentCode']}" if z["parentCode"] != "000000" else "AR_NATIONAL"
        if dry_run:
            print(f"  DRY-RUN: {node_id} {z['name']} [{z['taxPolicyTag']}]")
            inserted += 1
            continue
        ok = _exec(
            conn,
            "CREATE (n:AdministrativeRegion {id: $id, name: $name, regionType: $rt, level: $lvl, parentId: $pid, taxPolicyTag: $tag})",
            {"id": node_id, "name": z["name"], "rt": z["regionType"],
             "lvl": 3, "pid": parent_id, "tag": z["taxPolicyTag"]},
            label=f"zone {z['name']}",
        )
        if ok:
            inserted += 1
        else:
            skipped += 1
    print(f"OK: Special zones -- inserted {inserted}, skipped {skipped}")
    return inserted


def inject_edges(conn, dry_run=False):
    """Create parent-child hierarchy edges."""
    total = 0
    skipped = 0

    # Province -> National
    for p in PROVINCE_LEVEL:
        if dry_run:
            total += 1
            continue
        ok = _exec(
            conn,
            "MATCH (c:AdministrativeRegion {id: $cid}), (p:AdministrativeRegion {id: $pid}) CREATE (p)-[:REGION_PARENT_OF]->(c)",
            {"cid": f"AR_{p['code']}", "pid": "AR_NATIONAL"},
            label=f"edge national->{p['name']}",
        )
        if ok:
            total += 1
        else:
            skipped += 1

    # Prefecture -> Province
    for c in PREFECTURE_CITIES:
        if dry_run:
            total += 1
            continue
        ok = _exec(
            conn,
            "MATCH (c:AdministrativeRegion {id: $cid}), (p:AdministrativeRegion {id: $pid}) CREATE (p)-[:REGION_PARENT_OF]->(c)",
            {"cid": f"AR_{c['code']}", "pid": f"AR_{c['parent']}"},
            label=f"edge {c['parent']}->{c['name']}",
        )
        if ok:
            total += 1
        else:
            skipped += 1

    # Special zone -> Parent region
    for z in SPECIAL_TAX_ZONES:
        if dry_run:
            total += 1
            continue
        parent_id = f"AR_{z['parentCode']}" if z["parentCode"] != "000000" else "AR_NATIONAL"
        ok = _exec(
            conn,
            "MATCH (c:AdministrativeRegion {id: $cid}), (p:AdministrativeRegion {id: $pid}) CREATE (p)-[:REGION_PARENT_OF]->(c)",
            {"cid": f"AR_{z['code']}", "pid": parent_id},
            label=f"edge {z['parentCode']}->{z['name']}",
        )
        if ok:
            total += 1
        else:
            skipped += 1

    print(f"OK: Edges -- created {total}, skipped {skipped}")
    return total


def main():
    parser = argparse.ArgumentParser(description="Inject administrative regions into KuzuDB")
    parser.add_argument("--db", required=True, help="Path to KuzuDB directory")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists() and not args.dry_run:
        print(f"ERROR: DB path not found: {db_path}")
        sys.exit(1)

    print(f"{'DRY-RUN: ' if args.dry_run else ''}Administrative Region Injection")
    print(f"  DB: {db_path}")
    print(f"  Province-level: {len(PROVINCE_LEVEL)}")
    print(f"  Prefecture-level: {len(PREFECTURE_CITIES)}")
    print(f"  Special tax zones: {len(SPECIAL_TAX_ZONES)}")
    total_planned = len(PROVINCE_LEVEL) + len(PREFECTURE_CITIES) + len(SPECIAL_TAX_ZONES)
    print(f"  Total planned: {total_planned}")
    print()

    conn = None
    if not args.dry_run:
        db = kuzu.Database(str(db_path))
        conn = kuzu.Connection(db)
        ensure_schema(conn)

    t0 = time.time()
    n1 = inject_provinces(conn, args.dry_run)
    n2 = inject_prefectures(conn, args.dry_run)
    n3 = inject_special_zones(conn, args.dry_run)
    n4 = inject_edges(conn, args.dry_run)
    elapsed = time.time() - t0

    print()
    print(f"DONE: {n1 + n2 + n3} nodes + {n4} edges in {elapsed:.1f}s")

    # Verify counts
    if not args.dry_run:
        r = conn.execute("MATCH (n:AdministrativeRegion) RETURN count(n)")
        if r.has_next():
            print(f"  Total AdministrativeRegion nodes in DB: {r.get_next()[0]}")
        r = conn.execute("MATCH ()-[e:REGION_PARENT_OF]->() RETURN count(e)")
        if r.has_next():
            print(f"  Total REGION_PARENT_OF edges in DB: {r.get_next()[0]}")


if __name__ == "__main__":
    main()
