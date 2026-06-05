"""咨询链路 Prompt 模板。"""

SYSTEM_PROMPT = """你是孤独症（ASD）早期干预的循证信息助手，基于用户提供的文献片段与（可选）网络参考作答。

硬性规则：
1. 你是辅助信息参考工具，不是诊断工具，不替代专业医师/治疗师/特教评估。
2. 文献片段编号 [1][2] 是干预建议的主要依据；有文献时每条建议应尽量带 refs 引用文献编号。
3. 网络参考编号 [W1][W2] 仅作补充背景，可带 webRefs，不得替代文献或当作权威依据。
4. 若文献不足以回答，仍须在 suggestions 中返回说明；无文献仅有网络时，只能给方向性补充，须在 cautions 中声明「未命中本地权威文献」。
5. 不要给出用药剂量、确诊结论或急症处理方案。
6. 若存在【对话历史】，当前问题是追问；请结合历史语境作答，但文献引用编号 refs 仅对应本次【文献片段】中的 [1][2]。

请严格输出 JSON，不要包含 markdown 代码块或其它文字。JSON 结构：
{
  "suggestions": [{"text": "建议内容", "refs": [1], "webRefs": ["W1"]}],
  "cautions": ["注意事项1"],
  "whenToSeeDoctor": ["何时就医1"],
  "disclaimer": "免责声明全文"
}

要求：
- suggestions 至少 1 条；有文献时 refs 应尽量非空；网络补充用 webRefs（如 "W1"）。
- cautions、whenToSeeDoctor 各至少 1 条。
- disclaimer 必须说明本系统仅供参考、不构成医疗诊断。"""


def build_user_prompt(
    *,
    question: str,
    profile_text: str,
    chunks: list[dict],
    web_hits: list[dict] | None = None,
    history: list[dict] | None = None,
) -> str:
    lines = ["【个案画像】", profile_text or "（未提供）", ""]

    if history:
        lines.append("【对话历史（理解追问语境；文献编号以本次片段为准）】")
        for turn in history:
            lines.append(f"用户：{turn.get('question', '')}")
            summary = (turn.get("answerSummary") or turn.get("answer_summary") or "").strip()
            if summary:
                lines.append(f"助手：{summary}")
            lines.append("")
    else:
        lines.append("【对话历史】")
        lines.append("（首轮提问，无历史）")
        lines.append("")

    lines.extend(["【文献片段】"])
    if not chunks:
        lines.append("（知识库暂无相关文献片段）")
    else:
        for i, c in enumerate(chunks, start=1):
            loc = c.get("loc") or "未知位置"
            lines.append(f"[{i}] 来源：{c['source']} · {loc}")
            lines.append(c["snippet"])
            lines.append("")

    lines.append("")
    lines.append("【网络参考（补充，非用户上传权威文献）】")
    if not web_hits:
        lines.append("（未启用或未检索到网络参考）")
    else:
        for w in web_hits:
            lines.append(f"[{w['id']}] {w.get('title', '')} · {w.get('url', '')}")
            lines.append(w.get("snippet", ""))
            lines.append("")

    lines.extend(["【当前问题】", question])
    return "\n".join(lines)
