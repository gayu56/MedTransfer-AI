"""Seed database with synthetic patient data, facilities, and users for MVP."""
from datetime import date
from sqlalchemy import select
from app.database import async_session
from app.models.organization import Organization
from app.models.facility import Facility, FacilityCapability, BedAvailability
from app.models.user import User
from app.models.patient import Patient


async def seed_database():
    """Seed the database if empty."""
    async with async_session() as db:
        existing = (await db.execute(select(Organization))).scalars().first()
        if existing:
            return  # Already seeded

        # --- Organizations ---
        org_metro = Organization(id="org-metro", name="Metro Health System", type="HOSPITAL_SYSTEM", npi="1234567890", city="New York", state="NY")
        org_university = Organization(id="org-university", name="University Health Network", type="HOSPITAL_SYSTEM", npi="2345678901", city="New York", state="NY")
        org_community = Organization(id="org-community", name="Community Care Group", type="CLINIC_GROUP", npi="3456789012", city="New York", state="NY")
        org_stmarys = Organization(id="org-stmarys", name="St. Mary's Health", type="INDEPENDENT", npi="4567890123", city="Newark", state="NJ")
        db.add_all([org_metro, org_university, org_community, org_stmarys])

        # --- Facilities ---
        # Sending facility (Urgent Care)
        f_uc = Facility(
            id="facility-urgent-care-east", organization_id="org-community",
            name="Urgent Care East", facility_type="URGENT_CARE", trauma_level="NONE",
            npi="1111111111", address_line1="450 East 34th St", city="New York", state="NY",
            zip_code="10016", latitude=40.7448, longitude=-73.9732,
            phone="212-555-0100", transfer_center_phone="212-555-0101",
            accepts_transfers=False,
        )
        # Receiving hospitals
        f_metro = Facility(
            id="facility-metro-general", organization_id="org-metro",
            name="Metro General Hospital", facility_type="HOSPITAL", trauma_level="LEVEL_1",
            npi="2222222222", address_line1="100 First Avenue", city="New York", state="NY",
            zip_code="10009", latitude=40.7282, longitude=-73.9840,
            phone="212-555-0200", transfer_center_phone="212-555-0201",
        )
        f_univ = Facility(
            id="facility-university-medical", organization_id="org-university",
            name="University Medical Center", facility_type="HOSPITAL", trauma_level="LEVEL_1",
            npi="3333333333", address_line1="550 First Avenue", city="New York", state="NY",
            zip_code="10016", latitude=40.7420, longitude=-73.9742,
            phone="212-555-0300", transfer_center_phone="212-555-0301",
        )
        f_stmarys = Facility(
            id="facility-st-marys", organization_id="org-stmarys",
            name="St. Mary's Regional Medical Center", facility_type="HOSPITAL", trauma_level="LEVEL_2",
            npi="4444444444", address_line1="350 Boulevard", city="Newark", state="NJ",
            zip_code="07102", latitude=40.7357, longitude=-74.1724,
            phone="973-555-0400", transfer_center_phone="973-555-0401",
        )
        f_children = Facility(
            id="facility-childrens", organization_id="org-metro",
            name="Metro Children's Hospital", facility_type="HOSPITAL", trauma_level="LEVEL_2",
            npi="5555555555", address_line1="3959 Broadway", city="New York", state="NY",
            zip_code="10032", latitude=40.8400, longitude=-73.9420,
            phone="212-555-0500", transfer_center_phone="212-555-0501",
        )
        f_psych = Facility(
            id="facility-behavioral-health", organization_id="org-university",
            name="Behavioral Health Center", facility_type="PSYCH_FACILITY", trauma_level="NONE",
            npi="6666666666", address_line1="75 Morton St", city="New York", state="NY",
            zip_code="10014", latitude=40.7310, longitude=-74.0080,
            phone="212-555-0600", transfer_center_phone="212-555-0601",
        )
        f_burn = Facility(
            id="facility-burn-center", organization_id="org-metro",
            name="Metro Regional Burn Center", facility_type="BURN_CENTER", trauma_level="LEVEL_1",
            npi="7777777777", address_line1="21 S 3rd St", city="New York", state="NY",
            zip_code="10003", latitude=40.7260, longitude=-73.9897,
            phone="212-555-0700", transfer_center_phone="212-555-0701",
        )
        db.add_all([f_uc, f_metro, f_univ, f_stmarys, f_children, f_psych, f_burn])
        await db.flush()

        # --- Capabilities ---
        caps = [
            # Metro General
            FacilityCapability(facility_id="facility-metro-general", category="SPECIALTY", name="INTERVENTIONAL_CARDIOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="SPECIALTY", name="NEUROLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="SPECIALTY", name="TRAUMA_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="SPECIALTY", name="GENERAL_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="SERVICE", name="CATH_LAB", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="SERVICE", name="NEURO_IR", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="SERVICE", name="CT_SCANNER", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="UNIT_TYPE", name="CCU", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="UNIT_TYPE", name="TELE", available_24_7=True),
            FacilityCapability(facility_id="facility-metro-general", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),
            # University Medical
            FacilityCapability(facility_id="facility-university-medical", category="SPECIALTY", name="INTERVENTIONAL_CARDIOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-university-medical", category="SPECIALTY", name="NEUROSURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-university-medical", category="SPECIALTY", name="ORTHOPEDIC_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-university-medical", category="SERVICE", name="CATH_LAB", available_24_7=True),
            FacilityCapability(facility_id="facility-university-medical", category="SERVICE", name="NEURO_IR", available_24_7=True),
            FacilityCapability(facility_id="facility-university-medical", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-university-medical", category="UNIT_TYPE", name="CCU", available_24_7=True),
            FacilityCapability(facility_id="facility-university-medical", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),
            # St. Mary's
            FacilityCapability(facility_id="facility-st-marys", category="SPECIALTY", name="CARDIOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-st-marys", category="SPECIALTY", name="GENERAL_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-st-marys", category="SERVICE", name="CATH_LAB", available_24_7=False),
            FacilityCapability(facility_id="facility-st-marys", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-st-marys", category="UNIT_TYPE", name="TELE", available_24_7=True),
            # Children's
            FacilityCapability(facility_id="facility-childrens", category="SPECIALTY", name="PEDIATRIC_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-childrens", category="SPECIALTY", name="NEONATOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-childrens", category="UNIT_TYPE", name="PICU", available_24_7=True),
            FacilityCapability(facility_id="facility-childrens", category="UNIT_TYPE", name="NICU", available_24_7=True),
            # Behavioral Health
            FacilityCapability(facility_id="facility-behavioral-health", category="SPECIALTY", name="PSYCHIATRY", available_24_7=True),
            FacilityCapability(facility_id="facility-behavioral-health", category="UNIT_TYPE", name="PSYCH_ACUTE", available_24_7=True),
            FacilityCapability(facility_id="facility-behavioral-health", category="UNIT_TYPE", name="PSYCH_CRISIS", available_24_7=True),
            # Burn Center
            FacilityCapability(facility_id="facility-burn-center", category="SPECIALTY", name="BURN_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-burn-center", category="UNIT_TYPE", name="BURN_ICU", available_24_7=True),
        ]
        db.add_all(caps)

        # --- Bed Availability ---
        beds = [
            BedAvailability(facility_id="facility-metro-general", unit_type="ICU", total_beds=20, occupied_beds=16),
            BedAvailability(facility_id="facility-metro-general", unit_type="CCU", total_beds=12, occupied_beds=10),
            BedAvailability(facility_id="facility-metro-general", unit_type="TELE", total_beds=30, occupied_beds=22),
            BedAvailability(facility_id="facility-metro-general", unit_type="MED_SURG", total_beds=60, occupied_beds=48),
            BedAvailability(facility_id="facility-university-medical", unit_type="ICU", total_beds=24, occupied_beds=21),
            BedAvailability(facility_id="facility-university-medical", unit_type="CCU", total_beds=10, occupied_beds=9),
            BedAvailability(facility_id="facility-university-medical", unit_type="MED_SURG", total_beds=50, occupied_beds=38),
            BedAvailability(facility_id="facility-st-marys", unit_type="ICU", total_beds=12, occupied_beds=8),
            BedAvailability(facility_id="facility-st-marys", unit_type="TELE", total_beds=20, occupied_beds=14),
            BedAvailability(facility_id="facility-childrens", unit_type="PICU", total_beds=16, occupied_beds=12),
            BedAvailability(facility_id="facility-childrens", unit_type="NICU", total_beds=20, occupied_beds=15),
            BedAvailability(facility_id="facility-behavioral-health", unit_type="PSYCH_ACUTE", total_beds=30, occupied_beds=26),
            BedAvailability(facility_id="facility-behavioral-health", unit_type="PSYCH_CRISIS", total_beds=10, occupied_beds=7),
            BedAvailability(facility_id="facility-burn-center", unit_type="BURN_ICU", total_beds=8, occupied_beds=5),
        ]
        db.add_all(beds)

        # --- Users ---
        users = [
            User(id="user-np-sarah", email="sarah.johnson@urgentcare.com", first_name="Sarah", last_name="Johnson", role="NURSE_PRACTITIONER", phone="212-555-1001", organization_id="org-community", facility_id="facility-urgent-care-east"),
            User(id="user-coord-maria", email="maria.garcia@metrogeneral.com", first_name="Maria", last_name="Garcia", role="TRANSFER_COORDINATOR", phone="212-555-1002", organization_id="org-metro", facility_id="facility-metro-general"),
            User(id="user-md-patel", email="dr.patel@metrogeneral.com", first_name="Rajesh", last_name="Patel", role="PHYSICIAN", specialty="INTERVENTIONAL_CARDIOLOGY", npi="9876543210", phone="212-555-1003", organization_id="org-metro", facility_id="facility-metro-general"),
            User(id="user-md-chen", email="dr.chen@university.com", first_name="Wei", last_name="Chen", role="PHYSICIAN", specialty="NEUROSURGERY", phone="212-555-1004", organization_id="org-university", facility_id="facility-university-medical"),
            User(id="user-ems-mike", email="mike.thompson@metroems.com", first_name="Mike", last_name="Thompson", role="EMS_CREW", phone="212-555-1005"),
            User(id="user-admin-linda", email="linda.wilson@metrogeneral.com", first_name="Linda", last_name="Wilson", role="ADMINISTRATOR", phone="212-555-1006", organization_id="org-metro"),
        ]
        db.add_all(users)

        # --- Patients (realistic clinical scenarios) ---
        patients = [
            # Scenario 1: STEMI
            Patient(
                id="patient-stemi-01", mrn="MRN-10001",
                first_name="John", last_name="Doe", date_of_birth=date(1958, 3, 15), gender="M",
                insurance_provider="Blue Cross Blue Shield", insurance_plan_name="PPO Gold", insurance_member_id="BC-987654",
                code_status="FULL_CODE", allergies=[], primary_language="English",
                vitals={"bp_systolic": 160, "bp_diastolic": 95, "heart_rate": 110, "respiratory_rate": 22, "spo2": 94, "temperature": 98.6, "temperature_unit": "F", "pain_scale": 7, "gcs_total": 15, "oxygen_delivery": "Nasal Cannula", "oxygen_flow_rate": "2L"},
                active_conditions=[
                    {"code": "I21.09", "display": "Acute ST elevation myocardial infarction", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-08"},
                    {"code": "I10", "display": "Essential hypertension", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                    {"code": "E11.9", "display": "Type 2 diabetes mellitus", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Heparin Sodium", "dose": "1000", "dose_unit": "units/hr", "route": "IV", "frequency": "continuous"},
                    {"name": "Nitroglycerin", "dose": "10", "dose_unit": "mcg/min", "route": "IV", "frequency": "continuous"},
                    {"name": "Aspirin", "dose": "325", "dose_unit": "mg", "route": "PO", "frequency": "once"},
                    {"name": "Metoprolol", "dose": "50", "dose_unit": "mg", "route": "PO", "frequency": "BID"},
                    {"name": "Metformin", "dose": "1000", "dose_unit": "mg", "route": "PO", "frequency": "BID"},
                ],
                lab_results=[
                    {"name": "Troponin I", "value": "0.8", "unit": "ng/mL", "reference_range_text": "0.00-0.04", "interpretation": "HIGH", "flag": "CRITICAL"},
                    {"name": "WBC", "value": "12.1", "unit": "K/uL", "reference_range_text": "4.5-11.0", "flag": "HIGH"},
                    {"name": "Hemoglobin", "value": "14.2", "unit": "g/dL", "reference_range_text": "13.5-17.5", "flag": "NORMAL"},
                    {"name": "BMP - Sodium", "value": "140", "unit": "mEq/L", "reference_range_text": "136-145", "flag": "NORMAL"},
                    {"name": "BMP - Potassium", "value": "4.1", "unit": "mEq/L", "reference_range_text": "3.5-5.0", "flag": "NORMAL"},
                    {"name": "BMP - Creatinine", "value": "1.1", "unit": "mg/dL", "reference_range_text": "0.7-1.3", "flag": "NORMAL"},
                    {"name": "BMP - Glucose", "value": "186", "unit": "mg/dL", "reference_range_text": "70-100", "flag": "HIGH"},
                ],
                imaging_results=[
                    {"type": "ECG", "finding": "ST elevation in leads II, III, aVF with reciprocal changes in I, aVL", "impression": "Acute inferior STEMI"},
                    {"type": "Chest X-ray", "finding": "No acute cardiopulmonary process. Heart size normal.", "impression": "Normal"},
                ],
                medical_history=["Hypertension (10 years)", "Type 2 Diabetes (5 years)", "Prior MI 2019 — PCI to LAD", "Hyperlipidemia"],
            ),
            # Scenario 2: Stroke
            Patient(
                id="patient-stroke-01", mrn="MRN-10002",
                first_name="Margaret", last_name="Williams", date_of_birth=date(1954, 7, 22), gender="F",
                insurance_provider="Medicare", insurance_plan_name="Medicare Part A/B", insurance_member_id="MC-123456",
                code_status="FULL_CODE", allergies=["Penicillin - rash"], primary_language="English",
                vitals={"bp_systolic": 185, "bp_diastolic": 105, "heart_rate": 88, "respiratory_rate": 18, "spo2": 97, "temperature": 98.2, "temperature_unit": "F", "pain_scale": 0, "gcs_total": 12, "oxygen_delivery": "Room Air"},
                active_conditions=[
                    {"code": "I63.9", "display": "Acute ischemic stroke", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-08"},
                    {"code": "I48.91", "display": "Atrial fibrillation", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "tPA (Alteplase)", "dose": "0.9", "dose_unit": "mg/kg", "route": "IV", "frequency": "per protocol"},
                    {"name": "Labetalol", "dose": "20", "dose_unit": "mg", "route": "IV", "frequency": "PRN"},
                    {"name": "Apixaban", "dose": "5", "dose_unit": "mg", "route": "PO", "frequency": "BID (held)"},
                ],
                lab_results=[
                    {"name": "INR", "value": "1.2", "unit": "", "reference_range_text": "0.9-1.1", "flag": "NORMAL"},
                    {"name": "Glucose", "value": "145", "unit": "mg/dL", "reference_range_text": "70-100", "flag": "HIGH"},
                    {"name": "Platelet Count", "value": "210", "unit": "K/uL", "reference_range_text": "150-400", "flag": "NORMAL"},
                ],
                imaging_results=[
                    {"type": "CT Head", "finding": "No hemorrhage. Hyperdense MCA sign on right.", "impression": "Acute right MCA territory ischemic stroke"},
                    {"type": "CTA Head/Neck", "finding": "Large vessel occlusion — right M1 segment", "impression": "Right MCA occlusion — thrombectomy candidate"},
                ],
                medical_history=["Atrial fibrillation", "Hypertension", "Prior TIA 2024"],
            ),
            # Scenario 3: GI Bleed
            Patient(
                id="patient-gibleed-01", mrn="MRN-10003",
                first_name="Robert", last_name="Martinez", date_of_birth=date(1955, 11, 3), gender="M",
                insurance_provider="Aetna", insurance_plan_name="HMO Standard", insurance_member_id="AET-445566",
                code_status="FULL_CODE", allergies=["Sulfa drugs - anaphylaxis"], primary_language="Spanish", interpreter_needed=True,
                vitals={"bp_systolic": 98, "bp_diastolic": 62, "heart_rate": 118, "respiratory_rate": 24, "spo2": 96, "temperature": 97.8, "temperature_unit": "F", "pain_scale": 5, "gcs_total": 15, "oxygen_delivery": "Nasal Cannula", "oxygen_flow_rate": "4L"},
                active_conditions=[
                    {"code": "K92.0", "display": "Hematemesis - upper GI bleed", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe"},
                    {"code": "D62", "display": "Acute blood loss anemia", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Normal Saline", "dose": "500", "dose_unit": "mL/hr", "route": "IV", "frequency": "continuous"},
                    {"name": "Pantoprazole", "dose": "80", "dose_unit": "mg", "route": "IV", "frequency": "bolus then 8mg/hr"},
                    {"name": "Warfarin", "dose": "5", "dose_unit": "mg", "route": "PO", "frequency": "daily (held)"},
                ],
                lab_results=[
                    {"name": "Hemoglobin", "value": "6.2", "unit": "g/dL", "reference_range_text": "13.5-17.5", "flag": "CRITICAL"},
                    {"name": "INR", "value": "3.8", "unit": "", "reference_range_text": "2.0-3.0", "flag": "CRITICAL"},
                    {"name": "BUN", "value": "45", "unit": "mg/dL", "reference_range_text": "7-20", "flag": "HIGH"},
                    {"name": "Lactate", "value": "3.2", "unit": "mmol/L", "reference_range_text": "0.5-2.0", "flag": "HIGH"},
                ],
                imaging_results=[],
                medical_history=["Atrial fibrillation on Warfarin", "Peptic ulcer disease", "Chronic kidney disease stage 3"],
            ),
            # Scenario 4: Psychiatric Emergency
            Patient(
                id="patient-psych-01", mrn="MRN-10004",
                first_name="Emily", last_name="Chen", date_of_birth=date(2004, 2, 14), gender="F",
                insurance_provider="United Healthcare", insurance_plan_name="Student Plan", insurance_member_id="UHC-778899",
                code_status="FULL_CODE", allergies=[], primary_language="English",
                vitals={"bp_systolic": 122, "bp_diastolic": 78, "heart_rate": 92, "respiratory_rate": 16, "spo2": 99, "temperature": 98.4, "temperature_unit": "F", "pain_scale": 0, "gcs_total": 15, "oxygen_delivery": "Room Air"},
                active_conditions=[
                    {"code": "F32.9", "display": "Major depressive disorder, severe with suicidal ideation", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe"},
                ],
                current_medications=[
                    {"name": "Lorazepam", "dose": "1", "dose_unit": "mg", "route": "PO", "frequency": "once (given in ED)"},
                    {"name": "Sertraline", "dose": "100", "dose_unit": "mg", "route": "PO", "frequency": "daily"},
                ],
                lab_results=[
                    {"name": "Urine Drug Screen", "value": "Negative", "unit": "", "flag": "NORMAL"},
                    {"name": "Alcohol Level", "value": "0", "unit": "mg/dL", "flag": "NORMAL"},
                    {"name": "TSH", "value": "2.1", "unit": "mIU/L", "reference_range_text": "0.4-4.0", "flag": "NORMAL"},
                ],
                imaging_results=[],
                medical_history=["Major depressive disorder (2 years)", "Prior suicide attempt 2025"],
            ),
            # Scenario 5: Hip Fracture
            Patient(
                id="patient-hipfx-01", mrn="MRN-10005",
                first_name="Dorothy", last_name="Anderson", date_of_birth=date(1944, 5, 30), gender="F",
                insurance_provider="Medicare", insurance_plan_name="Medicare Advantage - Humana", insurance_member_id="HUM-112233",
                code_status="DNR_DNI", allergies=["Morphine - nausea", "Iodine contrast - hives"], primary_language="English",
                vitals={"bp_systolic": 142, "bp_diastolic": 78, "heart_rate": 82, "respiratory_rate": 16, "spo2": 97, "temperature": 98.0, "temperature_unit": "F", "pain_scale": 8, "gcs_total": 15, "oxygen_delivery": "Room Air"},
                active_conditions=[
                    {"code": "S72.001A", "display": "Fracture of right femoral neck", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "moderate"},
                    {"code": "M81.0", "display": "Osteoporosis", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Hydromorphone", "dose": "0.5", "dose_unit": "mg", "route": "IV", "frequency": "Q4H PRN"},
                    {"name": "Ondansetron", "dose": "4", "dose_unit": "mg", "route": "IV", "frequency": "Q6H PRN"},
                    {"name": "Alendronate", "dose": "70", "dose_unit": "mg", "route": "PO", "frequency": "weekly"},
                    {"name": "Lisinopril", "dose": "10", "dose_unit": "mg", "route": "PO", "frequency": "daily"},
                ],
                lab_results=[
                    {"name": "Hemoglobin", "value": "11.8", "unit": "g/dL", "reference_range_text": "12.0-16.0", "flag": "LOW"},
                    {"name": "BMP - Creatinine", "value": "0.9", "unit": "mg/dL", "reference_range_text": "0.6-1.2", "flag": "NORMAL"},
                    {"name": "PT/INR", "value": "1.0", "unit": "", "reference_range_text": "0.9-1.1", "flag": "NORMAL"},
                ],
                imaging_results=[
                    {"type": "X-ray Hip", "finding": "Displaced subcapital fracture of right femoral neck", "impression": "Right hip fracture — Garden type III"},
                ],
                medical_history=["Osteoporosis", "Hypertension", "Hypothyroidism", "Prior left hip replacement 2020"],
            ),
        ]
        db.add_all(patients)

        await db.commit()
        print("Database seeded with synthetic data.")

    # Always run — adds new facilities if they don't exist yet
    await seed_additional_facilities()


async def seed_additional_facilities():
    """Add extra facilities to an already-seeded database (idempotent)."""
    async with async_session() as db:
        # Check if any of the new facilities already exist
        check = await db.execute(select(Facility).where(Facility.id == "facility-manhattan-heart"))
        if check.scalar_one_or_none():
            return  # Already added

        # --- New Organizations ---
        org_check = await db.execute(select(Organization).where(Organization.id == "org-brooklyn"))
        if not org_check.scalar_one_or_none():
            new_orgs = [
                Organization(id="org-brooklyn", name="Brooklyn Health Partners", type="HOSPITAL_SYSTEM", npi="5678901234", city="Brooklyn", state="NY"),
                Organization(id="org-queens", name="Queens Health Network", type="HOSPITAL_SYSTEM", npi="6789012345", city="Queens", state="NY"),
                Organization(id="org-longisland", name="Long Island Health System", type="HOSPITAL_SYSTEM", npi="7890123456", city="Mineola", state="NY"),
                Organization(id="org-jerseycity", name="Hudson Medical Group", type="HOSPITAL_SYSTEM", npi="8901234567", city="Jersey City", state="NJ"),
            ]
            db.add_all(new_orgs)
            await db.flush()

        # --- New Facilities ---
        new_facilities = [
            # 1. Manhattan Heart Institute — specialized cardiac center
            Facility(
                id="facility-manhattan-heart", organization_id="org-metro",
                name="Manhattan Heart Institute", facility_type="HOSPITAL", trauma_level="NONE",
                npi="8881111111", address_line1="520 East 70th St", city="New York", state="NY",
                zip_code="10021", latitude=40.7661, longitude=-73.9553,
                phone="212-555-0800", transfer_center_phone="212-555-0801",
            ),
            # 2. Brooklyn Regional Medical Center — pulmonology/respiratory focus
            Facility(
                id="facility-brooklyn-regional", organization_id="org-brooklyn",
                name="Brooklyn Regional Medical Center", facility_type="HOSPITAL", trauma_level="LEVEL_2",
                npi="8882222222", address_line1="150 55th Street", city="Brooklyn", state="NY",
                zip_code="11220", latitude=40.6451, longitude=-74.0060,
                phone="718-555-0100", transfer_center_phone="718-555-0101",
            ),
            # 3. Queens Trauma & Neuroscience Center — Level 1 trauma + neuro
            Facility(
                id="facility-queens-trauma", organization_id="org-queens",
                name="Queens Trauma & Neuroscience Center", facility_type="HOSPITAL", trauma_level="LEVEL_1",
                npi="8883333333", address_line1="82-68 164th St", city="Jamaica", state="NY",
                zip_code="11432", latitude=40.7075, longitude=-73.7908,
                phone="718-555-0200", transfer_center_phone="718-555-0201",
            ),
            # 4. Long Island University Hospital — oncology/GI/hematology
            Facility(
                id="facility-longisland-univ", organization_id="org-longisland",
                name="Long Island University Hospital", facility_type="HOSPITAL", trauma_level="LEVEL_2",
                npi="8884444444", address_line1="259 First Street", city="Mineola", state="NY",
                zip_code="11501", latitude=40.7468, longitude=-73.6391,
                phone="516-555-0300", transfer_center_phone="516-555-0301",
            ),
            # 5. Jersey City Medical Center — nephrology/dialysis
            Facility(
                id="facility-jerseycity-med", organization_id="org-jerseycity",
                name="Jersey City Medical Center", facility_type="HOSPITAL", trauma_level="LEVEL_2",
                npi="8885555555", address_line1="355 Grand Street", city="Jersey City", state="NJ",
                zip_code="07302", latitude=40.7178, longitude=-74.0431,
                phone="201-555-0400", transfer_center_phone="201-555-0401",
            ),
            # 6. Bronx Pulmonary & Critical Care Hospital
            Facility(
                id="facility-bronx-pulmonary", organization_id="org-metro",
                name="Bronx Pulmonary & Critical Care Hospital", facility_type="HOSPITAL", trauma_level="NONE",
                npi="8886666666", address_line1="1400 Pelham Pkwy S", city="Bronx", state="NY",
                zip_code="10461", latitude=40.8568, longitude=-73.8567,
                phone="718-555-0500", transfer_center_phone="718-555-0501",
            ),
            # 7. Westchester County Medical Center — comprehensive
            Facility(
                id="facility-westchester-med", organization_id="org-university",
                name="Westchester County Medical Center", facility_type="HOSPITAL", trauma_level="LEVEL_1",
                npi="8887777777", address_line1="100 Woods Road", city="Valhalla", state="NY",
                zip_code="10595", latitude=41.0759, longitude=-73.7791,
                phone="914-555-0600", transfer_center_phone="914-555-0601",
            ),
            # 8. Hoboken General Hospital — small community hospital
            Facility(
                id="facility-hoboken-general", organization_id="org-jerseycity",
                name="Hoboken General Hospital", facility_type="HOSPITAL", trauma_level="NONE",
                npi="8888888888", address_line1="308 Willow Ave", city="Hoboken", state="NJ",
                zip_code="07030", latitude=40.7440, longitude=-74.0324,
                phone="201-555-0700", transfer_center_phone="201-555-0701",
            ),
        ]
        db.add_all(new_facilities)
        await db.flush()

        # --- Capabilities ---
        new_caps = [
            # Manhattan Heart Institute — cardiac specialty center
            FacilityCapability(facility_id="facility-manhattan-heart", category="SPECIALTY", name="CARDIOTHORACIC_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-manhattan-heart", category="SPECIALTY", name="INTERVENTIONAL_CARDIOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-manhattan-heart", category="SPECIALTY", name="HEART_FAILURE", available_24_7=True),
            FacilityCapability(facility_id="facility-manhattan-heart", category="SPECIALTY", name="ELECTROPHYSIOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-manhattan-heart", category="SERVICE", name="CATH_LAB", available_24_7=True),
            FacilityCapability(facility_id="facility-manhattan-heart", category="SERVICE", name="CARDIAC_REHAB", available_24_7=False),
            FacilityCapability(facility_id="facility-manhattan-heart", category="UNIT_TYPE", name="CCU", available_24_7=True),
            FacilityCapability(facility_id="facility-manhattan-heart", category="UNIT_TYPE", name="TELE", available_24_7=True),

            # Brooklyn Regional — pulmonology + general
            FacilityCapability(facility_id="facility-brooklyn-regional", category="SPECIALTY", name="PULMONOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="SPECIALTY", name="PULMONARY_CRITICAL_CARE", available_24_7=True),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="SPECIALTY", name="GENERAL_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="SPECIALTY", name="GASTROENTEROLOGY", available_24_7=False),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="SERVICE", name="BRONCHOSCOPY", available_24_7=True),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="SERVICE", name="CT_SCANNER", available_24_7=True),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),
            FacilityCapability(facility_id="facility-brooklyn-regional", category="UNIT_TYPE", name="TELE", available_24_7=True),

            # Queens Trauma & Neuro
            FacilityCapability(facility_id="facility-queens-trauma", category="SPECIALTY", name="NEUROSURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="SPECIALTY", name="TRAUMA_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="SPECIALTY", name="ORTHOPEDIC_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="SPECIALTY", name="NEUROLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="SERVICE", name="NEURO_IR", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="SERVICE", name="CT_SCANNER", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="SERVICE", name="MRI", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="UNIT_TYPE", name="NEURO_ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-queens-trauma", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),

            # Long Island University — oncology/GI
            FacilityCapability(facility_id="facility-longisland-univ", category="SPECIALTY", name="ONCOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-longisland-univ", category="SPECIALTY", name="HEMATOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-longisland-univ", category="SPECIALTY", name="GASTROENTEROLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-longisland-univ", category="SPECIALTY", name="GENERAL_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-longisland-univ", category="SERVICE", name="ENDOSCOPY", available_24_7=True),
            FacilityCapability(facility_id="facility-longisland-univ", category="SERVICE", name="CHEMOTHERAPY", available_24_7=False),
            FacilityCapability(facility_id="facility-longisland-univ", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-longisland-univ", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),
            FacilityCapability(facility_id="facility-longisland-univ", category="UNIT_TYPE", name="ONCOLOGY_UNIT", available_24_7=True),

            # Jersey City Medical — nephrology/dialysis
            FacilityCapability(facility_id="facility-jerseycity-med", category="SPECIALTY", name="NEPHROLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="SPECIALTY", name="INTERNAL_MEDICINE", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="SPECIALTY", name="CARDIOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="SPECIALTY", name="GENERAL_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="SERVICE", name="DIALYSIS", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="SERVICE", name="CT_SCANNER", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="UNIT_TYPE", name="TELE", available_24_7=True),
            FacilityCapability(facility_id="facility-jerseycity-med", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),

            # Bronx Pulmonary & Critical Care
            FacilityCapability(facility_id="facility-bronx-pulmonary", category="SPECIALTY", name="PULMONARY_CRITICAL_CARE", available_24_7=True),
            FacilityCapability(facility_id="facility-bronx-pulmonary", category="SPECIALTY", name="PULMONOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-bronx-pulmonary", category="SPECIALTY", name="INFECTIOUS_DISEASE", available_24_7=True),
            FacilityCapability(facility_id="facility-bronx-pulmonary", category="SERVICE", name="BRONCHOSCOPY", available_24_7=True),
            FacilityCapability(facility_id="facility-bronx-pulmonary", category="SERVICE", name="VENTILATOR_MANAGEMENT", available_24_7=True),
            FacilityCapability(facility_id="facility-bronx-pulmonary", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-bronx-pulmonary", category="UNIT_TYPE", name="TELE", available_24_7=True),

            # Westchester County — comprehensive Level 1
            FacilityCapability(facility_id="facility-westchester-med", category="SPECIALTY", name="TRAUMA_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="SPECIALTY", name="NEUROSURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="SPECIALTY", name="CARDIOLOGY", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="SPECIALTY", name="ORTHOPEDIC_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="SPECIALTY", name="GENERAL_SURGERY", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="SERVICE", name="CATH_LAB", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="SERVICE", name="CT_SCANNER", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="SERVICE", name="MRI", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="UNIT_TYPE", name="ICU", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="UNIT_TYPE", name="CCU", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="UNIT_TYPE", name="TELE", available_24_7=True),
            FacilityCapability(facility_id="facility-westchester-med", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),

            # Hoboken General — small community
            FacilityCapability(facility_id="facility-hoboken-general", category="SPECIALTY", name="INTERNAL_MEDICINE", available_24_7=True),
            FacilityCapability(facility_id="facility-hoboken-general", category="SPECIALTY", name="GENERAL_SURGERY", available_24_7=False),
            FacilityCapability(facility_id="facility-hoboken-general", category="UNIT_TYPE", name="MED_SURG", available_24_7=True),
            FacilityCapability(facility_id="facility-hoboken-general", category="UNIT_TYPE", name="TELE", available_24_7=True),
        ]
        db.add_all(new_caps)

        # --- Bed Availability ---
        new_beds = [
            BedAvailability(facility_id="facility-manhattan-heart", unit_type="CCU", total_beds=18, occupied_beds=14),
            BedAvailability(facility_id="facility-manhattan-heart", unit_type="TELE", total_beds=24, occupied_beds=18),

            BedAvailability(facility_id="facility-brooklyn-regional", unit_type="ICU", total_beds=16, occupied_beds=12),
            BedAvailability(facility_id="facility-brooklyn-regional", unit_type="MED_SURG", total_beds=40, occupied_beds=30),
            BedAvailability(facility_id="facility-brooklyn-regional", unit_type="TELE", total_beds=20, occupied_beds=15),

            BedAvailability(facility_id="facility-queens-trauma", unit_type="ICU", total_beds=22, occupied_beds=18),
            BedAvailability(facility_id="facility-queens-trauma", unit_type="NEURO_ICU", total_beds=10, occupied_beds=7),
            BedAvailability(facility_id="facility-queens-trauma", unit_type="MED_SURG", total_beds=50, occupied_beds=40),

            BedAvailability(facility_id="facility-longisland-univ", unit_type="ICU", total_beds=14, occupied_beds=10),
            BedAvailability(facility_id="facility-longisland-univ", unit_type="MED_SURG", total_beds=45, occupied_beds=35),
            BedAvailability(facility_id="facility-longisland-univ", unit_type="ONCOLOGY_UNIT", total_beds=20, occupied_beds=14),

            BedAvailability(facility_id="facility-jerseycity-med", unit_type="ICU", total_beds=12, occupied_beds=9),
            BedAvailability(facility_id="facility-jerseycity-med", unit_type="TELE", total_beds=18, occupied_beds=12),
            BedAvailability(facility_id="facility-jerseycity-med", unit_type="MED_SURG", total_beds=36, occupied_beds=28),

            BedAvailability(facility_id="facility-bronx-pulmonary", unit_type="ICU", total_beds=20, occupied_beds=16),
            BedAvailability(facility_id="facility-bronx-pulmonary", unit_type="TELE", total_beds=16, occupied_beds=10),

            BedAvailability(facility_id="facility-westchester-med", unit_type="ICU", total_beds=24, occupied_beds=19),
            BedAvailability(facility_id="facility-westchester-med", unit_type="CCU", total_beds=10, occupied_beds=8),
            BedAvailability(facility_id="facility-westchester-med", unit_type="TELE", total_beds=30, occupied_beds=22),
            BedAvailability(facility_id="facility-westchester-med", unit_type="MED_SURG", total_beds=60, occupied_beds=45),

            BedAvailability(facility_id="facility-hoboken-general", unit_type="MED_SURG", total_beds=24, occupied_beds=18),
            BedAvailability(facility_id="facility-hoboken-general", unit_type="TELE", total_beds=10, occupied_beds=6),
        ]
        db.add_all(new_beds)

        await db.commit()
        print("Added 8 new facilities to database.")

    await seed_additional_patients()


async def seed_additional_patients():
    """Add extra patient scenarios to an already-seeded database (idempotent)."""
    async with async_session() as db:
        check = await db.execute(select(Patient).where(Patient.id == "patient-copd-01"))
        if check.scalar_one_or_none():
            return  # Already added

        new_patients = [
            # Scenario 6: COPD Exacerbation — needs Pulmonology
            Patient(
                id="patient-copd-01", mrn="MRN-10006",
                first_name="Walter", last_name="Brown", date_of_birth=date(1948, 9, 12), gender="M",
                insurance_provider="Medicare", insurance_plan_name="Medicare Part A/B", insurance_member_id="MC-667788",
                code_status="FULL_CODE", allergies=["Aspirin - bronchospasm"], primary_language="English",
                vitals={"bp_systolic": 145, "bp_diastolic": 88, "heart_rate": 105, "respiratory_rate": 28, "spo2": 87, "temperature": 100.4, "temperature_unit": "F", "pain_scale": 3, "gcs_total": 15, "oxygen_delivery": "Non-rebreather mask", "oxygen_flow_rate": "15L"},
                active_conditions=[
                    {"code": "J44.1", "display": "Acute exacerbation of COPD with pneumonia", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-18"},
                    {"code": "J96.01", "display": "Acute hypoxemic respiratory failure", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe"},
                    {"code": "J18.9", "display": "Community-acquired pneumonia", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Albuterol Nebulizer", "dose": "2.5", "dose_unit": "mg", "route": "INH", "frequency": "Q2H"},
                    {"name": "Methylprednisolone", "dose": "125", "dose_unit": "mg", "route": "IV", "frequency": "Q6H"},
                    {"name": "Ceftriaxone", "dose": "2", "dose_unit": "g", "route": "IV", "frequency": "daily"},
                    {"name": "Azithromycin", "dose": "500", "dose_unit": "mg", "route": "IV", "frequency": "daily"},
                    {"name": "Tiotropium", "dose": "18", "dose_unit": "mcg", "route": "INH", "frequency": "daily"},
                ],
                lab_results=[
                    {"name": "ABG pH", "value": "7.31", "unit": "", "reference_range_text": "7.35-7.45", "flag": "LOW"},
                    {"name": "ABG pCO2", "value": "58", "unit": "mmHg", "reference_range_text": "35-45", "flag": "HIGH"},
                    {"name": "ABG pO2", "value": "52", "unit": "mmHg", "reference_range_text": "80-100", "flag": "CRITICAL"},
                    {"name": "WBC", "value": "18.5", "unit": "K/uL", "reference_range_text": "4.5-11.0", "flag": "HIGH"},
                    {"name": "Procalcitonin", "value": "2.8", "unit": "ng/mL", "reference_range_text": "<0.1", "flag": "CRITICAL"},
                ],
                imaging_results=[
                    {"type": "Chest X-ray", "finding": "Right lower lobe consolidation with air bronchograms. Hyperinflated lungs.", "impression": "RLL pneumonia with underlying COPD"},
                ],
                medical_history=["COPD — Gold Stage III (15 years)", "2 prior intubations", "Former smoker (40 pack-years)", "Chronic hypercapnic respiratory failure", "Cor pulmonale"],
            ),
            # Scenario 7: Acute Kidney Injury — needs Nephrology/Dialysis
            Patient(
                id="patient-aki-01", mrn="MRN-10007",
                first_name="Linda", last_name="Jackson", date_of_birth=date(1962, 4, 8), gender="F",
                insurance_provider="Cigna", insurance_plan_name="PPO Select", insurance_member_id="CIG-334455",
                code_status="FULL_CODE", allergies=["ACE inhibitors - angioedema"], primary_language="English",
                vitals={"bp_systolic": 168, "bp_diastolic": 102, "heart_rate": 96, "respiratory_rate": 22, "spo2": 95, "temperature": 98.8, "temperature_unit": "F", "pain_scale": 4, "gcs_total": 14, "oxygen_delivery": "Nasal Cannula", "oxygen_flow_rate": "3L"},
                active_conditions=[
                    {"code": "N17.9", "display": "Acute kidney injury, unspecified", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-17"},
                    {"code": "E87.5", "display": "Hyperkalemia", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe"},
                    {"code": "E11.22", "display": "Type 2 diabetes with diabetic nephropathy", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Normal Saline", "dose": "200", "dose_unit": "mL/hr", "route": "IV", "frequency": "continuous"},
                    {"name": "Calcium Gluconate", "dose": "2", "dose_unit": "g", "route": "IV", "frequency": "once"},
                    {"name": "Insulin Regular + D50", "dose": "10/25", "dose_unit": "units/g", "route": "IV", "frequency": "once"},
                    {"name": "Sodium Polystyrene", "dose": "30", "dose_unit": "g", "route": "PO", "frequency": "once"},
                    {"name": "Furosemide", "dose": "80", "dose_unit": "mg", "route": "IV", "frequency": "Q8H"},
                ],
                lab_results=[
                    {"name": "BMP - Creatinine", "value": "6.8", "unit": "mg/dL", "reference_range_text": "0.6-1.2", "flag": "CRITICAL"},
                    {"name": "BUN", "value": "88", "unit": "mg/dL", "reference_range_text": "7-20", "flag": "CRITICAL"},
                    {"name": "Potassium", "value": "6.4", "unit": "mEq/L", "reference_range_text": "3.5-5.0", "flag": "CRITICAL"},
                    {"name": "Bicarbonate", "value": "14", "unit": "mEq/L", "reference_range_text": "22-28", "flag": "LOW"},
                    {"name": "Phosphorus", "value": "7.2", "unit": "mg/dL", "reference_range_text": "2.5-4.5", "flag": "HIGH"},
                    {"name": "Hemoglobin", "value": "9.1", "unit": "g/dL", "reference_range_text": "12.0-16.0", "flag": "LOW"},
                ],
                imaging_results=[
                    {"type": "Renal Ultrasound", "finding": "Bilateral echogenic kidneys, no hydronephrosis, no stones", "impression": "Chronic kidney disease changes, no obstructive uropathy"},
                ],
                medical_history=["CKD Stage 4 (baseline Cr 3.2)", "Type 2 Diabetes (18 years)", "Hypertension", "Diabetic retinopathy", "Peripheral neuropathy"],
            ),
            # Scenario 8: Leukemia with Neutropenic Fever — needs Oncology/Hematology
            Patient(
                id="patient-onco-01", mrn="MRN-10008",
                first_name="James", last_name="Taylor", date_of_birth=date(1970, 12, 1), gender="M",
                insurance_provider="Blue Cross Blue Shield", insurance_plan_name="HMO", insurance_member_id="BC-112233",
                code_status="FULL_CODE", allergies=["Vancomycin - Red Man Syndrome"], primary_language="English",
                vitals={"bp_systolic": 92, "bp_diastolic": 58, "heart_rate": 118, "respiratory_rate": 20, "spo2": 96, "temperature": 102.8, "temperature_unit": "F", "pain_scale": 6, "gcs_total": 15, "oxygen_delivery": "Nasal Cannula", "oxygen_flow_rate": "2L"},
                active_conditions=[
                    {"code": "C91.00", "display": "Acute lymphoblastic leukemia, not in remission", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe"},
                    {"code": "D70.1", "display": "Neutropenic fever", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-19"},
                    {"code": "R65.20", "display": "Severe sepsis without septic shock", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Cefepime", "dose": "2", "dose_unit": "g", "route": "IV", "frequency": "Q8H"},
                    {"name": "Normal Saline", "dose": "500", "dose_unit": "mL/hr", "route": "IV", "frequency": "bolus"},
                    {"name": "Filgrastim (G-CSF)", "dose": "480", "dose_unit": "mcg", "route": "SubQ", "frequency": "daily"},
                    {"name": "Ondansetron", "dose": "4", "dose_unit": "mg", "route": "IV", "frequency": "Q8H PRN"},
                ],
                lab_results=[
                    {"name": "WBC", "value": "0.3", "unit": "K/uL", "reference_range_text": "4.5-11.0", "flag": "CRITICAL"},
                    {"name": "ANC", "value": "80", "unit": "/uL", "reference_range_text": ">1500", "flag": "CRITICAL"},
                    {"name": "Hemoglobin", "value": "7.2", "unit": "g/dL", "reference_range_text": "13.5-17.5", "flag": "LOW"},
                    {"name": "Platelet Count", "value": "18", "unit": "K/uL", "reference_range_text": "150-400", "flag": "CRITICAL"},
                    {"name": "Lactate", "value": "2.8", "unit": "mmol/L", "reference_range_text": "0.5-2.0", "flag": "HIGH"},
                    {"name": "Blood Cultures", "value": "Pending", "unit": "", "flag": "PENDING"},
                ],
                imaging_results=[
                    {"type": "Chest X-ray", "finding": "No focal consolidation. Port-a-cath in satisfactory position.", "impression": "No acute process"},
                ],
                medical_history=["ALL diagnosed 3 months ago", "Completed induction chemotherapy cycle 2 (14 days ago)", "Prior port-a-cath placement", "No prior transfusion reactions"],
            ),
            # Scenario 9: Multi-Trauma MVA — needs Trauma Surgery
            Patient(
                id="patient-trauma-01", mrn="MRN-10009",
                first_name="Carlos", last_name="Rivera", date_of_birth=date(1990, 6, 25), gender="M",
                insurance_provider="Aetna", insurance_plan_name="EPO Standard", insurance_member_id="AET-998877",
                code_status="FULL_CODE", allergies=[], primary_language="Spanish", interpreter_needed=True,
                vitals={"bp_systolic": 88, "bp_diastolic": 54, "heart_rate": 130, "respiratory_rate": 26, "spo2": 92, "temperature": 97.2, "temperature_unit": "F", "pain_scale": 9, "gcs_total": 13, "oxygen_delivery": "Non-rebreather mask", "oxygen_flow_rate": "15L"},
                active_conditions=[
                    {"code": "S27.301A", "display": "Bilateral pneumothorax — chest tubes placed", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-19"},
                    {"code": "S36.116A", "display": "Splenic laceration Grade III", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe"},
                    {"code": "S72.90XA", "display": "Open fracture left femur", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe"},
                    {"code": "T79.4XXA", "display": "Traumatic hemorrhagic shock", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Lactated Ringer's", "dose": "999", "dose_unit": "mL/hr", "route": "IV", "frequency": "wide open — 2 large bore IVs"},
                    {"name": "Tranexamic Acid", "dose": "1", "dose_unit": "g", "route": "IV", "frequency": "bolus over 10 min"},
                    {"name": "pRBCs", "dose": "2", "dose_unit": "units", "route": "IV", "frequency": "rapid transfusion (MTP activated)"},
                    {"name": "Fentanyl", "dose": "50", "dose_unit": "mcg", "route": "IV", "frequency": "Q15min PRN"},
                ],
                lab_results=[
                    {"name": "Hemoglobin", "value": "7.8", "unit": "g/dL", "reference_range_text": "13.5-17.5", "flag": "CRITICAL"},
                    {"name": "Lactate", "value": "5.6", "unit": "mmol/L", "reference_range_text": "0.5-2.0", "flag": "CRITICAL"},
                    {"name": "Base Deficit", "value": "-8", "unit": "mEq/L", "reference_range_text": "-2 to +2", "flag": "CRITICAL"},
                    {"name": "INR", "value": "1.6", "unit": "", "reference_range_text": "0.9-1.1", "flag": "HIGH"},
                    {"name": "Fibrinogen", "value": "120", "unit": "mg/dL", "reference_range_text": "200-400", "flag": "LOW"},
                ],
                imaging_results=[
                    {"type": "CT Chest/Abdomen/Pelvis", "finding": "Bilateral pneumothorax (chest tubes in place, improving). Grade III splenic laceration with moderate hemoperitoneum. Comminuted left femur fracture.", "impression": "Multi-system trauma — surgical consultation needed"},
                    {"type": "FAST Exam", "finding": "Free fluid in Morrison's pouch and pelvis", "impression": "Positive FAST — intra-abdominal hemorrhage"},
                ],
                medical_history=["No significant past medical history", "Restrained driver, high-speed MVA, rollover"],
            ),
            # Scenario 10: Acute Pancreatitis — needs Gastroenterology
            Patient(
                id="patient-panc-01", mrn="MRN-10010",
                first_name="Susan", last_name="Park", date_of_birth=date(1975, 3, 18), gender="F",
                insurance_provider="United Healthcare", insurance_plan_name="PPO Choice Plus", insurance_member_id="UHC-556677",
                code_status="FULL_CODE", allergies=["Codeine - nausea/vomiting"], primary_language="English",
                vitals={"bp_systolic": 105, "bp_diastolic": 68, "heart_rate": 108, "respiratory_rate": 22, "spo2": 95, "temperature": 101.2, "temperature_unit": "F", "pain_scale": 9, "gcs_total": 15, "oxygen_delivery": "Nasal Cannula", "oxygen_flow_rate": "3L"},
                active_conditions=[
                    {"code": "K85.1", "display": "Acute gallstone pancreatitis, severe", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-17"},
                    {"code": "K80.12", "display": "Choledocholithiasis with cholangitis", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "moderate"},
                ],
                current_medications=[
                    {"name": "Normal Saline", "dose": "250", "dose_unit": "mL/hr", "route": "IV", "frequency": "continuous"},
                    {"name": "Hydromorphone", "dose": "0.5", "dose_unit": "mg", "route": "IV", "frequency": "Q3H PRN"},
                    {"name": "Piperacillin/Tazobactam", "dose": "4.5", "dose_unit": "g", "route": "IV", "frequency": "Q6H"},
                    {"name": "Ondansetron", "dose": "4", "dose_unit": "mg", "route": "IV", "frequency": "Q6H PRN"},
                ],
                lab_results=[
                    {"name": "Lipase", "value": "4200", "unit": "U/L", "reference_range_text": "0-160", "flag": "CRITICAL"},
                    {"name": "Total Bilirubin", "value": "5.8", "unit": "mg/dL", "reference_range_text": "0.1-1.2", "flag": "HIGH"},
                    {"name": "ALT", "value": "320", "unit": "U/L", "reference_range_text": "7-56", "flag": "HIGH"},
                    {"name": "AST", "value": "280", "unit": "U/L", "reference_range_text": "10-40", "flag": "HIGH"},
                    {"name": "WBC", "value": "16.8", "unit": "K/uL", "reference_range_text": "4.5-11.0", "flag": "HIGH"},
                    {"name": "CRP", "value": "210", "unit": "mg/L", "reference_range_text": "<10", "flag": "CRITICAL"},
                ],
                imaging_results=[
                    {"type": "CT Abdomen with contrast", "finding": "Edematous pancreas with peripancreatic fat stranding and fluid. 1.2cm stone in distal CBD with upstream ductal dilation.", "impression": "Severe acute gallstone pancreatitis. Choledocholithiasis — ERCP recommended."},
                    {"type": "RUQ Ultrasound", "finding": "Multiple gallstones. CBD dilated to 12mm. GB wall thickening.", "impression": "Cholelithiasis with choledocholithiasis"},
                ],
                medical_history=["Gallstones (known, asymptomatic until now)", "Obesity (BMI 34)", "GERD"],
            ),
            # Scenario 11: Pediatric Seizures — needs Pediatric Neurology
            Patient(
                id="patient-peds-sz-01", mrn="MRN-10011",
                first_name="Aiden", last_name="Murphy", date_of_birth=date(2019, 8, 5), gender="M",
                insurance_provider="Medicaid", insurance_plan_name="CHIP", insurance_member_id="MCD-887766",
                code_status="FULL_CODE", allergies=[], primary_language="English",
                vitals={"bp_systolic": 95, "bp_diastolic": 60, "heart_rate": 140, "respiratory_rate": 30, "spo2": 94, "temperature": 103.2, "temperature_unit": "F", "pain_scale": 0, "gcs_total": 10, "oxygen_delivery": "Simple mask", "oxygen_flow_rate": "6L"},
                active_conditions=[
                    {"code": "G40.901", "display": "Status epilepticus — breakthrough seizures", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "severe", "onset_date": "2026-06-19"},
                    {"code": "R56.01", "display": "Complex febrile seizure", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Lorazepam", "dose": "0.1", "dose_unit": "mg/kg", "route": "IV", "frequency": "x2 doses given"},
                    {"name": "Levetiracetam", "dose": "20", "dose_unit": "mg/kg", "route": "IV", "frequency": "loading dose"},
                    {"name": "Acetaminophen", "dose": "15", "dose_unit": "mg/kg", "route": "PR", "frequency": "once"},
                    {"name": "Normal Saline", "dose": "20", "dose_unit": "mL/kg/hr", "route": "IV", "frequency": "maintenance"},
                ],
                lab_results=[
                    {"name": "Glucose", "value": "110", "unit": "mg/dL", "reference_range_text": "70-100", "flag": "HIGH"},
                    {"name": "Sodium", "value": "138", "unit": "mEq/L", "reference_range_text": "136-145", "flag": "NORMAL"},
                    {"name": "Calcium", "value": "9.2", "unit": "mg/dL", "reference_range_text": "8.5-10.5", "flag": "NORMAL"},
                    {"name": "WBC", "value": "14.0", "unit": "K/uL", "reference_range_text": "5.0-15.0", "flag": "NORMAL"},
                ],
                imaging_results=[
                    {"type": "CT Head", "finding": "No acute intracranial abnormality. No mass effect or hemorrhage.", "impression": "Normal for age"},
                ],
                medical_history=["Known epilepsy since age 4", "On Levetiracetam maintenance (partially controlled)", "2 prior admissions for breakthrough seizures", "Normal developmental milestones"],
            ),
            # Scenario 12: Aortic Dissection — needs Cardiothoracic Surgery
            Patient(
                id="patient-dissection-01", mrn="MRN-10012",
                first_name="Richard", last_name="Nguyen", date_of_birth=date(1960, 1, 30), gender="M",
                insurance_provider="Anthem", insurance_plan_name="Blue Cross PPO", insurance_member_id="ANT-445566",
                code_status="FULL_CODE", allergies=["Shellfish (iodine contrast — premedicate)"], primary_language="English",
                vitals={"bp_systolic": 198, "bp_diastolic": 110, "heart_rate": 100, "respiratory_rate": 24, "spo2": 96, "temperature": 98.6, "temperature_unit": "F", "pain_scale": 10, "gcs_total": 15, "oxygen_delivery": "Nasal Cannula", "oxygen_flow_rate": "4L"},
                active_conditions=[
                    {"code": "I71.01", "display": "Stanford Type A aortic dissection", "coding_system": "ICD-10-CM", "clinical_status": "active", "severity": "life-threatening", "onset_date": "2026-06-19"},
                    {"code": "I10", "display": "Essential hypertension — uncontrolled", "coding_system": "ICD-10-CM", "clinical_status": "active"},
                ],
                current_medications=[
                    {"name": "Esmolol", "dose": "50", "dose_unit": "mcg/kg/min", "route": "IV", "frequency": "continuous — titrating"},
                    {"name": "Nicardipine", "dose": "5", "dose_unit": "mg/hr", "route": "IV", "frequency": "continuous — titrating"},
                    {"name": "Morphine", "dose": "4", "dose_unit": "mg", "route": "IV", "frequency": "Q10min PRN"},
                ],
                lab_results=[
                    {"name": "Troponin I", "value": "0.15", "unit": "ng/mL", "reference_range_text": "0.00-0.04", "flag": "HIGH"},
                    {"name": "D-Dimer", "value": "12500", "unit": "ng/mL", "reference_range_text": "<500", "flag": "CRITICAL"},
                    {"name": "Hemoglobin", "value": "12.8", "unit": "g/dL", "reference_range_text": "13.5-17.5", "flag": "LOW"},
                    {"name": "Creatinine", "value": "1.4", "unit": "mg/dL", "reference_range_text": "0.7-1.3", "flag": "HIGH"},
                    {"name": "Lactate", "value": "3.1", "unit": "mmol/L", "reference_range_text": "0.5-2.0", "flag": "HIGH"},
                    {"name": "Type & Screen", "value": "O positive — 6 units crossmatched", "unit": "", "flag": "NORMAL"},
                ],
                imaging_results=[
                    {"type": "CTA Chest/Abdomen", "finding": "Intimal flap originating 2cm above aortic valve extending to aortic arch and proximal descending aorta. Moderate pericardial effusion. No coronary involvement.", "impression": "Stanford Type A aortic dissection — emergent surgical repair indicated"},
                    {"type": "Chest X-ray", "finding": "Widened mediastinum. Small left pleural effusion.", "impression": "Consistent with aortic pathology"},
                    {"type": "Echocardiogram (bedside)", "finding": "Moderate pericardial effusion, no tamponade. Aortic root dilation. Mild aortic regurgitation.", "impression": "Concerning for Type A dissection with pericardial involvement"},
                ],
                medical_history=["Hypertension (20 years, poorly controlled)", "Marfan syndrome (family history)", "Former smoker", "Bicuspid aortic valve"],
            ),
        ]
        db.add_all(new_patients)

        await db.commit()
        print("Added 7 new patient scenarios to database.")
