# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  main.py : نقطة الدخول الرئيسية
# =============================================================

from core.network      import GrowingNetwork
from immune.monitor    import ImmuneMonitor
from immune.apoptosis  import Apoptosis
from immune.antibodies import AntibodySystem
from lifecycle.chrysalis import Chrysalis
from lifecycle.autophage import Autophage
from config import SYSTEM


def run():

    # --- تهيئة المكونات ---
    monitor    = ImmuneMonitor()
    apoptosis  = Apoptosis()
    antibodies = AntibodySystem()
    chrysalis  = Chrysalis()
    autophage  = Autophage()

    # --- حمّل شبكة محفوظة أو ابدأ جديدة ---
    net = GrowingNetwork.load() or GrowingNetwork()

    # ==========================================================
    #  بيانات التدريب — غيّرها لأي مشكلة تريدها
    #  كل مثال: ( [مدخل1, مدخل2] , الهدف )
    # ==========================================================
    data = [
        ([0.9, 0.8], 1.0),   # طالب مجتهد
        ([0.1, 0.2], 0.0),   # طالب ضعيف
        ([0.7, 0.6], 1.0),   # طالب متوسط-جيد
        ([0.3, 0.8], 0.0),   # حضور عالٍ لكن درجة ضعيفة
        ([0.5, 0.5], 0.5),   # متوسط
        ([0.95, 0.9], 1.0),  # ممتاز
        ([0.05, 0.1], 0.0),  # ضعيف جداً
    ]

    print("\n  بدء التدريب...\n")
    rounds = 100

    for r in range(rounds):
        # --- جولة تدريب ---
        total_error = 0.0
        for inputs, target in data:
            err = net.train_step(inputs, target)
            total_error += err

        avg_error = total_error / len(data)

        # --- انقسام إذا لزم ---
        net.maybe_split(avg_error)

        # --- مراقبة مناعية ---
        alive = [n for n in net.neurons if n.is_alive]
        monitor.observe(alive)
        flagged = monitor.scan(alive)

        if flagged:
            for n in flagged:
                antibodies.register(n, net.round)
            dead = apoptosis.process(flagged, alive)
            # احذف الميتين من قائمة الشبكة
            for d in dead:
                if d in net.neurons:
                    net.neurons.remove(d)

        # --- الالتهام الذاتي ---
        autophage.run(net, antibodies)

        # --- طباعة الحالة كل 10 جولات ---
        if (r + 1) % 10 == 0:
            net.print_status()

        # --- الشرنقة إذا حان وقتها ---
        if chrysalis.should_transform(net):
            print("\n  🦋 بدء الشرنقة...")
            chrysalis.compress(net)
            net = chrysalis.reborn(GrowingNetwork)

    # --- حفظ نهائي ---
    net.save_all()

    # ==========================================================
    #  اختبار النتائج
    # ==========================================================
    print("\n" + "=" * 50)
    print("  📊 نتائج الاختبار")
    print("=" * 50)

    tests = [
        ([0.9, 0.8], "طالب مثالي",               0.5),
        ([0.1, 0.1], "طالب ضعيف جداً",           0.5),
        ([0.6, 0.5], "طالب متوسط",               0.5),
        ([0.3, 0.9], "حضور ممتاز لكن درجة ضعيفة", 0.5),
    ]

    for inputs, label, threshold in tests:
        result = net.predict(inputs)
        status = "✅ ناجح" if result >= threshold else "❌ راسب"
        print(f"  {label:<35} {result:.2f}  {status}")

    print(f"\n  {antibodies.summary()}")
    print(f"  إجمالي الجولات: {net.round}")
    print()


if __name__ == "__main__":
    run()