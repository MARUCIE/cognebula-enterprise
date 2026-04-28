"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  getOntologyAudit,
  getQuality,
  getStats,
  type KGQuality,
  type KGStats,
  type OntologyAudit,
} from "../../lib/kg-api";
import { CN, cnBadge, cnBtn, cnBtnPrimary, cnLabel, cnValue } from "../../lib/cognebula-theme";
import ClauseInspector from "../../components/ClauseInspector";
import styles from "./page.module.css";

type Tone = "green" | "amber" | "red" | "blue";

export interface DataQualitySnapshot {
  stats: KGStats;
  quality: KGQuality;
  audit: OntologyAudit;
}

function KPI({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className={styles.metricCard}>
      <div style={cnLabel}>{label}</div>
      <div style={cnValue(color)}>{value}</div>
      <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4 }}>{sub}</div>
    </div>
  );
}

function CoverageBar({
  label,
  value,
  target,
  desc,
}: {
  label: string;
  value: number;
  target: number;
  desc: string;
}) {
  const hit = value >= target;
  const color = hit ? CN.green : CN.amber;
  return (
    <div style={{ marginBottom: 18 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
          color: CN.textSecondary,
          marginBottom: 4,
        }}
      >
        <span>{label}</span>
        <span style={{ color, fontVariantNumeric: "tabular-nums" }}>
          {value.toFixed(1)}% / {target}%
        </span>
      </div>
      <div style={{ height: 6, background: CN.border, borderRadius: 999, overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${Math.min(value, 100)}%`,
            background: color,
            transition: "width 0.5s",
          }}
        />
      </div>
      <div style={{ fontSize: 11, color: CN.textMuted, marginTop: 4, lineHeight: 1.5 }}>{desc}</div>
    </div>
  );
}

function StatusBadge({ tone, children }: { tone: Tone; children: ReactNode }) {
  const style =
    tone === "green"
      ? cnBadge(CN.green, CN.greenBg)
      : tone === "amber"
        ? cnBadge(CN.amber, CN.amberBg)
        : tone === "red"
          ? cnBadge(CN.red, CN.redBg)
          : cnBadge(CN.blue, CN.blueBg);
  return <span style={style}>{children}</span>;
}

function formatCount(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return `${value}`;
}

function sampleNames(names: string[], fallback = "--"): string {
  return names.length ? names.slice(0, 3).join(" / ") : fallback;
}

function trackDataQualityEvent(event: string, detail: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent("cognebula:data-quality", {
      detail: {
        event,
        at: new Date().toISOString(),
        ...detail,
      },
    }),
  );
}

function issueLabel(options: { dominant: boolean; legacy: boolean; v1v2: boolean; duplicate: boolean; rogue: boolean }) {
  if (options.dominant) return "集中桶";
  if (options.v1v2) return "V1/V2";
  if (options.duplicate) return "重复簇";
  if (options.legacy) return "legacy";
  if (options.rogue) return "rogue";
  return "检查";
}

function scrollToSection(id: string, event: string) {
  if (typeof document === "undefined") return;
  const target = document.getElementById(id);
  target?.scrollIntoView({ behavior: "smooth", block: "start" });
  trackDataQualityEvent(event, { target: id });
}

export function DataQualityWorkbench({
  initialSnapshot,
  fixtureLabel,
}: {
  initialSnapshot?: DataQualitySnapshot;
  fixtureLabel?: string;
}) {
  const [stats, setStats] = useState<KGStats | null>(initialSnapshot?.stats ?? null);
  const [quality, setQuality] = useState<KGQuality | null>(initialSnapshot?.quality ?? null);
  const [audit, setAudit] = useState<OntologyAudit | null>(initialSnapshot?.audit ?? null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!initialSnapshot);

  useEffect(() => {
    if (initialSnapshot) {
      trackDataQualityEvent("fixture_loaded", { fixtureLabel: fixtureLabel || "snapshot" });
      return;
    }

    let cancelled = false;
    trackDataQualityEvent("load_started");

    Promise.allSettled([getStats(), getQuality(), getOntologyAudit()])
      .then(([statsResult, qualityResult, auditResult]) => {
        if (cancelled) return;

        const partialFailures: string[] = [];
        const statuses = {
          stats: statsResult.status,
          quality: qualityResult.status,
          audit: auditResult.status,
        };

        if (statsResult.status === "fulfilled") setStats(statsResult.value);
        else partialFailures.push("图谱统计");

        if (qualityResult.status === "fulfilled") setQuality(qualityResult.value);
        else partialFailures.push("内容覆盖");

        if (auditResult.status === "fulfilled") setAudit(auditResult.value);
        else partialFailures.push("结构审计");

        if (partialFailures.length === 3) {
          setError("KG API 无法连接 (请检查 Tailscale)");
          trackDataQualityEvent("load_failed", { statuses, partialFailures });
        } else if (partialFailures.length > 0) {
          setError(`部分接口暂不可用: ${partialFailures.join(" / ")}`);
          trackDataQualityEvent("load_partial", { statuses, partialFailures });
        } else {
          setError(null);
          trackDataQualityEvent("load_succeeded", { statuses });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("KG API 无法连接 (请检查 Tailscale)");
          trackDataQualityEvent("load_failed", { statuses: "unhandled_rejection" });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [fixtureLabel, initialSnapshot]);

  const topTypes = useMemo(
    () =>
      stats ? Object.entries(stats.nodes_by_type).sort((a, b) => b[1] - a[1]).slice(0, 15) : [],
    [stats],
  );

  const derived = useMemo(() => {
    const topType = topTypes[0];
    const topTypeShare = stats && topType ? ((topType[1] as number) / stats.total_nodes) * 100 : 0;
    const top3Share = stats
      ? (topTypes.slice(0, 3).reduce((sum, [, count]) => sum + (count as number), 0) / stats.total_nodes) * 100
      : 0;
    const rogueSet = new Set(audit?.rogue_in_prod || []);
    const legacySet = new Set(audit?.rogue_buckets.legacy || []);
    const v1v2Set = new Set(audit?.rogue_buckets.v1_v2_bleed || []);
    const duplicateMembers = Object.values(audit?.rogue_buckets.duplicate_clusters || {}).flat();
    const duplicateSet = new Set(duplicateMembers);
    const typeCount = (name: string) => stats?.nodes_by_type[name] || 0;
    const bucketNodeCount = (names: string[]) => names.reduce((sum, name) => sum + typeCount(name), 0);
    const duplicateNodeCount = bucketNodeCount(duplicateMembers);
    const edgeRogueCount = audit?.edges?.rogue_in_prod.length || 0;

    const cleanupPriorities = topTypes
      .filter(([type]) => type === topType?.[0] || rogueSet.has(type) || legacySet.has(type) || v1v2Set.has(type) || duplicateSet.has(type))
      .map(([type, count]) => {
        const dominant = type === topType?.[0] && topTypeShare > 25;
        const legacy = legacySet.has(type);
        const v1v2 = v1v2Set.has(type);
        const duplicate = duplicateSet.has(type);
        const rogue = rogueSet.has(type);
        const score =
          (dominant ? 100 : 0) +
          (v1v2 ? 80 : 0) +
          (duplicate ? 70 : 0) +
          (legacy ? 50 : 0) +
          (rogue ? 40 : 0) +
          Number(count);
        return {
          type,
          count: count as number,
          dominant,
          legacy,
          v1v2,
          duplicate,
          rogue,
          share: stats ? ((count as number) / stats.total_nodes) * 100 : 0,
          score,
        };
      })
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);

    return {
      topType,
      topTypeShare,
      top3Share,
      rogueSet,
      legacySet,
      v1v2Set,
      duplicateMembers,
      duplicateSet,
      bucketNodeCount,
      duplicateNodeCount,
      edgeRogueCount,
      cleanupPriorities,
    };
  }, [audit, stats, topTypes]);

  const structuralTone: Tone =
    audit?.severity === "high" ? "red" : audit?.severity === "medium" ? "amber" : audit ? "green" : "blue";
  const structuralColor =
    structuralTone === "red"
      ? CN.red
      : structuralTone === "amber"
        ? CN.amber
        : structuralTone === "green"
          ? CN.green
          : CN.blue;
  const releaseTone: Tone =
    audit?.verdict === "FAIL"
      ? "red"
      : quality && (quality.content_coverage || 0) < 80
        ? "amber"
        : audit
          ? "green"
          : "blue";
  const releaseLabel =
    audit?.verdict === "FAIL"
      ? "BLOCKED"
      : quality && (quality.content_coverage || 0) < 80
        ? "WARN"
        : audit
          ? "READY"
          : "PENDING";
  const primaryQueue = derived.cleanupPriorities[0];
  const partialFailure = error?.startsWith("部分接口");

  return (
    <div className={styles.page}>
      {fixtureLabel && (
        <div
          className={styles.panel}
          style={{
            padding: "10px 16px",
            borderColor: CN.blue,
            background: CN.blueBg,
            color: CN.blue,
            fontSize: 13,
          }}
          data-testid="dq-fixture-banner"
        >
          Validation fixture: {fixtureLabel}
        </div>
      )}

      {error && (
        <div
          className={styles.panel}
          style={{
            padding: "12px 16px",
            borderColor: partialFailure ? CN.amber : CN.red,
            background: partialFailure ? CN.amberBg : CN.redBg,
            color: partialFailure ? CN.amber : CN.red,
            fontSize: 13,
          }}
          data-testid="dq-error-state"
        >
          {error}
        </div>
      )}

      <section className={styles.heroGrid}>
        <div className={`${styles.panel} ${styles.heroPanel}`} data-testid="dq-hero">
          <div className={styles.eyebrow}>Data Quality Workbench</div>
          <h1 className={styles.heroTitle}>
            {audit?.verdict === "FAIL" ? "先停下来看结构，再决定治理动作" : "结构通过，可以继续推进内容治理与条款审核"}
          </h1>
          <p className={styles.heroLead}>
            这页的目标不是“展示几个分数”，而是帮助操作者在最短时间内完成三个动作：
            判断当前图谱能不能信、识别最该清理的节点桶、再决定是否进入逐条条款审核。
            {audit?.verdict === "FAIL" && audit
              ? ` 当前结构审计为 ${audit.verdict} / ${audit.severity}，说明卫生分不能单独作为发布依据。`
              : " 如果结构审计通过，覆盖率和边密度才有资格代表整体质量。"}
          </p>

          <div className={styles.actionRow}>
            <button
              style={{ ...cnBtnPrimary, padding: "10px 18px", fontSize: 13 }}
              onClick={() => scrollToSection("governance-lane", "jump_governance_lane")}
              data-testid="dq-primary-action"
            >
              {primaryQueue ? `先处理 ${primaryQueue.type}` : "查看治理优先级"}
            </button>
            <button
              style={{ ...cnBtn, padding: "10px 16px", fontSize: 13, background: CN.bg }}
              onClick={() => scrollToSection("clause-inspector", "jump_clause_inspector")}
              data-testid="dq-secondary-action"
            >
              跳到条款审核
            </button>
          </div>

          <div className={styles.statusFacts}>
            <div className={styles.factCard}>
              <div className={styles.factLabel}>发布门</div>
              <div className={styles.factValue} style={{ color: releaseTone === "red" ? CN.red : releaseTone === "amber" ? CN.amber : releaseTone === "green" ? CN.green : CN.blue }}>
                {releaseLabel}
              </div>
              <div className={styles.factSub}>
                {audit?.verdict === "FAIL"
                  ? "结构失败，当前不可发布"
                  : quality && (quality.content_coverage || 0) < 80
                    ? "结构可用，但内容卫生未达标"
                    : "结构与卫生均满足上线门槛"}
              </div>
            </div>
            <div className={styles.factCard}>
              <div className={styles.factLabel}>最大桶</div>
              <div className={styles.factValue}>
                {derived.topType ? `${derived.topTypeShare.toFixed(1)}%` : "--"}
              </div>
              <div className={styles.factSub}>
                {derived.topType ? `${derived.topType[0]} · ${formatCount(derived.topType[1] as number)}` : "等待 stats"}
              </div>
            </div>
            <div className={styles.factCard}>
              <div className={styles.factLabel}>结构漂移</div>
              <div className={styles.factValue}>
                {audit ? `${audit.live_count}/${audit.canonical_count}` : "--"}
              </div>
              <div className={styles.factSub}>
                {audit ? `live types / canonical · over ${audit.over_ceiling_by}` : "等待 audit"}
              </div>
            </div>
            <div className={styles.factCard}>
              <div className={styles.factLabel}>卫生分</div>
              <div className={styles.factValue} style={{ color: quality && (quality.content_coverage || 0) >= 80 ? CN.green : CN.amber }}>
                {quality ? `${(quality.content_coverage || 0).toFixed(1)}%` : "--"}
              </div>
              <div className={styles.factSub}>
                {quality ? `内容覆盖率 · score ${quality.quality_score}` : "等待 quality"}
              </div>
            </div>
          </div>
        </div>

        <aside className={`${styles.panel} ${styles.railPanel}`} data-testid="dq-task-rail">
          <h2 className={styles.railTitle}>Operator Flow</h2>
          <p className={styles.railText}>
            入口在 `/expert/data-quality`。主路径是先做结构判断，再落治理动作，最后才进入条款级语义审查。
            如果接口部分失败，页面也必须保留可读状态和下一步建议。
          </p>
          <div className={styles.laneList}>
            <div className={styles.laneItem}>
              <div className={styles.laneHead}>
                <div className={styles.laneLabel}>1. 判断风险级别</div>
                <StatusBadge tone={structuralTone}>{audit ? `${audit.verdict} / ${audit.severity}` : loading ? "LOADING" : "PENDING"}</StatusBadge>
              </div>
              <div className={styles.laneBody}>
                看结构审计、最大桶占比、rogue / V1-V2 / duplicate / legacy 这四类问题是否已经阻塞发布。
              </div>
            </div>
            <div className={styles.laneItem}>
              <div className={styles.laneHead}>
                <div className={styles.laneLabel}>2. 决定先清什么</div>
                <StatusBadge tone={primaryQueue ? "red" : "blue"}>{primaryQueue ? primaryQueue.type : "等待数据"}</StatusBadge>
              </div>
              <div className={styles.laneBody}>
                页面会根据线上桶大小和 drift 类型自动给出治理优先级，避免操作者只盯着覆盖率条。
              </div>
            </div>
            <div className={styles.laneItem}>
              <div className={styles.laneHead}>
                <div className={styles.laneLabel}>3. 逐条审计</div>
                <StatusBadge tone="blue">Inspector</StatusBadge>
              </div>
              <div className={styles.laneBody}>
                只有当结构问题被定位后，才进入 Clause Inspector 做单条或批量语义审查。
              </div>
            </div>
          </div>
        </aside>
      </section>

      {loading && !stats && !quality && !audit && (
        <section className={styles.loadingGrid} data-testid="dq-loading-state">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={`metric-${index}`} className={`${styles.panel} ${styles.skeleton} ${styles.skeletonMetric}`} />
          ))}
          <div className={`${styles.panel} ${styles.skeleton} ${styles.skeletonTall}`} />
          <div className={`${styles.panel} ${styles.skeleton} ${styles.skeletonTall}`} />
        </section>
      )}

      <section className={styles.metricStrip}>
        <KPI
          label="节点总数"
          value={stats ? `${(stats.total_nodes / 1000).toFixed(1)}K` : "..."}
          sub={stats ? `${stats.node_tables} 张表 · ${stats.rel_tables} 种关系` : "等待图谱统计"}
          color={CN.blue}
        />
        <KPI
          label="结构审计"
          value={audit ? audit.verdict : "..."}
          sub={audit ? `severity ${audit.severity} · live ${audit.live_count}` : "等待 canonical 对齐结果"}
          color={structuralColor}
        />
        <KPI
          label="Rogue 节点类型"
          value={audit ? `${audit.rogue_in_prod.length}` : "..."}
          sub={audit ? `legacy ${audit.rogue_buckets.legacy.length} · V1/V2 ${audit.rogue_buckets.v1_v2_bleed.length}` : "等待 drift buckets"}
          color={audit && audit.rogue_in_prod.length > 0 ? CN.red : CN.green}
        />
        <KPI
          label="Inspector 状态"
          value="READY"
          sub="可做单行或批量 NDJSON 审核"
          color={CN.purple}
        />
      </section>

      <section className={styles.mainGrid}>
        <div className={styles.stack} id="governance-lane">
          <div className={`${styles.panel} ${styles.sectionCard}`} data-testid="dq-governance-lane">
            <div className={styles.sectionHead}>
              <div>
                <h2 className={styles.sectionTitle}>治理优先级</h2>
                <p className={styles.sectionDesc}>
                  页面把“先改哪一类”直接排出来，避免用户看完图却仍然不知道该动哪个表、哪个桶、哪类关系。
                </p>
              </div>
              <StatusBadge tone={primaryQueue ? "red" : "blue"}>
                {primaryQueue ? `Primary · ${primaryQueue.type}` : "等待风险排序"}
              </StatusBadge>
            </div>
            <div className={styles.queueList}>
              {derived.cleanupPriorities.map((item) => {
                const tone: Tone = item.dominant || item.v1v2 || item.duplicate ? "red" : item.legacy || item.rogue ? "amber" : "blue";
                return (
                  <div key={item.type} className={styles.queueItem}>
                    <div>
                      <div className={styles.queueTitle}>{item.type}</div>
                      <div className={styles.queueMeta}>
                        {formatCount(item.count)} nodes · {item.share.toFixed(1)}% of live graph
                        {item.type === derived.topType?.[0] ? " · 当前最大节点桶" : ""}
                      </div>
                    </div>
                    <StatusBadge tone={tone}>{issueLabel(item)}</StatusBadge>
                    <div className={styles.queueAction}>
                      {item.dominant
                        ? "先拆分本体，避免异构内容继续堆进同一桶"
                        : item.v1v2
                          ? "先合并版本分叉，消掉并存表"
                          : item.duplicate
                            ? "先收敛重复语义，再补文本"
                            : item.legacy
                              ? "先清理遗留类型，再看覆盖率"
                              : "检查是否误归类"}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className={`${styles.panel} ${styles.sectionCard}`} data-testid="dq-distribution">
            <div className={styles.sectionHead}>
              <div>
                <h2 className={styles.sectionTitle}>节点类型分布</h2>
                <p className={styles.sectionDesc}>
                  红色表示 dominant / rogue / V1-V2 / duplicate，橙色表示 legacy。这个面板的作用是快速识别“垃圾桶节点”和异常集中。
                </p>
              </div>
              <StatusBadge tone={derived.topTypeShare > 25 ? "red" : derived.topTypeShare > 18 ? "amber" : "green"}>
                TOP-3 {derived.top3Share.toFixed(1)}%
              </StatusBadge>
            </div>
            <div className={styles.distList}>
              {topTypes.map(([type, count]) => {
                const maxCount = topTypes[0]?.[1] || 1;
                const pct = ((count as number) / (maxCount as number)) * 100;
                const dominant = type === derived.topType?.[0] && derived.topTypeShare > 25;
                const rogue = derived.rogueSet.has(type) || derived.v1v2Set.has(type) || derived.duplicateSet.has(type);
                const legacy = derived.legacySet.has(type);
                const barColor = dominant || rogue ? CN.red : legacy ? CN.amber : CN.blue;
                const tone: Tone = dominant || rogue ? "red" : legacy ? "amber" : "blue";

                return (
                  <div key={type} className={styles.distRow}>
                    <div className={styles.distLabel}>
                      <span className={styles.distName}>{type}</span>
                      {(dominant || rogue || legacy) && <StatusBadge tone={tone}>{issueLabel({ dominant, legacy, v1v2: derived.v1v2Set.has(type), duplicate: derived.duplicateSet.has(type), rogue })}</StatusBadge>}
                    </div>
                    <div className={styles.distBarTrack}>
                      <div className={styles.distBarFill} style={{ width: `${pct}%`, background: barColor }} />
                    </div>
                    <span className={styles.distCount}>{(count as number).toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
            {stats && derived.topType && (
              <div className={styles.distributionNote}>
                <strong>判读</strong>: 最大类型 {derived.topType[0]} 占全部节点 {derived.topTypeShare.toFixed(1)}%，TOP-3 类型合计 {derived.top3Share.toFixed(1)}%。
                如果这里持续被一两个大桶吞噬，覆盖率和边密度再漂亮，检索与推理也会因为分类失真而失去可信度。
              </div>
            )}
          </div>
        </div>

        <div className={styles.stack}>
          {audit && (
            <div className={`${styles.panel} ${styles.sectionCard}`} data-testid="dq-risk-breakdown">
              <div className={styles.sectionHead}>
                <div>
                  <h2 className={styles.sectionTitle}>结构风险分解</h2>
                  <p className={styles.sectionDesc}>
                    这些才是“能不能发布”和“能不能继续信这张图谱”的核心门，不是右上角那个 `100` 分。
                  </p>
                </div>
                <StatusBadge tone={structuralTone}>{audit.verdict} / {audit.severity.toUpperCase()}</StatusBadge>
              </div>
              <div className={styles.riskList}>
                {[
                  {
                    label: "超 Brooks 上限",
                    value: audit.over_ceiling_by ? `+${audit.over_ceiling_by}` : "0",
                    desc: `live ${audit.live_count} / canonical ${audit.canonical_count}`,
                    tone: audit.over_ceiling ? "red" : "green" as Tone,
                  },
                  {
                    label: "V1 / V2 并存",
                    value: `${audit.rogue_buckets.v1_v2_bleed.length}`,
                    desc: `${formatCount(derived.bucketNodeCount(audit.rogue_buckets.v1_v2_bleed))} nodes · ${sampleNames(audit.rogue_buckets.v1_v2_bleed)}`,
                    tone: audit.rogue_buckets.v1_v2_bleed.length ? "red" : "green" as Tone,
                  },
                  {
                    label: "重复簇未收敛",
                    value: `${derived.duplicateMembers.length}`,
                    desc: `${formatCount(derived.duplicateNodeCount)} nodes · ${Object.keys(audit.rogue_buckets.duplicate_clusters).join(" / ") || "--"}`,
                    tone: derived.duplicateMembers.length ? "red" : "green" as Tone,
                  },
                  {
                    label: "Legacy 表残留",
                    value: `${audit.rogue_buckets.legacy.length}`,
                    desc: `${formatCount(derived.bucketNodeCount(audit.rogue_buckets.legacy))} nodes · ${sampleNames(audit.rogue_buckets.legacy)}`,
                    tone: audit.rogue_buckets.legacy.length ? "amber" : "green" as Tone,
                  },
                  {
                    label: "SaaS 泄漏到 KG",
                    value: `${audit.rogue_buckets.saas_leak.length}`,
                    desc: sampleNames(audit.rogue_buckets.saas_leak),
                    tone: audit.rogue_buckets.saas_leak.length ? "amber" : "green" as Tone,
                  },
                  {
                    label: "Rogue 边类型",
                    value: `${derived.edgeRogueCount}`,
                    desc: sampleNames(audit.edges?.rogue_buckets.legacy_prefixes || []),
                    tone: derived.edgeRogueCount > 20 ? "red" : derived.edgeRogueCount > 0 ? "amber" : "green" as Tone,
                  },
                ].map((item) => (
                  <div key={item.label} className={styles.riskItem}>
                    <div className={styles.riskHead}>
                      <div className={styles.riskLabel}>{item.label}</div>
                      <div className={styles.riskValueWrap}>
                        <span
                          className={styles.riskValue}
                          style={{
                            color: item.tone === "red" ? CN.red : item.tone === "amber" ? CN.amber : CN.green,
                          }}
                        >
                          {item.value}
                        </span>
                        <StatusBadge tone={item.tone}>{item.tone === "green" ? "OK" : item.tone === "amber" ? "WARN" : "FAIL"}</StatusBadge>
                      </div>
                    </div>
                    <div className={styles.riskDesc}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {quality && (
            <div className={`${styles.panel} ${styles.sectionCard}`} data-testid="dq-hygiene">
              <div className={styles.sectionHead}>
                <div>
                  <h2 className={styles.sectionTitle}>基础卫生指标</h2>
                  <p className={styles.sectionDesc}>
                    卫生分有用，但只在结构门通过时有资格代表整体质量。现在它的职责是说明“局部文本质量如何”，不是替代结构结论。
                  </p>
                </div>
                <StatusBadge tone={quality.content_coverage >= 80 ? "green" : "amber"}>{quality.content_coverage.toFixed(1)}%</StatusBadge>
              </div>
              <CoverageBar
                label="标题覆盖率"
                value={quality.title_coverage || 0}
                target={95}
                desc="统计范围: v4.1 节点表 | 检查字段: title / name / topic | 有效阈值: >= 2 字符"
              />
              <CoverageBar
                label="内容覆盖率"
                value={quality.content_coverage || 0}
                target={80}
                desc="统计范围: v4.1 节点表 | 检查字段: fullText / content / description | 有效阈值: >= 20 字符"
              />
              <div className={styles.healthGrid}>
                <KPI label="质量评分" value={`${quality.quality_score || 0}`} sub="curated hygiene score" color={quality.quality_score >= 80 ? CN.green : CN.amber} />
                <KPI label="等级" value={quality.grade || "--"} sub="A/B/C by hygiene score" color={quality.grade === "A" || quality.grade === "B" ? CN.green : CN.amber} />
                <KPI label="边密度" value={(quality.edge_density || 0).toFixed(3)} sub="semantic edges / node" color={(quality.edge_density || 0) >= 0.5 ? CN.green : CN.amber} />
              </div>
              {audit?.verdict === "FAIL" && (
                <div style={{ marginTop: 14, fontSize: 12, color: CN.textSecondary, lineHeight: 1.8 }}>
                  <strong>解释</strong>: `100 / A` 只说明被纳入 <code>/api/v1/quality</code> 的 curated 表里，
                  标题、内容、边密度还可以。只要 <code>/api/v1/ontology-audit</code> 仍然 FAIL，这些分数就不能再被当成“整体图谱可发布”的结论。
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <details className={`${styles.panel} ${styles.detailsCard}`} data-testid="dq-methodology">
        <summary className={styles.detailsSummary}>
          <span>数据来源与计算方法</span>
          <StatusBadge tone="blue">展开说明</StatusBadge>
        </summary>
        <div className={styles.detailsBody}>
          <p style={{ margin: "14px 0 12px" }}>
            <strong>结构质量</strong>: 来自 <code style={{ fontSize: 11, padding: "1px 6px", background: CN.bgElevated, borderRadius: 3 }}>GET /api/v1/ontology-audit</code>，
            实时比对 live Kuzu 与 canonical <code style={{ fontSize: 11, padding: "1px 6px", background: CN.bgElevated, borderRadius: 3 }}>schemas/ontology_v4.2.cypher</code>。
            它负责回答“类型是否失控、V1/V2 是否并存、legacy/duplicate/saas leak 是否仍在污染图谱”。
          </p>
          <p style={{ margin: "0 0 12px" }}>
            <strong>基础卫生</strong>: 来自 <code style={{ fontSize: 11, padding: "1px 6px", background: CN.bgElevated, borderRadius: 3 }}>GET /api/v1/quality</code>，
            统计范围限定于 v4.1 curated 节点表，用于衡量标题覆盖率、内容覆盖率与边密度。它们不能替代结构门，只能辅助判断局部文本质量。
          </p>
          <p style={{ margin: 0 }}>
            <strong>类型集中度</strong>: 页面根据 <code style={{ fontSize: 11, padding: "1px 6px", background: CN.bgElevated, borderRadius: 3 }}>GET /api/v1/stats</code> 的 <code style={{ fontSize: 11, padding: "1px 6px", background: CN.bgElevated, borderRadius: 3 }}>nodes_by_type</code>
            派生最大桶占比与 TOP-3 占比，用来暴露 catch-all bucket 和本体粒度失真。
          </p>
        </div>
      </details>

      <section id="clause-inspector" className={`${styles.panel} ${styles.inspectorShell}`} data-testid="dq-inspector-section">
        <div className={styles.inspectorIntro}>
          <div>
            <div className={styles.eyebrow}>Clause Audit</div>
            <h2 className={styles.sectionTitle} style={{ marginTop: 6 }}>条款语义审核</h2>
          </div>
          <div className={styles.inspectorHint}>
            当结构问题已经定位，需要确认单条条款或批量条款记录有没有语义缺陷时，再进入这个面板。
            它不是首页任务，而是结构治理之后的精细化检查工具。
          </div>
        </div>
        <ClauseInspector />
      </section>
    </div>
  );
}

export default function DataQualityPage() {
  return <DataQualityWorkbench />;
}
