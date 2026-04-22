"use client";

import { useState } from "react";
import {
  inspectClause,
  inspectClauseBatch,
  type ClauseInspectRow,
  type ClauseInspectResult,
  type ClauseInspectBatchResponse,
} from "../lib/kg-api";
import {
  CN,
  cnCard,
  cnBtn,
  cnBtnPrimary,
  cnInput,
} from "../lib/cognebula-theme";

/* Operator-facing façade over POST /api/v1/inspect/clause[/batch].
   Mounted inside the Data Quality page as a per-clause audit tool:
   operator feeds a row (or NDJSON batch), gets CLEAN verdict or
   a list of semantic defect flags, with Chinese labels resolved
   from src/kg/clause_inspector.describe() response shape. */

const ROLES: { value: string; label: string }[] = [
  { value: "", label: "-- 未设置 --" },
  { value: "premise", label: "前提 (premise)" },
  { value: "rule", label: "规则 (rule)" },
  { value: "holding", label: "裁判要旨 (holding)" },
  { value: "dicta", label: "附随意见 (dicta)" },
  { value: "counter", label: "反对意见 (counter)" },
  { value: "concession", label: "让步 (concession)" },
  { value: "authority", label: "权威依据 (authority)" },
  { value: "analogy", label: "类推 (analogy) — 税法禁用" },
  { value: "interpretation", label: "解释 (interpretation, CN)" },
  { value: "reply", label: "答复 (reply, CN)" },
  { value: "notice", label: "通知 (notice, CN)" },
  { value: "guideline", label: "指引 (guideline, CN)" },
  { value: "principle", label: "原则 (principle, CN)" },
  { value: "illustration", label: "示例 (illustration, CN)" },
];

const SCOPES: { value: string; label: string }[] = [
  { value: "", label: "-- 未设置 --" },
  { value: "national", label: "national 全国" },
  { value: "subnational", label: "subnational 省级" },
  { value: "municipal", label: "municipal 市级" },
  { value: "special_zone", label: "special_zone 特区/自贸" },
  { value: "treaty", label: "treaty 税收协定" },
  { value: "international", label: "international 国际" },
];

const FLAG_LABEL: Record<string, string> = {
  prohibited_role: "税收法定禁止 (类推适用)",
  unknown_role: "未知论证角色",
  invalid_override_chain: "Override chain ID 非法",
  invalid_override_chain_parents: "多父链路非法",
  inconsistent_code_scope: "辖区代码与作用域不一致",
  unknown_jurisdiction_code: "未知辖区代码",
};

type Mode = "single" | "batch";

function FlagChip({ code }: { code: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        fontSize: 11,
        fontWeight: 600,
        padding: "3px 10px",
        marginRight: 6,
        marginBottom: 6,
        color: CN.red,
        background: CN.redBg,
        border: `1px solid ${CN.red}`,
        borderRadius: 3,
      }}
    >
      {FLAG_LABEL[code] || code}
    </span>
  );
}

function Verdict({ result }: { result: ClauseInspectResult }) {
  const ok = result.clean;
  return (
    <div
      style={{
        ...cnCard,
        borderLeft: `3px solid ${ok ? CN.green : CN.red}`,
        background: ok ? CN.greenBg : CN.redBg,
        marginBottom: 12,
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 700, color: ok ? CN.green : CN.red, marginBottom: ok ? 0 : 8 }}>
        {ok ? "CLEAN — 无语义缺陷" : "DEFECTS — 发现语义缺陷"}
      </div>
      {!ok && (
        <div>
          {result.defect_flags.map((f) => (
            <FlagChip key={f} code={f} />
          ))}
        </div>
      )}
    </div>
  );
}

function KVTable({ result }: { result: ClauseInspectResult }) {
  const role = result.argument.role;
  const strength = result.argument.strength;
  const chain = result.override_chain;
  const consistency = result.consistency;

  const rows: { k: string; v: React.ReactNode }[] = [
    {
      k: "论证角色",
      v: role ? (
        <span>
          {role.label_zh} ({role.key})
          {role.prohibited_in_tax_law && (
            <span style={{ color: CN.red, marginLeft: 8, fontSize: 11, fontWeight: 600 }}>税收法定禁止</span>
          )}
        </span>
      ) : (
        <span style={{ color: CN.textMuted }}>未设置</span>
      ),
    },
    {
      k: "论证强度",
      v: (
        <span>
          {strength.label_zh}
          {strength.raw != null && (
            <span style={{ color: CN.textMuted, marginLeft: 8, fontFamily: "'SF Mono', monospace" }}>
              ({strength.raw.toFixed(2)} / {strength.tier})
            </span>
          )}
        </span>
      ),
    },
    {
      k: "Override 链路",
      v: chain.code ? (
        <span>
          {result.override_chain_breadcrumb_zh || chain.label_zh || chain.code}
          {!chain.valid && chain.reason && (
            <span style={{ color: CN.red, marginLeft: 8, fontSize: 11 }}>— {chain.reason}</span>
          )}
        </span>
      ) : (
        <span style={{ color: CN.textMuted }}>未设置</span>
      ),
    },
    {
      k: "辖区一致性",
      v: (
        <span>
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              padding: "2px 6px",
              marginRight: 8,
              color: consistency.verdict === "consistent" ? CN.green : consistency.verdict === "inconsistent" ? CN.red : CN.amber,
              background:
                consistency.verdict === "consistent" ? CN.greenBg : consistency.verdict === "inconsistent" ? CN.redBg : CN.amberBg,
            }}
          >
            {consistency.verdict}
          </span>
          {consistency.code && (
            <span style={{ fontFamily: "'SF Mono', monospace", color: CN.text }}>
              {consistency.code} · {consistency.scope || "(no scope)"}
            </span>
          )}
          {consistency.reason && (
            <span style={{ color: CN.textMuted, marginLeft: 8, fontSize: 11 }}>— {consistency.reason}</span>
          )}
        </span>
      ),
    },
  ];

  return (
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
      <tbody>
        {rows.map((r) => (
          <tr key={r.k} style={{ borderBottom: `1px solid ${CN.border}` }}>
            <td style={{ padding: "8px 0", color: CN.textMuted, width: 120, verticalAlign: "top" }}>{r.k}</td>
            <td style={{ padding: "8px 0", color: CN.text, lineHeight: 1.7 }}>{r.v}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ClauseInspector() {
  const [mode, setMode] = useState<Mode>("single");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [single, setSingle] = useState<ClauseInspectResult | null>(null);
  const [batch, setBatch] = useState<ClauseInspectBatchResponse | null>(null);

  const [role, setRole] = useState("");
  const [strength, setStrength] = useState("");
  const [code, setCode] = useState("");
  const [scope, setScope] = useState("");
  const [chainId, setChainId] = useState("");
  const [ndjson, setNdjson] = useState("");

  async function submitSingle() {
    setError(null);
    setSingle(null);
    setLoading(true);
    try {
      const row: ClauseInspectRow = {
        argument_role: role || null,
        argument_strength: strength ? Number(strength) : null,
        override_chain_id: chainId || null,
        jurisdiction_code: code || null,
        jurisdiction_scope: scope || null,
      };
      const r = await inspectClause(row);
      setSingle(r);
    } catch (e) {
      setError((e as Error).message || "审核请求失败");
    } finally {
      setLoading(false);
    }
  }

  async function submitBatch() {
    setError(null);
    setBatch(null);
    const text = ndjson.trim();
    if (!text) {
      setError("请粘贴 NDJSON (每行一个 JSON 对象)");
      return;
    }
    const lines = text.split(/\r?\n/).filter((l) => l.trim());
    const rows: ClauseInspectRow[] = [];
    for (let i = 0; i < lines.length; i++) {
      try {
        rows.push(JSON.parse(lines[i]));
      } catch {
        setError(`第 ${i + 1} 行 JSON 解析失败: ${lines[i].slice(0, 60)}${lines[i].length > 60 ? "..." : ""}`);
        return;
      }
    }
    setLoading(true);
    try {
      const r = await inspectClauseBatch(rows);
      setBatch(r);
    } catch (e) {
      setError((e as Error).message || "批量审核失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ ...cnCard, borderTop: `2px solid ${CN.purple}` }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: CN.text }}>条款语义审核 — Clause Inspector</div>
        <div style={{ fontSize: 11, color: CN.textMuted }}>
          POST /api/v1/inspect/clause · v4.3 argument + jurisdiction + override-chain
        </div>
      </div>

      <div role="tablist" aria-label="审核模式" style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["single", "batch"] as Mode[]).map((m) => {
          const active = mode === m;
          return (
            <button
              key={m}
              role="tab"
              aria-selected={active}
              onClick={() => {
                setMode(m);
                setError(null);
              }}
              style={{
                ...(active ? cnBtnPrimary : cnBtn),
                padding: "6px 14px",
                fontSize: 12,
              }}
            >
              {m === "single" ? "单行" : "批量 NDJSON"}
            </button>
          );
        })}
      </div>

      {mode === "single" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
          <label style={{ fontSize: 12, color: CN.textSecondary }}>
            argument_role
            <select value={role} onChange={(e) => setRole(e.target.value)} style={{ ...cnInput, width: "100%", marginTop: 4 }}>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label style={{ fontSize: 12, color: CN.textSecondary }}>
            argument_strength (0.0 - 1.0)
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={strength}
              onChange={(e) => setStrength(e.target.value)}
              style={{ ...cnInput, width: "100%", marginTop: 4 }}
            />
          </label>
          <label style={{ fontSize: 12, color: CN.textSecondary }}>
            jurisdiction_code
            <input
              type="text"
              placeholder="CN / CN-11 / CN-FTZ-SHA ..."
              value={code}
              onChange={(e) => setCode(e.target.value)}
              style={{ ...cnInput, width: "100%", marginTop: 4, fontFamily: "'SF Mono', monospace" }}
            />
          </label>
          <label style={{ fontSize: 12, color: CN.textSecondary }}>
            jurisdiction_scope
            <select value={scope} onChange={(e) => setScope(e.target.value)} style={{ ...cnInput, width: "100%", marginTop: 4 }}>
              {SCOPES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <label style={{ fontSize: 12, color: CN.textSecondary, gridColumn: "span 2" }}>
            override_chain_id (optional)
            <input
              type="text"
              placeholder="e.g. OC-CN-FTZ-SHA-2024-001"
              value={chainId}
              onChange={(e) => setChainId(e.target.value)}
              style={{ ...cnInput, width: "100%", marginTop: 4, fontFamily: "'SF Mono', monospace" }}
            />
          </label>
        </div>
      )}

      {mode === "batch" && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, color: CN.textSecondary }}>
            NDJSON 输入 (每行一个 JSON 对象, 上限 1000 行)
            <textarea
              value={ndjson}
              onChange={(e) => setNdjson(e.target.value)}
              rows={8}
              placeholder={`{"argument_role":"rule","jurisdiction_code":"CN","jurisdiction_scope":"national"}\n{"argument_role":"analogy","jurisdiction_code":"CN-FTZ-SHA","jurisdiction_scope":"municipal"}`}
              style={{
                ...cnInput,
                width: "100%",
                marginTop: 4,
                fontFamily: "'SF Mono', Menlo, monospace",
                fontSize: 12,
                lineHeight: 1.5,
                resize: "vertical",
              }}
            />
          </label>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button
          onClick={mode === "single" ? submitSingle : submitBatch}
          disabled={loading}
          style={{ ...cnBtnPrimary, opacity: loading ? 0.6 : 1 }}
        >
          {loading ? "审核中…" : mode === "single" ? "审核" : "批量审核"}
        </button>
        <button
          onClick={() => {
            setRole("");
            setStrength("");
            setCode("");
            setScope("");
            setChainId("");
            setNdjson("");
            setSingle(null);
            setBatch(null);
            setError(null);
          }}
          style={cnBtn}
        >
          重置
        </button>
      </div>

      {error && (
        <div role="alert" style={{ ...cnCard, borderLeft: `3px solid ${CN.amber}`, background: CN.amberBg, color: CN.amber, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {mode === "single" && single && (
        <>
          <Verdict result={single} />
          <div style={cnCard}>
            <KVTable result={single} />
          </div>
        </>
      )}

      {mode === "batch" && batch && (
        <>
          <div
            style={{
              ...cnCard,
              borderLeft: `3px solid ${batch.defect_count === 0 ? CN.green : CN.red}`,
              marginBottom: 12,
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
            }}
          >
            <div>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>总计</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 800, color: CN.text, fontVariantNumeric: "tabular-nums" }}>
                {batch.count}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>CLEAN</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 800, color: CN.green, fontVariantNumeric: "tabular-nums" }}>
                {batch.clean_count}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>DEFECT</div>
              <div style={{ fontSize: "1.3rem", fontWeight: 800, color: CN.red, fontVariantNumeric: "tabular-nums" }}>
                {batch.defect_count}
              </div>
            </div>
          </div>
          <div style={{ maxHeight: 360, overflowY: "auto", border: `1px solid ${CN.border}`, borderRadius: 6 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead style={{ position: "sticky", top: 0, background: CN.bgElevated, zIndex: 1 }}>
                <tr>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>#</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>状态</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>缺陷</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontSize: 10, fontWeight: 700, color: CN.textMuted, textTransform: "uppercase", letterSpacing: "1px" }}>辖区</th>
                </tr>
              </thead>
              <tbody>
                {batch.results.map((r, i) => (
                  <tr key={i} style={{ borderTop: `1px solid ${CN.border}` }}>
                    <td style={{ padding: "6px 12px", color: CN.textMuted, fontVariantNumeric: "tabular-nums" }}>{i + 1}</td>
                    <td style={{ padding: "6px 12px" }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "2px 6px",
                          color: r.clean ? CN.green : CN.red,
                          background: r.clean ? CN.greenBg : CN.redBg,
                        }}
                      >
                        {r.clean ? "CLEAN" : "DEFECT"}
                      </span>
                    </td>
                    <td style={{ padding: "6px 12px" }}>
                      {r.defect_flags.length === 0 ? (
                        <span style={{ color: CN.textMuted }}>—</span>
                      ) : (
                        r.defect_flags.map((f) => <FlagChip key={f} code={f} />)
                      )}
                    </td>
                    <td style={{ padding: "6px 12px", color: CN.textSecondary, fontFamily: "'SF Mono', monospace" }}>
                      {r.consistency.code || "—"} / {r.consistency.scope || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
