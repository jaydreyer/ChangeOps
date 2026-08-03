from datetime import date

from sqlalchemy.orm import Session

from changeops.db.models import (
    CommitmentAssignment,
    CustomerCommitment,
    EnterpriseDocument,
    EnterpriseSystem,
    Organization,
    PolicyChange,
    PolicyChangeQuestion,
    PolicyDocumentDependency,
    PolicySystemDependency,
    PolicyTrainingDependency,
    Team,
    TrainingCourse,
    TrainingRecord,
    Trip,
    Worker,
    WorkerTeamMembership,
)

ORGANIZATION_ID = "org-acme-global-manufacturing"
POLICY_CHANGE_ID = "policy-international-travel-2026-09"
PROPOSED_POLICY_CHANGE_ID = "policy-international-travel-proposed-2026-10"
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

PROPOSED_POLICY_TEXT = """Effective October 1, 2026, U.S.-based employees traveling
internationally for business must complete the International Travel Security course before
departure.

Manager approval is required before any nonrefundable international travel is booked.

Travel booked before October 1, 2026 is exempt from the new manager-approval requirement.
However, travelers departing on or after October 1, 2026 must still complete the
International Travel Security course before departure.

Travel between the United States, Canada, and Mexico is excluded from this policy."""

PROPOSED_STRUCTURED_RULES = {
    "kind": "international_travel",
    "schema_version": 1,
    "worker_scope": {
        "assigned_work_country": "US",
        "worker_types": ["employee"],
    },
    "trip_scope": {
        "origin_country": "US",
        "excluded_destination_countries": ["US", "CA", "MX"],
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
        "manager_worker_id": "worker-manager-mike-wilson",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-marcus-lee",
        "full_name": "Marcus Lee",
        "worker_type": "contractor",
        "department": "Information Technology",
        "manager_name": "Anita Patel",
        "manager_worker_id": "worker-manager-anita-patel",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-elena-garcia",
        "full_name": "Elena García",
        "worker_type": "employee",
        "department": "Finance",
        "manager_name": "Carlos Martín",
        "manager_worker_id": "worker-manager-carlos-martin",
        "assigned_work_country": "ES",
    },
    {
        "id": "worker-david-miller",
        "full_name": "David Miller",
        "worker_type": "employee",
        "department": "Sales",
        "manager_name": "Jennifer Brooks",
        "manager_worker_id": "worker-manager-jennifer-brooks",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-priya-shah",
        "full_name": "Priya Shah",
        "worker_type": "employee",
        "department": "Product Management",
        "manager_name": "Robert Chen",
        "manager_worker_id": "worker-manager-robert-chen",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-thomas-green",
        "full_name": "Thomas Green",
        "worker_type": "employee",
        "department": "Operations",
        "manager_name": "Linda Evans",
        "manager_worker_id": "worker-manager-linda-evans",
        "assigned_work_country": "US",
    },
]

MANAGERS = [
    {
        "id": "worker-manager-mike-wilson",
        "full_name": "Mike Wilson",
        "worker_type": "employee",
        "department": "People Operations",
        "manager_name": "Executive Leadership",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-manager-anita-patel",
        "full_name": "Anita Patel",
        "worker_type": "employee",
        "department": "Technology Operations",
        "manager_name": "Executive Leadership",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-manager-carlos-martin",
        "full_name": "Carlos Martín",
        "worker_type": "employee",
        "department": "Finance",
        "manager_name": "Executive Leadership",
        "assigned_work_country": "ES",
    },
    {
        "id": "worker-manager-jennifer-brooks",
        "full_name": "Jennifer Brooks",
        "worker_type": "employee",
        "department": "Customer Delivery",
        "manager_name": "Executive Leadership",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-manager-robert-chen",
        "full_name": "Robert Chen",
        "worker_type": "employee",
        "department": "Product Management",
        "manager_name": "Executive Leadership",
        "assigned_work_country": "US",
    },
    {
        "id": "worker-manager-linda-evans",
        "full_name": "Linda Evans",
        "worker_type": "employee",
        "department": "Operations",
        "manager_name": "Executive Leadership",
        "assigned_work_country": "US",
    },
]

TEAMS = [
    {
        "id": "team-people-operations",
        "name": "People Operations",
        "manager_worker_id": "worker-manager-mike-wilson",
    },
    {
        "id": "team-technology-operations",
        "name": "Technology Operations",
        "manager_worker_id": "worker-manager-anita-patel",
    },
    {
        "id": "team-customer-delivery",
        "name": "Customer Delivery",
        "manager_worker_id": "worker-manager-jennifer-brooks",
    },
    {
        "id": "team-domestic-operations",
        "name": "Domestic Operations",
        "manager_worker_id": "worker-manager-linda-evans",
    },
]

TEAM_MEMBERSHIPS = [
    {
        "id": "membership-sarah-people-operations",
        "worker_id": "worker-sarah-johnson",
        "team_id": "team-people-operations",
    },
    {
        "id": "membership-marcus-technology-operations",
        "worker_id": "worker-marcus-lee",
        "team_id": "team-technology-operations",
    },
    {
        "id": "membership-david-customer-delivery",
        "worker_id": "worker-david-miller",
        "team_id": "team-customer-delivery",
    },
    {
        "id": "membership-elena-domestic-operations",
        "worker_id": "worker-elena-garcia",
        "team_id": "team-domestic-operations",
    },
    {
        "id": "membership-priya-domestic-operations",
        "worker_id": "worker-priya-shah",
        "team_id": "team-domestic-operations",
    },
    {
        "id": "membership-thomas-domestic-operations",
        "worker_id": "worker-thomas-green",
        "team_id": "team-domestic-operations",
    },
]

SYSTEMS = [
    {
        "id": "system-travel-request",
        "name": "Acme Travel Request",
        "system_type": "travel_workflow",
        "description": "Collects travel requests and manager approvals.",
        "active": True,
    },
    {
        "id": "system-learning-management",
        "name": "Acme Learning Hub",
        "system_type": "learning_management",
        "description": "Tracks course assignments and completions.",
        "active": True,
    },
    {
        "id": "system-expense-management",
        "name": "Acme Expense",
        "system_type": "expense_management",
        "description": "Processes employee expense reports.",
        "active": True,
    },
]

DOCUMENTS = [
    {
        "id": "document-international-travel-policy",
        "title": "International Business Travel Policy",
        "document_type": "policy",
        "source_system": "Acme Knowledge",
        "version": "1",
        "status": "published",
    },
    {
        "id": "kb-international-travel-booking",
        "title": "Booking International Business Travel",
        "document_type": "knowledge_article",
        "source_system": "Acme Knowledge",
        "version": "3",
        "status": "published",
    },
    {
        "id": "document-manager-travel-approval-guide",
        "title": "Manager Travel Approval Guide",
        "document_type": "guide",
        "source_system": "Acme Knowledge",
        "version": "2",
        "status": "published",
    },
    {
        "id": "document-expense-submission-guide",
        "title": "Expense Submission Guide",
        "document_type": "guide",
        "source_system": "Acme Knowledge",
        "version": "4",
        "status": "published",
    },
]

SYSTEM_DEPENDENCIES = [
    {
        "id": "dependency-policy-travel-request",
        "rule_code": "MANAGER_APPROVAL_REQUIRED",
        "system_id": "system-travel-request",
        "relationship_type": "supports_approval_workflow",
        "explanation": "The travel-request system implements manager approval handling.",
    },
    {
        "id": "dependency-policy-learning-management",
        "rule_code": "TRAINING_REQUIRED",
        "system_id": "system-learning-management",
        "relationship_type": "verifies_training_completion",
        "explanation": "The learning system verifies and assigns required travel training.",
    },
]

DOCUMENT_DEPENDENCIES = [
    {
        "id": "dependency-policy-primary-document",
        "rule_code": "POLICY_CHANGE",
        "document_id": "document-international-travel-policy",
        "relationship_type": "contains_changed_policy",
        "impact_classification": "update_required",
        "explanation": "The source policy document must reflect the approved policy change.",
    },
    {
        "id": "dependency-policy-booking-article",
        "rule_code": "MANAGER_APPROVAL_REQUIRED",
        "document_id": "kb-international-travel-booking",
        "relationship_type": "explains_changed_process",
        "impact_classification": "update_required",
        "explanation": "The booking article explains the process changed by the approval rule.",
    },
    {
        "id": "dependency-policy-manager-guide",
        "rule_code": "MANAGER_APPROVAL_REQUIRED",
        "document_id": "document-manager-travel-approval-guide",
        "relationship_type": "instructs_manager",
        "impact_classification": "review_required",
        "explanation": "The manager guide documents approval responsibilities.",
    },
]

COMMITMENTS = [
    {
        "id": "commitment-northwind-onsite",
        "customer_name": "Northwind Renewable Energy",
        "commitment_type": "onsite_delivery",
        "description": "Provide an on-site policy workshop in Paris.",
        "start_date": date(2026, 9, 14),
        "end_date": date(2026, 9, 18),
        "status": "active",
    },
    {
        "id": "commitment-contoso-launch",
        "customer_name": "Contoso Retail",
        "commitment_type": "implementation_launch",
        "description": "Support a remote implementation launch.",
        "start_date": date(2026, 10, 10),
        "end_date": date(2026, 10, 12),
        "status": "active",
    },
]

COMMITMENT_ASSIGNMENTS = [
    {
        "id": "assignment-northwind-sarah",
        "commitment_id": "commitment-northwind-onsite",
        "worker_id": "worker-sarah-johnson",
        "assignment_role": "workshop_lead",
        "required": True,
    },
    {
        "id": "assignment-contoso-marcus",
        "commitment_id": "commitment-contoso-launch",
        "worker_id": "worker-marcus-lee",
        "assignment_role": "technical_lead",
        "required": True,
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
        "completion_date": (date(2026, 7, 1) if worker["id"] == "worker-marcus-lee" else None),
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
    session.merge(
        PolicyChange(
            id=PROPOSED_POLICY_CHANGE_ID,
            organization_id=ORGANIZATION_ID,
            title="Proposed International Business Travel Revision",
            owner="Corporate Security and Global Travel",
            version="proposed-draft",
            effective_date=date(2026, 10, 1),
            policy_text=PROPOSED_POLICY_TEXT,
            structured_rules=PROPOSED_STRUCTURED_RULES,
        )
    )
    for manager in MANAGERS:
        session.merge(Worker(organization_id=ORGANIZATION_ID, **manager))
    session.flush()

    for team in TEAMS:
        session.merge(Team(organization_id=ORGANIZATION_ID, **team))
    session.flush()

    for worker in WORKERS:
        session.merge(Worker(organization_id=ORGANIZATION_ID, **worker))
    session.flush()
    for membership in TEAM_MEMBERSHIPS:
        session.merge(WorkerTeamMembership(**membership))

    session.merge(
        TrainingCourse(
            id=COURSE_IDENTIFIER,
            organization_id=ORGANIZATION_ID,
            course_code="ITS-100",
            name="International Travel Security",
            active=True,
        )
    )
    for system in SYSTEMS:
        session.merge(EnterpriseSystem(organization_id=ORGANIZATION_ID, **system))
    for document in DOCUMENTS:
        session.merge(EnterpriseDocument(organization_id=ORGANIZATION_ID, **document))
    for commitment in COMMITMENTS:
        session.merge(CustomerCommitment(organization_id=ORGANIZATION_ID, **commitment))
    session.flush()

    for trip in TRIPS:
        session.merge(Trip(**trip))
    for training_record in TRAINING_RECORDS:
        session.merge(TrainingRecord(**training_record))
    for dependency in SYSTEM_DEPENDENCIES:
        session.merge(
            PolicySystemDependency(
                policy_change_id=POLICY_CHANGE_ID,
                **dependency,
            )
        )
    for dependency in DOCUMENT_DEPENDENCIES:
        session.merge(
            PolicyDocumentDependency(
                policy_change_id=POLICY_CHANGE_ID,
                **dependency,
            )
        )
    session.merge(
        PolicyTrainingDependency(
            id="dependency-policy-security-course",
            policy_change_id=POLICY_CHANGE_ID,
            rule_code="TRAINING_REQUIRED",
            course_id=COURSE_IDENTIFIER,
            relationship_type="requires_course",
            explanation="The policy requires the International Travel Security course.",
        )
    )
    for assignment in COMMITMENT_ASSIGNMENTS:
        session.merge(CommitmentAssignment(**assignment))
    for sequence, question in enumerate(QUESTIONS, start=1):
        session.merge(
            PolicyChangeQuestion(
                id=f"policy-question-{sequence}",
                policy_change_id=POLICY_CHANGE_ID,
                sequence=sequence,
                question=question,
            )
        )
