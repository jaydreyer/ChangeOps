import Link from "next/link";
import { WorkbenchView } from "@/app/components/workbench";
import { getExecutionPreparation, getWorkbench } from "@/lib/api";

export default async function ApprovalPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  const result = await loadWorkbench(runId);
  if (result.workbench) {
    return (
      <WorkbenchView
        initialWorkbench={result.workbench}
        initialPreparation={result.preparation}
      />
    );
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
    const workbench = await getWorkbench(runId);
    const preparation =
      workbench.run.status === "completed" ? await getExecutionPreparation(runId) : null;
    return { workbench, preparation, message: "" };
  } catch (caught) {
    const message = caught instanceof Error ? caught.message.split("|").slice(1).join("|") : "";
    return {
      workbench: null,
      preparation: null,
      message: message || "The ChangeOps API is unavailable.",
    };
  }
}
