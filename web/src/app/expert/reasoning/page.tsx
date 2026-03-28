"use client";

const MOCK_CHAINS = [
  {
    id: "RC-001",
    agent: "林税安",
    task: "月度增值税申报 — 杭州明达科技",
    time: "2024-11-24 10:42",
    confidence: 98,
    steps: [
      { phase: "INPUT", label: "接收任务指令", detail: "用户请求查询杭州明达科技增值税申报情况", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "KG 实体检索", detail: "匹配 KnowledgeUnit + LawOrRegulation 共 12 条", confidence: 96, duration: "0.8s" },
      { phase: "REASONING", label: "规则推理", detail: "适用增值税一般纳税人 13% 税率，高新技术企业加计抵减", confidence: 94, duration: "0.3s" },
      { phase: "VALIDATION", label: "合规校验", detail: "交叉比对 3 条法规条款，无冲突", confidence: 98, duration: "0.2s" },
      { phase: "OUTPUT", label: "生成回复", detail: "输出申报状态 + 应纳税额 + 加计抵减说明", confidence: 98, duration: "1.2s" },
    ],
  },
  {
    id: "RC-002",
    agent: "赵合规",
    task: "跨境转让定价文档审查 — 华夏贸易",
    time: "2024-11-23 14:20",
    confidence: 72,
    steps: [
      { phase: "INPUT", label: "接收审查任务", detail: "审查华夏贸易进出口转让定价文档", confidence: 100, duration: "0.1s" },
      { phase: "RETRIEVAL", label: "法规库检索", detail: "匹配 OECD 转让定价指南 + 国内 42 号公告", confidence: 88, duration: "1.2s" },
      { phase: "REASONING", label: "合规性分析", detail: "发现可比交易法参数偏离行业均值 15%", confidence: 65, duration: "2.1s" },
      { phase: "ESCALATION", label: "触发人工审核", detail: "置信度低于 80% 阈值，标记为需关注", confidence: 72, duration: "0.1s" },
    ],
  },
];

export default function ReasoningPage() {
  return (
    <div style={{ height: "calc(100vh - var(--topbar-height))", background: "#0D1117", overflow: "auto" }}>
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "24px 32px" }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#C9D1D9", marginBottom: 4, fontFamily: "'SF Mono', monospace" }}>
          推理链检查器
        </h2>
        <p style={{ fontSize: 13, color: "#8B949E", marginBottom: 24 }}>
          审查 AI Agent 的推理过程，追溯每一步决策的依据和置信度
        </p>

        {MOCK_CHAINS.map((chain) => (
          <div
            key={chain.id}
            style={{
              background: "#161B22",
              borderRadius: 8,
              border: "1px solid #30363D",
              marginBottom: 16,
              overflow: "hidden",
            }}
          >
            {/* Header */}
            <div className="flex items-center justify-between" style={{ padding: "12px 16px", borderBottom: "1px solid #30363D" }}>
              <div>
                <span style={{ fontSize: 14, fontWeight: 700, color: "#C9D1D9" }}>{chain.task}</span>
                <span style={{ fontSize: 11, color: "#8B949E", marginLeft: 12 }}>{chain.agent} · {chain.time}</span>
              </div>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  padding: "4px 10px",
                  borderRadius: 4,
                  background: chain.confidence >= 90 ? "#0D3321" : chain.confidence >= 75 ? "#3D2E00" : "#3D1F1F",
                  color: chain.confidence >= 90 ? "#3FB950" : chain.confidence >= 75 ? "#D29922" : "#F85149",
                }}
              >
                {chain.confidence}%
              </span>
            </div>

            {/* Steps */}
            <div style={{ padding: "12px 16px" }}>
              {chain.steps.map((step, i) => (
                <div key={i} className="flex items-start gap-3" style={{ marginBottom: i < chain.steps.length - 1 ? 12 : 0 }}>
                  {/* Timeline dot + line */}
                  <div className="flex flex-col items-center" style={{ minWidth: 20 }}>
                    <div style={{
                      width: 10, height: 10, borderRadius: "50%",
                      background: step.confidence >= 90 ? "#3FB950" : step.confidence >= 75 ? "#D29922" : "#F85149",
                      marginTop: 4,
                    }} />
                    {i < chain.steps.length - 1 && <div style={{ width: 1, flex: 1, background: "#30363D", marginTop: 2 }} />}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-2">
                      <span style={{ fontSize: 9, fontWeight: 700, padding: "1px 6px", borderRadius: 3, background: "#21262D", color: "#8B949E", fontFamily: "'SF Mono', monospace" }}>
                        {step.phase}
                      </span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "#C9D1D9" }}>{step.label}</span>
                      <span style={{ fontSize: 10, color: "#484F58", marginLeft: "auto" }}>{step.duration}</span>
                    </div>
                    <p style={{ fontSize: 12, color: "#8B949E", margin: "4px 0 0", lineHeight: 1.5 }}>{step.detail}</p>
                  </div>

                  <span style={{ fontSize: 11, fontWeight: 600, color: step.confidence >= 90 ? "#3FB950" : step.confidence >= 75 ? "#D29922" : "#F85149", minWidth: 36, textAlign: "right" }}>
                    {step.confidence}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
