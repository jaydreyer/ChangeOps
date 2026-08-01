import Link from "next/link";
import { WorkbenchView } from "@/app/components/workbench";
import { getWorkbench } from "@/lib/api";

export default async function ApprovalPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const result = await loadWorkbench(runId);
  if (result.workbench) {
    return <WorkbenchView initialWorkbench={result.workbench} />;
  }
  return (
    <main className="entry-shell">
      <section className="entry-card">
        <p className="eyebrow">Approval workbench unavailable</p>
        <h1>Unable to load this approval run</h1>
        <p className="error" role="alert">
          {result.message}
        </p>
        <Link href="/">Return to assessment entry</Link>
      </section>
    </main>
  );
}

async function loadWorkbench(runId: string) {
  try {
    return { workbench: await getWorkbench(runId), message: "" };
  } catch (caught) {
    const message = caught instanceof Error ? caught.message.split("|").slice(1).join("|") : "";
    return { workbench: null, message: message || "The ChangeOps API is unavailable." };
  }
}
