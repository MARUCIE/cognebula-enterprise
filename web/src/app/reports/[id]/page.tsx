/* Report Detail -- "/reports/[id]"
   Jobs: "AI置信度+源追溯+变动高亮, NOT a PDF viewer"
   Drucker: "价值闭环的核心证明——AI生成+人工审批的完整动作" */

import { REPORT_IDS, getReportById } from "../../lib/reports";
import { ReportDetailClient } from "../../components/ReportDetailClient";

export function generateStaticParams() {
  return REPORT_IDS.map((id) => ({ id }));
}

export default async function ReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const report = getReportById(id);
  if (!report) return <div>报告不存在</div>;

  return <ReportDetailClient report={report} />;
}
