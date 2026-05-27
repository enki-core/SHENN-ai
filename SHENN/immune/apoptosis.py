# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  immune/apoptosis.py : الانتحار الخلوي والحجر الصحي
# =============================================================

from config import IMMUNE, SYSTEM


class Apoptosis:

    def quarantine(self, neuron):
        """ضع الخلية في الحجر الصحي"""
        neuron.is_quarantined  = True
        neuron.quarantine_count += 1
        if SYSTEM["debug"]:
            print(f"  🚧 حجر صحي: {neuron.id} "
                  f"(مرة {neuron.quarantine_count})")

    def release(self, neuron):
        """أطلق الخلية من الحجر إذا تحسّنت"""
        neuron.is_quarantined = False
        if SYSTEM["debug"]:
            print(f"  ✅ أُطلقت: {neuron.id}")

    def should_die(self, neuron):
        """هل تجاوزت الخلية حد الانتحار؟"""
        return neuron.quarantine_count >= IMMUNE["quarantine_limit"]

    def kill(self, neuron):
        """نفّذ الانتحار الخلوي"""
        neuron.is_alive       = False
        neuron.is_quarantined = False
        neuron.delete_file()
        if SYSTEM["debug"]:
            print(f"  💀 انتحار خلوي: {neuron.id} "
                  f"(جيل {neuron.generation}, عمر {neuron.age})")

    def process(self, flagged_neurons, all_neurons):
        """
        معالجة الخلايا الشاذة:
        - إذا عُزلت أكثر من الحد → انتحار
        - وإلا → حجر صحي مؤقت
        يُعيد قائمة الخلايا التي ماتت
        """
        dead = []
        for n in flagged_neurons:
            if self.should_die(n):
                self.kill(n)
                dead.append(n)
            else:
                self.quarantine(n)

        # تحقق من الخلايا المحجورة القديمة — هل تحسّنت؟
        for n in all_neurons:
            if n.is_quarantined and n.is_alive:
                if n.avg_error() < 0.3:   # تحسّن كافٍ
                    self.release(n)

        return dead