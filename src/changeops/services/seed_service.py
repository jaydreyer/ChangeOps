from datetime import date

from sqlalchemy.orm import Session

from changeops.db.models import (
    Organization,
    PolicyChange,
    PolicyChangeQuestion,
    TrainingRecord,
    Trip,
    Worker,
)

ORGANIZATION_ID = "org-acme-global-manufacturing"
POLICY_CHANGE_ID = "policy-international-travel-2026-09"
COURSE_IDENTIFIER = "international-travel-security"

POLICY_TEXT = """Effective September 1, 2026, U.S.-based employees and contractors traveling
internationally for business must complete the International Travel Security course before
departure.

Manager approval is required before any nonrefundable international travel is booked.

Travel booked before September 1, 2026 is exempt from the new manager-approval requirement.
However, travelers departing on or after September 1, 2026 must still complete the
International Travel Security course before departure.

Travel between the United States and Canada is excluded from this policy."""

STRUCTURED_RULES = {
    "kind": "international_travel",
    "schema_version": 1,
    "worker_scope": {
        "assigned_work_country": "US",
        "worker_types": ["employee", "contractor"],
    },
    "trip_scope": {
        "origin_country": "US",
        "excluded_destination_countries": ["US", "CA"],
    },
    "manager_approval": {
        "booking_before_effective_date_is_exempt": True,
    },
    "security_training": {
        "course_identifier": COURSE_IDENTIFIER,
    },
}

WORKERS = [
    {
        "id": "worker-sarah-johnson",
        "full_name": "Sarah Johnson",
        "worker_type": "employee",
        "department": "Human Resources",
        "manager_name": "Mike Wilson",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-marcus-lee",
        "full_name": "Marcus Lee",
        "worker_type": "contractor",
        "department": "Information Technology",
        "manager_name": "Anita Patel",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-elena-garcia",
        "full_name": "Elena García",
        "worker_type": "employee",
        "department": "Finance",
        "manager_name": "Carlos Martín",
        "assigned_work_country": "ES",
    },
    {
        "id": "worker-david-miller",
        "full_name": "David Miller",
        "worker_type": "employee",
        "department": "Sales",
        "manager_name": "Jennifer Brooks",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-priya-shah",
        "full_name": "Priya Shah",
        "worker_type": "employee",
        "department": "Product Management",
        "manager_name": "Robert Chen",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-thomas-green",
        "full_name": "Thomas Green",
        "worker_type": "employee",
        "department": "Operations",
        "manager_name": "Linda Evans",
        "assigned_work_country": "US",
    },
]

TRIPS = [
    {
        "id": "trip-sarah-france",
        "worker_id": "worker-sarah-johnson",
        "origin_country": "US",
        "destination_country": "FR",
        "departure_date": date(2026, 9, 15),
        "booking_date": None,
        "booking_status": "planned",
    },
    {
        "id": "trip-marcus-japan",
        "worker_id": "worker-marcus-lee",
        "origin_country": "US",
        "destination_country": "JP",
        "departure_date": date(2026, 10, 2),
        "booking_date": None,
        "booking_status": "planned",
    },
    {
        "id": "trip-elena-united-states",
        "worker_id": "worker-elena-garcia",
        "origin_country": "ES",
        "destination_country": "US",
        "departure_date": date(2026, 9, 20),
        "booking_date": date(2026, 8, 25),
        "booking_status": "booked",
    },
    {
        "id": "trip-david-germany",
        "worker_id": "worker-david-miller",
        "origin_country": "US",
        "destination_country": "DE",
        "departure_date": date(2026, 9, 10),
        "booking_date": date(2026, 8, 20),
        "booking_status": "booked",
    },
    {
        "id": "trip-priya-canada",
        "worker_id": "worker-priya-shah",
        "origin_country": "US",
        "destination_country": "CA",
        "departure_date": date(2026, 9, 18),
        "booking_date": None,
        "booking_status": "planned",
    },
    {
        "id": "trip-thomas-mexico",
        "worker_id": "worker-thomas-green",
        "origin_country": "US",
        "destination_country": "MX",
        "departure_date": date(2026, 8, 20),
        "booking_date": date(2026, 8, 1),
        "booking_status": "booked",
    },
]

TRAINING_RECORDS = [
    {
        "id": f"training-{worker['id']}",
        "worker_id": worker["id"],
        "course_identifier": COURSE_IDENTIFIER,
        "completion_status": (
            "completed" if worker["id"] == "worker-marcus-lee" else "not_completed"
        ),
        "completion_date": None,
    }
    for worker in WORKERS
]

QUESTIONS = [
    "How is “U.S.-based” officially determined in the source HR system?",
    "Does the policy apply to workers temporarily assigned to the United States?",
    "How long does the International Travel Security course remain valid?",
    "Who records and stores manager approval?",
    "Does approval apply per trip, per booking, or per traveler?",
    "Does a refundable reservation require approval before it becomes nonrefundable?",
    "Which team owns updates to the travel knowledge article?",
    "Are any countries subject to stricter security-review requirements outside this policy?",
]


def seed_database(session: Session) -> None:
    session.merge(
        Organization(
            id=ORGANIZATION_ID,
            name="Acme Global Manufacturing",
            industry="Manufacturing",
            headquarters="Minneapolis, Minnesota, United States",
        )
    )
    session.flush()

    session.merge(
        PolicyChange(
            id=POLICY_CHANGE_ID,
            organization_id=ORGANIZATION_ID,
            title="International Business Travel Approval and Security Training",
            owner="Corporate Security and Global Travel",
            version="1",
            effective_date=date(2026, 9, 1),
            policy_text=POLICY_TEXT,
            structured_rules=STRUCTURED_RULES,
        )
    )
    for worker in WORKERS:
        session.merge(Worker(organization_id=ORGANIZATION_ID, **worker))
    session.flush()

    for trip in TRIPS:
        session.merge(Trip(**trip))
    for training_record in TRAINING_RECORDS:
        session.merge(TrainingRecord(**training_record))
    for sequence, question in enumerate(QUESTIONS, start=1):
        session.merge(
            PolicyChangeQuestion(
                id=f"policy-question-{sequence}",
                policy_change_id=POLICY_CHANGE_ID,
                sequence=sequence,
                question=question,
            )
        )
