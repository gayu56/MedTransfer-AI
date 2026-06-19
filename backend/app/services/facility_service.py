import asyncio
import math

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.facility import Facility, FacilityCapability, BedAvailability
from app.models.transfer import FacilityMatch, TransferRequest
from app.models.call_log import CallLog


async def _llm_specialty_score(
    required_specialty: str,
    facility_capabilities: list[str],
    reason_for_transfer: str | None = None,
) -> float | None:
    """Use LLM to semantically score how well a facility's capabilities match
    the patient's required specialty. Returns 0-100 or None if LLM unavailable.

    This handles clinical synonym matching like:
      - 'Cardiac Surgery' ↔ 'Cardiothoracic Surgery'
      - 'Stroke' ↔ 'Neurology / Neuro-interventional'
      - 'Trauma' ↔ 'Level I Trauma Center'
    """
    from app.ai.sbar_generator import _get_llm_client, extract_json

    client, model = _get_llm_client()
    if not client:
        return None

    caps_str = ", ".join(facility_capabilities) if facility_capabilities else "General medical/surgical"
    context = f" The patient needs transfer for: {reason_for_transfer}." if reason_for_transfer else ""

    prompt = f"""Score how well this facility can handle the patient's needs.

Required specialty: {required_specialty}{context}
Facility capabilities: {caps_str}

Consider clinical synonyms (e.g., Cardiac Surgery = Cardiothoracic, Stroke = Neurology).
Return ONLY a JSON object: {{"score": <0-100>, "reason": "one-line explanation"}}

Scoring guide:
- 100: Exact match or clear clinical synonym
- 70-90: Strong match (related subspecialty or parent specialty)
- 40-60: Partial match (general capability that could handle it)
- 10-30: Weak match (tangentially related)
- 0: No relevant capability"""

    try:
        from app.config import settings as _settings
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a clinical matching assistant. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=100,
            ),
            timeout=_settings.llm_timeout_specialty,
        )
        data = extract_json(response.choices[0].message.content)
        if isinstance(data, dict) and "score" in data:
            return max(0.0, min(100.0, float(data["score"])))
    except asyncio.TimeoutError:
        print(f"LLM specialty matching timed out — falling back to string matching")
    except Exception as e:
        print(f"LLM specialty matching failed: {e}")
    return None


async def _historical_acceptance_rate(db: AsyncSession, facility_id: str) -> float:
    """Compute acceptance score (0-100) from past CallLog outcomes.
    Falls back to 60.0 if no call history exists (neutral prior)."""
    total_result = await db.execute(
        select(func.count()).where(
            CallLog.facility_id == facility_id,
            CallLog.outcome.in_(["ACCEPTED", "PROPOSED_ACCEPT", "DECLINED", "NO_ANSWER", "VOICEMAIL"]),
        )
    )
    total = total_result.scalar() or 0
    if total < 2:
        return 60.0  # Not enough data — neutral prior

    accepted_result = await db.execute(
        select(func.count()).where(
            CallLog.facility_id == facility_id,
            CallLog.outcome.in_(["ACCEPTED", "PROPOSED_ACCEPT"]),
        )
    )
    accepted = accepted_result.scalar() or 0
    rate = (accepted / total) * 100
    # Blend with prior: 70% real data + 30% neutral (60) to avoid extremes
    return round(rate * 0.7 + 60 * 0.3, 1)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in miles between two coordinates."""
    R = 3959  # Earth radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


async def list_facilities(
    db: AsyncSession,
    accepts_transfers: bool | None = None,
) -> list[Facility]:
    query = select(Facility).options(
        selectinload(Facility.capabilities),
        selectinload(Facility.bed_availability),
    )
    if accepts_transfers is not None:
        query = query.where(Facility.accepts_transfers == accepts_transfers)
    result = await db.execute(query.where(Facility.is_active == True))
    return list(result.scalars().all())


async def get_facility(db: AsyncSession, facility_id: str) -> Facility | None:
    result = await db.execute(
        select(Facility)
        .where(Facility.id == facility_id)
        .options(
            selectinload(Facility.capabilities),
            selectinload(Facility.bed_availability),
        )
    )
    return result.scalar_one_or_none()


async def match_facilities(
    db: AsyncSession,
    transfer_id: str,
    sending_facility_id: str,
    required_specialty: str | None = None,
    required_services: list[str] | None = None,
    required_unit_type: str | None = None,
    insurance_provider: str | None = None,
    max_distance_miles: float = 50.0,
    max_results: int = 5,
) -> list[FacilityMatch]:
    """Score and rank facilities for a transfer request."""
    sending = await get_facility(db, sending_facility_id)
    if not sending or not sending.latitude or not sending.longitude:
        return []

    # Load transfer for reason_for_transfer (used in LLM specialty matching)
    transfer_obj = await db.get(TransferRequest, transfer_id)
    reason_for_transfer = transfer_obj.reason_for_transfer if transfer_obj else None

    facilities = await list_facilities(db, accepts_transfers=True)
    scored: list[dict] = []

    for facility in facilities:
        if facility.id == sending_facility_id:
            continue
        if not facility.latitude or not facility.longitude:
            continue

        distance = _haversine_distance(
            sending.latitude, sending.longitude,
            facility.latitude, facility.longitude,
        )
        if distance > max_distance_miles:
            continue

        # --- Scoring ---
        # Specialty match (0-100) — try LLM semantic matching first
        cap_names = [c.name for c in facility.capabilities if c.is_active]
        cap_names_upper = [n.upper() for n in cap_names]
        specialty_score = 0.0

        if required_specialty:
            # Try LLM semantic matching
            llm_score = await _llm_specialty_score(
                required_specialty, cap_names,
                reason_for_transfer=reason_for_transfer,
            )
            if llm_score is not None:
                specialty_score = llm_score
            else:
                # Fallback: string matching
                if required_specialty.upper() in cap_names_upper:
                    specialty_score = 100.0
                elif any(required_specialty.upper() in cn for cn in cap_names_upper):
                    specialty_score = 70.0
        else:
            specialty_score = 50.0

        # Service match
        if required_services:
            matched = sum(1 for s in required_services if s.upper() in cap_names_upper)
            service_bonus = (matched / len(required_services)) * 30
            specialty_score = min(100, specialty_score + service_bonus)

        # Bed availability (0-100)
        bed_score = 0.0
        if required_unit_type:
            for bed in facility.bed_availability:
                if bed.unit_type.upper() == required_unit_type.upper():
                    avail = bed.available_beds
                    if avail >= 3:
                        bed_score = 100.0
                    elif avail >= 1:
                        bed_score = 70.0
                    else:
                        bed_score = 10.0
                    break
        else:
            total_avail = sum(b.available_beds for b in facility.bed_availability)
            bed_score = min(100, total_avail * 10)

        # Distance score (0-100, closer = better)
        distance_score = max(0, 100 - (distance / max_distance_miles) * 100)

        # Insurance score (0-100)
        insurance_score = 80.0  # Default (no real insurance API yet)
        if insurance_provider and hasattr(facility, 'accepted_insurances'):
            accepted_ins = [ins.upper() for ins in (facility.accepted_insurances or [])]
            if insurance_provider.upper() in accepted_ins:
                insurance_score = 100.0
            elif accepted_ins:  # Has a list but patient's insurance not in it
                insurance_score = 30.0

        # Historical acceptance (0-100) — computed from real CallLog data
        historical_score = await _historical_acceptance_rate(db, facility.id)

        # Weighted overall
        overall = (
            specialty_score * 0.30
            + bed_score * 0.25
            + distance_score * 0.15
            + insurance_score * 0.15
            + historical_score * 0.10
        )

        scored.append({
            "facility": facility,
            "overall_score": round(overall, 1),
            "specialty_score": round(specialty_score, 1),
            "bed_availability_score": round(bed_score, 1),
            "distance_score": round(distance_score, 1),
            "insurance_score": round(insurance_score, 1),
            "historical_score": round(historical_score, 1),
            "distance_miles": round(distance, 1),
            "estimated_transport_min": round(distance * 2.5),  # Rough estimate
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    scored = scored[:max_results]

    # Create FacilityMatch records
    matches = []
    for rank, item in enumerate(scored, 1):
        match = FacilityMatch(
            transfer_id=transfer_id,
            facility_id=item["facility"].id,
            rank=rank,
            overall_score=item["overall_score"],
            specialty_score=item["specialty_score"],
            bed_availability_score=item["bed_availability_score"],
            distance_score=item["distance_score"],
            insurance_score=item["insurance_score"],
            historical_score=item["historical_score"],
            distance_miles=item["distance_miles"],
            estimated_transport_min=item["estimated_transport_min"],
            status="SUGGESTED" if rank > 1 else "SENT",
        )
        db.add(match)
        matches.append(match)

    await db.flush()
    return matches
