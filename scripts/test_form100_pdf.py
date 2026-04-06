import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)
sys.path.insert(0, str(Path(r"c:\Users\user\Desktop\Program\Epid_System_Codex")))

from app.infrastructure.reporting.form100_pdf_report_v2 import export_form100_pdf_v2

def test_pdf():
    card = {
        "id": "test-card-1",
        "version": 3,
        "status": "SIGNED",
        "signed_by": "Петров П.П.",
        "signed_at": "2026-03-01 14:30",
        "birth_date": "1990-05-15",
        "main_full_name": "Иванов Иван Иванович",
        "main_unit": "в/ч 123456",
        "main_id_tag": "AB-123456",
        "main_diagnosis": "Огнестрельное ранение правого бедра, открытый перелом",
        "data": {
            "stub": {
                "stub_issued_time": "12:00",
                "stub_issued_date": "01.03.2026",
                "stub_rank": "Рядовой",
                "stub_unit": "в/ч 123456",
                "stub_full_name": "Иванов Иван Иванович",
                "stub_id_tag": "AB-123456",
                "stub_injury_time": "10:30",
                "stub_injury_date": "01.03.2026",
                "stub_evacuation_method": "самолет",
                "stub_evacuation_dest": "Госпиталь 2",
                "stub_diagnosis": "Огнестрельное ранение правого бедра, открытый перелом бедренной кости",
                "stub_med_help_antibiotic": "1",
                "stub_antibiotic_dose": "Цефтриаксон 1г",
                "stub_med_help_analgesic": "1",
                "stub_analgesic_dose": "Промедол 2%",
                "stub_tourniquet": "1",
            },
            "main": {
                "main_full_name": "Иванов Иван Иванович",
                "main_unit": "в/ч 123456",
                "main_rank": "Рядовой",
                "main_id_tag": "AB-123456",
                "main_issued_place": "Медрота 1",
                "main_issued_time": "12:00",
                "main_issued_date": "01.03.2026",
                "main_injury_time": "10:30",
                "main_injury_date": "01.03.2026",
                "main_diagnosis": "Огнестрельное ранение правого бедра, открытый перелом",
                "lesion_gunshot": "1",
                "san_loss_gunshot": "1",
                "isolation_required": "0",
                "mp_antibiotic": "1",
                "mp_antibiotic_dose": "Цефтриаксон 1г в/м",
                "mp_analgesic": "1",
                "mp_analgesic_dose": "Промедол 2% 1мл",
                "mp_immobilization": "1",
                "mp_bandage": "1",
                "mp_transfusion_blood": "1",
            },
            "bottom": {
                "tourniquet_time": "10:35",
                "sanitation_type": "частичная",
                "evacuation_dest": "Госпиталь №2 (ВМКГ)",
                "evacuation_priority": "I",
                "transport_type": "вертолет",
                "doctor_signature": "Петров П.П.",
                "main_diagnosis": "Огнестрельное ранение правого бедра, открытый перелом бедренной кости",
            },
            "flags": {
                "flag_emergency": "1",
                "flag_isolation": "0",
                "flag_sanitation": "1",
                "flag_radiation": "0",
            },
            "bodymap_annotations": [
                {"annotation_type": "WOUND_X", "silhouette": "male_front", "x": 0.35, "y": 0.72, "note": ""},
                {"annotation_type": "WOUND_X", "silhouette": "male_front", "x": 0.38, "y": 0.68, "note": "осколочное"},
                {"annotation_type": "TOURNIQUET", "silhouette": "male_front", "x": 0.35, "y": 0.62, "note": "наложен 10:35"},
                {"annotation_type": "BURN_HATCH", "silhouette": "male_back", "x": 0.5, "y": 0.3, "note": "термический"},
                {"annotation_type": "NOTE_PIN", "silhouette": "male_front", "x": 0.6, "y": 0.4, "note": "подкожная гематома"},
            ],
            "bodymap_tissue_types": ["мягкие ткани", "кости"],
            "san_loss": {},
            "lesion": {},
            "medical_help": {},
        },
    }
    
    export_form100_pdf_v2(card=card, file_path="test_form100_v2_new.pdf")
    logger.info("PDF generated: test_form100_v2_new.pdf")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    test_pdf()
