# =============================================================
#  SHENN GUI — واجهة إدارة الشبكة العصبية
#  SHENN/SHENN_GUI/app.py
# =============================================================

import sys
import os
import json
import threading
import time

# أضف مسار SHENN الرئيسي للـ import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSplitter, QProgressBar, QSlider, QCheckBox,
    QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QFont, QColor, QPalette

import config as cfg
from core.network       import GrowingNetwork
from immune.monitor     import ImmuneMonitor
from immune.apoptosis   import Apoptosis
from immune.antibodies  import AntibodySystem
from lifecycle.chrysalis import Chrysalis
from lifecycle.autophage import Autophage


# =============================================================
#  Worker — تشغيل التدريب في خيط منفصل
# =============================================================
class TrainWorker(QObject):
    update   = pyqtSignal(dict)   # إرسال بيانات الحالة
    log      = pyqtSignal(str)    # إرسال رسالة للسجل
    finished = pyqtSignal()

    def __init__(self, net, systems, data, rounds):
        super().__init__()
        self.net      = net
        self.systems  = systems
        self.data     = data
        self.rounds   = rounds
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        monitor, apoptosis, antibodies, chrysalis, autophage = self.systems

        for r in range(self.rounds):
            if not self._running:
                break

            total_error = 0.0
            for inputs, target in self.data:
                err = self.net.train_step(inputs, target)
                total_error += err

            avg_error = total_error / len(self.data)
            split     = self.net.maybe_split(avg_error)

            # مناعة
            alive   = [n for n in self.net.neurons if n.is_alive]
            monitor.observe(alive)
            flagged = monitor.scan(alive)
            dead    = []
            if flagged:
                for n in flagged:
                    antibodies.register(n, self.net.round)
                dead = apoptosis.process(flagged, alive)
                for d in dead:
                    if d in self.net.neurons:
                        self.net.neurons.remove(d)

            # الالتهام الذاتي
            autophage.run(self.net, antibodies)

            # الشرنقة
            if chrysalis.should_transform(self.net):
                self.log.emit("🦋 بدأت الشرنقة — إعادة ولادة الشبكة")
                chrysalis.compress(self.net)
                self.net = chrysalis.reborn(GrowingNetwork)

            # إرسال البيانات للواجهة
            status = self.net.status()
            status["avg_error"]   = round(avg_error, 4)
            status["split"]       = split
            status["flagged"]     = len(flagged)
            status["dead"]        = len(dead)
            status["antibodies"]  = len(antibodies.antibodies)
            status["neurons_info"] = [
                {
                    "id"         : n.id,
                    "generation" : n.generation,
                    "age"        : n.age,
                    "avg_error"  : round(n.avg_error(), 4),
                    "quarantined": n.is_quarantined,
                    "output"     : round(n.last_output, 4),
                }
                for n in self.net.neurons if n.is_alive
            ]
            self.update.emit(status)

            if split:
                self.log.emit(f"✂️  انقسام في الجولة {self.net.round}")
            if dead:
                self.log.emit(f"💀 انتحار خلوي: {len(dead)} خلية في الجولة {self.net.round}")

            time.sleep(0.05)

        self.net.save_all()
        self.log.emit("✅ اكتمل التدريب وحُفظت الشبكة")
        self.finished.emit()


# =============================================================
#  تبويب التدريب
# =============================================================
class TrainTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw       = main_window
        self.worker   = None
        self.thread   = None
        self.errors   = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- صف التحكم العلوي ---
        ctrl = QHBoxLayout()

        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(1, 10000)
        self.rounds_spin.setValue(100)
        self.rounds_spin.setPrefix("جولات: ")

        self.btn_start = QPushButton("▶  تشغيل")
        self.btn_stop  = QPushButton("⏹  إيقاف")
        self.btn_reset = QPushButton("🔄  شبكة جديدة")
        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self.start_training)
        self.btn_stop.clicked.connect(self.stop_training)
        self.btn_reset.clicked.connect(self.reset_network)

        ctrl.addWidget(self.rounds_spin)
        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        ctrl.addWidget(self.btn_reset)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # --- بطاقات الحالة ---
        cards = QHBoxLayout()
        self.card_round      = self._card("الجولة",       "0")
        self.card_error      = self._card("الخطأ",        "—")
        self.card_neurons    = self._card("الخلايا",      "1")
        self.card_params     = self._card("البارامترات",  "3")
        self.card_quarantine = self._card("محجورة",       "0")
        self.card_antibodies = self._card("أجسام مضادة", "0")
        for c in [self.card_round, self.card_error, self.card_neurons,
                  self.card_params, self.card_quarantine, self.card_antibodies]:
            cards.addWidget(c)
        layout.addLayout(cards)

        # --- رسم بياني بسيط للخطأ ---
        self.error_label = QLabel("سجل الخطأ عبر الزمن:")
        layout.addWidget(self.error_label)

        self.error_bar = QProgressBar()
        self.error_bar.setRange(0, 100)
        self.error_bar.setValue(0)
        self.error_bar.setFormat("خطأ: %v%")
        layout.addWidget(self.error_bar)

        # --- جدول الخلايا ---
        grp = QGroupBox("الخلايا الحية")
        grp_layout = QVBoxLayout(grp)
        self.cell_table = QTableWidget(0, 6)
        self.cell_table.setHorizontalHeaderLabels(
            ["المعرّف", "الجيل", "العمر", "متوسط الخطأ", "الخرج", "الحالة"]
        )
        self.cell_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cell_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        grp_layout.addWidget(self.cell_table)
        layout.addWidget(grp)

        # --- سجل الأحداث ---
        grp2 = QGroupBox("سجل الأحداث")
        grp2_layout = QVBoxLayout(grp2)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(120)
        grp2_layout.addWidget(self.log_box)
        layout.addWidget(grp2)

    def _card(self, title, value):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        fl = QVBoxLayout(frame)
        fl.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("color: #aaa; font-size: 11px;")
        lbl_val = QLabel(value)
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_val.setStyleSheet("font-size: 20px; font-weight: bold;")
        lbl_val.setObjectName(f"card_{title}")
        fl.addWidget(lbl_title)
        fl.addWidget(lbl_val)
        return frame

    def _set_card(self, frame, value):
        for child in frame.findChildren(QLabel):
            if child.styleSheet().startswith("font-size: 20"):
                child.setText(str(value))

    def start_training(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_box.append("▶ بدأ التدريب...")

        data = self.mw.get_training_data()

        self.thread = QThread()
        self.worker = TrainWorker(
            self.mw.net,
            self.mw.get_systems(),
            data,
            self.rounds_spin.value()
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.update.connect(self.on_update)
        self.worker.log.connect(self.on_log)
        self.worker.finished.connect(self.on_finished)
        self.thread.start()

    def stop_training(self):
        if self.worker:
            self.worker.stop()
        self.btn_stop.setEnabled(False)
        self.log_box.append("⏹ تم الإيقاف")

    def reset_network(self):
        reply = QMessageBox.question(
            self, "تأكيد", "هل تريد حذف الشبكة الحالية وبدء شبكة جديدة؟"
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.mw.net = GrowingNetwork()
            self.log_box.append("🔄 شبكة جديدة من الصفر")

    def on_update(self, status):
        self._set_card(self.card_round,      status["round"])
        self._set_card(self.card_error,      status["avg_error"])
        self._set_card(self.card_neurons,    status["total"])
        self._set_card(self.card_params,     status["params"])
        self._set_card(self.card_quarantine, status["quarantined"])
        self._set_card(self.card_antibodies, status["antibodies"])

        err_pct = int(status["avg_error"] * 100)
        self.error_bar.setValue(min(err_pct, 100))

        # تحديث جدول الخلايا
        neurons = status.get("neurons_info", [])
        self.cell_table.setRowCount(len(neurons))
        for i, n in enumerate(neurons):
            self.cell_table.setItem(i, 0, QTableWidgetItem(n["id"]))
            self.cell_table.setItem(i, 1, QTableWidgetItem(str(n["generation"])))
            self.cell_table.setItem(i, 2, QTableWidgetItem(str(n["age"])))
            self.cell_table.setItem(i, 3, QTableWidgetItem(str(n["avg_error"])))
            self.cell_table.setItem(i, 4, QTableWidgetItem(str(n["output"])))
            status_text = "🚧 محجورة" if n["quarantined"] else "✅ سليمة"
            item = QTableWidgetItem(status_text)
            if n["quarantined"]:
                item.setForeground(QColor("#ff6b6b"))
            self.cell_table.setItem(i, 5, item)

    def on_log(self, msg):
        self.log_box.append(msg)

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.thread.quit()


# =============================================================
#  تبويب الإعدادات
# =============================================================
class ConfigTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- الشبكة ---
        grp1 = QGroupBox("إعدادات الشبكة الأساسية")
        g1 = QGridLayout(grp1)
        self.lr          = self._dspin(cfg.NETWORK["learning_rate"],   0.001, 1.0, 3)
        self.max_neurons = self._spin(cfg.NETWORK["max_neurons"],      2, 64)
        self.split_thr   = self._dspin(cfg.NETWORK["split_threshold"], 0.01, 1.0, 2)
        self.split_cd    = self._spin(cfg.NETWORK["split_cooldown"],   1, 50)
        g1.addWidget(QLabel("معدل التعلم"),        0, 0); g1.addWidget(self.lr,          0, 1)
        g1.addWidget(QLabel("أقصى خلايا"),         1, 0); g1.addWidget(self.max_neurons, 1, 1)
        g1.addWidget(QLabel("حد الانقسام"),        2, 0); g1.addWidget(self.split_thr,   2, 1)
        g1.addWidget(QLabel("انتظار الانقسام"),    3, 0); g1.addWidget(self.split_cd,    3, 1)
        layout.addWidget(grp1)

        # --- المناعة ---
        grp2 = QGroupBox("إعدادات الجهاز المناعي")
        g2 = QGridLayout(grp2)
        self.anomaly_thr   = self._dspin(cfg.IMMUNE["anomaly_threshold"], 0.5, 1.0, 2)
        self.anomaly_win   = self._spin(cfg.IMMUNE["anomaly_window"],     3, 50)
        self.quar_limit    = self._spin(cfg.IMMUNE["quarantine_limit"],   1, 10)
        self.antibody_max  = self._spin(cfg.IMMUNE["antibody_max"],       10, 500)
        g2.addWidget(QLabel("حد الشذوذ"),          0, 0); g2.addWidget(self.anomaly_thr,  0, 1)
        g2.addWidget(QLabel("نافذة المراقبة"),     1, 0); g2.addWidget(self.anomaly_win,  1, 1)
        g2.addWidget(QLabel("حد الحجر"),           2, 0); g2.addWidget(self.quar_limit,   2, 1)
        g2.addWidget(QLabel("أقصى أجسام مضادة"),  3, 0); g2.addWidget(self.antibody_max, 3, 1)
        layout.addWidget(grp2)

        # --- دورة الحياة ---
        grp3 = QGroupBox("إعدادات دورة الحياة")
        g3 = QGridLayout(grp3)
        self.old_age    = self._spin(cfg.LIFECYCLE["old_age_threshold"],  10, 5000)
        self.complexity = self._dspin(cfg.LIFECYCLE["complexity_limit"],  0.1, 1.0, 1)
        self.autophage  = self._spin(cfg.LIFECYCLE["autophage_interval"], 5,  500)
        g3.addWidget(QLabel("عمر الشيخوخة"),       0, 0); g3.addWidget(self.old_age,    0, 1)
        g3.addWidget(QLabel("حد التعقيد"),          1, 0); g3.addWidget(self.complexity, 1, 1)
        g3.addWidget(QLabel("فترة الالتهام"),      2, 0); g3.addWidget(self.autophage,  2, 1)
        layout.addWidget(grp3)

        # --- زر الحفظ ---
        btn_save = QPushButton("💾  حفظ الإعدادات")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)
        layout.addStretch()

    def _spin(self, val, mn, mx):
        s = QSpinBox(); s.setRange(mn, mx); s.setValue(val); return s

    def _dspin(self, val, mn, mx, dec):
        s = QDoubleSpinBox(); s.setRange(mn, mx)
        s.setDecimals(dec); s.setValue(val); return s

    def save_config(self):
        cfg.NETWORK["learning_rate"]    = self.lr.value()
        cfg.NETWORK["max_neurons"]      = self.max_neurons.value()
        cfg.NETWORK["split_threshold"]  = self.split_thr.value()
        cfg.NETWORK["split_cooldown"]   = self.split_cd.value()
        cfg.IMMUNE["anomaly_threshold"] = self.anomaly_thr.value()
        cfg.IMMUNE["anomaly_window"]    = self.anomaly_win.value()
        cfg.IMMUNE["quarantine_limit"]  = self.quar_limit.value()
        cfg.IMMUNE["antibody_max"]      = self.antibody_max.value()
        cfg.LIFECYCLE["old_age_threshold"]  = self.old_age.value()
        cfg.LIFECYCLE["complexity_limit"]   = self.complexity.value()
        cfg.LIFECYCLE["autophage_interval"] = self.autophage.value()
        QMessageBox.information(self, "تم", "✅ حُفظت الإعدادات في الذاكرة")


# =============================================================
#  تبويب الذاكرة
# =============================================================
class MemoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        # --- أزرار التحكم ---
        ctrl = QHBoxLayout()
        btn_refresh  = QPushButton("🔄  تحديث")
        btn_del_cell = QPushButton("🗑  حذف خلية محددة")
        btn_del_ab   = QPushButton("🧹  مسح الأجسام المضادة")
        btn_del_all  = QPushButton("⚠️  مسح الذاكرة كاملاً")
        btn_refresh.clicked.connect(self.refresh)
        btn_del_cell.clicked.connect(self.delete_selected_cell)
        btn_del_ab.clicked.connect(self.clear_antibodies)
        btn_del_all.clicked.connect(self.clear_all)
        for b in [btn_refresh, btn_del_cell, btn_del_ab, btn_del_all]:
            ctrl.addWidget(b)
        layout.addLayout(ctrl)

        # --- جدول الخلايا ---
        grp1 = QGroupBox("ملفات الخلايا في الذاكرة الصلبة")
        g1   = QVBoxLayout(grp1)
        self.cell_table = QTableWidget(0, 4)
        self.cell_table.setHorizontalHeaderLabels(["المعرّف", "الجيل", "العمر", "متوسط الخطأ"])
        self.cell_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        g1.addWidget(self.cell_table)
        layout.addWidget(grp1)

        # --- الأجسام المضادة ---
        grp2 = QGroupBox("الأجسام المضادة المحفوظة")
        g2   = QVBoxLayout(grp2)
        self.ab_table = QTableWidget(0, 4)
        self.ab_table.setHorizontalHeaderLabels(["النمط avg", "النمط spread", "التكرار", "آخر ظهور"])
        self.ab_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        g2.addWidget(self.ab_table)
        layout.addWidget(grp2)

        # --- الجينات ---
        grp3 = QGroupBox("الجينات المحفوظة (الشرنقة)")
        g3   = QVBoxLayout(grp3)
        self.genes_box = QTextEdit()
        self.genes_box.setReadOnly(True)
        self.genes_box.setMaximumHeight(100)
        g3.addWidget(self.genes_box)
        layout.addWidget(grp3)

        self.refresh()

    def refresh(self):
        self._load_cells()
        self._load_antibodies()
        self._load_genes()

    def _load_cells(self):
        cells_dir = cfg.MEMORY["cells_dir"]
        self.cell_table.setRowCount(0)
        if not os.path.exists(cells_dir):
            return
        for fname in os.listdir(cells_dir):
            if fname.startswith("_") or not fname.endswith(".json"):
                continue
            path = os.path.join(cells_dir, fname)
            with open(path) as f:
                data = json.load(f)
            row = self.cell_table.rowCount()
            self.cell_table.insertRow(row)
            self.cell_table.setItem(row, 0, QTableWidgetItem(data.get("id", "")))
            self.cell_table.setItem(row, 1, QTableWidgetItem(str(data.get("generation", ""))))
            self.cell_table.setItem(row, 2, QTableWidgetItem(str(data.get("age", ""))))
            hist = data.get("error_history", [])
            avg  = round(sum(hist)/len(hist), 4) if hist else 0
            self.cell_table.setItem(row, 3, QTableWidgetItem(str(avg)))

    def _load_antibodies(self):
        path = cfg.MEMORY["antibodies_file"]
        self.ab_table.setRowCount(0)
        if not os.path.exists(path):
            return
        with open(path) as f:
            antibodies = json.load(f)
        for ab in antibodies:
            row = self.ab_table.rowCount()
            self.ab_table.insertRow(row)
            self.ab_table.setItem(row, 0, QTableWidgetItem(str(ab["pattern"]["avg"])))
            self.ab_table.setItem(row, 1, QTableWidgetItem(str(ab["pattern"]["spread"])))
            self.ab_table.setItem(row, 2, QTableWidgetItem(str(ab["count"])))
            self.ab_table.setItem(row, 3, QTableWidgetItem(str(ab["last_seen"])))

    def _load_genes(self):
        path = cfg.MEMORY["genes_file"]
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            self.genes_box.setText(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            self.genes_box.setText("لا توجد جينات محفوظة بعد")

    def delete_selected_cell(self):
        row = self.cell_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر خلية أولاً")
            return
        nid  = self.cell_table.item(row, 0).text()
        path = os.path.join(cfg.MEMORY["cells_dir"], f"{nid}.json")
        if os.path.exists(path):
            os.remove(path)
        self.cell_table.removeRow(row)

    def clear_antibodies(self):
        path = cfg.MEMORY["antibodies_file"]
        if os.path.exists(path):
            os.remove(path)
        self.ab_table.setRowCount(0)
        QMessageBox.information(self, "تم", "🧹 حُذفت الأجسام المضادة")

    def clear_all(self):
        reply = QMessageBox.question(self, "تأكيد", "هل تريد مسح الذاكرة كاملاً؟")
        if reply != QMessageBox.StandardButton.Yes:
            return
        cells_dir = cfg.MEMORY["cells_dir"]
        if os.path.exists(cells_dir):
            for f in os.listdir(cells_dir):
                os.remove(os.path.join(cells_dir, f))
        for p in [cfg.MEMORY["antibodies_file"], cfg.MEMORY["genes_file"]]:
            if os.path.exists(p):
                os.remove(p)
        self.refresh()
        QMessageBox.information(self, "تم", "⚠️ مُسحت الذاكرة كاملاً")


# =============================================================
#  تبويب الاختبار
# =============================================================
class TestTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.mw = main_window
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        grp = QGroupBox("اختبر الشبكة — أدخل مدخلات وشوف التوقع")
        gl  = QGridLayout(grp)

        gl.addWidget(QLabel("المدخل الأول (0.0 → 1.0):"), 0, 0)
        self.in1 = QDoubleSpinBox()
        self.in1.setRange(0.0, 1.0); self.in1.setSingleStep(0.05); self.in1.setValue(0.5)
        gl.addWidget(self.in1, 0, 1)

        gl.addWidget(QLabel("المدخل الثاني (0.0 → 1.0):"), 1, 0)
        self.in2 = QDoubleSpinBox()
        self.in2.setRange(0.0, 1.0); self.in2.setSingleStep(0.05); self.in2.setValue(0.5)
        gl.addWidget(self.in2, 1, 1)

        btn_predict = QPushButton("🔮  توقّع")
        btn_predict.clicked.connect(self.predict)
        gl.addWidget(btn_predict, 2, 0, 1, 2)

        self.result_label = QLabel("النتيجة: —")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("font-size: 28px; font-weight: bold; padding: 16px;")
        gl.addWidget(self.result_label, 3, 0, 1, 2)

        self.verdict_label = QLabel("")
        self.verdict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict_label.setStyleSheet("font-size: 18px;")
        gl.addWidget(self.verdict_label, 4, 0, 1, 2)

        layout.addWidget(grp)

        # --- اختبار دفعي ---
        grp2 = QGroupBox("اختبار دفعي — أدخل قيم متعددة")
        g2   = QVBoxLayout(grp2)
        self.batch_input = QTextEdit()
        self.batch_input.setPlaceholderText(
            "أدخل كل سطر: مدخل1, مدخل2\nمثال:\n0.9, 0.8\n0.1, 0.2\n0.5, 0.5"
        )
        self.batch_input.setMaximumHeight(100)
        g2.addWidget(self.batch_input)
        btn_batch = QPushButton("🔮  اختبار دفعي")
        btn_batch.clicked.connect(self.batch_predict)
        g2.addWidget(btn_batch)
        self.batch_result = QTextEdit()
        self.batch_result.setReadOnly(True)
        g2.addWidget(self.batch_result)
        layout.addWidget(grp2)
        layout.addStretch()

    def predict(self):
        inputs = [self.in1.value(), self.in2.value()]
        result = self.mw.net.predict(inputs)
        self.result_label.setText(f"النتيجة: {result:.4f}")
        if result >= 0.5:
            self.verdict_label.setText("✅ ناجح")
            self.verdict_label.setStyleSheet("font-size: 18px; color: #4caf50;")
        else:
            self.verdict_label.setText("❌ راسب")
            self.verdict_label.setStyleSheet("font-size: 18px; color: #f44336;")

    def batch_predict(self):
        lines = self.batch_input.toPlainText().strip().split("\n")
        self.batch_result.clear()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                parts  = [float(x.strip()) for x in line.split(",")]
                result = self.mw.net.predict(parts)
                verdict = "✅" if result >= 0.5 else "❌"
                self.batch_result.append(f"{line}  →  {result:.4f}  {verdict}")
            except Exception as e:
                self.batch_result.append(f"{line}  →  خطأ: {e}")


# =============================================================
#  تبويب بيانات التدريب
# =============================================================
class DataTab(QWidget):
    def __init__(self):
        super().__init__()
        self.default_data = [
            ("0.9, 0.8", "1.0"),
            ("0.1, 0.2", "0.0"),
            ("0.7, 0.6", "1.0"),
            ("0.3, 0.8", "0.0"),
            ("0.5, 0.5", "0.5"),
            ("0.95, 0.9", "1.0"),
            ("0.05, 0.1", "0.0"),
        ]
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        grp = QGroupBox("بيانات التدريب — عدّل أو أضف أمثلة")
        gl  = QVBoxLayout(grp)

        ctrl = QHBoxLayout()
        btn_add = QPushButton("➕  إضافة سطر")
        btn_del = QPushButton("🗑  حذف سطر")
        btn_add.clicked.connect(self.add_row)
        btn_del.clicked.connect(self.delete_row)
        ctrl.addWidget(btn_add)
        ctrl.addWidget(btn_del)
        ctrl.addStretch()
        gl.addLayout(ctrl)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["المدخلات (مفصولة بفاصلة)", "الهدف"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        gl.addWidget(self.table)
        layout.addWidget(grp)

        for inputs, target in self.default_data:
            self._add_row(inputs, target)

    def _add_row(self, inputs="0.5, 0.5", target="0.5"):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(inputs))
        self.table.setItem(row, 1, QTableWidgetItem(target))

    def add_row(self):
        self._add_row()

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def get_data(self):
        data = []
        for row in range(self.table.rowCount()):
            try:
                inputs_str = self.table.item(row, 0).text()
                target_str = self.table.item(row, 1).text()
                inputs = [float(x.strip()) for x in inputs_str.split(",")]
                target = float(target_str.strip())
                data.append((inputs, target))
            except:
                pass
        return data


# =============================================================
#  النافذة الرئيسية
# =============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SHENN — إدارة الشبكة العصبية التطورية")
        self.setMinimumSize(900, 700)

        # --- تهيئة النظام ---
        self.net = GrowingNetwork.load() or GrowingNetwork()
        self.monitor    = ImmuneMonitor()
        self.apoptosis  = Apoptosis()
        self.antibodies = AntibodySystem()
        self.chrysalis  = Chrysalis()
        self.autophage  = Autophage()

        # --- التبويبات ---
        tabs = QTabWidget()
        self.data_tab   = DataTab()
        self.train_tab  = TrainTab(self)
        self.config_tab = ConfigTab()
        self.memory_tab = MemoryTab()
        self.test_tab   = TestTab(self)

        tabs.addTab(self.train_tab,  "🧠  التدريب")
        tabs.addTab(self.data_tab,   "📊  البيانات")
        tabs.addTab(self.config_tab, "⚙️  الإعدادات")
        tabs.addTab(self.memory_tab, "💾  الذاكرة")
        tabs.addTab(self.test_tab,   "🔮  الاختبار")

        self.setCentralWidget(tabs)
        self._load_stylesheet()

    def _load_stylesheet(self):
        qss_path = os.path.join(os.path.dirname(__file__), "assets", "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path) as f:
                self.setStyleSheet(f.read())

    def get_systems(self):
        return (self.monitor, self.apoptosis,
                self.antibodies, self.chrysalis, self.autophage)

    def get_training_data(self):
        return self.data_tab.get_data()


# =============================================================
#  التشغيل
# =============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())