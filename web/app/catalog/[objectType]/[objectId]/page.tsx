import { CatalogObjectDetailView, CatalogUnavailable } from "../../../components/catalog-views";
import { getCatalogObject } from "@/lib/api";

export default async function CatalogObjectPage({
  params,
}: {
  params: Promise<{ objectType: string; objectId: string }>;
}) {
  const { objectType, objectId } = await params;
  const result = await loadCatalogObject(objectType, objectId);
  return result.detail ? (
    <CatalogObjectDetailView detail={result.detail} />
  ) : (
    <CatalogUnavailable message={result.message} />
  );
}

async function loadCatalogObject(objectType: string, objectId: string) {
  try {
    return { detail: await getCatalogObject(objectType, objectId), message: "" };
  } catch (caught) {
    return { detail: null, message: catalogErrorMessage(caught) };
  }
}

function catalogErrorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message.split("|").slice(1).join("|") || caught.message;
  }
  return "The ChangeOps API is unavailable. Check that the local stack is running.";
}
