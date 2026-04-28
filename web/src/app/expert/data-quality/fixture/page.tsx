import { DataQualityWorkbench } from "../page";
import { PROD_SNAPSHOT_FIXTURE } from "../prodSnapshot";

export default function DataQualityFixturePage() {
  return (
    <DataQualityWorkbench
      initialSnapshot={PROD_SNAPSHOT_FIXTURE}
      fixtureLabel="prod-snapshot · 2026-04-23 app.hegui.org"
    />
  );
}
