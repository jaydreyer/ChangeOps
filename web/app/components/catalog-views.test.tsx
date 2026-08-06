import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  CatalogBrowseView,
  CatalogObjectDetailView,
  PolicyRuleReferenceView,
} from "./catalog-views";
import type { CatalogBrowse, CatalogObjectDetail, PolicyRuleReference } from "@/lib/types";

const browse: CatalogBrowse = {
  organization: { id: "org-acme", name: "Acme Global Manufacturing" },
  catalog_context: {
    kind: "seeded_demonstration",
    label: "Seeded demonstration catalog",
    record_level_origin: "not_recorded",
  },
  catalog_counts: {
    enterprise_document: 4,
    enterprise_system: 3,
    training_course: 1,
  },
  assessment_context_counts: { worker: 12, team: 4, customer_commitment: 2 },
  objects: [
    {
      object_type: "enterprise_document",
      object_id: "document-manager-travel-approval-guide",
      display_name: "Manager Travel Approval Guide",
      description: null,
      owner: null,
      source_system: "Acme Knowledge",
      status: { value: "published", basis: "stored" },
      metadata: { document_type: "guide", version: "2" },
      relationship_count: 2,
    },
    {
      object_type: "enterprise_system",
      object_id: "system-travel-request",
      display_name: "Acme Travel Request",
      description: "Collects travel requests and manager approvals.",
      owner: null,
      source_system: null,
      status: { value: "active", basis: "normalized" },
      metadata: { system_type: "travel_workflow" },
      relationship_count: 2,
    },
    {
      object_type: "training_course",
      object_id: "international-travel-security",
      display_name: "International Travel Security",
      description: null,
      owner: null,
      source_system: null,
      status: { value: "active", basis: "normalized" },
      metadata: { course_code: "ITS-100", completion_record_count: 6 },
      relationship_count: 2,
    },
  ],
};

const relationship = {
  relationship_id: "dependency-policy-manager-guide",
  relationship_source_type: "policy_document_dependency" as const,
  relationship_type: "instructs_manager",
  explanation: "The manager guide documents approval responsibilities.",
  impact_classification: "review_required" as const,
  policy: {
    id: "policy-international-travel-2026-09",
    title: "International Business Travel Approval and Security Training",
    version: "1",
  },
  source: {
    object_type: "policy_rule_reference" as const,
    stable_key: "policy-international-travel-2026-09:MANAGER_APPROVAL_REQUIRED",
    display_name: "MANAGER_APPROVAL_REQUIRED",
    href: "/api/v1/policy-changes/policy-international-travel-2026-09/rule-references/MANAGER_APPROVAL_REQUIRED",
  },
  target: {
    object_type: "enterprise_document" as const,
    stable_key: "document-manager-travel-approval-guide",
    display_name: "Manager Travel Approval Guide",
    href: "/catalog/enterprise_document/document-manager-travel-approval-guide",
  },
  trust: {
    level: "trusted" as const,
    state: "persisted_typed_relationship" as const,
    basis: "deterministic_enterprise_relationship" as const,
    integrity: [
      "policy_change_foreign_key",
      "enterprise_document_foreign_key",
      "semantic_uniqueness",
    ],
    used_deterministically: true as const,
  },
  provenance: {
    classification: "seeded_demonstration" as const,
    source_label: "Seeded demonstration data" as const,
    creator: null,
    owning_authority: "ChangeOps demonstration seed",
    reference: "changeops.seed.relationships.v1",
    recorded_at: "2026-08-06T00:00:00Z",
    approval: null,
    ai_involvement: "none" as const,
  },
};

const detail: CatalogObjectDetail = {
  object: {
    ...browse.objects[0],
    organization_id: "org-acme",
    record_provenance: {
      classification: "not_recorded",
      catalog_context: "seeded_demonstration",
    },
  },
  external_source_state: "not_imported",
  external_source: null,
  relationships: [
    relationship,
    {
      ...relationship,
      relationship_id: "dependency-policy-manager-guide-proposed",
      policy: {
        id: "policy-international-travel-proposed-2026-10",
        title: "Proposed International Business Travel Revision",
        version: "proposed-draft",
      },
      source: {
        ...relationship.source,
        stable_key:
          "policy-international-travel-proposed-2026-10:MANAGER_APPROVAL_REQUIRED",
      },
    },
  ],
  assessment_usage: {
    statement: "The deterministic enterprise analyzer uses this dependency.",
    changes_assessment_behavior: false,
  },
};

describe("enterprise knowledge catalog views", () => {
  it("renders primary categories separately from compact assessment context", () => {
    render(<CatalogBrowseView catalog={browse} />);

    expect(
      screen.getByRole("heading", { name: "What enterprise knowledge does ChangeOps use?" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Seeded demonstration catalog")).toBeInTheDocument();
    expect(
      screen.getByText(
        "This is fictional demonstration data. Object-level origin is not recorded; seeded relationship origin is available on each object detail.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Catalog categories" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Open Manager Travel Approval Guide details" }),
    ).toHaveAttribute(
      "href",
      "/catalog/enterprise_document/document-manager-travel-approval-guide",
    );

    const context = screen.getByRole("heading", { name: "Other authoritative inputs" }).closest("section");
    expect(context).not.toBeNull();
    expect(within(context!).getByText("Workers")).toBeInTheDocument();
    expect(within(context!).getByText("12")).toBeInTheDocument();
    expect(within(context!).queryByRole("link")).not.toBeInTheDocument();
  });

  it("keeps baseline and proposed dependency rows distinct and technical details collapsed", () => {
    render(<CatalogObjectDetailView detail={detail} />);

    expect(screen.getByRole("heading", { name: "Manager Travel Approval Guide" })).toBeInTheDocument();
    expect(screen.getByText("Not recorded")).toBeInTheDocument();
    expect(screen.getByText("International Business Travel Approval and Security Training · 1")).toBeInTheDocument();
    expect(screen.getByText("Proposed International Business Travel Revision · proposed-draft")).toBeInTheDocument();
    expect(screen.getAllByText("Instructs Manager")).toHaveLength(2);
    expect(screen.getAllByRole("heading", { name: "Relationship Provenance" })).toHaveLength(2);
    expect(screen.getAllByText("Seeded demonstration data")).toHaveLength(2);
    expect(screen.getAllByText("Trusted")).toHaveLength(2);
    expect(
      screen.getAllByText("None — AI did not create or infer this relationship."),
    ).toHaveLength(2);
    expect(
      screen.getAllByText(
        "Manager Travel Approval Guide → MANAGER_APPROVAL_REQUIRED",
      ),
    ).toHaveLength(2);
    expect(screen.getByText("Confluence metadata has not been imported.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Explain this policy rule" })[0]).toHaveAttribute(
      "href",
      "/catalog/policy-rules/policy-international-travel-2026-09/MANAGER_APPROVAL_REQUIRED",
    );
    for (const summary of screen.getAllByText(/Technical relationship details|Technical object identity/)) {
      expect(summary.closest("details")).not.toHaveAttribute("open");
    }
    expect(
      screen.queryByRole("button", { name: /edit|import|approve|refresh|search/i }),
    ).not.toBeInTheDocument();
  });

  it("shows validated read-only Confluence identity and an external link", () => {
    const imported: CatalogObjectDetail = {
      ...detail,
      external_source_state: "imported",
      external_source: {
        provider: "confluence_cloud",
        provider_label: "Confluence Cloud",
        external_page_id: "123456789",
        external_title: "Manager Travel Approval Guide",
        canonical_url: "https://acme.atlassian.net/wiki/spaces/TRAVEL/pages/123456789",
        space_id: "987654321",
        space_key: "TRAVEL",
        external_version: 7,
        external_status: "current",
        source_updated_at: "2026-08-01T16:30:00Z",
        imported_at: "2026-08-04T15:00:00Z",
        refreshed_at: "2026-08-04T15:10:00Z",
        source_fingerprint: "a".repeat(64),
        last_refresh_result: "already_current",
        last_refresh_message: "Confluence metadata is already current.",
        last_refresh_attempted_at: "2026-08-04T15:10:00Z",
      },
    };

    render(<CatalogObjectDetailView detail={imported} />);

    expect(screen.getByText("Confluence Cloud")).toBeInTheDocument();
    expect(screen.getByText("123456789")).toBeInTheDocument();
    expect(screen.getByText("TRAVEL · 987654321")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open in Confluence" })).toHaveAttribute(
      "href",
      imported.external_source?.canonical_url,
    );
    expect(screen.getByText("Technical source details").closest("details")).not.toHaveAttribute(
      "open",
    );
  });

  it("shows last-known-good metadata as stale after a failed refresh", () => {
    const stale: CatalogObjectDetail = {
      ...detail,
      external_source_state: "imported",
      external_source: {
        provider: "confluence_cloud",
        provider_label: "Confluence Cloud",
        external_page_id: "123456789",
        external_title: "Manager Travel Approval Guide",
        canonical_url: "https://acme.atlassian.net/wiki/spaces/TRAVEL/pages/123456789",
        space_id: "987654321",
        space_key: "TRAVEL",
        external_version: 7,
        external_status: "current",
        source_updated_at: "2026-08-01T16:30:00Z",
        imported_at: "2026-08-04T15:00:00Z",
        refreshed_at: "2026-08-04T15:10:00Z",
        source_fingerprint: "a".repeat(64),
        last_refresh_result: "permission_denied",
        last_refresh_message: "Confluence denied access to the configured page or space.",
        last_refresh_attempted_at: "2026-08-04T16:10:00Z",
      },
    };

    render(<CatalogObjectDetailView detail={stale} />);

    expect(
      screen.getByText("Last refresh failed; showing last-known-good metadata."),
    ).toBeInTheDocument();
    expect(screen.getByText(/denied access/i)).toBeInTheDocument();
  });

  it("explains a policy-scoped rule and links back to each typed target", () => {
    const reference: PolicyRuleReference = {
      stable_key: "policy-international-travel-2026-09:MANAGER_APPROVAL_REQUIRED",
      policy: relationship.policy,
      rule_code: "MANAGER_APPROVAL_REQUIRED",
      structured_rule_reference: {
        field_path: "manager_approval",
        label: "Manager approval rule",
        mapping_status: "supported",
      },
      relationships: [
        {
          relationship_id: relationship.relationship_id,
          relationship_type: relationship.relationship_type,
          target_type: "enterprise_document",
          target_id: relationship.target.stable_key,
          target_name: relationship.target.display_name,
          target_href: relationship.target.href,
        },
      ],
      authority_boundary: {
        is_standalone_persisted_rule: false,
        relationship_source: "persisted_dependency_rows",
        assessment_use: "deterministic",
      },
    };

    render(<PolicyRuleReferenceView reference={reference} />);

    expect(screen.getByRole("heading", { name: "MANAGER_APPROVAL_REQUIRED" })).toBeInTheDocument();
    expect(screen.getByText(/not from a standalone rule table/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open catalog object" })).toHaveAttribute(
      "href",
      relationship.target.href,
    );
    expect(screen.getByText("Policy-rule authority boundary").closest("details")).not.toHaveAttribute("open");
  });
});
