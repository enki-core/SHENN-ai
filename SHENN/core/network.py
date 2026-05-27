# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  core/network.py : الشبكة الكاملة
# =============================================================

import json
import os
from core.neuron import Neuron
from config import NETWORK, MEMORY, SYSTEM


class GrowingNetwork:
    def __init__(self):
        self.neurons      = []       # قائمة الخلايا الحية
        self.round        = 0        # عداد الجولات
        self.split_cooldown = 0      # عداد الانتظار بين الانقسامات

        # --- ابدأ بخلية واحدة ---
        first = Neuron()
        self.neurons.append(first)

        if SYSTEM["debug"]:
            print("=" * 50)
            print("  SHENN — شبكة عصبية ذاتية النمو والشفاء")
            print("=" * 50)
            print(f"  البداية: خلية واحدة — {self._param_count()} بارامتر\n")

    # ----------------------------------------------------------
    #  التوقع
    # ----------------------------------------------------------
    def predict(self, inputs):
        """احسب خرج الشبكة بأخذ متوسط الخلايا السليمة"""
        active = [n for n in self.neurons if n.is_alive and not n.is_quarantined]
        if not active:
            return 0.0
        outputs = [n.forward(inputs) for n in active]
        return sum(outputs) / len(outputs)

    # ----------------------------------------------------------
    #  جولة تدريب
    # ----------------------------------------------------------
    def train_step(self, inputs, target):
        """درّب الشبكة على مثال واحد"""
        prediction = self.predict(inputs)
        error      = target - prediction

        # درّب كل خلية سليمة
        active = [n for n in self.neurons if n.is_alive and not n.is_quarantined]
        for neuron in active:
            neuron.train(inputs, error)

        self.round += 1
        if self.split_cooldown > 0:
            self.split_cooldown -= 1

        # احفظ الحالة كل فترة
        if self.round % MEMORY["save_interval"] == 0:
            self.save_all()

        return abs(error)

    # ----------------------------------------------------------
    #  الانقسام
    # ----------------------------------------------------------
    def maybe_split(self, current_error):
        """تحقق هل يجب الانقسام"""
        if self.split_cooldown > 0:
            return False
        if len(self.neurons) >= NETWORK["max_neurons"]:
            return False
        if current_error < NETWORK["split_threshold"]:
            return False

        # اختر الخلية الأعلى خطأً للانقسام
        active = [n for n in self.neurons if n.is_alive and not n.is_quarantined]
        if not active:
            return False

        worst = max(active, key=lambda n: n.avg_error())
        child_a, child_b = worst.split()

        # استبدل الأم بالابنين
        self.neurons.remove(worst)
        worst.delete_file()
        self.neurons.append(child_a)
        self.neurons.append(child_b)

        self.split_cooldown = NETWORK["split_cooldown"]

        if SYSTEM["debug"]:
            print(f"  ✂️  انقسمت {worst.id} (جيل {worst.generation})"
                  f" ← {child_a.id} و {child_b.id} (جيل {worst.generation+1})")
        return True

    # ----------------------------------------------------------
    #  الحالة
    # ----------------------------------------------------------
    def status(self):
        alive       = [n for n in self.neurons if n.is_alive]
        quarantined = [n for n in alive if n.is_quarantined]
        avg_err     = (sum(n.avg_error() for n in alive) / len(alive)) if alive else 0
        return {
            "round"       : self.round,
            "total"       : len(alive),
            "quarantined" : len(quarantined),
            "params"      : self._param_count(),
            "avg_error"   : round(avg_err, 4),
        }

    def print_status(self):
        s = self.status()
        print(f"  جولة {s['round']:03d} | "
              f"خطأ: {s['avg_error']:.3f} | "
              f"خلايا: {s['total']} | "
              f"محجورة: {s['quarantined']} | "
              f"بارامترات: {s['params']}")

    # ----------------------------------------------------------
    #  الحفظ والتحميل
    # ----------------------------------------------------------
    def save_all(self):
        """احفظ كل الخلايا + فهرس الشبكة"""
        for n in self.neurons:
            if n.is_alive:
                n.save()

        index = {
            "round"      : self.round,
            "neuron_ids" : [n.id for n in self.neurons if n.is_alive],
        }
        path = os.path.join(MEMORY["cells_dir"], "_index.json")
        os.makedirs(MEMORY["cells_dir"], exist_ok=True)
        with open(path, "w") as f:
            json.dump(index, f, indent=2)

    @classmethod
    def load(cls):
        """أعد بناء الشبكة من الذاكرة الصلبة"""
        index_path = os.path.join(MEMORY["cells_dir"], "_index.json")
        if not os.path.exists(index_path):
            return None

        with open(index_path, "r") as f:
            index = json.load(f)

        net = cls.__new__(cls)
        net.neurons        = []
        net.round          = index["round"]
        net.split_cooldown = 0

        for nid in index["neuron_ids"]:
            neuron = Neuron.load(nid)
            if neuron:
                net.neurons.append(neuron)

        if SYSTEM["debug"]:
            print(f"  ♻️  تم تحميل الشبكة — {len(net.neurons)} خلية من الذاكرة")
        return net

    # ----------------------------------------------------------
    #  مساعد
    # ----------------------------------------------------------
    def _param_count(self):
        alive = [n for n in self.neurons if n.is_alive]
        return sum(len(n.weights) + 1 for n in alive)  # +1 للـ bias

    def __repr__(self):
        s = self.status()
        return f"GrowingNetwork(خلايا={s['total']}, جولة={s['round']})"