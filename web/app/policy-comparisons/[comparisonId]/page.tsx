import Link from "next/link";
import { PolicyComparisonView } from "@/app/components/policy-comparison";
import { getPolicyComparison } from "@/lib/api";

export default async function PolicyComparisonPage({
  params,
}: {
  params: Promise<{ comparisonId: string }>;
}) {
  const { comparisonId } = await params;
  const result = await loadComparison(comparisonId);
  if (result.comparison) {
    return <PolicyComparisonView comparison={result.comparison} />;
  }
  return (
    <main className="entry-shell">
      <section className="entry-card">
        <p className="eyebrow">Policy comparison unavailable</p>
        <h1>Unable to load this comparison</h1>
        <p className="error" role="alert">
          {result.message}
        </p>
        <Link href="/">Return to policy analysis and comparison</Link>
      </section>
    </main>
  );
}

async function loadComparison(comparisonId: string) {
  try {
    const comparison = await getPolicyComparison(comparisonId);
    return { comparison, message: "" };
  } catch (caught) {
    const message = caught instanceof Error ? caught.message.split("|").slice(1).join("|") : "";
    return {
      comparison: null,
      message: message || "The ChangeOps API is unavailable.",
    };
  }
}
