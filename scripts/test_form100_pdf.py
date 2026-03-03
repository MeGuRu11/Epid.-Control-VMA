import sys
from pathlib import Path
sys.path.insert(0, str(Path(r"c:\Users\user\Desktop\Program\Epid_System_Codex")))

from app.infrastructure.reporting.form100_pdf_report_v2 import export_form100_pdf_v2

def test_pdf():
    card = {
        "id": "test-card-1",
        "data": {
            "main": {
                "main_full_name": "Иванов Иван Иванович",
                "main_unit": "в/ч 123456",
                "main_rank": "Рядовой",
                "main_id_tag": "AB-123456",
                "main_date": "01.01.2026",
                "main_time": "12:00",
                "main_diagnosis": "Огнестрельное ранение правого бедра, открытый перелом"
            },
            "bottom": {
                "doctor_signature": "Петров П.П.",
                "issued_by": "Медрота 1",
                "evac_destination": "Госпиталь 2"
            },
            "flags": {
                "flag_emergency": True,
                "flag_isolation": False,
                "flag_sanitation": True,
                "flag_radiation": False
            },
            "bodymap_annotations": [
                {"annotation_type": "WOUND_X", "silhouette": "male_front"}
            ]
        }
    }
    
    export_form100_pdf_v2(card=card, file_path="test_form100_v2_new.pdf")
    print("PDF generated: test_form100_v2_new.pdf")

if __name__ == "__main__":
    test_pdf()
