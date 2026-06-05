"""安全护栏：高风险问题拒答。"""

HIGH_RISK_KEYWORDS = [
    "用药",
    "药物",
    "吃药",
    "剂量",
    "服用",
    "处方",
    "抗精神",
    "利培酮",
    "急症",
    "抽搐",
    "惊厥",
    "自残",
    "自杀",
    "窒息",
    "昏迷",
    "确诊",
    "是不是自闭症",
    "是不是孤独症",
    "能不能治好",
    "能治愈",
]

DISCLAIMER = "本系统为信息参考工具，不替代专业诊疗。"


def check_high_risk(question: str) -> str | None:
    for kw in HIGH_RISK_KEYWORDS:
        if kw in question:
            return kw
    return None


def refused_response(risk_word: str) -> dict:
    return {
        "refused": True,
        "riskWord": risk_word,
        "answer": (
            f"您的问题涉及「{risk_word}」相关的高风险内容（用药 / 急症 / 确诊等）。"
            "本系统不提供此类结论，请尽快带孩子到正规医疗机构，"
            "由专业医师 / 治疗师当面评估处理。"
        ),
        "disclaimer": DISCLAIMER,
    }
