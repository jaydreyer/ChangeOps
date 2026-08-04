import { CatalogBrowseView, CatalogUnavailable } from "../components/catalog-views";
import { getCatalogBrowse } from "@/lib/api";

const ORGANIZATION_ID = "org-acme-global-manufacturing";

export default async function CatalogPage() {
  const result = await loadCatalog();
  return result.catalog ? (
    <CatalogBrowseView catalog={result.catalog} />
  ) : (
    <CatalogUnavailable message={result.message} />
  );
}

async function loadCatalog() {
  try {
    return { catalog: await getCatalogBrowse(ORGANIZATION_ID), message: "" };
  } catch (caught) {
    return { catalog: null, message: catalogErrorMessage(caught) };
  }
}

function catalogErrorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message.split("|").slice(1).join("|") || caught.message;
  }
  return "The ChangeOps API is unavailable. Check that the local stack is running.";
}
