"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { parseApiError } from "@/lib/api";

export function AssessmentEntry() {
  const router = useRouter();
  const [assessmentId, setAssessmentId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch(
        `/api/v1/impact-assessments/${encodeURIComponent(assessmentId.trim())}/approval-run`,
        { method: "POST" },
      );
      if (!response.ok) {
        const apiError = await parseApiError(response);
        setError(apiError.message);
        return;
      }
      const run = (await response.json()) as { id: string };
      router.push(`/approvals/${run.id}`);
    } catch {
      setError("The ChangeOps API is unavailable. Check that the local stack is running.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="entry-form">
      <label htmlFor="assessment-id">Completed assessment ID</label>
      <div className="input-row">
        <input
          id="assessment-id"
          value={assessmentId}
          onChange={(event) => setAssessmentId(event.target.value)}
          placeholder="UUID"
          required
        />
        <button type="submit" disabled={submitting}>
          {submitting ? "Opening…" : "Open workbench"}
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
