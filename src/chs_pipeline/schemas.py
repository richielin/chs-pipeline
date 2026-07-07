"""Pydantic schemas for CHS pipeline data."""
from pydantic import BaseModel
from typing import Optional


class CensusLOS(BaseModel):
    average_daily_census: Optional[int] = None
    median_length_of_stay_days: Optional[int] = None
    confidence: float = 0.0


class AgeDistribution(BaseModel):
    pct_18_21: Optional[float] = None
    pct_55_plus: Optional[float] = None
    median_age: Optional[int] = None
    confidence: float = 0.0


class ScoreCard(BaseModel):
    percentage: Optional[float] = None
    confidence: float = 0.0


class Conditions(BaseModel):
    # Aggregated
    mental_health_history_pct: Optional[float] = None
    substance_use_history_pct: Optional[float] = None
    chronic_medical_history_pct: Optional[float] = None
    # Individual — Mental Health
    mh_enrolled_pct: Optional[float] = None
    serious_mh_pct: Optional[float] = None
    # Individual — Substance Use
    alcohol_use_pct: Optional[float] = None
    opioid_use_pct: Optional[float] = None
    # Individual — Chronic Medical
    pulmonary_pct: Optional[float] = None
    cardiovascular_pct: Optional[float] = None
    neurologic_pct: Optional[float] = None
    endocrine_pct: Optional[float] = None
    renal_pct: Optional[float] = None
    malignancy_pct: Optional[float] = None
    hepatitis_pct: Optional[float] = None
    hiv_pct: Optional[float] = None
    confidence: float = 0.0


class PatientProfileResult(BaseModel):
    document_id: str
    source_type: str = "patient_profile"
    report_month: str
    template_version: str = "pp_v1"
    processed_at: str
    confidence: float = 0.0
    modules: dict
    model_run: Optional[dict] = None


# ── Access Report schemas ──────────────────────────────────────────────


class ARMetric(BaseModel):
    metric_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    confidence: float = 0.0


class FacilityData(BaseModel):
    facility_code: str
    page_number: int
    metrics: list[ARMetric]


class AccessReportResult(BaseModel):
    document_id: str
    source_type: str = "access_report"
    report_period: str  # "YYYY-MM" or "YYYY-QN"
    report_type: str  # "monthly" or "quarterly"
    template_version: str = "ar_v1"
    processed_at: str
    confidence: float = 0.0
    summary: Optional[dict] = None
    facilities: list[FacilityData] = []
    model_runs: list[dict] = []
