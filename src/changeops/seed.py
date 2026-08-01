from changeops.db.session import SessionLocal
from changeops.services.demo_assessment_seed_service import seed_demo_assessment
from changeops.services.seed_service import seed_database


def main() -> None:
    with SessionLocal.begin() as session:
        seed_database(session)
    with SessionLocal() as session:
        assessment_id = seed_demo_assessment(session)
    print(f"Seeded demonstration assessment: {assessment_id}")


if __name__ == "__main__":
    main()
