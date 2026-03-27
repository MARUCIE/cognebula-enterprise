/* Audit Workbench -- "智能审计工作台"
   Layout reference: design/stitch-export/stitch/audit_workbench/screen.png
   Audit findings list + AI agent analysis panel + flow progress */

const AUDIT_FLOW = [
  { label: "证据采集", icon: "upload", status: "done" as const, detail: "共上传 124 份原始凭证" },
  { label: "AI 智能分析", icon: "brain", status: "done" as const, detail: "全量文本及结构化处理完毕" },
  { label: "异常检测", icon: "search", status: "active" as const, detail: "当前发现 8 处潜在风险点" },
  { label: "证据核对", icon: "check", status: "pending" as const, detail: "等待异常点确认后开启" },
];

const FINDINGS = [
  {
    id: "FND-9022",
    title: "关联交易价格偏离市场公允值",
    desc: "检测到与关联方\u201C华瑞实业\u201D在11月的原材料采购价格高于市场均价 18.5%，可能涉及利益输送。",
    severity: "critical" as const,
    company: "华瑞国际贸易有限公司",
    action: "建议立即核查关联交易定价依据",
  },
  {
    id: "FND-8104",
    title: "发票日期与报销周期严重滞后",
    desc: "多张大额增值税专用发票开具日期早于业务实际发生日期 3 个月，需要进一步核实业务真实性。",
    severity: "warning" as const,
    company: "华瑞国际贸易有限公司",
    action: "核实合同与物流记录一致性",
    selected: true,
  },
  {
    id: "FND-7721",
    title: "交通补贴发放标准不一",
    desc: "技术部门部分员工差旅补贴高于公司行政手册规定 15 元/天。",
    severity: "info" as const,
    company: "华瑞国际贸易有限公司",
    action: "建议统一差旅补贴标准",
  },
  {
    id: "FND-8992",
    title: "银行对账单大额异常流出",
    desc: "尾号 8829 的银行账户在非办公时间出现 50 万元以上的单笔转账，且无匹配合同。",
    severity: "critical" as const,
    company: "华瑞实业集团",
    action: "紧急核查资金流向与审批记录",
  },
  {
    id: "FND-7689",
    title: "固定资产折旧方法变更未披露",
    desc: "2023年Q3起部分设备折旧由直线法变更为加速折旧法，未在附注中披露变更原因及影响。",
    severity: "warning" as const,
    company: "华瑞国际贸易有限公司",
    action: "补充会计政策变更披露",
  },
];

const FOOTER_STATS = [
  { label: "当前审计效率", value: "提升 420%", color: "var(--color-primary)" },
  { label: "模型准确率", value: "99.8%", color: "var(--color-secondary-dim)" },
  { label: "疑似风险总额", value: "¥ 2,840,100", color: "var(--color-danger)" },
];

export default function AuditWorkbenchPage() {
  return (
    <div>
      {/* Breadcrumb-like context */}
      <div
        className="flex items-center gap-3"
        style={{ marginBottom: "var(--space-6)", fontSize: 13 }}
      >
        <span style={{ color: "var(--color-text-tertiary)" }}>审计工作台</span>
        <span style={{ color: "var(--color-outline-variant)" }}>/</span>
        <span className="font-bold" style={{ color: "var(--color-primary)" }}>
          华瑞国际 - 2023年度Q4审计
        </span>
      </div>

      {/* Audit flow progress */}
      <section
        className="grid gap-4"
        style={{
          gridTemplateColumns: "repeat(4, 1fr)",
          marginBottom: "var(--space-8)",
        }}
      >
        {AUDIT_FLOW.map((step) => (
          <FlowStep key={step.label} step={step} />
        ))}
      </section>

      {/* Two-column: findings list + analysis panel */}
      <section
        className="grid gap-6"
        style={{
          gridTemplateColumns: "380px 1fr",
          marginBottom: "var(--space-8)",
        }}
      >
        {/* Left: Findings list */}
        <div>
          <div
            className="flex items-center justify-between"
            style={{ marginBottom: "var(--space-4)" }}
          >
            <h2
              className="font-display font-extrabold"
              style={{ fontSize: 18, color: "var(--color-primary)" }}
            >
              审计发现 ({FINDINGS.length})
            </h2>
            <button
              className="font-bold flex items-center gap-1"
              style={{ fontSize: 12, color: "var(--color-secondary-dim)" }}
            >
              <FilterIcon /> 筛选
            </button>
          </div>
          <div
            className="flex flex-col gap-3"
            style={{ maxHeight: 620, overflowY: "auto", paddingRight: "var(--space-2)" }}
          >
            {FINDINGS.map((f) => (
              <FindingItem key={f.id} finding={f} />
            ))}
          </div>
        </div>

        {/* Right: Deep analysis panel */}
        <div>
          <div
            className="flex items-center justify-between"
            style={{ marginBottom: "var(--space-4)" }}
          >
            <div className="flex items-center gap-3">
              <span
                className="ai-glow"
                style={{
                  display: "inline-block",
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--color-secondary)",
                }}
              />
              <h2
                className="font-display font-extrabold"
                style={{ fontSize: 18, color: "var(--color-primary)" }}
              >
                异常深度核查
              </h2>
            </div>
            <div className="flex gap-2">
              <button
                className="font-bold"
                style={{
                  fontSize: 12,
                  padding: "6px 14px",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--color-surface-container-low)",
                  color: "var(--color-text-secondary)",
                }}
              >
                要求 AI 重分析
              </button>
              <button
                className="font-bold"
                style={{
                  fontSize: 12,
                  padding: "6px 14px",
                  borderRadius: "var(--radius-sm)",
                  background: "linear-gradient(135deg, var(--color-secondary), #C5913E)",
                  color: "var(--color-on-primary)",
                }}
              >
                确认审计发现
              </button>
            </div>
          </div>

          {/* Analysis card */}
          <div
            style={{
              padding: "var(--space-6)",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-container-lowest)",
              boxShadow: "var(--shadow-sm)",
              position: "relative",
              minHeight: 560,
            }}
          >
            {/* AI agent header */}
            <div
              className="flex items-center gap-3"
              style={{ marginBottom: "var(--space-6)" }}
            >
              <div
                className="flex items-center justify-center shrink-0"
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: "50%",
                  background: "var(--color-primary)",
                }}
              >
                <AiSparkIcon />
              </div>
              <div>
                <h3
                  className="font-display font-bold"
                  style={{ fontSize: 14, color: "var(--color-primary)" }}
                >
                  灵阙审计 AI 助手
                </h3>
                <p style={{ fontSize: 11, color: "var(--color-text-tertiary)" }}>
                  正在深度剖析凭证：VAT-2023-0992
                </p>
              </div>
            </div>

            {/* Two-column: document scan + AI analysis */}
            <div
              className="grid gap-6"
              style={{ gridTemplateColumns: "1fr 1fr" }}
            >
              {/* Left: document scan placeholder */}
              <div>
                <span
                  style={{
                    display: "block",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "var(--color-text-tertiary)",
                    marginBottom: "var(--space-3)",
                  }}
                >
                  扫描件原件
                </span>
                <div
                  style={{
                    background: "var(--color-surface-container-low)",
                    borderRadius: "var(--radius-sm)",
                    padding: "var(--space-3)",
                    aspectRatio: "3/4",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    position: "relative",
                  }}
                >
                  <DocPlaceholderIcon />
                  {/* Highlight area */}
                  <div
                    style={{
                      position: "absolute",
                      top: "25%",
                      left: "20%",
                      width: "60%",
                      height: 36,
                      background: "color-mix(in srgb, var(--color-secondary) 10%, transparent)",
                      border: "1px dashed var(--color-secondary)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  />
                </div>
                <p
                  className="tabular-nums"
                  style={{
                    fontSize: 10,
                    color: "var(--color-text-tertiary)",
                    marginTop: "var(--space-2)",
                    fontFamily: "monospace",
                    textAlign: "left",
                  }}
                >
                  OCR 解析状态: 100% 成功 | 校验指纹: 8829-AF21-9920-XX
                </p>
              </div>

              {/* Right: AI structured analysis */}
              <div className="flex flex-col gap-4">
                <span
                  style={{
                    display: "block",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "var(--color-text-tertiary)",
                  }}
                >
                  AI 结构化解析及异常分析
                </span>

                {/* Key info extraction */}
                <div
                  style={{
                    padding: "var(--space-4)",
                    borderRadius: "var(--radius-sm)",
                    background: "color-mix(in srgb, var(--color-primary) 4%, transparent)",
                    borderLeft: "2px solid var(--color-primary)",
                  }}
                >
                  <p
                    className="font-bold"
                    style={{
                      fontSize: 11,
                      color: "var(--color-primary)",
                      marginBottom: "var(--space-2)",
                    }}
                  >
                    关键信息提取
                  </p>
                  <div
                    className="grid gap-y-2"
                    style={{ gridTemplateColumns: "1fr 1fr" }}
                  >
                    <InfoPair label="发票号码" value="02391029" />
                    <InfoPair label="开票金额" value="¥ 45,200.00" />
                    <InfoPair label="购买方" value="华瑞国际贸易" />
                    <InfoPair label="开票日期" value="2023-11-20" />
                  </div>
                </div>

                {/* Anomaly diagnosis */}
                <div
                  style={{
                    padding: "var(--space-4)",
                    borderRadius: "var(--radius-sm)",
                    background: "color-mix(in srgb, var(--color-secondary) 4%, transparent)",
                    borderLeft: "2px solid var(--color-secondary)",
                  }}
                >
                  <p
                    className="font-bold"
                    style={{
                      fontSize: 11,
                      color: "var(--color-secondary-dim)",
                      marginBottom: "var(--space-2)",
                    }}
                  >
                    异常诊断报告
                  </p>
                  <p style={{ fontSize: 13, color: "var(--color-text-primary)", lineHeight: 1.75 }}>
                    <span className="font-bold">诊断结果：</span>发票日期滞后异常。
                  </p>
                  <p
                    style={{
                      fontSize: 12,
                      color: "var(--color-text-secondary)",
                      lineHeight: 1.75,
                      marginTop: "var(--space-2)",
                    }}
                  >
                    通过语义分析对比采购合同（CONT-2023-011），合同明确交付日期为
                    2023-08-15。然而，该发票开具日期为 11-20，且在该时间段内企业未发生相关物流动作。
                  </p>
                </div>

                {/* Evidence chain */}
                <div>
                  <p
                    className="font-bold"
                    style={{
                      fontSize: 12,
                      color: "var(--color-text-primary)",
                      marginBottom: "var(--space-2)",
                    }}
                  >
                    相关联证据链 (3)
                  </p>
                  <div className="flex gap-2">
                    {["采购合同", "银行流水", "物流单据"].map((label) => (
                      <div
                        key={label}
                        className="flex items-center justify-center"
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: "var(--radius-sm)",
                          background: "var(--color-surface-container)",
                          cursor: "pointer",
                        }}
                        title={label}
                      >
                        <EvidenceIcon />
                      </div>
                    ))}
                  </div>
                </div>

                {/* Auditor notes */}
                <div style={{ marginTop: "var(--space-2)" }}>
                  <p style={{ fontSize: 10, color: "var(--color-text-tertiary)", marginBottom: 4 }}>
                    审计员备注
                  </p>
                  <textarea
                    className="font-body"
                    placeholder="输入您的复核意见..."
                    style={{
                      width: "100%",
                      height: 72,
                      fontSize: 13,
                      padding: "var(--space-3)",
                      background: "var(--color-surface)",
                      border: "none",
                      borderRadius: "var(--radius-sm)",
                      resize: "none",
                      color: "var(--color-text-primary)",
                      outline: "none",
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Floating AI status */}
            <div
              className="flex items-center gap-3"
              style={{
                position: "absolute",
                bottom: "var(--space-4)",
                left: "50%",
                transform: "translateX(-50%)",
                padding: "8px 20px",
                borderRadius: 999,
                background: "var(--glass-bg)",
                backdropFilter: "blur(var(--glass-blur))",
                boxShadow: "var(--shadow-ambient)",
                fontSize: 11,
              }}
            >
              <span
                style={{
                  position: "relative",
                  display: "inline-flex",
                  width: 8,
                  height: 8,
                }}
              >
                <span
                  className="ai-glow"
                  style={{
                    position: "absolute",
                    inset: 0,
                    borderRadius: "50%",
                    background: "var(--color-primary)",
                  }}
                />
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "var(--color-primary)",
                  }}
                />
              </span>
              <span className="font-bold" style={{ color: "var(--color-primary)" }}>
                AI 正在联想相关法规：第十二条 业务真实性准则
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer stats */}
      <section
        className="grid gap-6"
        style={{
          gridTemplateColumns: "repeat(3, 1fr)",
          paddingTop: "var(--space-6)",
        }}
      >
        {FOOTER_STATS.map((stat) => (
          <div key={stat.label} className="flex items-center gap-4">
            <div
              className="flex items-center justify-center shrink-0"
              style={{
                width: 44,
                height: 44,
                borderRadius: "50%",
                background: "var(--color-surface-container)",
              }}
            >
              <StatIcon color={stat.color} />
            </div>
            <div>
              <p
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: "var(--color-text-tertiary)",
                  marginBottom: 2,
                }}
              >
                {stat.label}
              </p>
              <p
                className="font-display font-extrabold"
                style={{ fontSize: 18, color: "var(--color-primary)" }}
              >
                {stat.value}
              </p>
            </div>
          </div>
        ))}
      </section>

      {/* Footer */}
      <footer
        className="text-center"
        style={{
          padding: "var(--space-12) 0 var(--space-8)",
          color: "var(--color-text-tertiary)",
          fontSize: 12,
        }}
      >
        <p>安全加密数据环境 -- 灵阙 AI 引擎 V2.4</p>
        <p style={{ marginTop: 4, opacity: 0.7 }}>&copy; 2024 灵阙财税科技. All rights reserved.</p>
      </footer>
    </div>
  );
}

/* ================================================================
   Sub-components (co-located, audit-specific)
   ================================================================ */

function FlowStep({
  step,
}: {
  step: (typeof AUDIT_FLOW)[number];
}) {
  const isDone = step.status === "done";
  const isActive = step.status === "active";
  const isPending = step.status === "pending";

  return (
    <div
      className="flex flex-col gap-3"
      style={{
        padding: "var(--space-6)",
        borderRadius: "var(--radius-md)",
        background: isActive
          ? "var(--color-surface-container-low)"
          : isDone
            ? "var(--color-surface-container-lowest)"
            : "var(--color-surface-container-low)",
        boxShadow: isDone || isActive ? "var(--shadow-sm)" : "none",
        opacity: isPending ? 0.5 : 1,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div className="flex items-center justify-between">
        <FlowStepIcon status={step.status} />
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: isActive
              ? "var(--color-primary)"
              : isDone
                ? "var(--color-secondary-dim)"
                : "var(--color-text-tertiary)",
          }}
        >
          {isActive && (
            <span
              className="ai-glow"
              style={{
                display: "inline-block",
                width: 5,
                height: 5,
                borderRadius: "50%",
                background: "var(--color-primary)",
                marginRight: 6,
                verticalAlign: "middle",
              }}
            />
          )}
          {isDone ? "已完成" : isActive ? "分析中" : "待开始"}
        </span>
      </div>
      <h3
        className="font-display font-bold"
        style={{
          fontSize: 15,
          color: isPending ? "var(--color-text-tertiary)" : "var(--color-primary)",
        }}
      >
        {step.label}
      </h3>
      <p style={{ fontSize: 11, color: "var(--color-text-tertiary)", margin: 0 }}>
        {step.detail}
      </p>
      {/* Bottom accent bar */}
      {isDone && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            width: "100%",
            height: 2,
            background: "var(--color-secondary)",
          }}
        />
      )}
      {isActive && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            width: "100%",
            height: 2,
            background: "var(--color-primary)",
          }}
        />
      )}
    </div>
  );
}

function FindingItem({
  finding,
}: {
  finding: (typeof FINDINGS)[number];
}) {
  const isSelected = finding.selected;
  const severityMap = {
    critical: {
      label: "高风险",
      badgeClass: "badge-danger",
      borderColor: "var(--color-danger)",
    },
    warning: {
      label: "中风险",
      badgeClass: "badge-warning",
      borderColor: "var(--color-secondary)",
    },
    info: {
      label: "低风险",
      badgeClass: "",
      borderColor: "var(--color-outline-variant)",
    },
  } as const;
  const sev = severityMap[finding.severity];

  return (
    <div
      style={{
        padding: "var(--space-4) var(--space-4) var(--space-4) var(--space-4)",
        borderRadius: "var(--radius-sm)",
        background: isSelected ? "var(--color-primary)" : "var(--color-surface-container-lowest)",
        boxShadow: isSelected ? "none" : "var(--shadow-sm)",
        borderLeft: `4px solid ${isSelected ? "var(--color-secondary)" : sev.borderColor}`,
        cursor: "pointer",
      }}
    >
      <div
        className="flex items-center justify-between"
        style={{ marginBottom: "var(--space-2)" }}
      >
        {finding.severity === "info" ? (
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              background: "var(--color-surface-container)",
              color: "var(--color-text-tertiary)",
            }}
          >
            {sev.label}
          </span>
        ) : isSelected && finding.severity === "warning" ? (
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
              background: "var(--color-secondary)",
              color: "var(--color-on-primary)",
            }}
          >
            {sev.label}
          </span>
        ) : (
          <span
            className={sev.badgeClass}
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "var(--radius-sm)",
            }}
          >
            {sev.label}
          </span>
        )}
        <span
          style={{
            fontSize: 11,
            color: isSelected ? "var(--color-primary-fixed)" : "var(--color-text-tertiary)",
          }}
        >
          {finding.id}
        </span>
      </div>
      <h4
        className="font-bold"
        style={{
          fontSize: 13,
          color: isSelected ? "var(--color-on-primary)" : "var(--color-text-primary)",
          marginBottom: "var(--space-1)",
        }}
      >
        {finding.title}
      </h4>
      <p
        style={{
          fontSize: 12,
          lineHeight: 1.75,
          color: isSelected ? "var(--color-primary-fixed)" : "var(--color-text-secondary)",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical" as const,
          overflow: "hidden",
          margin: 0,
        }}
      >
        {finding.desc}
      </p>
    </div>
  );
}

function InfoPair({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 10, color: "var(--color-text-tertiary)", margin: 0, marginBottom: 2 }}>
        {label}
      </p>
      <p className="font-bold" style={{ fontSize: 13, margin: 0 }}>
        {value}
      </p>
    </div>
  );
}

/* ── Inline SVG icons ── */

function FlowStepIcon({ status }: { status: "done" | "active" | "pending" }) {
  const color =
    status === "done"
      ? "var(--color-primary)"
      : status === "active"
        ? "var(--color-primary)"
        : "var(--color-text-tertiary)";
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      {status === "done" && (
        <path
          d="M6 2h8l6 6v14H6z M14 2v6h6 M8 14l3 3 5-6"
          stroke={color}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      {status === "active" && (
        <>
          <circle cx="12" cy="12" r="9" stroke={color} strokeWidth="1.8" />
          <path d="M12 7v5l3 2" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </>
      )}
      {status === "pending" && (
        <>
          <rect x="4" y="4" width="16" height="16" rx="2" stroke={color} strokeWidth="1.8" />
          <path d="M9 12h6" stroke={color} strokeWidth="1.8" strokeLinecap="round" />
        </>
      )}
    </svg>
  );
}

function FilterIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M3 6h18M7 12h10M10 18h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function AiSparkIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2l2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2z"
        fill="var(--color-on-primary)"
        stroke="var(--color-on-primary)"
        strokeWidth="1"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function DocPlaceholderIcon() {
  return (
    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" style={{ opacity: 0.3 }}>
      <path d="M6 2h8l6 6v14H6z" stroke="var(--color-text-tertiary)" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M14 2v6h6" stroke="var(--color-text-tertiary)" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M9 13h6M9 16h4" stroke="var(--color-text-tertiary)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function EvidenceIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path d="M6 2h8l6 6v14H6z" stroke="var(--color-text-tertiary)" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M14 2v6h6" stroke="var(--color-text-tertiary)" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

function StatIcon({ color }: { color: string }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M3 20h18M6 16v4M10 12v8M14 8v12M18 4v16" stroke={color} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
