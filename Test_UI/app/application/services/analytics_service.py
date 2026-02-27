from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...domain.calculations import incidence_density, prevalence_rate
from ...infrastructure.db.models_sqlalchemy import (
    EmrCase,
    EmrCaseVersion,
    EmrIntervention,
    LabAbxSusceptibility,
    LabSample,
    Patient,
    RefAntibioticGroup,
    SanitarySample,
)


class AnalyticsService:
    def __init__(self, engine, session_ctx):
        self._engine = engine
        self._session = session_ctx

    def summary(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        department_id: int | None = None,
    ) -> dict:
        with Session(self._engine) as s:
            patients = int(s.execute(select(func.count(Patient.id))).scalar_one())

            case_q = select(func.count(EmrCase.id))
            if department_id is not None:
                case_q = case_q.where(EmrCase.department_id == department_id)
            cases = int(s.execute(case_q).scalar_one())

            ver_q = select(func.count(EmrCaseVersion.id))
            if date_from is not None:
                ver_q = ver_q.where(EmrCaseVersion.admission_date >= date_from)
            if date_to is not None:
                ver_q = ver_q.where(EmrCaseVersion.admission_date <= date_to)
            versions = int(s.execute(ver_q).scalar_one())

            lab_q = select(func.count(LabSample.id))
            if date_from is not None:
                lab_q = lab_q.where(LabSample.created_at >= date_from)
            if date_to is not None:
                lab_q = lab_q.where(LabSample.created_at <= date_to)
            lab = int(s.execute(lab_q).scalar_one())

            san_q = select(func.count(SanitarySample.id))
            if department_id is not None:
                san_q = san_q.where(SanitarySample.department_id == department_id)
            sanitary = int(s.execute(san_q).scalar_one())

            sev_q = select(func.count(EmrCaseVersion.id)).where(EmrCaseVersion.severity == "тяжелая")
            if date_from is not None:
                sev_q = sev_q.where(EmrCaseVersion.admission_date >= date_from)
            if date_to is not None:
                sev_q = sev_q.where(EmrCaseVersion.admission_date <= date_to)
            severe = int(s.execute(sev_q).scalar_one())

        return {
            "patients": patients,
            "cases": cases,
            "versions": versions,
            "lab_samples": lab,
            "sanitary_samples": sanitary,
            "severe_versions": severe,
        }

    def ismp_metrics(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """ИСМП: counts of VAP/CA-BSI/CA-UTI-related interventions."""
        with Session(self._engine) as s:
            def _count(intvn_type: str) -> int:
                q = select(func.count(EmrIntervention.id)).where(EmrIntervention.type == intvn_type)
                if date_from is not None:
                    q = q.where(EmrIntervention.start_dt >= date_from)
                if date_to is not None:
                    q = q.where(EmrIntervention.start_dt <= date_to)
                return int(s.execute(q).scalar_one())

            vap = _count("ИВЛ")
            ca_bsi = _count("ЦВК")
            ca_uti = _count("Мочевой катетер")
        return {"vap": vap, "ca_bsi": ca_bsi, "ca_uti": ca_uti}

    def mortality_rate(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        with Session(self._engine) as s:
            total_q = select(func.count(EmrCaseVersion.id))
            died_q = select(func.count(EmrCaseVersion.id)).where(
                EmrCaseVersion.outcome_type == "died"
            )
            for q in (total_q, died_q):
                pass  # applied below to avoid reference issues
            if date_from is not None:
                total_q = total_q.where(EmrCaseVersion.admission_date >= date_from)
                died_q = died_q.where(EmrCaseVersion.admission_date >= date_from)
            if date_to is not None:
                total_q = total_q.where(EmrCaseVersion.admission_date <= date_to)
                died_q = died_q.where(EmrCaseVersion.admission_date <= date_to)
            total = int(s.execute(total_q).scalar_one())
            died = int(s.execute(died_q).scalar_one())
        rate_pct = round(died / total * 100, 1) if total else 0.0
        return {"total": total, "died": died, "rate_pct": rate_pct}

    def avg_los_days(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> float:
        with Session(self._engine) as s:
            q = select(EmrCaseVersion.admission_date, EmrCaseVersion.outcome_date).where(
                EmrCaseVersion.outcome_date.is_not(None),
                EmrCaseVersion.admission_date.is_not(None),
            )
            if date_from is not None:
                q = q.where(EmrCaseVersion.admission_date >= date_from)
            if date_to is not None:
                q = q.where(EmrCaseVersion.admission_date <= date_to)
            rows = s.execute(q).all()
        if not rows:
            return 0.0
        los_values = []
        for adm, dis in rows:
            if adm and dis:
                try:
                    delta = (dis - adm).days
                    if delta >= 0:
                        los_values.append(delta)
                except Exception:
                    pass
        return round(sum(los_values) / len(los_values), 1) if los_values else 0.0

    def top_organisms(
        self,
        limit: int = 10,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        with Session(self._engine) as s:
            q = (
                select(LabSample.organism, func.count(LabSample.id).label("cnt"))
                .where(LabSample.organism.is_not(None))
                .where(LabSample.organism != "")
                .group_by(LabSample.organism)
                .order_by(func.count(LabSample.id).desc())
                .limit(limit)
            )
            if date_from is not None:
                q = q.where(LabSample.created_at >= date_from)
            if date_to is not None:
                q = q.where(LabSample.created_at <= date_to)
            rows = s.execute(q).all()
        return [{"organism": row.organism, "count": row.cnt} for row in rows]

    def antibiogram(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict]:
        from collections import defaultdict
        with Session(self._engine) as s:
            q = (
                select(
                    LabSample.organism,
                    RefAntibioticGroup.name.label("group_name"),
                    LabAbxSusceptibility.ris,
                    func.count(LabAbxSusceptibility.id).label("cnt"),
                )
                .join(LabSample, LabAbxSusceptibility.lab_sample_id == LabSample.id)
                .join(RefAntibioticGroup, LabAbxSusceptibility.group_id == RefAntibioticGroup.id)
                .where(
                    LabSample.organism.is_not(None),
                    LabSample.organism != "",
                    LabAbxSusceptibility.ris.is_not(None),
                )
                .group_by(LabSample.organism, RefAntibioticGroup.name, LabAbxSusceptibility.ris)
            )
            if date_from is not None:
                q = q.where(LabSample.created_at >= date_from)
            if date_to is not None:
                q = q.where(LabSample.created_at <= date_to)
            rows = s.execute(q).all()
        data: dict = defaultdict(lambda: {"S": 0, "I": 0, "R": 0, "total": 0})
        for row in rows:
            key = (row.organism or "—", row.group_name or "—")
            ris = (row.ris or "").upper()
            if ris in ("S", "I", "R"):
                data[key][ris] += row.cnt
                data[key]["total"] += row.cnt
        result = []
        for (organism, group), counts in sorted(data.items()):
            total = counts["total"]
            result.append({
                "organism": organism,
                "group": group,
                "pct_S": round(counts["S"] / total * 100) if total else 0,
                "pct_I": round(counts["I"] / total * 100) if total else 0,
                "pct_R": round(counts["R"] / total * 100) if total else 0,
                "n_tests": total,
            })
        return result

    def incidence_density(self, date_from: date | None = None, date_to: date | None = None) -> float:
        data = self.summary(date_from=date_from, date_to=date_to)
        return incidence_density(data["lab_samples"], data["cases"])

    def prevalence(self, date_from: date | None = None, date_to: date | None = None) -> float:
        data = self.summary(date_from=date_from, date_to=date_to)
        return prevalence_rate(data["severe_versions"], data["patients"])
