# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  immune/monitor.py : مراقبة الخلايا (الخلايا البيضاء)
# =============================================================

from config import IMMUNE, SYSTEM


class ImmuneMonitor:
    def __init__(self):
        self.watch = {}   # { neuron_id: [قائمة الخرج الأخيرة] }

    def observe(self, neurons):
        """راقب خرج كل خلية وسجّله"""
        for n in neurons:
            if not n.is_alive or n.is_quarantined:
                continue
            if n.id not in self.watch:
                self.watch[n.id] = []
            self.watch[n.id].append(n.last_output)
            # احتفظ بآخر N قراءة فقط
            window = IMMUNE["anomaly_window"]
            if len(self.watch[n.id]) > window:
                self.watch[n.id].pop(0)

    def scan(self, neurons):
        """افحص الخلايا وأعد قائمة الشاذة منها"""
        flagged = []
        threshold = IMMUNE["anomaly_threshold"]
        window    = IMMUNE["anomaly_window"]

        for n in neurons:
            if not n.is_alive or n.is_quarantined:
                continue
            history = self.watch.get(n.id, [])
            if len(history) < window:
                continue   # لم تُراقَب كفاية بعد

            # شذوذ: الخرج عالق فوق الحد دائماً أو ثابت تماماً
            all_high  = all(v > threshold for v in history)
            all_stuck = (max(history) - min(history)) < 0.001

            if all_high or all_stuck:
                flagged.append(n)
                if SYSTEM["debug"]:
                    reason = "خرج مرتفع دائماً" if all_high else "خرج ثابت لا يتغير"
                    print(f"  🔍 شذوذ في {n.id} — {reason}")

        return flagged