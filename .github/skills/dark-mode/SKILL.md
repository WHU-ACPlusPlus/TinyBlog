---
name: dark-mode
description: 'Apply 深色模式 (Dark Mode) design style to QML UI. Use when: user asks for dark theme, dark mode,夜间模式,暗色, low-light, OLED, or night-friendly interface. Keywords: 深色模式, 暗色, dark mode, dark theme, 夜间, 护眼, low-light, OLED.'
---

# 深色模式 (Dark Mode) — QML Design Tokens

Apply this for comfortable low-light, low-glare interfaces. **Can be combined with other styles.**

## Design Tokens

```qml
// ── Surface Colors (never pure black) ──
readonly property color bgBase:         "#121212"    // M3 dark surface
readonly property color bgElevated:     "#1e1e1e"    // Slightly lighter
readonly property color bgCard:         "#1e1e24"    // Subtle blue-black
readonly property color bgInput:        "#2a2a2e"

// ── Divider / Border ──
readonly property color divider:        Qt.rgba(1, 1, 1, 0.12)
readonly property color borderSubtle:   Qt.rgba(1, 1, 1, 0.08)

// ── Text (阶梯对比) ──
readonly property color textPrimary:    Qt.rgba(1, 1, 1, 0.87)
readonly property color textSecondary:  Qt.rgba(1, 1, 1, 0.60)
readonly property color textTertiary:   Qt.rgba(1, 1, 1, 0.38)
readonly property color textDisabled:   Qt.rgba(1, 1, 1, 0.20)

// ── Accent (克制高光) ──
readonly property color accent:         "#7cacf8"    // Muted blue, not full saturation
readonly property color accentHover:    "#9cc0ff"
readonly property color accentPressed:  "#5c8ce0"
readonly property color error:          "#ff6b6b"    // Soft red, not pure #ff0000

// ── Card Shadows ──
// Dark mode: subtle inner/outer instead of dark-on-light
// Outer: color "#000", opacity 0.20, radius 8, offset (0, 4)
// Or use border elevation instead of shadow

// ── Radii ──
readonly property int radiusSm:   8
readonly property int radiusMd:   12
readonly property int radiusLg:   16

// ── Borders ──
readonly property int borderWidth: 1
// border.color: divider

// ── Surface Elevation (via lightness, not shadow) ──
// L0: bgBase     (#121212)
// L1: bgElevated (#1e1e1e)
// L2: bgCard     (#242424)
// L3: bgInput    (#2a2a2a)
// Higher = lighter surface (inverse of light mode)

// ── Animation ──
readonly property int animDuration: 180  // 150-220ms, smooth
readonly property string animCurve: "easeOutCubic"
// Reduce animation brightness/speed for comfort
```

## QML Implementation Pattern

```qml
// Dark base — never pure black
Rectangle {
    color: "#121212"

    // Elevated card (lighter surface = "higher")
    Rectangle {
        color: "#1e1e24"
        radius: 12
        border { width: 1; color: Qt.rgba(1, 1, 1, 0.08) }

        // Optional subtle inner shadow for depth
        // Use a gradient overlay instead of heavy box-shadow
    }

    // Text — opacity hierarchy, never pure white
    Text { color: Qt.rgba(1, 1, 1, 0.87); font.pixelSize: 16 }  // Primary
    Text { color: Qt.rgba(1, 1, 1, 0.60); font.pixelSize: 14 }  // Secondary
    Text { color: Qt.rgba(1, 1, 1, 0.38); font.pixelSize: 12 }  // Caption

    // Muted accent button — avoid saturated colors on dark bg
    Rectangle {
        color: "#7cacf8"
        radius: 8
        Text { color: "#121212"; text: "Action" }  // Dark text on light accent
        Behavior on color { ColorAnimation { duration: 180 } }
    }

    // Separator — thin, subtle
    Rectangle {
        height: 1
        color: Qt.rgba(1, 1, 1, 0.12)
    }
}

// Hover: surface lightens + border contrast increases
// Active: surface lightens slightly more, subtle sink
```

## Key Principles

1. **Never pure black** — `#121212` minimum, or `#0d0d1a` for blue-black
2. **Elevation = lighter surface** — inverse of light mode; higher cards are brighter
3. **Text opacity阶梯** — 87% → 60% → 38% → 20%
4. **Muted accent colors** — desaturate by ~30% vs light mode to avoid glare
5. **No glass over-brightness** — translucent cards must stay dark enough to prevent glare
6. **Separation via lightness + borders** — not shadows (shadows invisible on dark)
7. **Reduce animation brightness** — dynamic elements should not flash white
