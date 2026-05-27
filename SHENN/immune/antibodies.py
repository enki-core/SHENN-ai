# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  immune/antibodies.py : الأجسام المضادة
# =============================================================

import json
import os
from config import IMMUNE, MEMORY, SYSTEM


class AntibodySystem:
    def __init__(self):
        self.antibodies = []   # [ { pattern, count, last_seen, round_born } ]
        self._load()

    # ----------------------------------------------------------
    #  التعرف على النمط
    # ----------------------------------------------------------
    def _pattern_from_neuron(self, neuron):
        """استخرج بصمة الشذوذ من الخلية"""
        if not neuron.output_history:
            return None
        avg = sum(neuron.output_history) / len(neuron.output_history)
        spread = max(neuron.output_history) - min(neuron.output_history)
        # بصمة بسيطة: متوسط مقرّب + مدى مقرّب
        return {
            "avg"    : round(avg, 1),
            "spread" : round(spread, 1),
        }

    def _match(self, pattern):
        """هل يطابق النمط جسماً مضاداً موجوداً؟"""
        for ab in self.antibodies:
            if (ab["pattern"]["avg"]    == pattern["avg"] and
                ab["pattern"]["spread"] == pattern["spread"]):
                return ab
        return None

    # ----------------------------------------------------------
    #  التسجيل والفحص
    # ----------------------------------------------------------
    def register(self, neuron, current_round):
        """سجّل شذوذ الخلية كجسم مضاد"""
        pattern = self._pattern_from_neuron(neuron)
        if not pattern:
            return

        existing = self._match(pattern)
        if existing:
            existing["count"]     += 1
            existing["last_seen"]  = current_round
        else:
            if len(self.antibodies) >= IMMUNE["antibody_max"]:
                # احذف الأقدم
                self.antibodies.sort(key=lambda x: x["last_seen"])
                self.antibodies.pop(0)

            self.antibodies.append({
                "pattern"    : pattern,
                "count"      : 1,
                "last_seen"  : current_round,
                "round_born" : current_round,
            })
            if SYSTEM["debug"]:
                print(f"  🧬 جسم مضاد جديد: avg={pattern['avg']} spread={pattern['spread']}")

        self._save()

    def is_known_threat(self, neuron):
        """هل هذه الخلية تُطابق تهديداً معروفاً؟"""
        pattern = self._pattern_from_neuron(neuron)
        if not pattern:
            return False
        return self._match(pattern) is not None

    # ----------------------------------------------------------
    #  الالتهام الذاتي — حذف الأجسام المضادة القديمة
    # ----------------------------------------------------------
    def autophage(self, current_round):
        """احذف الأجسام المضادة التي لم تُستخدم منذ مدة"""
        max_age = 100   # من config يمكن نقله لاحقاً
        before  = len(self.antibodies)
        self.antibodies = [
            ab for ab in self.antibodies
            if (current_round - ab["last_seen"]) < max_age
        ]
        removed = before - len(self.antibodies)
        if removed > 0 and SYSTEM["debug"]:
            print(f"  🧹 الالتهام: حُذف {removed} جسم مضاد قديم")
        self._save()

    # ----------------------------------------------------------
    #  الحفظ والتحميل
    # ----------------------------------------------------------
    def _save(self):
        os.makedirs(os.path.dirname(MEMORY["antibodies_file"]), exist_ok=True)
        with open(MEMORY["antibodies_file"], "w") as f:
            json.dump(self.antibodies, f, indent=2)

    def _load(self):
        path = MEMORY["antibodies_file"]
        if os.path.exists(path):
            with open(path, "r") as f:
                self.antibodies = json.load(f)
        else:
            self.antibodies = []

    def summary(self):
        return f"أجسام مضادة: {len(self.antibodies)}"