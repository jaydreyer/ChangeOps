import { PolicyAnalysisEntryView } from "./components/policy-analysis-entry";
import { getPolicyAnalysisEntry } from "@/lib/api";

export default async function HomePage() {
  const result = await loadEntry();
  if (result.entry) {
    return <PolicyAnalysisEntryView entry={result.entry} />;
  }
  return (
    <main className="entry-shell">
      <section className="entry-card">
        <p className="eyebrow">Policy analysis unavailable</p>
        <h1>Unable to load the analysis entry</h1>
        <p className="error" role="alert">
          {result.message}
        </p>
      </section>
    </main>
  );
}

async function loadEntry() {
  try {
    const entry = await getPolicyAnalysisEntry();
    return { entry, message: "" };
  } catch (caught) {
    const message = caught instanceof Error ? caught.message.split("|").slice(1).join("|") : "";
    return {
      entry: null,
      message:
        message || "The ChangeOps API is unavailable. Check that the local stack is running.",
    };
  }
}
