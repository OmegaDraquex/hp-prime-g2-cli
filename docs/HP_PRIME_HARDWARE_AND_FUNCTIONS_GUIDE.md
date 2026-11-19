# HP Prime Graphing Calculator (G2 / G1) Reference Manual
## Hardware, Keyboard Keys, Built-in Apps, Functions & Operating Modes

This document provides a comprehensive reference covering every physical button, shift combination, operating environment, built-in application, and core math/CAS functions of the HP Prime Graphing Calculator.

---

## 1. Operating Modes & Key Environments

The HP Prime operates across three primary environments:

| Environment | Purpose | How to Access | Key Behavior |
| :--- | :--- | :--- | :--- |
| **Home View** | Numerical calculations, standard scientific operations, real and complex numbers. | Press [Home] | Evaluates expressions numerically (approximations, floating point IEEE 754). |
| **CAS View** | Symbolic mathematics, exact algebra, symbolic calculus, polynomial factorization. | Press [CAS] | Uses the Xcas/Giac computer algebra engine. Results remain exact (e.g. 8*sqrt(5) instead of 17.8885). |
| **HP Apps** | Dedicated mathematical exploration tools (Function, Geometry, Statistics, Solver, etc.). | Press [Apps] | Each app features three specialized views: **Plot**, **Symbolic**, and **Numeric**. |

### Entry Modes
* **Textbook (Default):** Mathematical equations are formatted naturally with 2D fractions, integrals, roots, and exponents.
* **Algebraic:** Standard single-line linear syntax.
* **RPN (Reverse Polish Notation):** Uses a multi-level stack where arguments precede operations ([Enter] pushes to stack, operations evaluate immediately).

---

## 2. Complete Physical Keyboard & Button Directory

The HP Prime keyboard features primary physical functions, secondary functions accessed via the blue **[Shift]** key, and alpha characters accessed via the orange **[Alpha]** key.

### A. Navigation & Control Keys (Top Section)

| Key Face | Blue [Shift] Function | Purpose & Description |
| :--- | :--- | :--- |
| **Apps** | **Info** | **Apps:** Opens the Application Library.<br>**Shift + Apps (Info):** Opens the online documentation and help browser. |
| **Symb** | **Symb Setup** | **Symb:** Opens the Symbolic view for the current app (e.g., F1(X)=).<br>**Shift + Symb (Setup):** Symbolic setup parameters. |
| **Plot** | **Plot Setup** | **Plot:** Renders graphs and geometric views.<br>**Shift + Plot (Setup):** Configures display window axes (Xmin, Xmax, Ymin, Ymax, grid, ticks). |
| **Num** | **Num Setup** | **Num:** Opens table/numerical views of data.<br>**Shift + Num (Setup):** Configures table starting values (NumStart) and step increments (NumStep). |
| **Home** | **Settings** | **Home:** Switches to the standard numerical computation view.<br>**Shift + Home (Settings):** System-wide preferences (Angle Measure, Number Format, Decimal Mark). |
| **CAS** | **CAS Settings** | **CAS:** Toggles the Computer Algebra System.<br>**Shift + CAS (Settings):** Configures CAS precision, simplification level, complex mode, and base. |
| **View** | **Copy** | **View:** Displays view options for the current app (e.g., Split Screen Plot/Table, Auto Scale).<br>**Shift + View (Copy):** Copies selected object or history line to clipboard. |
| **Menu** | **Paste** | **Menu:** Displays context-sensitive menu options or toolbox popup.<br>**Shift + Menu (Paste):** Pastes contents from clipboard. |
| **Esc / Clear** | **Clear** | **Esc:** Cancels operation, exits menus, or backs up one level.<br>**Shift + Esc (Clear):** Clears the entire screen or calculation history. |
| **Rocker Wheel** | — | 8-way directional navigation pad for moving cursor, tracing plots, and scrolling tables. |

---

### B. Function, Catalog & Tool Keys (Middle Section)

| Key Face | Blue [Shift] Function | Purpose & Description |
| :--- | :--- | :--- |
| **Toolbox** | — | Opens categorized menus: **Math**, **CAS**, **App**, and **Catlg** (Catalog of all functions). |
| **Vars (x#)** | **Chars** | **Vars:** Opens the Variable management menu (Home, App, and CAS variables).<br>**Shift + Vars (Chars):** Character map selector for Greek letters, math accents, and unicode symbols. |
| **Math Template** | — | Opens 2D fill-in template palette: fractions, square roots, n-th roots, derivatives, definite integrals, summations, limits, matrices, absolute values. |
| **X, T, theta, N** | — | Inserts independent variable according to current app mode (X for Function, T for Parametric, theta for Polar, N for Sequence). |
| **Memory (List)** | **[List]** | Opens List catalog and list editor (L1 through L0, custom lists). |
| **Matrix** | **[Matrix]** | Opens Matrix catalog and matrix editor (M1 through M0, vectors, linear algebra arrays). |
| **Program** | **[Program]** | Opens Program Catalog to create, edit, run, and debug HP PPL scripts. |
| **Notes** | **[Notes]** | Opens Note Editor to write and review text notes and documentation. |

---

### C. Scientific & Math Keys (Mid-Lower Section)

| Key Face | Blue [Shift] Function | Orange [Alpha] | Purpose & Description |
| :--- | :--- | :--- | :--- |
| **SIN** | **ASIN** | **S** | Sine and Inverse Sine (ArcSine). |
| **COS** | **ACOS** | **C** | Cosine and Inverse Cosine (ArcCosine). |
| **TAN** | **ATAN** | **T** | Tangent and Inverse Tangent (ArcTangent). |
| **LN** | **e^x** | **L** | Natural logarithm (ln) and Exponential function (e^x). |
| **LOG** | **10^x** | **G** | Common logarithm (log10) and base-10 power (10^x). |
| **x^2** | **sqrt(x)** | **Q** | Square (x^2) and Square Root. |
| **x^y** | **root(n, x)** | **P** | Arbitrary power (x^y) and arbitrary root. |
| **x^-1** | **|x| (Abs)** | **I** | Reciprocal (1/x) and Absolute Value. |
| **a b/c (Frac)** | **Hex / DMS** | — | Cycles numeric answers between Proper Fraction, Mixed Fraction, and Decimal. **Shift:** Degrees/Minutes/Seconds or Hex conversions. |

---

### D. Input, Editing, and Entry Keys (Bottom Section)

| Key Face | Blue [Shift] Function | Purpose & Description |
| :--- | :--- | :--- |
| **Shift** | — | Activates blue function printed above/beside each key. Double-tap locks Shift. |
| **Alpha** | — | Activates orange letter/symbol on key. Double-tap locks Alpha mode. |
| **ON / Off** | **Off** | **Tap:** Turns calculator on; acts as Cancel/Break during program execution.<br>**Shift + ON:** Powers off the device. |
| **Backspace** | **Del** | Deletes character to the left. **Shift + Backspace:** Deletes character under cursor. |
| **Ans** | **Last Value** | Inserts the result of the previous calculation (Ans). |
| **Sto ->** | — | Assigns and stores values into variables (e.g. 25 STO A). |
| **Enter** | — | Evaluates expression, calculates result, confirms dialog choice. |
| **(-)** | — | Unary negative sign (distinct from subtraction operator -). |
| **EEX** | — | Scientific exponent notation: 10^n (e.g. 1.23 EEX 6). |
| **Relations** | — | Pops up relational/boolean palette (=, !=, <, <=, >, >=, AND, OR, NOT, XOR). |

---

## 3. Built-in HP Applications Reference

The HP Prime includes 18 specialized applications:

* **Function App:** Analyzes 2D functions y = f(x). Features root-finding, extrema (min/max), slopes (dy/dx), definite integrals, and intersections.
* **Advanced Graphing App:** Plots implicit relations and inequalities in two variables (e.g., x^2 + y^2 <= 25).
* **Graph 3D App:** Renders three-dimensional surfaces defined by z = f(x, y) with 3D touch rotation and cross sections.
* **Parametric App:** Plots parametric functions defined by (X(T), Y(T)).
* **Polar App:** Plots polar equations defined by r = f(theta).
* **Sequence App:** Models recurrences and discrete differences, e.g., U1 = U1(N-1) + U1(N-2).
* **Solve App:** Solves single equations or systems of non-linear equations numerically for any selected variable.
* **Linear Solver:** Instant solutions for 2x2 and 3x3 linear systems of equations.
* **Triangle Solver:** Solves unknown angles and sides of arbitrary triangles using Law of Sines / Cosines.
* **Finance App:** Solves Time-Value-of-Money (TVM) problems (PV, FV, NPV, amortization).
* **Statistics 1Var:** Univariate descriptive statistics, histograms, box plots, mean, standard deviation.
* **Statistics 2Var:** Bivariate statistics, scatter plots, linear and non-linear regressions.
* **Inference App:** Hypothesis testing and confidence intervals (z-test, t-test, ANOVA).
* **Geometry App:** Dynamic Euclidean geometric constructions (points, circles, segments, loci).
* **Spreadsheet:** Grid spreadsheet supporting formulas, cell references, and data visualization.

---

## 4. Comprehensive Command & Function Categories

The **Toolbox key** gives access to hundreds of commands organized across four major menus:

### A. Math Menu (Numerical Functions)
* **Numbers:** CEILING, FLOOR, ROUND, TRUNCATE, MANT, XPON, IP, FP.
* **Arithmetic:** MAX, MIN, MOD, ROOT, %, %CHANGE.
* **Complex:** ARG, CONJ, RE, IM, SIGN.
* **Trigonometric & Hyperbolic:** SIN, COS, TAN, CSC, SEC, COT, SINH, COSH, TANH, ASINH, ACOSH, ATANH.
* **Probability & Distributions:** !, COMB, PERM, RANDOM, RANDINT, RANDNORM, NORMAL_CDF, STUDENT_CDF, BINOMIAL_CDF, POISSON_CDF.

### B. CAS Menu (Computer Algebra System - Symbolic)
* **Algebra:** FACTOR, EXPAND, SIMPLIFY, PARTFRAC, SUBST.
* **Calculus:** DIFF, INT, LIMIT, SERIES, CURL, DIVERGENCE.
* **Solvers:** SOLVE, ZEROS, DESOLVE, LINSOLVE.
* **Matrices & Vectors:** DET, INV, RREF, EIGENVAL, EIGENVV, CROSS, DOT.
* **Polynomials:** ROOTS, GCD, LCM, POLYFORM, TAYLOR.

---

## 5. Touch Gestures & Hardware Shortcuts

* **Tap:** Select menu item, cell, or position cursor.
* **Pinch-to-Zoom:** Zoom in/out on graphs horizontally, vertically, or proportionally.
* **Drag / Pan:** Pan plot axes or navigate spreadsheet cells.
* **Shift + ON:** Power Off.
* **Shift + Esc:** Complete screen reset/clear.
* **Tap Battery / Clock Icon:** Quick Settings slider for brightness, volume, and date/time.

*(For the complete 761-page unabridged manual with step-by-step mathematical proofs and examples, refer to HP_Prime_User_Guide_EN.pdf in this directory).*
