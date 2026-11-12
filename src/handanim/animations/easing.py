from __future__ import annotations

import math

from .zoom import ZoomInAnimation


def linear(t: float) -> float:
    """Linear identity easing: f(t) = t."""
    return float(t)


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in: f(t) = t^2."""
    return float(t * t)


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out: f(t) = 1 - (1 - t)^2."""
    u = 1.0 - t
    return float(1.0 - u * u)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out."""
    if t < 0.5:
        return float(2.0 * t * t)
    return float(1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0)


def ease_in_cubic(t: float) -> float:
    """Cubic ease-in: f(t) = t^3."""
    return float(t * t * t)


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out: f(t) = 1 - (1 - t)^3."""
    return float(1.0 - (1.0 - t) ** 3)


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out: accelerates to midpoint then decelerates smoothly."""
    if t < 0.5:
        return float(4.0 * t * t * t)
    return float(1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0)


# Standard smooth ease-in-out alias used in shorts/hand.py
ease_in_out = ease_in_out_cubic


def ease_in_back(t: float, overshoot: float = 1.70158) -> float:
    """Back ease-in: pulls back slightly before accelerating forward."""
    c3 = overshoot + 1.0
    return float(c3 * t * t * t - overshoot * t * t)


def ease_out_back(t: float, overshoot: float = 1.9) -> float:
    """Overshoot 'pop' ease-out: overshoots 1.0 slightly then settles back to 1.0."""
    c3 = overshoot + 1.0
    u = t - 1.0
    return float(1.0 + c3 * u * u * u + overshoot * u * u)


def ease_in_out_back(t: float, overshoot: float = 1.70158) -> float:
    """Symmetric back ease-in-out with slight pull-back and overshoot."""
    c2 = overshoot * 1.525
    if t < 0.5:
        return float(((2.0 * t) ** 2 * ((c2 + 1.0) * 2.0 * t - c2)) / 2.0)
    return float(((2.0 * t - 2.0) ** 2 * ((c2 + 1.0) * (t * 2.0 - 2.0) + c2) + 2.0) / 2.0)


def ease_out_elastic(t: float) -> float:
    """Elastic spring ease-out."""
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return float(2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * c4) + 1.0)


def ease_out_bounce(t: float) -> float:
    """Bounce ease-out."""
    n1 = 7.5625
    d1 = 2.75
    if t < 1.0 / d1:
        return float(n1 * t * t)
    if t < 2.0 / d1:
        t -= 1.5 / d1
        return float(n1 * t * t + 0.75)
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return float(n1 * t * t + 0.9375)
    t -= 2.625 / d1
    return float(n1 * t * t + 0.984375)


class PopAnimation(ZoomInAnimation):
    """Zoom-in animation with an overshoot 'pop' easing (`ease_out_back`)."""

    def __init__(
        self,
        start_time: float = 0.0,
        duration: float = 0.32,
        overshoot: float = 1.9,
        easing_fun=None,
        data: dict | None = None,
    ) -> None:
        if easing_fun is None:
            def _pop_ease(p: float) -> float:
                return ease_out_back(p, overshoot=overshoot)

            easing_fun = _pop_ease
        super().__init__(start_time=start_time, duration=duration, easing_fun=easing_fun, data=data)

