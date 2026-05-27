# =============================================================
#  SHENN — Self-Healing Evolutionary Neural Network
#  core/activations.py : دوال التفعيل
# =============================================================

import math


def sigmoid(x):
    """تحول أي رقم إلى قيمة بين 0 و 1"""
    x = max(-500, min(500, x))  # منع overflow
    return 1.0 / (1.0 + math.exp(-x))


def sigmoid_deriv(x):
    """مشتقة sigmoid — تُستخدم في التدريب"""
    s = sigmoid(x)
    return s * (1.0 - s)


def relu(x):
    """تعطي الرقم كما هو إذا موجب، وصفر إذا سالب"""
    return max(0.0, x)


def relu_deriv(x):
    """مشتقة relu"""
    return 1.0 if x > 0 else 0.0


def tanh_activation(x):
    """تحول الرقم إلى قيمة بين -1 و 1"""
    return math.tanh(x)


def tanh_deriv(x):
    """مشتقة tanh"""
    return 1.0 - math.tanh(x) ** 2


# --- الدالة المختارة للنظام ---
# غيّر هذا المتغير لتغيير دالة التفعيل في كل النظام
ACTIVATION       = sigmoid
ACTIVATION_DERIV = sigmoid_deriv