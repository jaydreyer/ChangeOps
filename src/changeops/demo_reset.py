from changeops.config import get_settings
from changeops.db.session import SessionLocal
from changeops.services.demo_reset_service import reset_from_environment


def main() -> None:
    settings = get_settings()
    with SessionLocal.begin() as session:
        summary = reset_from_environment(session, settings.database_url)
    print(
        "Demo reset complete: "
        f"{summary.policy_comparisons} policy comparisons, "
        f"{summary.policy_analysis_runs} analysis runs, "
        f"{summary.approval_runs} approval runs, "
        f"{summary.execution_results} execution results."
    )


if __name__ == "__main__":
    main()
