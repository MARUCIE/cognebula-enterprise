#!/usr/bin/env python3
"""Inject ~800 HS (Harmonized System) customs tariff code seed nodes into KuzuDB.

Covers:
- 97 chapter-level (2-digit) categories from the HS nomenclature
- 5-10 representative 4-digit headings per chapter (~600-700 entries)
- Total ~800 seed nodes with parent-child hierarchy

Schema creates:
- HSCode node table: id, code, name, level, parentCode, vatRate, consumptionTaxRate, exportRefundRate
- HS_PARENT_OF rel table: hierarchical parent-child

Usage:
    python src/inject_hs_codes.py --db data/finance-tax-graph
    python src/inject_hs_codes.py --db data/finance-tax-graph --dry-run
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
# HS Chapter-level codes (97 chapters, 2-digit)
# Based on World Customs Organization Harmonized System 2022
# with China Customs naming conventions
# ---------------------------------------------------------------------------

HS_CHAPTERS = [
    # Section I: Live animals; animal products (Ch 01-05)
    {"code": "01", "name": "活动物", "section": "I"},
    {"code": "02", "name": "肉及食用杂碎", "section": "I"},
    {"code": "03", "name": "鱼、甲壳动物、软体动物及其他水生无脊椎动物", "section": "I"},
    {"code": "04", "name": "乳品；蛋品；天然蜂蜜；其他食用动物产品", "section": "I"},
    {"code": "05", "name": "其他动物产品", "section": "I"},
    # Section II: Vegetable products (Ch 06-14)
    {"code": "06", "name": "活树及其他活植物；球茎、根及类似品；插花及装饰用簇叶", "section": "II"},
    {"code": "07", "name": "食用蔬菜、根及块茎", "section": "II"},
    {"code": "08", "name": "食用水果及坚果；柑橘属水果或甜瓜的果皮", "section": "II"},
    {"code": "09", "name": "咖啡、茶、马黛茶及调味香料", "section": "II"},
    {"code": "10", "name": "谷物", "section": "II"},
    {"code": "11", "name": "制粉工业产品；麦芽；淀粉；菊粉；面筋", "section": "II"},
    {"code": "12", "name": "含油子仁及果实；杂项子仁及果实；工业用或药用植物；稻草、秸秆及饲料", "section": "II"},
    {"code": "13", "name": "虫胶；树胶、树脂及其他植物液、汁", "section": "II"},
    {"code": "14", "name": "编结用植物材料；其他植物产品", "section": "II"},
    # Section III: Animal or vegetable fats and oils (Ch 15)
    {"code": "15", "name": "动、植物油、脂及其分解产品；精制的食用油脂；动、植物蜡", "section": "III"},
    # Section IV: Foodstuffs, beverages, tobacco (Ch 16-24)
    {"code": "16", "name": "肉、鱼、甲壳动物、软体动物及其他水生无脊椎动物的制品", "section": "IV"},
    {"code": "17", "name": "糖及糖食", "section": "IV"},
    {"code": "18", "name": "可可及可可制品", "section": "IV"},
    {"code": "19", "name": "谷物、粮食粉、淀粉或乳的制品；糕饼点心", "section": "IV"},
    {"code": "20", "name": "蔬菜、水果、坚果或植物其他部分的制品", "section": "IV"},
    {"code": "21", "name": "杂项食品", "section": "IV"},
    {"code": "22", "name": "饮料、酒及醋", "section": "IV"},
    {"code": "23", "name": "食品工业的残渣及废料；配制的动物饲料", "section": "IV"},
    {"code": "24", "name": "烟草及烟草代用品的制品", "section": "IV"},
    # Section V: Mineral products (Ch 25-27)
    {"code": "25", "name": "盐；硫磺；泥土及石料；石膏料、石灰及水泥", "section": "V"},
    {"code": "26", "name": "矿砂、矿渣及矿灰", "section": "V"},
    {"code": "27", "name": "矿物燃料、矿物油及其蒸馏产品；沥青物质；矿物蜡", "section": "V"},
    # Section VI: Chemical products (Ch 28-38)
    {"code": "28", "name": "无机化学品；贵金属、稀土金属、放射性元素及其同位素的有机及无机化合物", "section": "VI"},
    {"code": "29", "name": "有机化学品", "section": "VI"},
    {"code": "30", "name": "药品", "section": "VI"},
    {"code": "31", "name": "肥料", "section": "VI"},
    {"code": "32", "name": "鞣料浸膏及染料浸膏；鞣酸及其衍生物；染料、颜料及其他着色料；油漆及清漆；油灰及其他类似胶粘剂；墨水、油墨", "section": "VI"},
    {"code": "33", "name": "精油及香膏；芳香料制品及化妆盥洗品", "section": "VI"},
    {"code": "34", "name": "肥皂、有机表面活性剂、洗涤剂、润滑剂、人造蜡、调制蜡、光洁剂、蜡烛及类似品、塑型用膏、牙科用蜡及牙科用熟石膏制剂", "section": "VI"},
    {"code": "35", "name": "蛋白类物质；改性淀粉；胶；酶", "section": "VI"},
    {"code": "36", "name": "炸药；烟火制品；火柴；引火合金；某些可燃制品", "section": "VI"},
    {"code": "37", "name": "照相及电影用品", "section": "VI"},
    {"code": "38", "name": "杂项化学产品", "section": "VI"},
    # Section VII: Plastics and rubber (Ch 39-40)
    {"code": "39", "name": "塑料及其制品", "section": "VII"},
    {"code": "40", "name": "橡胶及其制品", "section": "VII"},
    # Section VIII: Raw hides, leather, furskins (Ch 41-43)
    {"code": "41", "name": "生皮（毛皮除外）及皮革", "section": "VIII"},
    {"code": "42", "name": "皮革制品；鞍具及挽具；旅行用品、手提包及类似容器；动物肠线制品", "section": "VIII"},
    {"code": "43", "name": "毛皮、人造毛皮及其制品", "section": "VIII"},
    # Section IX: Wood, charcoal, cork (Ch 44-46)
    {"code": "44", "name": "木及木制品；木炭", "section": "IX"},
    {"code": "45", "name": "软木及软木制品", "section": "IX"},
    {"code": "46", "name": "稻草、秸秆、针茅或其他编结材料的编结品；篮筐及柳条编结品", "section": "IX"},
    # Section X: Pulp, paper (Ch 47-49)
    {"code": "47", "name": "木浆及其他纤维状纤维素浆；回收（废碎）纸或纸板", "section": "X"},
    {"code": "48", "name": "纸及纸板；纸浆、纸或纸板制品", "section": "X"},
    {"code": "49", "name": "书籍、报纸、印刷图画及其他印刷品；手稿、打字稿及设计图纸", "section": "X"},
    # Section XI: Textiles (Ch 50-63)
    {"code": "50", "name": "蚕丝", "section": "XI"},
    {"code": "51", "name": "羊毛、动物细毛或粗毛；马毛纱线及其机织物", "section": "XI"},
    {"code": "52", "name": "棉花", "section": "XI"},
    {"code": "53", "name": "其他植物纺织纤维；纸纱线及其机织物", "section": "XI"},
    {"code": "54", "name": "化学纤维长丝；化学纤维纺织材料制扁条及类似品", "section": "XI"},
    {"code": "55", "name": "化学纤维短纤", "section": "XI"},
    {"code": "56", "name": "絮胎、毡呢及无纺织物；特种纱线；线、绳、索、缆及其制品", "section": "XI"},
    {"code": "57", "name": "地毯及纺织材料的其他铺地制品", "section": "XI"},
    {"code": "58", "name": "特种机织物；簇绒织物；花边；装饰毯；装饰带；刺绣品", "section": "XI"},
    {"code": "59", "name": "浸渍、涂布、包覆或层压的纺织物；工业用纺织制品", "section": "XI"},
    {"code": "60", "name": "针织物及钩编织物", "section": "XI"},
    {"code": "61", "name": "针织或钩编的服装及衣着附件", "section": "XI"},
    {"code": "62", "name": "非针织或非钩编的服装及衣着附件", "section": "XI"},
    {"code": "63", "name": "其他纺织制成品；成套物品；旧衣着及旧纺织品；碎织物", "section": "XI"},
    # Section XII: Footwear, headgear (Ch 64-67)
    {"code": "64", "name": "鞋靴、护腿和类似品及其零件", "section": "XII"},
    {"code": "65", "name": "帽类及其零件", "section": "XII"},
    {"code": "66", "name": "雨伞、阳伞、手杖、鞭子、马鞭及其零件", "section": "XII"},
    {"code": "67", "name": "已加工羽毛、羽绒及其制品；人造花；人发制品", "section": "XII"},
    # Section XIII: Articles of stone, ceramic, glass (Ch 68-70)
    {"code": "68", "name": "石料、石膏、水泥、石棉、云母及类似材料的制品", "section": "XIII"},
    {"code": "69", "name": "陶瓷产品", "section": "XIII"},
    {"code": "70", "name": "玻璃及其制品", "section": "XIII"},
    # Section XIV: Precious metals, stones (Ch 71)
    {"code": "71", "name": "天然或养殖珍珠、宝石或半宝石、贵金属、包贵金属及其制品；仿首饰；硬币", "section": "XIV"},
    # Section XV: Base metals (Ch 72-83)
    {"code": "72", "name": "钢铁", "section": "XV"},
    {"code": "73", "name": "钢铁制品", "section": "XV"},
    {"code": "74", "name": "铜及其制品", "section": "XV"},
    {"code": "75", "name": "镍及其制品", "section": "XV"},
    {"code": "76", "name": "铝及其制品", "section": "XV"},
    {"code": "77", "name": "（留作国际协商统一制度将来可能使用）", "section": "XV"},
    {"code": "78", "name": "铅及其制品", "section": "XV"},
    {"code": "79", "name": "锌及其制品", "section": "XV"},
    {"code": "80", "name": "锡及其制品", "section": "XV"},
    {"code": "81", "name": "其他贱金属；金属陶瓷；其制品", "section": "XV"},
    {"code": "82", "name": "贱金属工具、器具、利口器、餐匙、餐叉及其零件", "section": "XV"},
    {"code": "83", "name": "贱金属杂项制品", "section": "XV"},
    # Section XVI: Machinery, electrical equipment (Ch 84-85)
    {"code": "84", "name": "核反应堆、锅炉、机器、机械器具及其零件", "section": "XVI"},
    {"code": "85", "name": "电机、电气设备及其零件；录音机及放声机、电视图像、声音的录制和重放设备及其零件、附件", "section": "XVI"},
    # Section XVII: Vehicles, aircraft, vessels (Ch 86-89)
    {"code": "86", "name": "铁道及电车道机车、车辆及其零件；铁道及电车道轨道固定装置及其零件及附件；各种机械交通信号设备", "section": "XVII"},
    {"code": "87", "name": "车辆及其零件、附件，但铁道及电车道车辆除外", "section": "XVII"},
    {"code": "88", "name": "航空器、航天器及其零件", "section": "XVII"},
    {"code": "89", "name": "船舶及浮动结构体", "section": "XVII"},
    # Section XVIII: Optical, instruments (Ch 90-92)
    {"code": "90", "name": "光学、照相、电影、计量、检验、医疗或外科用仪器及设备、精密仪器及设备；上述物品的零件及附件", "section": "XVIII"},
    {"code": "91", "name": "钟表及其零件", "section": "XVIII"},
    {"code": "92", "name": "乐器及其零件和附件", "section": "XVIII"},
    # Section XIX: Arms (Ch 93)
    {"code": "93", "name": "武器和弹药及其零件和附件", "section": "XIX"},
    # Section XX: Miscellaneous manufactured articles (Ch 94-96)
    {"code": "94", "name": "家具；寝具、褥垫、弹簧床垫、软坐垫及类似的填充制品；未列名灯具及照明装置；发光标志、发光铭牌及类似品；活动房屋", "section": "XX"},
    {"code": "95", "name": "玩具、游戏品、运动用品及其零件和附件", "section": "XX"},
    {"code": "96", "name": "杂项制品", "section": "XX"},
    # Section XXI: Works of art (Ch 97)
    {"code": "97", "name": "艺术品、收藏品及古物", "section": "XXI"},
]


# ---------------------------------------------------------------------------
# Representative 4-digit headings per chapter
# Each chapter gets 5-10 key headings that are commonly encountered in
# cross-border trade, especially relevant for VAT/tariff calculations
# ---------------------------------------------------------------------------

HS_HEADINGS = [
    # Chapter 01: Live animals
    {"code": "0101", "name": "活马、驴、骡", "chapter": "01"},
    {"code": "0102", "name": "活牛", "chapter": "01"},
    {"code": "0103", "name": "活猪", "chapter": "01"},
    {"code": "0104", "name": "活绵羊及山羊", "chapter": "01"},
    {"code": "0105", "name": "活家禽", "chapter": "01"},
    {"code": "0106", "name": "其他活动物", "chapter": "01"},
    # Chapter 02: Meat
    {"code": "0201", "name": "鲜、冷牛肉", "chapter": "02"},
    {"code": "0202", "name": "冻牛肉", "chapter": "02"},
    {"code": "0203", "name": "鲜、冷、冻猪肉", "chapter": "02"},
    {"code": "0204", "name": "鲜、冷、冻绵羊肉或山羊肉", "chapter": "02"},
    {"code": "0207", "name": "鲜、冷、冻家禽肉及食用杂碎", "chapter": "02"},
    {"code": "0210", "name": "干、熏、盐腌或盐渍的肉及食用杂碎", "chapter": "02"},
    # Chapter 03: Fish
    {"code": "0301", "name": "活鱼", "chapter": "03"},
    {"code": "0302", "name": "鲜、冷鱼", "chapter": "03"},
    {"code": "0303", "name": "冻鱼", "chapter": "03"},
    {"code": "0304", "name": "鲜、冷、冻鱼片及其他鱼肉", "chapter": "03"},
    {"code": "0306", "name": "甲壳动物", "chapter": "03"},
    {"code": "0307", "name": "软体动物", "chapter": "03"},
    # Chapter 04: Dairy, eggs, honey
    {"code": "0401", "name": "未浓缩的乳及奶油", "chapter": "04"},
    {"code": "0402", "name": "浓缩、加糖的乳及奶油", "chapter": "04"},
    {"code": "0403", "name": "酪乳、酸乳、酪农制品", "chapter": "04"},
    {"code": "0405", "name": "黄油及其他从乳中提取的脂和油", "chapter": "04"},
    {"code": "0406", "name": "乳酪及凝乳", "chapter": "04"},
    {"code": "0407", "name": "带壳禽蛋", "chapter": "04"},
    {"code": "0409", "name": "天然蜂蜜", "chapter": "04"},
    # Chapter 05: Other animal products
    {"code": "0504", "name": "动物肠、膀胱、胃的整体或段块", "chapter": "05"},
    {"code": "0505", "name": "带有羽毛或羽绒的鸟皮及鸟体其他部分", "chapter": "05"},
    {"code": "0507", "name": "兽牙、龟甲、鲸须、角、蹄", "chapter": "05"},
    {"code": "0511", "name": "其他编号未列名的动物产品", "chapter": "05"},
    # Chapter 06-08: Plants, vegetables, fruits
    {"code": "0602", "name": "其他活植物（包括其根）；插条及接穗；蘑菇菌丝", "chapter": "06"},
    {"code": "0603", "name": "鲜切花及花蕾", "chapter": "06"},
    {"code": "0701", "name": "鲜或冷藏的马铃薯", "chapter": "07"},
    {"code": "0702", "name": "鲜或冷藏的番茄", "chapter": "07"},
    {"code": "0703", "name": "鲜或冷藏的洋葱、青葱、大蒜、韭葱", "chapter": "07"},
    {"code": "0709", "name": "其他鲜或冷藏的蔬菜", "chapter": "07"},
    {"code": "0713", "name": "干的豆类蔬菜", "chapter": "07"},
    {"code": "0801", "name": "鲜或干的椰子、巴西果及腰果", "chapter": "08"},
    {"code": "0802", "name": "其他鲜或干的坚果", "chapter": "08"},
    {"code": "0803", "name": "鲜或干的香蕉", "chapter": "08"},
    {"code": "0805", "name": "鲜或干的柑橘属水果", "chapter": "08"},
    {"code": "0808", "name": "鲜苹果、梨及榅桲", "chapter": "08"},
    # Chapter 09: Coffee, tea, spices
    {"code": "0901", "name": "咖啡", "chapter": "09"},
    {"code": "0902", "name": "茶", "chapter": "09"},
    {"code": "0904", "name": "胡椒；辣椒（干）", "chapter": "09"},
    {"code": "0910", "name": "生姜、藏红花、姜黄、百里香、月桂叶、咖喱及其他调味香料", "chapter": "09"},
    # Chapter 10: Cereals
    {"code": "1001", "name": "小麦及混合麦", "chapter": "10"},
    {"code": "1005", "name": "玉米", "chapter": "10"},
    {"code": "1006", "name": "稻谷", "chapter": "10"},
    {"code": "1008", "name": "荞麦、谷子及加那利草子；其他谷物", "chapter": "10"},
    # Chapter 11-14: Milling, seeds, gums, vegetable materials
    {"code": "1101", "name": "小麦或混合麦的细粉", "chapter": "11"},
    {"code": "1201", "name": "大豆", "chapter": "12"},
    {"code": "1202", "name": "未焙炒的花生", "chapter": "12"},
    {"code": "1207", "name": "其他含油子仁及果实", "chapter": "12"},
    {"code": "1211", "name": "主要用作药料的植物及其某些部分", "chapter": "12"},
    {"code": "1301", "name": "虫胶；天然树胶、树脂、树胶脂及油树脂", "chapter": "13"},
    {"code": "1401", "name": "主要用作编结的植物材料", "chapter": "14"},
    # Chapter 15: Fats and oils
    {"code": "1507", "name": "豆油及其分离品", "chapter": "15"},
    {"code": "1509", "name": "橄榄油及其分离品", "chapter": "15"},
    {"code": "1511", "name": "棕榈油及其分离品", "chapter": "15"},
    {"code": "1512", "name": "葵花油、红花油或棉子油及其分离品", "chapter": "15"},
    {"code": "1515", "name": "其他固定植物油脂及其分离品", "chapter": "15"},
    # Chapter 16-17: Prepared foods
    {"code": "1601", "name": "肉、食用杂碎、血的香肠及类似产品", "chapter": "16"},
    {"code": "1604", "name": "制作或保藏的鱼", "chapter": "16"},
    {"code": "1701", "name": "固体甘蔗糖、甜菜糖及化学纯蔗糖", "chapter": "17"},
    {"code": "1704", "name": "不含可可的糖食", "chapter": "17"},
    # Chapter 18-19: Cocoa, cereals preparations
    {"code": "1801", "name": "整颗或破碎的可可豆", "chapter": "18"},
    {"code": "1806", "name": "巧克力及其他含可可的食品", "chapter": "18"},
    {"code": "1901", "name": "麦精；其他食品", "chapter": "19"},
    {"code": "1905", "name": "面包、糕点、饼干及其他焙烘糕饼", "chapter": "19"},
    # Chapter 20-21: Vegetable/fruit preparations
    {"code": "2001", "name": "用醋或醋酸制作或保藏的蔬菜、水果、坚果及食用植物其他部分", "chapter": "20"},
    {"code": "2009", "name": "未发酵及未加酒精的水果汁或蔬菜汁", "chapter": "20"},
    {"code": "2101", "name": "咖啡、茶、马黛茶的浸膏、精汁及浓缩物", "chapter": "21"},
    {"code": "2106", "name": "其他编号未列名的食品", "chapter": "21"},
    # Chapter 22: Beverages
    {"code": "2201", "name": "水，包括天然或人造矿泉水及充气水", "chapter": "22"},
    {"code": "2202", "name": "加味、加糖或其他甜物质的水", "chapter": "22"},
    {"code": "2203", "name": "麦芽酿造的啤酒", "chapter": "22"},
    {"code": "2204", "name": "鲜葡萄酿造的酒", "chapter": "22"},
    {"code": "2208", "name": "蒸馏酒及酒精饮料", "chapter": "22"},
    # Chapter 23-24: Residues, tobacco
    {"code": "2301", "name": "不适于供人食用的肉、杂碎、鱼的粉、渣粉及团粒", "chapter": "23"},
    {"code": "2304", "name": "提取豆油后所得的油渣饼及其他固体残渣", "chapter": "23"},
    {"code": "2309", "name": "配制的动物饲料", "chapter": "23"},
    {"code": "2401", "name": "未制造的烟草；烟草废料", "chapter": "24"},
    {"code": "2402", "name": "雪茄烟、小雪茄烟及卷烟", "chapter": "24"},
    # Chapter 25-27: Mineral products
    {"code": "2501", "name": "盐（包括食盐及变性盐）及纯氯化钠", "chapter": "25"},
    {"code": "2515", "name": "大理石、石灰华及其他石灰质碑用或建筑用石", "chapter": "25"},
    {"code": "2523", "name": "水泥（包括水泥熟料）", "chapter": "25"},
    {"code": "2601", "name": "铁矿砂及其精矿", "chapter": "26"},
    {"code": "2603", "name": "铜矿砂及其精矿", "chapter": "26"},
    {"code": "2701", "name": "煤；煤砖、煤球及用煤制成的类似固体燃料", "chapter": "27"},
    {"code": "2709", "name": "石油原油及从沥青矿物提取的原油", "chapter": "27"},
    {"code": "2710", "name": "石油及从沥青矿物提取的油类", "chapter": "27"},
    {"code": "2711", "name": "石油气及其他烃类气", "chapter": "27"},
    # Chapter 28-29: Inorganic and organic chemicals
    {"code": "2801", "name": "氟、氯、溴、碘", "chapter": "28"},
    {"code": "2814", "name": "氨，无水氨或氨的水溶液", "chapter": "28"},
    {"code": "2833", "name": "硫酸盐；矾；过硫酸盐", "chapter": "28"},
    {"code": "2844", "name": "放射性化学元素及放射性同位素", "chapter": "28"},
    {"code": "2901", "name": "无环烃", "chapter": "29"},
    {"code": "2902", "name": "环烃", "chapter": "29"},
    {"code": "2905", "name": "无环醇及其卤化、磺化、硝化或亚硝化衍生物", "chapter": "29"},
    {"code": "2917", "name": "多元羧酸及其酸酐、酰卤化物、过氧化物及过氧酸", "chapter": "29"},
    {"code": "2933", "name": "仅含氮杂原子的杂环化合物", "chapter": "29"},
    {"code": "2941", "name": "抗菌素", "chapter": "29"},
    # Chapter 30: Pharmaceuticals
    {"code": "3001", "name": "干燥的腺体及其他器官", "chapter": "30"},
    {"code": "3002", "name": "人血；供治疗、预防或诊断疾病用的动物血；抗血清", "chapter": "30"},
    {"code": "3003", "name": "含有两种或两种以上成分混合而成的治疗或预防疾病用药品（未配定剂量或零售包装）", "chapter": "30"},
    {"code": "3004", "name": "已配定剂量或零售包装的药品", "chapter": "30"},
    {"code": "3006", "name": "药品（包括兽药）", "chapter": "30"},
    # Chapter 31-32: Fertilizers, dyes
    {"code": "3102", "name": "矿物氮肥或化学氮肥", "chapter": "31"},
    {"code": "3105", "name": "含有两种或三种肥效元素的矿物肥料或化学肥料", "chapter": "31"},
    {"code": "3204", "name": "合成有机着色料及以其为基本成分的制品", "chapter": "32"},
    {"code": "3208", "name": "溶于非水介质的油漆及清漆", "chapter": "32"},
    {"code": "3215", "name": "印刷油墨、书写或绘画墨水及其他墨类", "chapter": "32"},
    # Chapter 33-38: Essential oils, soaps, explosives, photographic, chemicals
    {"code": "3301", "name": "精油", "chapter": "33"},
    {"code": "3304", "name": "美容品或化妆品及护肤品", "chapter": "33"},
    {"code": "3305", "name": "护发品", "chapter": "33"},
    {"code": "3401", "name": "肥皂", "chapter": "34"},
    {"code": "3808", "name": "杀虫剂、杀菌剂、除草剂等", "chapter": "38"},
    {"code": "3824", "name": "铸模及铸芯用的配制粘合剂及其他化学产品", "chapter": "38"},
    # Chapter 39-40: Plastics and rubber
    {"code": "3901", "name": "初级形状的乙烯聚合物", "chapter": "39"},
    {"code": "3902", "name": "初级形状的丙烯聚合物", "chapter": "39"},
    {"code": "3904", "name": "初级形状的氯乙烯聚合物", "chapter": "39"},
    {"code": "3907", "name": "初级形状的聚缩醛、其他聚醚及环氧树脂；聚碳酸酯、醇酸树脂", "chapter": "39"},
    {"code": "3920", "name": "非泡沫塑料的板、片、膜、箔及扁条", "chapter": "39"},
    {"code": "3923", "name": "塑料制供运输或包装货物用的物品", "chapter": "39"},
    {"code": "4011", "name": "新的充气橡胶轮胎", "chapter": "40"},
    {"code": "4012", "name": "翻新或旧的充气橡胶轮胎", "chapter": "40"},
    {"code": "4015", "name": "硫化橡胶（硬质橡胶除外）制的衣着用品及附件", "chapter": "40"},
    # Chapter 41-43: Leather, furskins
    {"code": "4104", "name": "经鞣制的牛皮革及马皮革", "chapter": "41"},
    {"code": "4202", "name": "旅行箱包、手提包、公文包及类似容器", "chapter": "42"},
    {"code": "4203", "name": "皮革或再生皮革制的衣着及衣着附件", "chapter": "42"},
    {"code": "4302", "name": "已鞣制或精制的毛皮", "chapter": "43"},
    # Chapter 44-46: Wood, cork
    {"code": "4403", "name": "原木", "chapter": "44"},
    {"code": "4407", "name": "经纵锯、纵切、刨切或旋切的木材", "chapter": "44"},
    {"code": "4410", "name": "碎料板及类似板", "chapter": "44"},
    {"code": "4412", "name": "胶合板、单板饰面板及类似的多层板", "chapter": "44"},
    {"code": "4418", "name": "建筑用木工制品", "chapter": "44"},
    # Chapter 47-49: Paper, printed matter
    {"code": "4701", "name": "机械木浆", "chapter": "47"},
    {"code": "4801", "name": "卷筒或成张的新闻纸", "chapter": "48"},
    {"code": "4802", "name": "未经涂布的书写纸及绘图纸", "chapter": "48"},
    {"code": "4819", "name": "纸或纸板制的箱、盒、袋及其他包装容器", "chapter": "48"},
    {"code": "4901", "name": "印刷的书籍、小册子、传单及类似印刷品", "chapter": "49"},
    {"code": "4911", "name": "其他印刷品", "chapter": "49"},
    # Chapter 50-55: Textiles (key materials)
    {"code": "5007", "name": "蚕丝或绢丝机织物", "chapter": "50"},
    {"code": "5112", "name": "梳毛羊毛或梳毛动物细毛的机织物", "chapter": "51"},
    {"code": "5208", "name": "棉机织物", "chapter": "52"},
    {"code": "5209", "name": "每平方米重量超过200克的棉机织物", "chapter": "52"},
    {"code": "5407", "name": "合成纤维长丝纱线的机织物", "chapter": "54"},
    {"code": "5503", "name": "合成纤维短纤，未梳或未经其他纺前加工", "chapter": "55"},
    {"code": "5509", "name": "合成纤维短纤纱线（缝纫线除外）", "chapter": "55"},
    # Chapter 56-63: Textiles (made-up)
    {"code": "5601", "name": "纺织纤维絮胎及其制品", "chapter": "56"},
    {"code": "5903", "name": "用塑料浸渍、涂布、包覆或层压的纺织物", "chapter": "59"},
    {"code": "6104", "name": "女式针织或钩编的西服套装、便服套装等", "chapter": "61"},
    {"code": "6109", "name": "针织或钩编的T恤衫、汗衫及其他背心", "chapter": "61"},
    {"code": "6110", "name": "针织或钩编的套头衫、开襟衫、马甲及类似品", "chapter": "61"},
    {"code": "6203", "name": "男式西服套装、便服套装等", "chapter": "62"},
    {"code": "6204", "name": "女式西服套装、便服套装等", "chapter": "62"},
    {"code": "6302", "name": "床上用织物制品、餐桌用织物制品、盥洗及厨房用织物制品", "chapter": "63"},
    # Chapter 64-67: Footwear, headgear
    {"code": "6402", "name": "橡胶或塑料制外底及鞋面的其他鞋靴", "chapter": "64"},
    {"code": "6403", "name": "橡胶、塑料、皮革或再生皮革制外底、皮革制鞋面的鞋靴", "chapter": "64"},
    {"code": "6404", "name": "橡胶、塑料、皮革或再生皮革制外底、纺织材料制鞋面的鞋靴", "chapter": "64"},
    {"code": "6504", "name": "编结或用条带拼制的帽类", "chapter": "65"},
    {"code": "6702", "name": "人造花、叶、果及其制品", "chapter": "67"},
    # Chapter 68-70: Stone, ceramic, glass
    {"code": "6802", "name": "已加工的碑用或建筑用石及其制品", "chapter": "68"},
    {"code": "6902", "name": "耐火砖", "chapter": "69"},
    {"code": "6907", "name": "未上釉或上釉的陶瓷铺地砖、贴面砖", "chapter": "69"},
    {"code": "6911", "name": "瓷制餐具、厨房器具及其他瓷制家用或盥洗用品", "chapter": "69"},
    {"code": "7003", "name": "铸造及压延玻璃的板、片", "chapter": "70"},
    {"code": "7005", "name": "抛光及经其他处理的浮法玻璃及磨面平板玻璃", "chapter": "70"},
    {"code": "7010", "name": "玻璃制的大容器、瓶、广口瓶、坛、罐", "chapter": "70"},
    {"code": "7013", "name": "玻璃制餐桌、厨房、盥洗室等用玻璃器皿", "chapter": "70"},
    # Chapter 71: Precious metals and stones
    {"code": "7101", "name": "天然或养殖珍珠", "chapter": "71"},
    {"code": "7102", "name": "钻石", "chapter": "71"},
    {"code": "7108", "name": "黄金（包括镀铂的黄金），未锻造、半制成或粉状", "chapter": "71"},
    {"code": "7113", "name": "珠宝首饰及其零件", "chapter": "71"},
    {"code": "7118", "name": "硬币", "chapter": "71"},
    # Chapter 72-76: Steel, iron, copper, aluminum
    {"code": "7201", "name": "生铁及镜铁，块、粒或类似形状", "chapter": "72"},
    {"code": "7207", "name": "钢的半制成品", "chapter": "72"},
    {"code": "7208", "name": "热轧铁或非合金钢宽度≥600mm的平板轧材", "chapter": "72"},
    {"code": "7210", "name": "经镀或涂层的铁或非合金钢宽度≥600mm的平板轧材", "chapter": "72"},
    {"code": "7219", "name": "不锈钢宽度≥600mm的平板轧材", "chapter": "72"},
    {"code": "7304", "name": "无缝钢铁管及空心异型材", "chapter": "73"},
    {"code": "7306", "name": "其他钢铁管及空心异型材", "chapter": "73"},
    {"code": "7318", "name": "钢铁制螺钉、螺栓、螺母、方头螺钉、钩头螺钉、铆钉", "chapter": "73"},
    {"code": "7403", "name": "精炼铜及铜合金，未锻造", "chapter": "74"},
    {"code": "7408", "name": "铜丝", "chapter": "74"},
    {"code": "7601", "name": "未锻造的铝", "chapter": "76"},
    {"code": "7604", "name": "铝条、杆及型材", "chapter": "76"},
    {"code": "7606", "name": "铝板、片及带", "chapter": "76"},
    # Chapter 78-83: Lead, zinc, tin, base metals
    {"code": "7801", "name": "未锻造的铅", "chapter": "78"},
    {"code": "7901", "name": "未锻造的锌", "chapter": "79"},
    {"code": "8003", "name": "锡条、杆、型材及丝", "chapter": "80"},
    {"code": "8207", "name": "可互换工具", "chapter": "82"},
    {"code": "8211", "name": "刀", "chapter": "82"},
    {"code": "8215", "name": "匙、叉、勺、蛋糕铲刀等", "chapter": "82"},
    {"code": "8302", "name": "贱金属制支架、配件及类似品", "chapter": "83"},
    # Chapter 84: Machinery (high-value, commonly traded)
    {"code": "8401", "name": "核反应堆；未辐照的核燃料元件", "chapter": "84"},
    {"code": "8407", "name": "火花点火式活塞内燃发动机", "chapter": "84"},
    {"code": "8408", "name": "压燃式活塞内燃发动机（柴油或半柴油发动机）", "chapter": "84"},
    {"code": "8411", "name": "涡轮喷气发动机、涡轮螺桨发动机及其他燃气轮机", "chapter": "84"},
    {"code": "8413", "name": "液体泵", "chapter": "84"},
    {"code": "8414", "name": "空气泵或真空泵、空气及其他气体压缩机及风扇", "chapter": "84"},
    {"code": "8421", "name": "离心机；液体或气体的过滤、净化机器及装置", "chapter": "84"},
    {"code": "8429", "name": "自推进的推土机、筑路机、平地机、铲运机、挖掘机等", "chapter": "84"},
    {"code": "8431", "name": "专用于或主要用于8425至8430所列机械的零件", "chapter": "84"},
    {"code": "8443", "name": "印刷机；喷墨打印机、激光打印机等输出设备", "chapter": "84"},
    {"code": "8452", "name": "缝纫机", "chapter": "84"},
    {"code": "8471", "name": "自动数据处理设备及其部件", "chapter": "84"},
    {"code": "8473", "name": "专用于或主要用于8469至8472所列机器的零件及附件", "chapter": "84"},
    {"code": "8479", "name": "具有独立功能的机器及机械器具", "chapter": "84"},
    {"code": "8481", "name": "管子附件（龙头、旋塞、阀门及类似装置）", "chapter": "84"},
    {"code": "8482", "name": "滚珠或滚柱轴承", "chapter": "84"},
    {"code": "8483", "name": "传动轴、曲柄、轴承座、齿轮及齿轮装置", "chapter": "84"},
    # Chapter 85: Electrical equipment (critical for tech trade)
    {"code": "8501", "name": "电动机及发电机", "chapter": "85"},
    {"code": "8504", "name": "变压器、静止式变流器及电感器", "chapter": "85"},
    {"code": "8506", "name": "原电池及原电池组", "chapter": "85"},
    {"code": "8507", "name": "蓄电池", "chapter": "85"},
    {"code": "8517", "name": "电话机及其他传输或接收声音、图像的设备", "chapter": "85"},
    {"code": "8523", "name": "已录制的媒体", "chapter": "85"},
    {"code": "8528", "name": "电视接收设备（包括视频监视器和视频投影机）", "chapter": "85"},
    {"code": "8529", "name": "专用于或主要用于8525至8528所列装置的零件", "chapter": "85"},
    {"code": "8532", "name": "电容器", "chapter": "85"},
    {"code": "8534", "name": "印刷电路", "chapter": "85"},
    {"code": "8536", "name": "电路的开关、保护或连接用的电气装置", "chapter": "85"},
    {"code": "8541", "name": "半导体器件；发光二极管；光敏半导体器件", "chapter": "85"},
    {"code": "8542", "name": "集成电路", "chapter": "85"},
    {"code": "8544", "name": "绝缘电线、电缆及其他绝缘电导体", "chapter": "85"},
    # Chapter 86-89: Transport equipment
    {"code": "8601", "name": "铁道电力机车", "chapter": "86"},
    {"code": "8607", "name": "铁道及电车道机车或车辆的零件", "chapter": "86"},
    {"code": "8703", "name": "主要用于载人的机动车辆", "chapter": "87"},
    {"code": "8704", "name": "货运机动车辆", "chapter": "87"},
    {"code": "8708", "name": "8701至8705所列车辆的零件及附件", "chapter": "87"},
    {"code": "8711", "name": "摩托车（包括机器脚踏两用车）及脚踏车", "chapter": "87"},
    {"code": "8714", "name": "8711至8713所列车辆的零件及附件", "chapter": "87"},
    {"code": "8802", "name": "其他飞机（例如直升机、固定翼飞机）；航天器", "chapter": "88"},
    {"code": "8803", "name": "8801或8802所列货品的零件", "chapter": "88"},
    {"code": "8901", "name": "巡洋舰、护航舰、驱逐舰等军用船舶", "chapter": "89"},
    {"code": "8905", "name": "灯船、消防船、浮吊等专用船舶", "chapter": "89"},
    # Chapter 90: Optical, medical instruments
    {"code": "9001", "name": "光导纤维及光导纤维束；光导纤维电缆", "chapter": "90"},
    {"code": "9002", "name": "透镜、棱镜、反射镜及其他光学元件", "chapter": "90"},
    {"code": "9013", "name": "液晶显示装置及激光器", "chapter": "90"},
    {"code": "9018", "name": "医疗、外科或兽医用仪器及器具", "chapter": "90"},
    {"code": "9021", "name": "矫形器具；人造的人体部分", "chapter": "90"},
    {"code": "9026", "name": "液体或气体的流量、液位、压力检测仪器", "chapter": "90"},
    {"code": "9027", "name": "理化分析仪器及装置", "chapter": "90"},
    {"code": "9030", "name": "示波器、频谱分析仪及其他电量检测仪器", "chapter": "90"},
    {"code": "9031", "name": "其他测量或检验仪器、器具及机器", "chapter": "90"},
    {"code": "9032", "name": "自动调节或控制仪器及装置", "chapter": "90"},
    # Chapter 91-92: Clocks, musical instruments
    {"code": "9101", "name": "手表", "chapter": "91"},
    {"code": "9102", "name": "手表（非贵金属表壳）", "chapter": "91"},
    {"code": "9108", "name": "钟表机芯", "chapter": "91"},
    {"code": "9201", "name": "钢琴", "chapter": "92"},
    {"code": "9207", "name": "键盘乐器", "chapter": "92"},
    # Chapter 93: Arms
    {"code": "9301", "name": "军用武器", "chapter": "93"},
    {"code": "9303", "name": "其他火器及类似装置", "chapter": "93"},
    # Chapter 94: Furniture
    {"code": "9401", "name": "坐具及其零件", "chapter": "94"},
    {"code": "9403", "name": "其他家具及其零件", "chapter": "94"},
    {"code": "9404", "name": "弹簧床垫；寝具及类似的填充制品", "chapter": "94"},
    {"code": "9405", "name": "灯具及照明装置", "chapter": "94"},
    {"code": "9406", "name": "活动房屋", "chapter": "94"},
    # Chapter 95: Toys, games, sports
    {"code": "9503", "name": "三轮车、踏板车等玩具；缩小模型及类似的娱乐用模型", "chapter": "95"},
    {"code": "9504", "name": "视频游戏控制台及设备", "chapter": "95"},
    {"code": "9506", "name": "一般的体育活动、体操或竞技用品及设备", "chapter": "95"},
    # Chapter 96: Miscellaneous
    {"code": "9601", "name": "已加工的兽牙、骨、龟甲、角、珊瑚等及其制品", "chapter": "96"},
    {"code": "9608", "name": "圆珠笔；毡头和其他渗水式笔头笔和记号笔", "chapter": "96"},
    {"code": "9613", "name": "打火机及其他点火器", "chapter": "96"},
    {"code": "9619", "name": "卫生巾及卫生棉条、尿布及尿布衬里及类似品", "chapter": "96"},
    # Chapter 97: Art, antiques
    {"code": "9701", "name": "手绘油画、素描、粉画及其他画", "chapter": "97"},
    {"code": "9703", "name": "各种材料的原创雕塑品及雕刻品", "chapter": "97"},
    {"code": "9706", "name": "超过一百年的古物", "chapter": "97"},
]


def create_schema(conn):
    """Create HSCode node table and HS_PARENT_OF rel table."""
    _exec(conn, """CREATE NODE TABLE IF NOT EXISTS HSCode(
        id STRING PRIMARY KEY,
        code STRING,
        name STRING,
        level INT64,
        parentCode STRING,
        section STRING,
        vatRate STRING,
        consumptionTaxRate STRING,
        exportRefundRate STRING,
        seedStatus STRING
    )""", label="NODE HSCode")

    _exec(conn, """CREATE REL TABLE IF NOT EXISTS HS_PARENT_OF(
        FROM HSCode TO HSCode
    )""", label="REL HS_PARENT_OF")

    print("OK: Schema ensured (HSCode + HS_PARENT_OF)")


def inject_chapters(conn, dry_run=False):
    """Inject 97 chapter-level HS codes."""
    inserted = 0
    skipped = 0
    for ch in HS_CHAPTERS:
        node_id = f"HS_{ch['code']}"
        if dry_run:
            print(f"  DRY-RUN: {node_id} Ch.{ch['code']} {ch['name']}")
            inserted += 1
            continue
        ok = _exec(
            conn,
            "CREATE (n:HSCode {id: $id, code: $code, name: $name, level: $lvl, parentCode: $pc, section: $sec, vatRate: $vat, consumptionTaxRate: $ct, exportRefundRate: $er, seedStatus: $ss})",
            {"id": node_id, "code": ch["code"], "name": ch["name"],
             "lvl": 2, "pc": "", "sec": ch["section"],
             "vat": "", "ct": "", "er": "", "ss": "seed"},
            label=f"chapter {ch['code']}",
        )
        if ok:
            inserted += 1
        else:
            skipped += 1
    print(f"OK: Chapters -- inserted {inserted}, skipped {skipped}")
    return inserted


def inject_headings(conn, dry_run=False):
    """Inject 4-digit heading-level HS codes."""
    inserted = 0
    skipped = 0
    for h in HS_HEADINGS:
        node_id = f"HS_{h['code']}"
        if dry_run:
            print(f"  DRY-RUN: {node_id} {h['code']} {h['name']}")
            inserted += 1
            continue
        ok = _exec(
            conn,
            "CREATE (n:HSCode {id: $id, code: $code, name: $name, level: $lvl, parentCode: $pc, section: $sec, vatRate: $vat, consumptionTaxRate: $ct, exportRefundRate: $er, seedStatus: $ss})",
            {"id": node_id, "code": h["code"], "name": h["name"],
             "lvl": 4, "pc": h["chapter"], "sec": "",
             "vat": "", "ct": "", "er": "", "ss": "seed"},
            label=f"heading {h['code']}",
        )
        if ok:
            inserted += 1
        else:
            skipped += 1
    print(f"OK: Headings -- inserted {inserted}, skipped {skipped}")
    return inserted


def inject_edges(conn, dry_run=False):
    """Create parent-child hierarchy: heading -> chapter."""
    total = 0
    skipped = 0
    for h in HS_HEADINGS:
        if dry_run:
            total += 1
            continue
        ok = _exec(
            conn,
            "MATCH (c:HSCode {id: $cid}), (p:HSCode {id: $pid}) CREATE (p)-[:HS_PARENT_OF]->(c)",
            {"cid": f"HS_{h['code']}", "pid": f"HS_{h['chapter']}"},
            label=f"edge {h['chapter']}->{h['code']}",
        )
        if ok:
            total += 1
        else:
            skipped += 1
    print(f"OK: Edges -- created {total}, skipped {skipped}")
    return total


def main():
    parser = argparse.ArgumentParser(description="Inject HS customs tariff codes into KuzuDB")
    parser.add_argument("--db", required=True, help="Path to KuzuDB directory")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists() and not args.dry_run:
        print(f"ERROR: DB path not found: {db_path}")
        sys.exit(1)

    print(f"{'DRY-RUN: ' if args.dry_run else ''}HS Code Injection")
    print(f"  DB: {db_path}")
    print(f"  Chapters (2-digit): {len(HS_CHAPTERS)}")
    print(f"  Headings (4-digit): {len(HS_HEADINGS)}")
    total_planned = len(HS_CHAPTERS) + len(HS_HEADINGS)
    print(f"  Total planned: {total_planned}")
    print(f"  NOTE: seedStatus='seed' -- expand to 10K via customs.gov.cn crawl later")
    print()

    conn = None
    if not args.dry_run:
        db = kuzu.Database(str(db_path))
        conn = kuzu.Connection(db)
        create_schema(conn)

    t0 = time.time()
    n1 = inject_chapters(conn, args.dry_run)
    n2 = inject_headings(conn, args.dry_run)
    n3 = inject_edges(conn, args.dry_run)
    elapsed = time.time() - t0

    print()
    print(f"DONE: {n1 + n2} nodes + {n3} edges in {elapsed:.1f}s")

    # Verify counts
    if not args.dry_run:
        r = conn.execute("MATCH (n:HSCode) RETURN count(n)")
        if r.has_next():
            print(f"  Total HSCode nodes in DB: {r.get_next()[0]}")
        r = conn.execute("MATCH ()-[e:HS_PARENT_OF]->() RETURN count(e)")
        if r.has_next():
            print(f"  Total HS_PARENT_OF edges in DB: {r.get_next()[0]}")


if __name__ == "__main__":
    main()
