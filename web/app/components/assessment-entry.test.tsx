import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AssessmentEntry } from "./assessment-entry";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("assessment entry", () => {
  it("renders a safe backend error message", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "approval_assessment_not_completed",
            message: "Approval requires a completed policy-analysis assessment.",
          },
        }),
        { status: 422, headers: { "content-type": "application/json" } },
      ),
    );
    render(<AssessmentEntry />);

    await user.type(screen.getByLabelText("Completed assessment ID"), "assessment-1");
    await user.click(screen.getByRole("button", { name: "Open workbench" }));

    expect(
      await screen.findByText("Approval requires a completed policy-analysis assessment."),
    ).toBeInTheDocument();
  });
});
