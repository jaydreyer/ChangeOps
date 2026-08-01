import { AssessmentEntry } from "./components/assessment-entry";

export default function HomePage() {
  return (
    <main className="entry-shell">
      <section className="entry-card" aria-labelledby="entry-title">
        <p className="eyebrow">ChangeOps · Milestone 3</p>
        <h1 id="entry-title">Human Approval Workbench</h1>
        <p className="lede">
          Open a completed impact assessment to create or retrieve its durable approval run.
        </p>
        <AssessmentEntry />
        <aside className="notice">
          <strong>Approval does not execute actions.</strong>
          <span> All execution states remain not_executed in this milestone.</span>
        </aside>
      </section>
    </main>
  );
}
