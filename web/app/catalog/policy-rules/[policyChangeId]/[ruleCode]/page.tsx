import { CatalogUnavailable, PolicyRuleReferenceView } from "../../../../components/catalog-views";
import { getPolicyRuleReference } from "@/lib/api";

export default async function PolicyRuleReferencePage({
  params,
}: {
  params: Promise<{ policyChangeId: string; ruleCode: string }>;
}) {
  const { policyChangeId, ruleCode } = await params;
  const result = await loadRuleReference(policyChangeId, ruleCode);
  return result.reference ? (
    <PolicyRuleReferenceView reference={result.reference} />
  ) : (
    <CatalogUnavailable message={result.message} />
  );
}

async function loadRuleReference(policyChangeId: string, ruleCode: string) {
  try {
    return {
      reference: await getPolicyRuleReference(policyChangeId, ruleCode),
      message: "",
    };
  } catch (caught) {
    return { reference: null, message: catalogErrorMessage(caught) };
  }
}

function catalogErrorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message.split("|").slice(1).join("|") || caught.message;
  }
  return "The ChangeOps API is unavailable. Check that the local stack is running.";
}
