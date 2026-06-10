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
