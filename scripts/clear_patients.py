from app.infrastructure.db.models_sqlalchemy import (
    EmrAntibioticCourse,
    EmrCase,
    EmrCaseVersion,
    EmrDiagnosis,
    EmrIntervention,
    LabAbxSusceptibility,
    LabMicrobeIsolation,
    LabPhagePanelResult,
    LabSample,
    Patient,
)
from app.infrastructure.db.session import session_scope


def main() -> None:
    with session_scope() as session:
        session.query(EmrDiagnosis).delete()
        session.query(EmrIntervention).delete()
        session.query(EmrAntibioticCourse).delete()
        session.query(EmrCaseVersion).delete()
        session.query(EmrCase).delete()
        session.query(LabMicrobeIsolation).delete()
        session.query(LabAbxSusceptibility).delete()
        session.query(LabPhagePanelResult).delete()
        session.query(LabSample).delete()
        session.query(Patient).delete()


if __name__ == "__main__":
    main()
