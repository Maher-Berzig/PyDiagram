# plot_math.py
"""
App addition (not in the manual): a small, restricted expression
evaluator for the Plot shape's f1(x)/f2(x) fields (items/plot_item.py)
- Python syntax (e.g. "sin(x) + 1", "x**2 - 3*x"), with only Python's
math module and a handful of builtins exposed, and no access to
__builtins__. This isn't a general-purpose sandbox (PyDiagram is a
local desktop app, not a network service) - it's just enough that a
typo, or a stray "import os", fails to evaluate rather than doing
something surprising.
"""

import math

_SAFE_NAMES = {
    name: getattr(math, name)
    for name in dir(math)
    if not name.startswith("_")
}
_SAFE_NAMES.update({
    "abs": abs, "min": min, "max": max, "pow": pow, "round": round,
})


class FunctionError(ValueError):
    pass


def compile_function(expr):
    """
    Compiles `expr` (a Python expression in `x`, e.g. "sin(x) + 1")
    once, returning a callable f(x) -> float. A bare "^" is rewritten
    to "**" first, since anyone coming from ordinary math notation
    (x^2) means exponentiation, not Python's bitwise XOR - which is
    what a literal "^" would otherwise silently (and confusingly) do
    here. Raises FunctionError immediately - not at first use - if
    the expression doesn't parse, or fails outright at a test point,
    so a typo shows up the moment the Properties dialog's OK is
    clicked, not as a silently blank plot. The returned f(x) itself
    never raises: a domain error at one particular x (e.g. sqrt(-1) or
    log(0)) returns NaN there instead, which just leaves a gap in the
    curve at that point - matplotlib's own behavior for the same case.
    """

    expr = (expr or "").strip()

    if not expr:
        raise FunctionError("Enter an expression in x, e.g. sin(x)")

    expr = expr.replace("^", "**")

    try:
        code = compile(expr, "<plot-function>", "eval")
    except SyntaxError as exc:
        raise FunctionError(f"Invalid expression: {exc}") from exc

    namespace = {"__builtins__": {}, **_SAFE_NAMES}

    try:
        eval(code, namespace, {"x": 1.0})
    except Exception as exc:
        raise FunctionError(f"Couldn't evaluate \"{expr}\" at x=1: {exc}") from exc

    def f(x):
        try:
            return float(eval(code, namespace, {"x": x}))
        except Exception:
            return float("nan")

    return f


def sample(f, x_start, x_end, num_points, extra_xs=()):
    """
    (xs, ys) sampled from `f` across [x_start, x_end] - `num_points`
    evenly spaced points, plus any `extra_xs` (e.g. the fill region's
    own x_min/x_max) merged in and sorted, so a boundary the fill
    region depends on always lands exactly on a sample point rather
    than only approximately (matching the reference implementation's
    own np.concatenate([linspace(...), [x_min, x_max]])).
    """

    num_points = max(2, int(num_points))
    step = (x_end - x_start) / (num_points - 1) if num_points > 1 else 0

    xs = sorted({
        *(x_start + i * step for i in range(num_points)),
        *(x for x in extra_xs if x_start <= x <= x_end),
    })

    ys = [f(x) for x in xs]

    return xs, ys
