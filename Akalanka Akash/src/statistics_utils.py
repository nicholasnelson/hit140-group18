from __future__ import annotations

import math
import random
from statistics import mean, median, stdev


def describe(values: list[float]) -> dict[str, float | int]:
    if len(values) < 2:
        raise ValueError("At least two observations are required")
    return {
        "n": len(values),
        "mean": mean(values),
        "median": median(values),
        "sd": stdev(values),
        "variance": stdev(values) ** 2,
        "min": min(values),
        "max": max(values),
        "skewness": sample_skewness(values),
    }


def sample_skewness(values: list[float]) -> float:
    n = len(values)
    avg = mean(values)
    sd = stdev(values)
    if sd == 0:
        return 0.0
    third_moment = sum(((value - avg) / sd) ** 3 for value in values)
    return n * third_moment / ((n - 1) * (n - 2))


def _continued_fraction_beta(a: float, b: float, x: float) -> float:
    max_iterations = 300
    epsilon = 3e-14
    floor = 1e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = floor if abs(d) < floor else d
    d = 1.0 / d
    result = d
    for iteration in range(1, max_iterations + 1):
        m2 = 2 * iteration
        coefficient = iteration * (b - iteration) * x / ((qam + m2) * (a + m2))
        d = 1.0 + coefficient * d
        d = floor if abs(d) < floor else d
        c = 1.0 + coefficient / c
        c = floor if abs(c) < floor else c
        d = 1.0 / d
        result *= d * c

        coefficient = -(a + iteration) * (qab + iteration) * x / ((a + m2) * (qap + m2))
        d = 1.0 + coefficient * d
        d = floor if abs(d) < floor else d
        c = 1.0 + coefficient / c
        c = floor if abs(c) < floor else c
        d = 1.0 / d
        change = d * c
        result *= change
        if abs(change - 1.0) < epsilon:
            return result
    raise ArithmeticError("Incomplete beta calculation did not converge")


def regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    if not 0.0 <= x <= 1.0:
        raise ValueError("x must be between zero and one")
    if x in (0.0, 1.0):
        return x
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _continued_fraction_beta(a, b, x) / a
    return 1.0 - front * _continued_fraction_beta(b, a, 1.0 - x) / b


def student_t_cdf(value: float, degrees_freedom: float) -> float:
    if degrees_freedom <= 0:
        raise ValueError("Degrees of freedom must be positive")
    if value == 0:
        return 0.5
    x = degrees_freedom / (degrees_freedom + value * value)
    tail = 0.5 * regularized_incomplete_beta(x, degrees_freedom / 2.0, 0.5)
    return 1.0 - tail if value > 0 else tail


def student_t_quantile(probability: float, degrees_freedom: float) -> float:
    if not 0.0 < probability < 1.0:
        raise ValueError("Probability must be between zero and one")
    if probability == 0.5:
        return 0.0
    if probability < 0.5:
        return -student_t_quantile(1.0 - probability, degrees_freedom)
    low, high = 0.0, 1.0
    while student_t_cdf(high, degrees_freedom) < probability:
        high *= 2.0
    for _ in range(100):
        midpoint = (low + high) / 2.0
        if student_t_cdf(midpoint, degrees_freedom) < probability:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2.0


def welch_test(first: list[float], second: list[float]) -> dict[str, float]:
    n1, n2 = len(first), len(second)
    mean1, mean2 = mean(first), mean(second)
    variance1, variance2 = stdev(first) ** 2, stdev(second) ** 2
    if variance1 == 0 and variance2 == 0:
        raise ValueError("Welch's test is undefined when both samples have zero variance")
    component1, component2 = variance1 / n1, variance2 / n2
    standard_error = math.sqrt(component1 + component2)
    statistic = (mean1 - mean2) / standard_error
    degrees = (component1 + component2) ** 2 / (
        component1 ** 2 / (n1 - 1) + component2 ** 2 / (n2 - 1)
    )
    p_value = 2.0 * (1.0 - student_t_cdf(abs(statistic), degrees))
    critical = student_t_quantile(0.975, degrees)
    difference = mean1 - mean2
    return {
        "mean_difference": difference,
        "standard_error": standard_error,
        "degrees_freedom": degrees,
        "t_statistic": statistic,
        "p_value_two_sided": p_value,
        "ci_95_low": difference - critical * standard_error,
        "ci_95_high": difference + critical * standard_error,
    }


def hedges_g(first: list[float], second: list[float]) -> float:
    n1, n2 = len(first), len(second)
    pooled_variance = (
        (n1 - 1) * stdev(first) ** 2 + (n2 - 1) * stdev(second) ** 2
    ) / (n1 + n2 - 2)
    correction = 1.0 - 3.0 / (4.0 * (n1 + n2) - 9.0)
    if pooled_variance == 0:
        raise ValueError("Hedges' g is undefined when pooled variance is zero")
    return correction * (mean(first) - mean(second)) / math.sqrt(pooled_variance)


def randomisation_test(
    first: list[float],
    second: list[float],
    iterations: int = 100_000,
    seed: int = 140,
) -> dict[str, float | int]:
    observed = abs(mean(first) - mean(second))
    combined = first + second
    first_size = len(first)
    rng = random.Random(seed)
    at_least_as_extreme = 0
    for _ in range(iterations):
        shuffled = combined.copy()
        rng.shuffle(shuffled)
        difference = abs(mean(shuffled[:first_size]) - mean(shuffled[first_size:]))
        if difference >= observed - 1e-12:
            at_least_as_extreme += 1
    return {
        "iterations": iterations,
        "seed": seed,
        "observed_absolute_mean_difference": observed,
        "p_value_two_sided": (at_least_as_extreme + 1) / (iterations + 1),
    }
