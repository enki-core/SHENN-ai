# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  core/neuron.py : الخلية العصبية الأساسية
# =============================================================

import random
import json
import os
from core.activations import ACTIVATION, ACTIVATION_DERIV
from config import NETWORK, MEMORY


class Neuron:
    def __init__(self, input_size=None, generation=0, neuron_id=None):
        # --- الهوية ---
        self.id         = neuron_id or self._generate_id()
        self.generation = generation        # الجيل (0 = أصل، 1 = ابن، 2 = حفيد...)
        self.age        = 0                 # عدد جولات التدريب

        # --- الأوزان ---
        size = input_size or NETWORK["input_size"]
        self.weights = [random.uniform(-1.0, 1.0) for _ in range(size)]
        self.bias    = random.uniform(-1.0, 1.0)

        # --- التتبع ---
        self.last_output  = 0.0    # آخر خرج أنتجته
        self.last_raw     = 0.0    # الخرج قبل دالة التفعيل
        self.error_history = []    # تاريخ الأخطاء
        self.output_history = []   # تاريخ الخرج (للمناعة)

        # --- حالة الخلية ---
        self.is_quarantined = False   # هل في الحجر الصحي؟
        self.quarantine_count = 0     # كم مرة عُزلت
        self.is_alive = True          # هل لا تزال حية؟

    # ----------------------------------------------------------
    #  الحساب الأمامي
    # ----------------------------------------------------------
    def forward(self, inputs):
        """احسب خرج الخلية من المدخلات"""
        if not self.is_alive:
            return 0.0

        raw = sum(w * x for w, x in zip(self.weights, inputs)) + self.bias
        output = ACTIVATION(raw)

        self.last_raw    = raw
        self.last_output = output
        self.output_history.append(output)

        # احتفظ بآخر 20 خرج فقط
        if len(self.output_history) > 20:
            self.output_history.pop(0)

        return output

    # ----------------------------------------------------------
    #  التدريب
    # ----------------------------------------------------------
    def train(self, inputs, error):
        """حدّث الأوزان بناءً على الخطأ"""
        if not self.is_alive or self.is_quarantined:
            return

        lr    = NETWORK["learning_rate"]
        delta = error * ACTIVATION_DERIV(self.last_raw)

        self.weights = [w + lr * delta * x for w, x in zip(self.weights, inputs)]
        self.bias   += lr * delta

        self.error_history.append(abs(error))
        if len(self.error_history) > 20:
            self.error_history.pop(0)

        self.age += 1

    # ----------------------------------------------------------
    #  الانقسام
    # ----------------------------------------------------------
    def split(self):
        """انقسم إلى خليتين — كل واحدة ترث خبرة الأم"""
        child_a = Neuron(
            input_size = len(self.weights),
            generation = self.generation + 1
        )
        child_b = Neuron(
            input_size = len(self.weights),
            generation = self.generation + 1
        )

        # الابن الأول يرث الأوزان مع ضوضاء خفيفة
        child_a.weights = [w + random.uniform(-0.1, 0.1) for w in self.weights]
        child_a.bias    = self.bias + random.uniform(-0.1, 0.1)

        # الابن الثاني يرث بضوضاء مختلفة
        child_b.weights = [w + random.uniform(-0.1, 0.1) for w in self.weights]
        child_b.bias    = self.bias + random.uniform(-0.1, 0.1)

        # ينقلان تاريخ الخطأ
        child_a.error_history = self.error_history.copy()
        child_b.error_history = self.error_history.copy()

        return child_a, child_b

    # ----------------------------------------------------------
    #  متوسط الخطأ
    # ----------------------------------------------------------
    def avg_error(self):
        """متوسط الخطأ في التاريخ الأخير"""
        if not self.error_history:
            return 0.0
        return sum(self.error_history) / len(self.error_history)

    # ----------------------------------------------------------
    #  الحفظ والتحميل
    # ----------------------------------------------------------
    def save(self):
        """احفظ حالة الخلية في ملف"""
        path = os.path.join(MEMORY["cells_dir"], f"{self.id}.json")
        data = {
            "id"               : self.id,
            "generation"       : self.generation,
            "age"              : self.age,
            "weights"          : self.weights,
            "bias"             : self.bias,
            "error_history"    : self.error_history,
            "quarantine_count" : self.quarantine_count,
        }
        os.makedirs(MEMORY["cells_dir"], exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, neuron_id):
        """حمّل خلية من ملف"""
        path = os.path.join(MEMORY["cells_dir"], f"{neuron_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        n = cls(input_size=len(data["weights"]), generation=data["generation"])
        n.id               = data["id"]
        n.age              = data["age"]
        n.weights          = data["weights"]
        n.bias             = data["bias"]
        n.error_history    = data["error_history"]
        n.quarantine_count = data["quarantine_count"]
        return n

    def delete_file(self):
        """احذف ملف الخلية من الذاكرة الصلبة"""
        path = os.path.join(MEMORY["cells_dir"], f"{self.id}.json")
        if os.path.exists(path):
            os.remove(path)

    # ----------------------------------------------------------
    #  مساعد
    # ----------------------------------------------------------
    @staticmethod
    def _generate_id():
        return f"n_{random.randint(100000, 999999)}"

    def __repr__(self):
        status = "محجورة" if self.is_quarantined else "سليمة"
        return (f"Neuron(id={self.id}, gen={self.generation}, "
                f"age={self.age}, status={status})")