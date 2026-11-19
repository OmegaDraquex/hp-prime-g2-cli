# HP Prime G2 PPL: Complete Autonomous LLM Agent Engineering Guide

> **Authoritative Specification & Architecture Guide**  
> Target Platform: **HP Prime Graphing Calculator (G1 & G2 Hardware)**  
> Firmware Target: **HP Prime Firmware 2.4.15515+ / HP Prime Virtual Calculator**  
> Language: **HP PPL (Prime Programming Language)**  
> Automated Validator: [test_ppl_syntax.py](../tools/test_ppl_syntax.py)

---

## 1. Executive Summary & Architecture Selection

The HP Prime G2 supports two runtimes: **HP PPL** and **MicroPython**. For games, graphical utilities, and responsive user interfaces, **always choose HP PPL**.

| Feature | HP PPL (Prime Programming Language) | HP Prime MicroPython |
| :--- | :--- | :--- |
| **GPU / Buffer Access** | Direct, zero-overhead hardware blitting (`G0`–`G9`, `BLIT_P`, `RECT_P`). | High-overhead Python wrapper (`hpgraphics`), visible lag. |
| **Touchscreen API** | Native `MOUSE` event system (coordinates, touch-down, release). | Fragile, inconsistent across firmware builds. |
| **Persistence** | Native `EXPORT` variables stored in non-volatile calculator memory. | Requires file I/O operations (`open()`), prone to permission bugs. |
| **Execution Safety** | Fast deterministic bytecode execution; native event loops. | Memory fragmentation, slow garbage collection spikes. |
| **Compatibility** | 100% compatible across all physical Prime G1/G2 hardware and emulators. | Requires recent firmware; frequently absent on exam/school units. |

---

## 2. The 10 Inviolable Compiler Rules (The "Never Do" List)

The HP Prime G2 PPL compiler is notoriously unforgiving. The compiler will reject your source file with a cryptic `"Syntax Error"` if you violate any of the following hardware and language constraints:

### Rule 1: Lists and Matrices Are Indexed With Parentheses `L(i)`, NEVER Square Brackets `L[i]`
* In HP PPL, square brackets `[` and `]` are **exclusively reserved for matrix/vector literals** (e.g., `[[1, 2], [3, 4]]`).
* Postfix indexing for lists, strings, and matrices **always uses parentheses**.
* ❌ **WRONG**: `deck[idx]`, `hand[1]`, `matrix[r, c]`
* ✅ **CORRECT**: `deck(idx)`, `hand(1)`, `matrix(r, c)`
* ❌ **WRONG**: `counts[val] := counts[val] + 1;`
* ✅ **CORRECT**: `counts(val) := counts(val) + 1;`

### Rule 2: Lists and Matrices Are 1-Based (`1..N`)
* Indexing starts at `1`.
* Reading index `0` on a list returns the *last* element on some firmware or throws an out-of-range error; on matrices and strings, index `0` causes an immediate runtime exception.
* A list of 5 elements is indexed from `1` to `5`.

### Rule 3: `ELSEIF` and `ELIF` Do NOT Exist in HP PPL
* HP PPL only recognizes `IF ... THEN ... ELSE ... END;` and `CASE ... END;`.
* ❌ **WRONG**:
  ```ppl
  IF x == 1 THEN
    DoA();
  ELSEIF x == 2 THEN
    DoB();
  END;
  ```
* ✅ **CORRECT** (Nested IFs):
  ```ppl
  IF x == 1 THEN
    DoA();
  ELSE
    IF x == 2 THEN
      DoB();
    END;
  END;
  ```
* ✅ **CORRECT** (Sequential Independent IFs or CASE):
  ```ppl
  CASE
    IF x == 1 THEN DoA(); END;
    IF x == 2 THEN DoB(); END;
    DEFAULT DoC(); END;
  END;
  ```

### Rule 4: `LOCAL` Declarations MUST Be at the Top of `BEGIN` ($\le 8$ Variables per Line)
* In HP PPL, `LOCAL` declarations must occur **immediately after `BEGIN`**, before *any* executable code or assignments.
* Declaring `LOCAL` inside an `IF`, `FOR`, or `WHILE` block will fail compilation on physical G2 hardware (`ppl.locals-at-top`).
* Hardware limit: A single `LOCAL` statement can declare at most **8 variables**. If you declare 9 or more on one line, compilation fails (`ppl.local-limit`).
* ✅ **CORRECT**:
  ```ppl
  EXPORT MyFunction()
  BEGIN
    LOCAL a, b, c, d;
    LOCAL e, f, g, h;
    LOCAL result, idx;
    
    // Executable code only begins HERE
    a := 10;
  ```

### Rule 5: Assignments Require `:=` (Single `=` Is Equality Test Only)
* Single `=` is strictly an equality operator in PPL expressions. Writing `x = 10;` compiles but performs a no-op comparison, leaving `x` unmodified.
* Always use `:=` for assignment: `target := value;`.

### Rule 6: Every Block Closer Requires a Semicolon (`END;`)
* In HP PPL, block terminators must end with a semicolon: `END;`
* ❌ **WRONG**: `IF x > 0 THEN y := 1; END`
* ✅ **CORRECT**: `IF x > 0 THEN y := 1; END;`

### Rule 7: Never Index the Return Value of a Function Call Directly (`index-call`)
* The HP Prime compiler rejects indexing the result of a function invocation directly at compile time (`ppl.index-call`).
* ❌ **WRONG**: `val := GetTouchInput()(1);`
* ❌ **WRONG**: `sizeVal := SIZE(myList)(1);`
* ✅ **CORRECT**:
  ```ppl
  inp := GetTouchInput();
  val := inp(1);
  ```

### Rule 8: Top-to-Bottom Dependency Order (Calldown Order)
* Declare helper functions **above** the main entry point `EXPORT PROGNAME()`.
* If a helper calls another helper, declare the callee first. This eliminates the need for forward declarations (`MyHelper();`), which can trigger syntax errors if mismatched.

### Rule 9: Source Code Must Be Strict ASCII (No Unicode / UTF-8 Multi-Byte)
* The physical G2 lexer rejects non-ASCII bytes (character codes > 127).
* Do not use curly quotation marks (`“`, `”`), en-dashes (`–`), or Unicode emoji symbols in string literals or comments. Use plain ASCII quotes (`"`) and standard characters.

### Rule 10: Delete the Auto-Generated Calculator Stub Before Pasting
* When creating a new program `PROGNAME` in the HP Connectivity Kit or on the calculator editor (`Shift` + `1` -> `New`), the editor automatically injects:
  ```ppl
  EXPORT PROGNAME()
  BEGIN

  END;
  ```
* If you paste full source code that already contains helper functions and `EXPORT PROGNAME()`, you will end up with duplicate headers or misplaced `EXPORT` statements, triggering a syntax error.
* **Instruction for users**: Always select all and delete the auto-generated template before pasting!

---

## 3. Launching Programs from the Calculator Home Screen

There is a major quirk when running programs from the HP Prime Home screen (`ppl.home-no-parentheses`):
* Zero-argument exported functions must be invoked on the Home screen **WITHOUT parentheses**:
  * ❌ **WRONG on Home Screen**: `LOOGYPOKER()` $\rightarrow$ Produces `Syntax Error`.
  * ✅ **CORRECT on Home Screen**: `LOOGYPOKER` $\rightarrow$ Executes the program cleanly.
* Alternatively, users can press `Shift` + `1` (**Program**), highlight the program name, and tap the **`[Run]`** on-screen button.

---

## 4. Hardware Specifications & Screen Architecture

* **Display**: $320 \times 240$ color TFT LCD.
* **Coordinate System**:
  * X coordinates: `0` (left) to `319` (right).
  * Y coordinates: `0` (top) to `239` (bottom).
* **Graphic Objects (GROBs)**:
  * `G0`: The physical LCD screen buffer. Writing to `G0` directly causes visible screen tearing.
  * `G1` through `G9`: Offscreen framebuffers available for double buffering.
* **Color Representation**:
  * Encoded as 24-bit RGB integers: `color := RGB(red, green, blue);`
  * Formula: $\text{color} = (\text{red} \times 65536) + (\text{green} \times 256) + \text{blue}$.

### The Double-Buffering Standard Pattern
Always render entire frames off-screen onto `G1`, then blit to `G0` in a single atomic pass:

```ppl
// Initialize G1 to full screen dimensions once during startup
DIMGROB_P(G1, 320, 240, RGB(0, 0, 0));

// Inside your render loop:
RECT_P(G1, 0, 0, 319, 239, RGB(0, 0, 0), RGB(20, 60, 30)); // Clear background
// ... draw sprites, shapes, text onto G1 ...
BLIT_P(G0, 0, 0, G1); // Blit G1 onto physical screen G0 instantly
```

---

## 5. Primitive Graphics Reference

### `RECT_P` (Filled and Outlined Rectangles)
```ppl
// Full syntax: RECT_P(grob, x1, y1, x2, y2, borderColor, fillColor)
RECT_P(G1, 10, 20, 62, 78, RGB(255, 215, 0), RGB(255, 255, 255));

// Screen clear syntax:
RECT_P(G1, 0, 0, 319, 239, 0, 0); // Fills G1 with black
```

### `LINE_P` (Lines)
```ppl
// Syntax: LINE_P(grob, x1, y1, x2, y2, color)
LINE_P(G1, 10, 50, 100, 50, RGB(255, 0, 0));
```

### `PIXON_P` (Single Pixel)
```ppl
// Syntax: PIXON_P(grob, x, y, color)
PIXON_P(G1, 160, 120, RGB(0, 255, 0));
```

### `TEXTOUT_P` (Text Rendering)
* **Fonts available**:
  * `1`: Small system font ($\approx 10\text{px}$ height).
  * `2`: Medium font ($\approx 14\text{px}$ height).
  * `3`: Large bold font ($\approx 20\text{px}$ height).
  * ⚠️ *Warning*: Passing `0` for font is invalid on HP Prime G2!
* **Explicit Width Parameter**: Always provide the explicit max-width parameter (7th argument with grob, 6th without grob) to prevent the text engine from clipping or wrapping unexpectedly (`interface.textout-width`).
```ppl
// Syntax: TEXTOUT_P(text, grob, x, y, font, color, width)
TEXTOUT_P("PLAYER SCORE: " + STRING(score), G1, 10, 5, 2, RGB(255, 255, 255), 300);
```

---

## 6. Input Handling: Touchscreen & Physical Keyboard

### The `MOUSE` Command
`MOUSE` returns a nested list structure:
* When screen is **untouched**: `{{}, {}}`
* When screen is **touched**: `{{x, y, original_x, original_y, event_type}, {}}`
  * `event_type`: `0` = touch down / drag, `1` = touch release.

#### Safe Touch Extraction Pattern:
```ppl
PollTouch()
BEGIN
  LOCAL m, f;
  m := MOUSE;
  IF SIZE(m) >= 1 THEN
    f := m(1);
    IF SIZE(f) >= 5 THEN
      // Touch is active!
      // f(1) is current X, f(2) is current Y
      RETURN {f(1), f(2)};
    END;
  END;
  RETURN {-1, -1}; // Not touched
END;
```

### The `GETKEY` Command
* `GETKEY` is written **without parentheses** (it is a system reserved token).
* Returns `-1` if no key is currently pressed.
* Returns an integer keycode when pressed:
  * `4`: `[ON]` key
  * `30` or `4`: `[Esc]` key
  * `51`: `[Enter]` key

### Input Buffer Flushing (`FlushInput`)
Touchscreens generate streams of events. When transitioning between game states or dialog screens, you **must flush the input buffer** to prevent the user's previous tap from registering on the new screen:

```ppl
FlushInput()
BEGIN
  LOCAL m, f, k;
  // Drain physical keyboard queue
  REPEAT
    k := GETKEY;
  UNTIL k == -1;
  
  // Wait until user lifts finger off touchscreen
  REPEAT
    m := MOUSE;
    f := m(1);
    IF SIZE(f) > 0 THEN
      WAIT(0.02);
    END;
  UNTIL SIZE(f) == 0;
  RETURN 0;
END;
```

---

## 7. Persistent Variables Across Calculator Sessions

Any global variable prefixed with `EXPORT` before the functions are defined is placed into the calculator's battery-backed non-volatile RAM:

```ppl
// Top of file, before any function definitions:
EXPORT GAME_COINS := 10;
EXPORT GAME_HIGHSCORE := 0;
EXPORT GAME_STARS := 0;

// Inside game loop:
GAME_COINS := GAME_COINS + payout;
IF GAME_COINS > GAME_HIGHSCORE THEN
  GAME_HIGHSCORE := GAME_COINS;
END;
```
Even if the calculator auto-powers off or the user exits to calculate a matrix, these values retain their state until manually cleared or reset.

---

## 8. Verified Architectural Game Engine Pattern

Below is a complete, copy-pasteable minimal game template adhering to 100% of the HP Prime G2 compiler constraints.

```ppl
// ============================================================================
// MYGAME for HP Prime G2
// Fully compliant PPL Template
// ============================================================================

// 1. Persistent Globals (Persist after exit)
EXPORT MYGAME_COINS := 100;
EXPORT MYGAME_HIGHSCORE := 100;

// 2. Helper: Wait for input release
FlushInput()
BEGIN
  LOCAL m, f, k;
  REPEAT
    k := GETKEY;
  UNTIL k == -1;
  REPEAT
    m := MOUSE;
    f := m(1);
    IF SIZE(f) > 0 THEN
      WAIT(0.02);
    END;
  UNTIL SIZE(f) == 0;
  RETURN 0;
END;

// 3. Helper: Poll Touch and Physical Key
GetInput()
BEGIN
  LOCAL m, f, k, res;
  res := {-1, -1, -1}; // {touch_x, touch_y, key_code}
  
  k := GETKEY;
  IF k >= 0 THEN
    res(3) := k;
    RETURN res;
  END;
  
  m := MOUSE;
  IF SIZE(m) >= 1 THEN
    f := m(1);
    IF SIZE(f) >= 5 THEN
      res(1) := f(1);
      res(2) := f(2);
      RETURN res;
    END;
  END;
  
  RETURN res;
END;

// 4. Helper: Render complete frame onto G1 and flip to G0
RenderFrame(score, buttonPressed)
BEGIN
  LOCAL cBg, cWhite, cGold, cBtn;
  cBg := RGB(20, 50, 30);
  cWhite := RGB(255, 255, 255);
  cGold := RGB(255, 215, 0);
  cBtn := IFTE(buttonPressed == 1, RGB(180, 50, 50), RGB(50, 150, 50));
  
  // Background felt
  RECT_P(G1, 0, 0, 319, 239, RGB(10, 30, 15), cBg);
  
  // Header bar
  RECT_P(G1, 0, 0, 319, 30, RGB(180, 140, 20), RGB(10, 30, 15));
  TEXTOUT_P("MYGAME PPL", G1, 10, 8, 2, cGold, 150);
  TEXTOUT_P("SCORE: " + STRING(score), G1, 200, 8, 2, cWhite, 110);
  
  // Interactive Button (X: 80..240, Y: 100..150)
  RECT_P(G1, 80, 100, 240, 150, cGold, cBtn);
  TEXTOUT_P("TAP TO SCORE", G1, 105, 118, 2, cWhite, 120);
  
  // Blit offscreen buffer G1 to physical screen G0
  BLIT_P(G0, 0, 0, G1);
  RETURN 0;
END;

// 5. Main Program Entry Point
EXPORT MYGAME()
BEGIN
  LOCAL running, inp, tx, ty, tkey;
  LOCAL score, btnToggled;
  
  // Ensure persistent state is valid
  IF MYGAME_COINS < 0 THEN
    MYGAME_COINS := 0;
  END;
  
  // Allocate 320x240 offscreen buffer
  DIMGROB_P(G1, 320, 240, RGB(0, 0, 0));
  
  running := 1;
  score := 0;
  btnToggled := 0;
  
  FlushInput();
  RenderFrame(score, btnToggled);
  
  // Main event loop
  WHILE running == 1 DO
    inp := GetInput();
    tx := inp(1);
    ty := inp(2);
    tkey := inp(3);
    
    // ESC (key 4 / 30) exits program
    IF tkey == 4 OR tkey == 30 THEN
      running := 0;
    END;
    
    // Handle Touch on Button (X: 80..240, Y: 100..150)
    IF tx >= 80 AND tx <= 240 AND ty >= 100 AND ty <= 150 THEN
      score := score + 10;
      IF score > MYGAME_HIGHSCORE THEN
        MYGAME_HIGHSCORE := score;
      END;
      btnToggled := 1;
      RenderFrame(score, btnToggled);
      WAIT(0.1);
      btnToggled := 0;
      RenderFrame(score, btnToggled);
      FlushInput();
    END;
    
    WAIT(0.03); // Frame limiter (~30 FPS)
  END;
  
  // Exit message
  RECT_P(G0, 0, 0, 319, 239, 0, 0);
  TEXTOUT_P("THANKS FOR PLAYING!", G0, 60, 110, 2, RGB(255, 255, 255), 200);
  WAIT(1.0);
  RETURN 0;
END;
```

---

## 9. Automated Verification & Testing Pipeline

Before delivering any PPL code to the user, run the test toolchain in the workspace:

```bash
# 1. Parse, lint, and AST-execute the PPL program with simulated touch events
python3 test_ppl_syntax.py LOOGYPOKER.txt

# 2. Test procedural evaluation algorithms against reference implementations
python3 test_ppl_eval.py

# 3. Test mathematical game logic, random shuffle, and probabilities
python3 test_game_logic.py
```

### What [test_ppl_syntax.py](../tools/test_ppl_syntax.py) Validates:
1. Rejects any square-bracket indexing `L[i]`.
2. Flags missing semicolons on `END;`.
3. Verifies `LOCAL` variables are declared strictly at the top of `BEGIN` ($\le 8$ per statement).
4. Forbids `ELSEIF` and invalid keywords.
5. Catches direct function call indexing `F()(i)`.
6. Parses the complete code into an AST and executes every function, verifying memory assignments, double-buffered graphics calls, and touch loops without calculator access.
