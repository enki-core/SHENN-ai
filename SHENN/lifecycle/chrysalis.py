# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  lifecycle/chrysalis.py : الشرنقة — موت وبعث
# =============================================================

import json
import os
from config import LIFECYCLE, MEMORY, NETWORK, SYSTEM


class Chrysalis:

    def should_transform(self, network):
        """هل حان وقت الشرنقة؟"""
        alive = [n for n in network.neurons if n.is_alive]

        # الشبكة عجوزة؟
        too_old = network.round >= LIFECYCLE["old_age_threshold"]

        # الشبكة ممتلئة جداً؟
        too_full = (len(alive) / NETWORK["max_neurons"]) >= LIFECYCLE["complexity_limit"]

        return too_old or too_full

    def compress(self, network):
        """
        اضغط خبرة الشبكة في جينات مضغوطة
        قبل الموت — هذا هو DNA التلخيصي
        """
        alive = [n for n in network.neurons if n.is_alive]

        # متوسط الأوزان عبر كل الخلايا
        if not alive:
            return {}

        input_size = len(alive[0].weights)
        avg_weights = []
        for i in range(input_size):
            avg_w = sum(n.weights[i] for n in alive) / len(alive)
            avg_weights.append(round(avg_w, 4))

        avg_bias = sum(n.bias for n in alive) / len(alive)

        # أفضل جيل وصل إليه النظام
        max_gen = max(n.generation for n in alive)

        genes = {
            "avg_weights"  : avg_weights,
            "avg_bias"     : round(avg_bias, 4),
            "max_generation": max_gen,
            "rounds_lived" : network.round,
            "neuron_count" : len(alive),
        }

        os.makedirs(os.path.dirname(MEMORY["genes_file"]), exist_ok=True)
        with open(MEMORY["genes_file"], "w") as f:
            json.dump(genes, f, indent=2)

        if SYSTEM["debug"]:
            print(f"\n  🦋 الشرنقة — ضُغطت خبرة {len(alive)} خلية في جينات")
            print(f"     أقصى جيل: {max_gen} | جولات عاشها: {network.round}")

        return genes

    def reborn(self, network_class):
        """
        أنشئ شبكة جديدة صغيرة ورشيقة
        وأحقنها بالذاكرة الجينية للشبكة الميتة
        """
        genes_path = MEMORY["genes_file"]
        if not os.path.exists(genes_path):
            if SYSTEM["debug"]:
                print("  🐣 ولادة جديدة بدون جينات — بداية نظيفة")
            return network_class()

        with open(genes_path, "r") as f:
            genes = json.load(f)

        # شبكة جديدة
        net = network_class()

        # احقن الجينات في الخلية الأولى
        first = net.neurons[0]
        if len(first.weights) == len(genes["avg_weights"]):
            first.weights = genes["avg_weights"]
            first.bias    = genes["avg_bias"]

        if SYSTEM["debug"]:
            print(f"\n  🐣 ولادة جديدة — ورثت {genes['rounds_lived']} جولة من الخبرة")
            print(f"     من جيل {genes['max_generation']} | "
                  f"بدأت بـ {len(net.neurons)} خلية\n")

        return net