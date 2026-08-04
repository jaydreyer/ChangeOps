import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CatalogPage from "./page";
import { getCatalogBrowse } from "@/lib/api";

vi.mock("@/lib/api", () => ({ getCatalogBrowse: vi.fn() }));
vi.mock("../components/catalog-views", () => ({
  CatalogBrowseView: () => <div>Catalog browse</div>,
  CatalogUnavailable: ({ message }: { message: string }) => <div role="alert">{message}</div>,
}));

describe("catalog page", () => {
  it("renders a stable unavailable state when the API fails", async () => {
    vi.mocked(getCatalogBrowse).mockRejectedValue(
      new Error("catalog_projection_inconsistent|A relationship endpoint is missing."),
    );

    render(await CatalogPage());

    expect(screen.getByRole("alert")).toHaveTextContent("A relationship endpoint is missing.");
  });
});
