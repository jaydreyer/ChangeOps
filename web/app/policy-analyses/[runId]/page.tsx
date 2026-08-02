import Link from "next/link";
import { PolicyAnalysisJourneyView } from "@/app/components/policy-analysis-journey";
import { getPolicyAnalysisJourney } from "@/lib/api";

export default async function PolicyAnalysisPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  const result = await loadJourney(runId);
  if (result.journey) {
    return <PolicyAnalysisJourneyView initialJourney={result.journey} />;
  }
  return (
    <main className="entry-shell">
      <section className="entry-card">
        <p className="eyebrow">Policy analysis unavailable</p>
        <h1>Unable to load this analysis journey</h1>
        <p className="error" role="alert">
          {result.message}
        </p>
        <Link href="/">Return to policy analysis</Link>
      </section>
    </main>
  );
}

async function loadJourney(runId: string) {
  try {
    const journey = await getPolicyAnalysisJourney(runId);
    return { journey, message: "" };
  } catch (caught) {
    const message = caught instanceof Error ? caught.message.split("|").slice(1).join("|") : "";
    return {
      journey: null,
      message: message || "The ChangeOps API is unavailable.",
    };
  }
}
