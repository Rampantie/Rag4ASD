// 个案咨询的模拟数据层（路线 A：前端先行）。
// 对应 docs/页面与交互设计.md 页面③ 的两条交互：①上传报告→提炼画像 ②提问→带出处建议。
// 接真后端时新建 consult.js（真实 /api 客户端，函数签名保持一致），切换 import 即可。

const delay = (ms) => new Promise((r) => setTimeout(r, ms))

export const MODELS = ['DeepSeek-V3', '智谱 GLM-4', 'Qwen-Max']

// 高风险关键词 → 触发拒答转介（安全护栏，见 CLAUDE.md 第一约束）
const HIGH_RISK = [
  '用药', '药物', '吃药', '剂量', '服用', '处方', '抗精神', '利培酮',
  '急症', '抽搐', '惊厥', '自残', '自杀', '窒息', '昏迷',
  '确诊', '是不是自闭症', '是不是孤独症', '能不能治好', '能治愈',
]

function hitHighRisk(q) {
  return HIGH_RISK.find((k) => q.includes(k))
}

// POST /api/case/profile —— 上传成长报告 → 提炼个案画像（报告不入公共库）
// 演示：不做真实解析，返回一份可编辑的示例画像，供用户在界面上修正。
export async function extractProfile(file, onProgress) {
  onProgress?.({ stage: '抽取', detail: `解析 ${file.name}` })
  await delay(500)
  onProgress?.({ stage: '提炼', detail: '提取年龄 / 核心表现 / 既往评估' })
  await delay(600)
  return {
    sourceName: file.name,
    age: '3 岁 6 个月',
    coreSymptoms: ['少有眼神对视', '无主动语言', '呼名反应弱', '重复摆放玩具'],
    assessments: ['ABC 量表偏高', 'M-CHAT 阳性'],
    note: '（演示数据，请按孩子真实情况修改后再提问）',
  }
}

function buildProfileText(p) {
  if (!p) return ''
  return `年龄：${p.age}；核心表现：${(p.coreSymptoms || []).join('、')}；既往评估：${(p.assessments || []).join('、')}`
}

// POST /api/case/ask —— 提问 → 安全护栏 → 检索 → 生成带出处的结构化建议
export async function askQuestion({ question, profile, config }, onProgress) {
  // 1. 安全护栏前置校验
  onProgress?.({ stage: '安全护栏', detail: '校验问题风险等级' })
  await delay(450)
  const risk = hitHighRisk(question)
  if (risk) {
    return {
      refused: true,
      riskWord: risk,
      answer:
        `您的问题涉及「${risk}」相关的高风险内容（用药 / 急症 / 确诊等）。` +
        `本系统不提供此类结论，请尽快带孩子到正规医疗机构，由专业医师 / 治疗师当面评估处理。`,
      disclaimer: '本系统为信息参考工具，不替代专业诊疗。',
    }
  }

  // 2. 检索文献 Top-K（演示：返回示例片段）
  onProgress?.({ stage: '检索', detail: `从文献库召回 Top-${config.topK} 相关片段` })
  await delay(700)

  // 3. 拼装 Prompt + LLM 生成
  onProgress?.({ stage: '生成', detail: `${config.model} 基于文献组织建议` })
  await delay(900)

  const citations = [
    { id: 1, source: '儿童孤独症诊疗康复指南.pdf', loc: '第 4 章 · 早期干预', snippet: '对于核心症状为社交沟通缺陷的低龄儿童，应尽早启动以共同注意、模仿、轮流为目标的结构化干预，每周干预强度建议不低于 20 小时。' },
    { id: 2, source: 'ASD早期行为干预循证综述.pdf', loc: 'p.12', snippet: '自然情境教学（NDBI）将干预嵌入日常游戏与照护，强调跟随儿童兴趣发起互动，对提升主动沟通意愿证据等级较高。' },
    { id: 3, source: '家庭参与式干预手册.docx', loc: '第 2 节', snippet: '家长可在进食、洗漱等日常环节创造沟通机会，使用夸张表情与简短语言示范，配合等待与提示逐步建立眼神对视与回应。' },
  ]

  return {
    refused: false,
    profileEcho: buildProfileText(profile),
    suggestions: [
      { text: '尽早开始高强度、结构化的早期干预，优先以共同注意、模仿、轮流等社交沟通基础能力为目标。', refs: [1] },
      { text: '采用自然情境教学（NDBI），把训练融入日常游戏，跟随孩子兴趣发起互动，提升主动沟通意愿。', refs: [2] },
      { text: '家庭可在进食、洗漱等日常环节制造沟通机会，用夸张表情与简短语言示范，配合等待和提示建立眼神对视与回应。', refs: [2, 3] },
    ],
    cautions: [
      '干预需循序渐进，关注孩子情绪与配合度，避免强迫造成抵触。',
      '不同孩子个体差异大，本建议为方向性参考，具体方案应由专业治疗师制定。',
    ],
    whenToSeeDoctor: [
      '若伴随明显发育倒退、自伤、严重睡眠或进食问题，应尽快就医。',
      '建议尽早到具备资质的机构完成系统评估与诊断。',
    ],
    citations,
    disclaimer: '以上为基于所给文献的信息参考，不构成医疗诊断或治疗方案，不替代专业医师 / 治疗师 / 特教评估。',
  }
}
