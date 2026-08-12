"""Mock LLM 响应数据 — 用于 E2E 测试，零真实 Token 消耗。

激活方式：设置环境变量 MOCK_LLM=true

覆盖 LLMClient 的三个核心方法：
1. generate_guests → 返回 1 host + N expert 嘉宾数据
2. generate_speech → 返回话题特定的 40-80 字中文发言
3. chat_completion → 返回共识/分歧 JSON（话题相关，格式匹配 orchestrator 预期）
"""

import json
import random
import re
import hashlib


# ══════════════════════════════════════════════════════════════════════
# 嘉宾生成 Mock
# ══════════════════════════════════════════════════════════════════════

HOST_POOL = [
    {
        "name": "张明",
        "profession": "科技媒体主编",
        "title": "资深科技评论员",
        "stance": "作为中立主持人，致力于引导各方深入探讨，不偏袒任何一方观点",
        "color": "#4A90D9",
        "role": "host",
    },
    {
        "name": "陈静",
        "profession": "学术期刊编辑",
        "title": "科学与技术研究主编",
        "stance": "保持中立客观，引导不同背景的专家进行理性、有深度的对话",
        "color": "#5B8EC9",
        "role": "host",
    },
]

EXPERT_POSITIVE_POOL = [
    {
        "name": "李伟",
        "profession": "AI 研究员",
        "title": "机器学习博士",
        "stance": "坚信 AI 将大幅提升人类生产力，在创造性任务上也能与人类协同，最终造福全社会",
        "color": "#FF6B6B",
        "role": "guest",
    },
    {
        "name": "刘洋",
        "profession": "科技企业家",
        "title": "AI 创业公司 CEO",
        "stance": "从商业角度看好 AI 的发展前景，认为 AI 将创造全新的产业和就业机会",
        "color": "#FF8A5C",
        "role": "guest",
    },
]

EXPERT_SKEPTICAL_POOL = [
    {
        "name": "王芳",
        "profession": "社会学家",
        "title": "人文与科技研究中心主任",
        "stance": "对 AI 的快速发展持审慎态度，关注其对就业结构、社会公平和人类自主性的潜在冲击",
        "color": "#4ECDC4",
        "role": "guest",
    },
    {
        "name": "黄磊",
        "profession": "伦理学家",
        "title": "科技伦理研究所研究员",
        "stance": "强调 AI 发展需以人类价值观为底线，呼吁加强AI伦理规范和监管框架建设",
        "color": "#96CEB4",
        "role": "guest",
    },
]

EXPERT_PRACTICAL_POOL = [
    {
        "name": "赵强",
        "profession": "软件工程师",
        "title": "资深全栈开发者",
        "stance": "认为 AI 是强大的辅助工具，关键在于人类如何合理利用它来增强而非替代自身能力",
        "color": "#45B7D1",
        "role": "guest",
    },
    {
        "name": "周敏",
        "profession": "教育工作者",
        "title": "教育技术专家",
        "stance": "关注 AI 在教育领域的应用，主张培养学生的人机协作能力和批判性思维",
        "color": "#DDA0DD",
        "role": "guest",
    },
]

EXPERT_NEUTRAL_POOL = [
    {
        "name": "吴昊",
        "profession": "数据科学家",
        "title": "大数据分析专家",
        "stance": "基于数据分析客观评估 AI 的影响，既不盲目乐观也不过度恐慌",
        "color": "#FFEAA7",
        "role": "guest",
    },
    {
        "name": "孙丽",
        "profession": "经济学家",
        "title": "数字经济研究所高级研究员",
        "stance": "从经济学角度分析 AI 对产业结构和劳动力市场的长期影响",
        "color": "#F7DC6F",
        "role": "guest",
    },
]

EXPERT_POOLS = [
    EXPERT_POSITIVE_POOL,
    EXPERT_SKEPTICAL_POOL,
    EXPERT_PRACTICAL_POOL,
    EXPERT_NEUTRAL_POOL,
]


def _make_guest_id(name: str, index: int) -> str:
    raw = f"{name}-{index}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def mock_generate_guests(topic: str, expert_count: int) -> list[dict]:
    """Mock 嘉宾生成：返回 1 host + expert_count experts。"""
    host = dict(HOST_POOL[hash(topic) % len(HOST_POOL)])

    experts = []
    for i in range(expert_count):
        pool = EXPERT_POOLS[i % len(EXPERT_POOLS)]
        expert = dict(pool[i // len(EXPERT_POOLS) % len(pool)])
        if topic not in expert["stance"]:
            expert["stance"] = f"关于「{topic}」的立场：" + expert["stance"]
        experts.append(expert)

    return [host] + experts


# ══════════════════════════════════════════════════════════════════════
# 话题提取
# ══════════════════════════════════════════════════════════════════════

def _extract_topic_from_purpose(speech_purpose: str) -> str:
    """从 speech_purpose 中提取讨论话题。

    orchestrator 传入的 purpose 格式示例：
        "第 1 轮发言。请基于讨论话题「量子计算的商业化前景」和之前的讨论内容..."
        "作为主持人，请你围绕「碳中和的技术路线选择」做开场白..."
    """
    # 匹配中文书名号中的话题
    m = re.search(r'「(.+?)」', speech_purpose)
    if m:
        return m.group(1)
    # 匹配 "围绕" 后面的内容
    m = re.search(r'围绕(.+?)(?:做|。|，|$)', speech_purpose)
    if m:
        return m.group(1).strip()
    return None


def _extract_topic_from_context(discussion_context: list[dict]) -> str | None:
    """从讨论上下文中提取话题（回退方案）。"""
    for msg in discussion_context:
        content = msg.get("content", "")
        m = re.search(r'「(.+?)」', content)
        if m:
            return m.group(1)
    return None


def _extract_guest_names(discussion_context: list[dict]) -> list[str]:
    """从讨论上下文中提取所有嘉宾姓名。"""
    names = []
    seen = set()
    for msg in discussion_context:
        content = msg.get("content", "")
        for m in re.finditer(r'【(.+?)】', content):
            name = m.group(1)
            if name not in seen:
                names.append(name)
                seen.add(name)
    return names


# ══════════════════════════════════════════════════════════════════════
# 发言生成 Mock — 话题特定 + 立场感知
# ══════════════════════════════════════════════════════════════════════

# 每种发言类别有多组模板，每组包含多个变体。
# {topic} = 话题, {name} = 嘉宾名

_OPENING_TEMPLATES = [
    # 模板组 1：直接点出话题核心
    [
        "感谢各位专家今天参与讨论。{topic}是当下备受关注的议题，它涉及技术发展、社会影响和人类未来等多个维度。让我们从各自的专业视角出发，深入探讨。",
        "欢迎各位来到今天的圆桌讨论。{topic}不仅是一个理论问题，更关乎我们每个人的生活和未来。我期待听到各位的真知灼见。",
    ],
    # 模板组 2：抛出开放性问题
    [
        "今天我们要讨论的是{topic}。这个话题看似简单，但背后涉及的复杂性远超表面。各位专家，你们怎么看这个问题最关键的切入点是什么？",
        "很高兴能主持这场关于{topic}的讨论。这个话题近年来引发了大量争议和思考，让我们先听听各位的初步判断。",
    ],
]

_STATEMENT_TEMPLATES = [
    # 乐观/积极类
    [
        "关于{topic}，我想从积极的角度来看。技术的发展史表明，每一次重大突破最终都带来了生产力的飞跃。关键在于我们如何引导和利用这些进步，让更多人受益。",
        "我认为{topic}代表了未来的发展方向。从已有的实践案例来看，它能显著提升效率、降低成本，而且应用前景远比大多数人预期的更广阔。",
        "我对{topic}持乐观态度。我之所以这么判断，是因为我们已经看到了在几个关键指标上的实质性突破，而不仅仅是理论上的可能性。",
        "从实际数据来看，{topic}带来的改变已经超出了许多人的想象。这不仅仅是渐进式的改进，而是一次范式级别的跃迁。",
    ],
    # 审慎/保守类
    [
        "关于{topic}，我想提出一些审慎的思考。过于乐观的预期可能忽视了一些深层次的风险——包括公平性、安全性和长期社会影响。我们需要更全面的评估。",
        "我对{topic}有一些保留意见。虽然短期内效果显著，但我们需要认真思考：谁从中受益？谁可能被排除在外？这些问题不是技术的副产品，而是核心考量。",
        "在讨论{topic}时，我们不能只看技术指标。从社会层面来看，过快推进可能带来不可逆的后果。我主张在有充分风险评估的前提下稳步推进。",
        "我很理解大家对{topic}的热情，但历史上有太多技术乐观主义最终落空的例子。我认为需要在实践中逐步验证，而不是一开始就全面铺开。",
    ],
    # 务实/建设类
    [
        "在我看来，{topic}的关键不在于'要不要做'，而在于'怎么做好'。我们需要平衡技术创新和社会责任，找到一个可持续、可落地的路径。",
        "讨论{topic}时，我想强调的是实践层面的问题。任何好的理念都需要经受现实世界的检验。我建议从具体场景出发，逐步迭代优化。",
        "关于{topic}，我的核心判断是：技术本身是中性的，关键在于使用它的人以及我们设置的规则。与其争论对错，不如聚焦在如何构建好的机制上。",
        "从落地角度看，{topic}面临的最大挑战不是技术瓶颈，而是组织变革和人才培养。我们在推进技术的同时，必须配套做好这些基础工作。",
    ],
]

_RESPONSE_TEMPLATES = [
    [
        "感谢你的分享。关于{topic}，我想补充一个不同的视角：我们还需要考虑区域差异和群体差异。一刀切的分析往往掩盖了重要的细节。",
        "你提到了一个很好的观点。不过，我想从另一个维度来回应：{topic}的时间尺度也很关键。短期影响和长期趋势有时是相反的，需要区分看待。",
    ],
    [
        "我理解你的关切，但我认为情况可能没有那么极端。在{topic}这个问题上，我们既不需要过度恐慌，也不应该盲目乐观。中间道路可能更明智。",
        "你刚才说的确实是一个重要方面，但我认为{topic}还有另一个不容忽视的维度——经济激励。市场力量和商业逻辑在其中扮演的角色往往被低估。",
    ],
]

_FOLLOWUP_TEMPLATES = [
    [
        "你刚才提到了{topic}中一个非常关键的点——能否请你进一步展开？特别是在实际应用层面，你认为有哪些具体的场景最有可能率先突破？",
        "你关于{topic}的分析很有启发性。我想追问一个具体问题：在你看来，未来三到五年这个领域会发生什么实质性变化？",
    ],
]

_SUMMARY_TEMPLATES = [
    [
        "本轮的讨论非常精彩。关于{topic}，我听到了几种不同的声音：有技术驱动的乐观派，有社会影响优先的审慎派，也有强调落地实践的务实派。这些多元视角正是理性对话的价值所在。",
        "总结这一轮，各位围绕{topic}从不同维度做了深入分析。一个值得注意的共识是：技术本身不是目的，服务于人才是。但在如何服务的路径上，大家的分歧依然很大，这也是下一轮需要深入的方向。",
    ],
    [
        "本轮讨论中，{topic}的几个核心命题逐渐清晰：效率与公平的平衡、短期与长期的权衡、技术与制度的协同。各位专家的观点在'是什么'上趋同，在'怎么做'上分化——这是非常健康的讨论状态。",
        "这一轮让我印象最深的是，{topic}不是一个单一维度能回答的问题。有人提供了数据，有人提供了伦理框架，有人提供了实践案例。将这些拼图放在一起，我们离真相更近了一步。",
    ],
]


def _pick_template(template_group: list[list[str]], guest_name: str, topic: str,
                   stance_hint: str) -> str:
    """从模板组中选取并填充一个模板。

    根据 stance 关键词选择最匹配的模板子组，然后随机选取一个变体。
    """
    stance_lower = stance_hint.lower()

    # 根据 stance 选择模板子组
    if any(kw in stance_lower for kw in ["乐观", "积极", "提升", "赋能", "发展", "机遇", "看好"]):
        group_idx = 0  # 乐观组
    elif any(kw in stance_lower for kw in ["审慎", "保守", "风险", "担心", "担忧", "谨慎", "质疑"]):
        group_idx = min(1, len(template_group) - 1)  # 审慎组
    elif any(kw in stance_lower for kw in ["务实", "实践", "工具", "辅助", "平衡", "数据"]):
        group_idx = min(2, len(template_group) - 1)  # 务实组
    else:
        group_idx = random.randint(0, len(template_group) - 1)

    templates = template_group[group_idx]
    template = random.choice(templates)
    return template.format(topic=topic, name=guest_name)


def mock_generate_speech(
    guest_name: str,
    guest_stance: str,
    role: str,
    discussion_context: list[dict],
    speech_purpose: str,
) -> str:
    """Mock 发言生成：根据话题和嘉宾立场生成具体的 40-80 字中文发言。

    流程：
    1. 从 speech_purpose 中提取话题（orchestrator 已把话题写入 purpose）
    2. 根据 purpose 判断发言类别（开场/观点/回应/追问/总结）
    3. 根据嘉宾立场选择匹配的模板子组
    4. 填充话题和姓名，确保内容具体而非泛泛而谈
    """
    # ── 提取话题 ──
    topic = _extract_topic_from_purpose(speech_purpose)
    if not topic:
        topic = _extract_topic_from_context(discussion_context)
    if not topic:
        topic = "这个议题"

    # ── 判断发言类别 ──
    purpose_text = speech_purpose.lower()

    if any(kw in speech_purpose for kw in ["开场", "欢迎", "开始"]):
        category = "开场"
        speech = _pick_template(_OPENING_TEMPLATES, guest_name, topic, guest_stance)
    elif any(kw in speech_purpose for kw in ["回应", "反驳", "深入辩论"]):
        category = "回应"
        speech = _pick_template(_RESPONSE_TEMPLATES, guest_name, topic, guest_stance)
    elif any(kw in speech_purpose for kw in ["追问", "引导", "展开"]):
        category = "追问"
        speech = _pick_template(_FOLLOWUP_TEMPLATES, guest_name, topic, guest_stance)
    elif any(kw in speech_purpose for kw in ["总结", "小结", "提炼"]):
        category = "总结"
        speech = _pick_template(_SUMMARY_TEMPLATES, guest_name, topic, guest_stance)
    else:
        category = "发表观点"
        speech = _pick_template(_STATEMENT_TEMPLATES, guest_name, topic, guest_stance)

    # ── 确保长度合理（40-80 字） ──
    if len(speech) < 35:
        speech += f"这是我对{topic}的核心看法，希望能抛砖引玉，听到更多不同意见。"
    if len(speech) > 90:
        speech = speech[:88] + "…"

    return speech


# ══════════════════════════════════════════════════════════════════════
# 共识/分歧提炼 Mock — 话题相关动态生成
# ══════════════════════════════════════════════════════════════════════

def _generate_topic_consensus(topic: str, guest_names: list[str]) -> list[dict]:
    """基于话题动态生成共识条目。"""
    if not guest_names:
        guest_names = ["与会专家"]

    # 为每个话题生成 1-2 条共识，内容直接提及话题
    consensus_pool = [
        {
            "content": f"在{topic}领域，技术进步与制度建设需要同步推进，单纯追求技术突破而忽视配套规范将带来系统性风险",
            "supporter_names": random.sample(guest_names, min(3, len(guest_names))),
        },
        {
            "content": f"{topic}的发展应以提升人类福祉为终极目标，而非仅仅追求效率或利润最大化",
            "supporter_names": random.sample(guest_names, min(3, len(guest_names))),
        },
        {
            "content": f"{topic}不是单一技术问题，而是涉及经济、社会、伦理等多维度的复杂议题，需要跨学科协作",
            "supporter_names": random.sample(guest_names, min(3, len(guest_names))),
        },
        {
            "content": f"在{topic}的推进过程中，数据透明和公众参与至关重要，封闭决策容易导致信任危机和方向偏差",
            "supporter_names": random.sample(guest_names, min(3, len(guest_names))),
        },
        {
            "content": f"当前{topic}正处于关键转折期，未来五年内的决策和布局将深刻影响长期走向",
            "supporter_names": random.sample(guest_names, min(3, len(guest_names))),
        },
        {
            "content": f"无论对{topic}持何种态度，各方均认同加强公众教育和信息透明度是当务之急",
            "supporter_names": random.sample(guest_names, min(3, len(guest_names))),
        },
    ]
    return random.sample(consensus_pool, k=random.randint(1, 2))


def _generate_topic_divergence(topic: str, guest_names: list[str]) -> list[dict]:
    """基于话题动态生成分歧条目。"""
    if len(guest_names) < 2:
        return []

    # 从嘉宾名单中构建对立配对
    n = len(guest_names)
    half = max(n // 2, 1)
    side_a = guest_names[:half]
    side_b = guest_names[half:]

    divergence_pool = [
        {
            "content": f"关于{topic}的发展速度：一派主张加速推进以抢占先机，另一派认为应审慎评估风险后再逐步展开",
            "opposing_names": _make_pairs(side_a, side_b),
        },
        {
            "content": f"关于{topic}的核心驱动力：一派认为技术创新是首要推动力，另一派强调制度完善和市场需求才是关键",
            "opposing_names": _make_pairs(side_a, side_b),
        },
        {
            "content": f"关于{topic}的受益群体：一方认为技术红利最终会惠及全社会，另一方担忧可能加剧既有不平等",
            "opposing_names": _make_pairs(side_a, side_b),
        },
        {
            "content": f"关于{topic}的评估标准：一方主张以效率和产出为核心指标，另一方坚持应将社会影响和公平性纳入首要考量",
            "opposing_names": _make_pairs(side_a, side_b),
        },
        {
            "content": f"关于{topic}的推进路径：一派倾向自上而下的顶层设计，另一派认为自下而上的市场驱动更有效",
            "opposing_names": _make_pairs(side_a, side_b),
        },
        {
            "content": f"关于{topic}的国际合作：一方强调开放共享加速全球进步，另一方担心竞争格局下技术主权和安全性问题",
            "opposing_names": _make_pairs(side_a, side_b),
        },
    ]
    return random.sample(divergence_pool, k=random.randint(1, 2))


def _make_pairs(side_a: list[str], side_b: list[str]) -> list[list[str]]:
    """从两个阵营中各取一个姓名组成对立配对。"""
    pairs = []
    for i in range(min(len(side_a), len(side_b))):
        pairs.append([side_a[i], side_b[i]])
    if not pairs and side_a and side_b:
        pairs.append([side_a[0], side_b[0]])
    return pairs


def mock_chat_completion(messages: list[dict], temperature: float = 0.8) -> str:
    """Mock chat completion：返回话题相关的共识+分歧 JSON。

    返回格式必须匹配 orchestrator._generate_summary 的预期：
    {
      "consensus_list": [
        {"content": "...", "supporter_names": ["张三", "李四"]}
      ],
      "divergence_list": [
        {"content": "...", "opposing_names": [["张三", "李四"]]}
      ]
    }

    从消息上下文中提取话题和嘉宾姓名，生成动态相关的内容，
    而非返回固定的 AI 话题模板。
    """
    # 合并所有消息内容
    context_text = " ".join(m.get("content", "") for m in messages)

    # ── 提取话题 ──
    topic = "这个议题"
    topic_match = re.search(r'「(.+?)」', context_text)
    if topic_match:
        topic = topic_match.group(1)
    else:
        # 从"可供参考的嘉宾名单"之前的文字中提取话题
        for m in messages:
            content = m.get("content", "")
            # 尝试从讨论上下文中提取
            speech_match = re.search(r'基于讨论话题(.+?)和', content)
            if speech_match:
                topic = speech_match.group(1).strip()
                break

    # ── 提取嘉宾姓名 ──
    guest_names = []
    name_match = re.search(r'可供参考的嘉宾名单：主持人 (.+?)，专家：(.+?)(?:$|\n)',
                           context_text)
    if name_match:
        host_name = name_match.group(1).strip()
        expert_str = name_match.group(2).strip()
        expert_names = [n.strip() for n in re.split(r'[、，,]', expert_str) if n.strip()]
        guest_names.append(host_name)
        guest_names.extend(expert_names)
    else:
        # 从上下文消息中提取
        guest_names = _extract_guest_names(messages)

    # ── 生成动态共识和分歧 ──
    consensus_list = _generate_topic_consensus(topic, guest_names)
    divergence_list = _generate_topic_divergence(topic, guest_names)

    result = {
        "consensus_list": consensus_list,
        "divergence_list": divergence_list,
    }

    return json.dumps(result, ensure_ascii=False)
