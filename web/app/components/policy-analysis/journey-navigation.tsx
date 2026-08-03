import type { PolicyAnalysisJourney } from "@/lib/types";
import { humanize } from "./formatters";
import { deriveJourneyStates, journeyStepNames } from "./journey-state";

export function JourneyNavigation({ journey }: { journey: PolicyAnalysisJourney }) {
  const states = deriveJourneyStates(journey);
  return (
    <nav className="journey-nav" aria-label="ChangeOps workflow">
      <ol>
        {journeyStepNames.map((name, index) => (
          <li
            key={name}
            className={states[index]}
            aria-current={states[index] === "current" ? "step" : undefined}
          >
            <span>{index + 1}</span>
            <strong>{name}</strong>
            <small>{humanize(states[index])}</small>
          </li>
        ))}
      </ol>
    </nav>
  );
}
