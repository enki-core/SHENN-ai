# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  config.py : إعدادات النظام الكامل
# =============================================================

# --- الشبكة الأساسية ---
NETWORK = {
    "input_size"       : 2,      # عدد المدخلات
    "learning_rate"    : 0.15,   # سرعة التعلم
    "max_neurons"      : 16,     # أقصى عدد خلايا مسموح
    "split_threshold"  : 0.25,   # حد الخطأ الذي يُفعّل الانقسام
    "split_cooldown"   : 5,      # جولات الانتظار بين كل انقسام
}

# --- الجهاز المناعي ---
IMMUNE = {
    "anomaly_threshold"  : 0.95,  # حد اعتبار الخلية شاذة (خرج > 95% دائماً)
    "anomaly_window"     : 10,    # عدد الجولات لمراقبة الخلية قبل الحكم عليها
    "quarantine_limit"   : 3,     # كم مرة تُعزل قبل الانتحار الخلوي
    "antibody_max"       : 50,    # أقصى عدد أجسام مضادة في الذاكرة
}

# --- الذاكرة الصلبة ---
MEMORY = {
    "cells_dir"       : "memory/cells/",
    "genes_file"      : "memory/genes.json",
    "antibodies_file" : "memory/antibodies.json",
    "save_interval"   : 10,   # احفظ الحالة كل كم جولة
}

# --- دورة الحياة ---
LIFECYCLE = {
    "old_age_threshold"  : 200,   # عدد الجولات قبل اعتبار الشبكة "عجوزاً"
    "complexity_limit"   : 0.8,   # نسبة امتلاء الخلايا التي تُفعّل الشرنقة
    "autophage_interval" : 50,    # كل كم جولة يعمل الالتهام الذاتي
    "autophage_age"      : 100,   # احذف الأجسام المضادة الأقدم من كذا جولة
}

# --- النظام العام ---
SYSTEM = {
    "debug"    : True,   # اطبع تفاصيل أثناء التشغيل
    "log_file" : "shenn.log",
}