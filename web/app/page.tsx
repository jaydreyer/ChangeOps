import { AssessmentEntry } from "./components/assessment-entry";

export default function HomePage() {
  return (
    <main className="entry-shell">
      <section className="entry-card" aria-labelledby="entry-title">
        <p className="eyebrow">ChangeOps · Milestone 4</p>
        <h1 id="entry-title">Human Approval Workbench</h1>
        <p className="lede">
          Open a completed impact assessment to create or retrieve its durable approval run.
        </p>
        <AssessmentEntry />
        <aside className="notice">
          <strong>Approval alone does not execute actions.</strong>
          <span>
            {" "}
            An authorized user must explicitly execute the supported training-assignment command
            against the simulated Learning System. Other approved actions remain visible and
            unsupported.
          </span>
        </aside>
      </section>
    </main>
  );
}
