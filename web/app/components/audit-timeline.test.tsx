import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { AuditTimeline as AuditTimelineType } from "@/lib/types";
import { AuditTimeline } from "./audit-timeline";

const timeline: AuditTimelineType = {
  subject_type: "policy_analysis_run",
  subject_id: "run-1",
  entries: [
    {
      entry_key: "attempt-1:attempted",
      occurred_at: "2026-08-01T12:00:00Z",
      actor_category: "ai_assisted",
      actor_identity: null,
      event_type: "extraction_attempted",
      title: "Policy meaning extraction attempted",
      description: "An AI-assisted extractor proposed structured policy rules.",
      outcome: "completed",
      artifact: {
        artifact_type: "policy_extraction_attempt",
        artifact_id: "attempt-1",
        href: "/policy-analyses/run-1#extraction-heading",
      },
      metadata: { model_identifier: "extractor-v1" },
    },
    {
      entry_key: "decision-1:recorded",
      occurred_at: "2026-08-01T12:01:00Z",
      actor_category: "human",
      actor_identity: "reviewer@example.com",
      event_type: "human_action_decision_recorded",
      title: "Action approved",
      description: "Approved with evidence.",
      outcome: "succeeded",
      artifact: {
        artifact_type: "action_review_decision",
        artifact_id: "decision-1",
        href: null,
      },
      metadata: {},
    },
    {
      entry_key: "jira-1:created",
      occurred_at: "2026-08-01T12:02:00Z",
      actor_category: "external_system",
      actor_identity: "jira",
      event_type: "jira_issue_created",
      title: "Jira issue created",
      description: "Jira created issue ECM-42.",
      outcome: "succeeded",
      artifact: {
        artifact_type: "jira_issue",
        artifact_id: "jira-1",
        href: "https://jira.example/browse/ECM-42",
      },
      metadata: { issue_key: "ECM-42" },
    },
  ],
};

describe("audit timeline", () => {
  it("renders API order, actor/outcome labels, identities, and authoritative artifacts", () => {
    render(<AuditTimeline timeline={timeline} />);

    const entries = screen.getAllByRole("listitem");
    expect(within(entries[0]).getByText("Policy meaning extraction attempted")).toBeVisible();
    expect(within(entries[1]).getByText("Action approved")).toBeVisible();
    expect(within(entries[2]).getByText("Jira issue created")).toBeVisible();
    expect(screen.getByText("AI-assisted")).toBeVisible();
    expect(screen.getByText("Human")).toBeVisible();
    expect(screen.getByText("External system")).toBeVisible();
    expect(screen.getAllByText("Succeeded")).toHaveLength(2);
    expect(screen.getByText("reviewer@example.com")).toBeVisible();
    expect(screen.getByText(/Action review decision · decision-1/)).toBeVisible();
  });

  it("links only artifacts with hrefs and marks external destinations", () => {
    render(<AuditTimeline timeline={timeline} />);

    expect(
      screen.getByRole("link", { name: /Policy extraction attempt · attempt-1/ }),
    ).toHaveAttribute("href", "/policy-analyses/run-1#extraction-heading");
    expect(screen.queryByRole("link", { name: /decision-1/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Jira issue · jira-1/ })).toHaveAttribute(
      "target",
      "_blank",
    );
  });

  it("exposes secondary metadata through an accessible disclosure", async () => {
    const user = userEvent.setup();
    render(<AuditTimeline timeline={timeline} />);

    const details = screen.getAllByText("View supporting details")[0].closest("details");
    expect(details).not.toHaveAttribute("open");
    await user.click(screen.getAllByText("View supporting details")[0]);
    expect(details).toHaveAttribute("open");
    expect(screen.getByText("extractor-v1")).toBeVisible();
  });

  it("handles an empty timeline", () => {
    render(<AuditTimeline timeline={{ ...timeline, entries: [] }} />);

    expect(
      screen.getByText("No authoritative lifecycle records are available for this journey yet."),
    ).toBeVisible();
  });

  it("handles an API failure using an alert", () => {
    render(<AuditTimeline timeline={null} errorMessage="The audit timeline is unavailable." />);

    expect(screen.getByRole("alert")).toHaveTextContent("The audit timeline is unavailable.");
  });
});
