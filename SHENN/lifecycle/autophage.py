# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  lifecycle/autophage.py : الالتهام الذاتي
# =============================================================

import os
import json
from config import LIFECYCLE, MEMORY, SYSTEM


class Autophage:

    def run(self, network, antibody_system):
        """
        نظّف الذاكرة والخلايا الميتة
        يُستدعى كل autophage_interval جولة
        """
        if network.round % LIFECYCLE["autophage_interval"] != 0:
            return

        if SYSTEM["debug"]:
            print(f"\n  🧹 الالتهام الذاتي — جولة {network.round}")

        cleaned = 0

        # 1 — احذف ملفات الخلايا الميتة من القرص
        cleaned += self._clean_dead_cells(network)

        # 2 — احذف الأجسام المضادة القديمة
        antibody_system.autophage(network.round)

        # 3 — نظّف تاريخ الأخطاء الطويل جداً في الخلايا الحية
        cleaned += self._trim_histories(network)

        if SYSTEM["debug"]:
            print(f"     تم تنظيف {cleaned} عنصر\n")

    def _clean_dead_cells(self, network):
        """احذف ملفات الخلايا الميتة من الذاكرة الصلبة"""
        cells_dir = MEMORY["cells_dir"]
        if not os.path.exists(cells_dir):
            return 0

        alive_ids = {n.id for n in network.neurons if n.is_alive}
        removed   = 0

        for filename in os.listdir(cells_dir):
            if filename == "_index.json" or not filename.endswith(".json"):
                continue
            neuron_id = filename.replace(".json", "")
            if neuron_id not in alive_ids:
                os.remove(os.path.join(cells_dir, filename))
                removed += 1

        if removed > 0 and SYSTEM["debug"]:
            print(f"     خلايا ميتة محذوفة: {removed}")

        return removed

    def _trim_histories(self, network):
        """قلّص تاريخ الأخطاء في الخلايا الحية لتوفير الذاكرة"""
        trimmed = 0
        for n in network.neurons:
            if n.is_alive and len(n.error_history) > 20:
                n.error_history = n.error_history[-20:]
                trimmed += 1
            if n.is_alive and len(n.output_history) > 20:
                n.output_history = n.output_history[-20:]
                trimmed += 1
        return trimmed