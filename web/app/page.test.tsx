import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HomePage from "./page";

vi.mock("./components/assessment-entry", () => ({
  AssessmentEntry: () => <div>Assessment entry</div>,
}));

describe("home page", () => {
  it("describes the narrow explicit Milestone 4 execution boundary", () => {
    render(<HomePage />);

    expect(screen.getByText("ChangeOps · Milestone 4")).toBeInTheDocument();
    expect(screen.getByText("Approval alone does not execute actions.")).toBeInTheDocument();
    expect(
      screen.getByText(/explicitly execute the supported training-assignment command/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Other approved actions remain visible and unsupported/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/All execution states remain not_executed/)).not.toBeInTheDocument();
  });
});
