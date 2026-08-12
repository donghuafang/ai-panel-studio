#!/usr/bin/env python3
"""AI Panel Studio — 高质量样例数据

提供 7 组预设讨论话题及对应嘉宾阵容，覆盖科技、社会、经济、文化等多元领域。
每组嘉宾阵容经过精心设计，确保立场多元、观点碰撞。

用法：
    from scripts.seed_data import SEED_DISCUSSIONS
    # 或者直接运行导入到数据库：
    python scripts/seed_data.py
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

# ══════════════════════════════════════════════════════════════════════════
# 7 组高质量样例数据
# ══════════════════════════════════════════════════════════════════════════

SEED_DISCUSSIONS = [
    # ── 样例 1: AI 与就业 ──────────────────────────────────────────
    {
        "topic": "AI 会取代人类创造力吗",
        "expert_count": 4,
        "max_rounds": 3,
        "guests": [
            {
                "name": "陈文博",
                "profession": "科技媒体主编",
                "title": "资深科技评论员",
                "stance": "作为中立主持人，引导各方充分表达观点，聚焦 AI 对创造性行业的具体影响。",
                "color": "#4A90D9",
                "role": "host",
            },
            {
                "name": "林晓",
                "profession": "AI 研究员",
                "title": "机器学习博士",
                "stance": "认为 AI 在模式识别和数据分析方面已超越人类，但真正的创意突破仍需要人类的情感体验和直觉判断。",
                "color": "#FF6B6B",
                "role": "guest",
            },
            {
                "name": "王子轩",
                "profession": "独立艺术家",
                "title": "当代艺术策展人",
                "stance": "坚持艺术创作的核心是人的情感表达，AI 生成的内容缺乏灵魂和生命体验，不可能真正'创造'。",
                "color": "#4ECDC4",
                "role": "guest",
            },
            {
                "name": "张雪琳",
                "profession": "产品设计师",
                "title": "UX 设计总监",
                "stance": "认为 AI 是强大的创意辅助工具，能够激发灵感、加速迭代，但最终的设计决策权仍在人类手中。",
                "color": "#FFD93D",
                "role": "guest",
            },
            {
                "name": "赵明远",
                "profession": "企业家",
                "title": "AI 创业公司 CEO",
                "stance": "相信 AI 将在 5 年内全面渗透创意产业，人类的角色将从'创作者'转变为'策展人'和'价值判断者'。",
                "color": "#C44DFF",
                "role": "guest",
            },
        ],
    },
    # ── 样例 2: 自动驾驶伦理 ─────────────────────────────────────
    {
        "topic": "自动驾驶的伦理困境：电车难题如何抉择",
        "expert_count": 5,
        "max_rounds": 3,
        "guests": [
            {
                "name": "何思远",
                "profession": "法学教授",
                "title": "科技伦理研究中心主任",
                "stance": "中立主持，聚焦技术、法律与伦理的交叉点，引导嘉宾从多维度探讨自动驾驶的决策框架。",
                "color": "#4A90D9",
                "role": "host",
            },
            {
                "name": "刘工程师",
                "profession": "自动驾驶架构师",
                "title": "某头部车企首席技术官",
                "stance": "强调技术方案的可行性——通过传感器融合和 V2X 通信，可以大幅降低电车难题的发生概率，技术才是根本解。",
                "color": "#FF6B6B",
                "role": "guest",
            },
            {
                "name": "沈法学家",
                "profession": "法律顾问",
                "title": "交通法规专家",
                "stance": "认为法律必须为自动驾驶事故的责任归属提供清晰框架，责任应当由制造商、算法开发者和监管机构共同承担。",
                "color": "#4ECDC4",
                "role": "guest",
            },
            {
                "name": "吴哲学",
                "profession": "伦理学家",
                "title": "北京大学哲学系教授",
                "stance": "质疑功利主义算法在生命价值衡量上的合法性，主张任何生命都不应被量化为可比较的数字。",
                "color": "#FFD93D",
                "role": "guest",
            },
            {
                "name": "马思思",
                "profession": "保险精算师",
                "title": "车险产品总监",
                "stance": "从风险分摊角度提出'无过错保险'模型，认为社会应通过保险机制集体承担自动驾驶的技术风险。",
                "color": "#45B7D1",
                "role": "guest",
            },
            {
                "name": "陈媒体",
                "profession": "科技记者",
                "title": "知名汽车媒体人",
                "stance": "关注公众认知和舆论——公众对自动驾驶的恐惧很大程度上源于媒体的选择性报道，需要更透明的信息披露。",
                "color": "#C44DFF",
                "role": "guest",
            },
        ],
    },
    # ── 样例 3: 远程办公 ──────────────────────────────────────────
    {
        "topic": "远程办公是未来还是泡沫",
        "expert_count": 4,
        "max_rounds": 3,
        "guests": [
            {
                "name": "黄一鸣",
                "profession": "商业评论主编",
                "title": "组织管理专栏作家",
                "stance": "中立主持，引导各方从生产力、组织文化、员工福祉等维度剖析远程办公的利弊。",
                "color": "#4A90D9",
                "role": "host",
            },
            {
                "name": "孙远程",
                "profession": "远程办公倡导者",
                "title": "RemoteWork 中国社区发起人",
                "stance": "坚信远程办公是信息时代的必然趋势，能打破地域限制、提升员工幸福感、降低企业运营成本。",
                "color": "#FF6B6B",
                "role": "guest",
            },
            {
                "name": "宋传统",
                "profession": "企业管理者",
                "title": "制造业集团 HRVP",
                "stance": "认为远程办公严重影响团队凝聚力和创新活力——'你无法远程建立真正的信任和默契'，适合部分岗位但非普适方案。",
                "color": "#4ECDC4",
                "role": "guest",
            },
            {
                "name": "苏心理",
                "profession": "组织心理学博士",
                "title": "员工福祉研究员",
                "stance": "数据驱动——远程办公对心理健康的影响因人而异，关键在于'自主权'而非'地点'，混合办公可能是最优解。",
                "color": "#FFD93D",
                "role": "guest",
            },
            {
                "name": "钱地产",
                "profession": "商业地产分析师",
                "title": "国际地产咨询总监",
                "stance": "从商业地产数据出发，远程办公已导致全球写字楼空置率飙升，将深刻重塑城市空间格局。",
                "color": "#45B7D1",
                "role": "guest",
            },
        ],
    },
    # ── 样例 4: 基因编辑 ──────────────────────────────────────────
    {
        "topic": "基因编辑技术应不应该用于人类增强",
        "expert_count": 5,
        "max_rounds": 4,
        "guests": [
            {
                "name": "钟生科",
                "profession": "生命科学评论员",
                "title": "NSR 期刊特邀撰稿人",
                "stance": "中立主持，以严谨的科学态度引导讨论，确保各方基于事实而非情绪发表观点。",
                "color": "#4A90D9",
                "role": "host",
            },
            {
                "name": "魏基因",
                "profession": "遗传学教授",
                "title": "CRISPR 技术研究组负责人",
                "stance": "技术乐观派——基因编辑是人类战胜遗传病的最有力工具，从治疗到增强是技术发展的自然延伸。",
                "color": "#FF6B6B",
                "role": "guest",
            },
            {
                "name": "江伦理",
                "profession": "生命伦理学家",
                "title": "卫健委伦理委员会委员",
                "stance": "坚决反对基因增强——这将创造'基因阶级社会'，富裕阶层通过基因编辑获取先天优势，彻底摧毁社会公平。",
                "color": "#4ECDC4",
                "role": "guest",
            },
            {
                "name": "欧医生",
                "profession": "妇产科主任医师",
                "title": "产前诊断中心主任",
                "stance": "区分治疗与增强——治疗性编辑（如预防遗传病）应被允许，但非医学目的的增强编辑必须严格禁止。",
                "color": "#FFD93D",
                "role": "guest",
            },
            {
                "name": "韩未来",
                "profession": "未来学家",
                "title": "科技趋势预测顾问",
                "stance": "认为伦理讨论无法阻止技术发展——一旦技术成熟，'基因黑市'必然出现，与其禁止不如建立全球监管框架。",
                "color": "#45B7D1",
                "role": "guest",
            },
            {
                "name": "郑法规",
                "profession": "国际法专家",
                "title": "生物安全法起草组成员",
                "stance": "强调全球治理——基因编辑的后果跨代跨国界，需要类似《核不扩散条约》的国际法律框架来约束。",
                "color": "#C44DFF",
                "role": "guest",
            },
        ],
    },
    # ── 样例 5: 数字货币 ──────────────────────────────────────────
    {
        "topic": "央行数字货币会取代现金吗",
        "expert_count": 4,
        "max_rounds": 3,
        "guests": [
            {
                "name": "林宏观",
                "profession": "财经节目主持人",
                "title": "前央媒首席财经记者",
                "stance": "中立主持，以普通民众关心的视角切入，让专业讨论变得通俗易懂。",
                "color": "#4A90D9",
                "role": "host",
            },
            {
                "name": "周央行",
                "profession": "金融监管研究员",
                "title": "央行数字货币研究所高级研究员",
                "stance": "认为数字人民币是货币形态的自然进化，将提升支付效率、降低铸币成本、增强反洗钱能力。",
                "color": "#FF6B6B",
                "role": "guest",
            },
            {
                "name": "李隐私",
                "profession": "隐私保护律师",
                "title": "数字权利倡导者",
                "stance": "警告数字货币的可追踪性将彻底消灭金融隐私——每一笔交易都可能被监控，这是对公民自由的巨大威胁。",
                "color": "#4ECDC4",
                "role": "guest",
            },
            {
                "name": "吴加密",
                "profession": "区块链技术专家",
                "title": "去中心化金融协议创始人",
                "stance": "主张央行数字货币与去中心化加密货币应共存——前者用于日常支付，后者保护金融自由。",
                "color": "#FFD93D",
                "role": "guest",
            },
            {
                "name": "冯银行",
                "profession": "商业银行行长",
                "title": "零售银行数字化转型负责人",
                "stance": "关注对商业银行的冲击——如果民众直接将存款转为数字人民币，银行的信贷创造能力将受到严重削弱。",
                "color": "#45B7D1",
                "role": "guest",
            },
        ],
    },
    # ── 样例 6: 教育变革 ──────────────────────────────────────────
    {
        "topic": "AI 时代还需要传统教育吗",
        "expert_count": 3,
        "max_rounds": 3,
        "guests": [
            {
                "name": "王教育",
                "profession": "教育评论家",
                "title": "中国教育报专栏主编",
                "stance": "中立主持，从教育本质出发，引导嘉宾思考'什么是 AI 无法取代的教育价值'。",
                "color": "#4A90D9",
                "role": "host",
            },
            {
                "name": "张创新",
                "profession": "教育科技创业者",
                "title": "AI 自适应学习平台 CEO",
                "stance": "坚信 AI 个性化教学将颠覆传统'一刀切'课堂——每个学生都能拥有 AI 导师，教育将从'批量生产'转向'精雕细琢'。",
                "color": "#FF6B6B",
                "role": "guest",
            },
            {
                "name": "刘传统",
                "profession": "资深教师",
                "title": "全国优秀教师、特级教师",
                "stance": "教育不只是知识传递，更是人格塑造——老师的一句话、一个眼神、一次鼓励，是 AI 永远无法替代的。",
                "color": "#4ECDC4",
                "role": "guest",
            },
            {
                "name": "陈研究",
                "profession": "教育经济学家",
                "title": "劳动经济学研究员",
                "stance": "用数据说话——AI 时代最需要的不是知识储备，而是批判性思维、创造力和协作能力，这些恰恰是应试教育的短板。",
                "color": "#FFD93D",
                "role": "guest",
            },
        ],
    },
    # ── 样例 7: 太空探索 ──────────────────────────────────────────
    {
        "topic": "人类应该优先探索太空还是解决地球问题",
        "expert_count": 4,
        "max_rounds": 3,
        "guests": [
            {
                "name": "宇探索",
                "profession": "科普作家",
                "title": "天文科普畅销书作者",
                "stance": "中立主持，对宇宙探索和地球可持续发展都怀有深厚兴趣，引导辩证看待'仰望星空'与'脚踏实地'的关系。",
                "color": "#4A90D9",
                "role": "host",
            },
            {
                "name": "陆航天",
                "profession": "航天工程师",
                "title": "载人航天任务设计师",
                "stance": "太空探索是人类文明存续的终极保险——地球面临小行星撞击、气候灾难等灭绝风险，星际移民是物种生存的必然选择。",
                "color": "#FF6B6B",
                "role": "guest",
            },
            {
                "name": "绿地球",
                "profession": "气候变化活动家",
                "title": "环保 NGO 创始人",
                "stance": "认为巨额太空预算是对地球危机的逃避——当数亿人还缺乏清洁饮用水时，'火星梦'是一种道德上的傲慢。",
                "color": "#4ECDC4",
                "role": "guest",
            },
            {
                "name": "罗技术",
                "profession": "技术转移专家",
                "title": "航天技术民用转化顾问",
                "stance": "不认可'非此即彼'的二元对立——太空探索催生的技术（卫星通信、气象预报、GPS）已经在解决地球问题，投资太空就是投资地球。",
                "color": "#FFD93D",
                "role": "guest",
            },
            {
                "name": "宁经济",
                "profession": "太空经济学家",
                "title": "商业航天咨询分析师",
                "stance": "太空产业的 ROI 远超想象——商业航天正在从'成本中心'转变为'利润中心'，太空采矿可能成为万亿美元产业。",
                "color": "#45B7D1",
                "role": "guest",
            },
        ],
    },
]


def run_seed(session):
    """将样例数据写入数据库。

    Args:
        session: SQLAlchemy Session 对象

    Returns:
        int: 导入的讨论数量
    """
    from app.models import Discussion, Guest

    count = 0
    for data in SEED_DISCUSSIONS:
        # 创建讨论
        disc = Discussion(
            topic=data["topic"],
            status="pending",
            expert_count=data["expert_count"],
            max_rounds=data["max_rounds"],
        )
        session.add(disc)
        session.flush()  # 获取 discussion.id

        # 创建嘉宾
        for guest_data in data["guests"]:
            guest = Guest(
                discussion_id=disc.id,
                name=guest_data["name"],
                profession=guest_data["profession"],
                title=guest_data["title"],
                stance=guest_data["stance"],
                color=guest_data["color"],
                role=guest_data["role"],
                agent_state="ready",
            )
            session.add(guest)

            # 如果是主持人，回填 host_id
            if guest_data["role"] == "host":
                session.flush()
                disc.host_id = guest.id

        count += 1

    session.commit()
    return count


# ── 命令行入口 ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    from app.database import SessionLocal

    print("🎯 AI Panel Studio — 样例数据导入")
    print(f"   共 {len(SEED_DISCUSSIONS)} 组预设讨论\n")

    session = SessionLocal()
    try:
        n = run_seed(session)
        print(f"✅ 成功导入 {n} 条样例讨论")
        print(f"   (每条讨论包含 1 位主持人 + N 位专家)")

        # 显示导入的话题
        for i, data in enumerate(SEED_DISCUSSIONS, 1):
            expert_count = data["expert_count"]
            print(f"   {i}. {data['topic']} (1 主持 + {expert_count} 专家)")

    except Exception as e:
        session.rollback()
        print(f"❌ 导入失败: {e}")
        sys.exit(1)
    finally:
        session.close()

    print("\n✨ 样例数据导入完成。可启动后端查看讨论列表。")
