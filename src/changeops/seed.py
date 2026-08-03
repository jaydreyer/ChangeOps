from changeops.db.session import SessionLocal
from changeops.services.seed_service import seed_database


def main() -> None:
    with SessionLocal.begin() as session:
        seed_database(session)
    print("Seeded fictional enterprise catalog and international-travel policy.")


if __name__ == "__main__":
    main()
