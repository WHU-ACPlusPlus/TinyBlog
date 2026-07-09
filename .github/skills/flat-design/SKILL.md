---
name: flat-design
description: 'Apply 平面设计系统 (Flat Design) style to QML UI. Use when: user asks for flat,扁平, flat design, no shadows, bold colors, clean, modern minimal, or 2D pure interface. Keywords: 扁平, flat, flat design, 纯色, 无阴影, bold colors, 二维, clean.'
---

# 平面设计系统 (Flat Design) — QML Design Tokens

Apply this for bold, shadow-free, poster-like interfaces.

## Design Tokens

```qml
// ── Colors (bold, saturated, no gradients) ──
readonly property color bgPrimary:     "#ffffff"
readonly property color bgSecondary:   "#f8f9fa"
readonly property color primary:       "#2563eb"    // Bold blue
readonly property color primaryDark:   "#1d4ed8"
readonly property color secondary:     "#059669"    // Bold green
readonly property color accent:        "#dc2626"    // Bold red
readonly property color warning:       "#f59e0b"

// ── Text (pure black and white, no opacity tricks) ──
readonly property color textPrimary:   "#111827"
readonly property color textSecondary: "#6b7280"
readonly property color textOnColor:   "#ffffff"

// ── No Shadows — period ──
// shadow: none on ALL elements
// Hierarchy via color, size, spacing ONLY

// ── Radii (small to none) ──
readonly property int radiusNone:  0      // Sharp corners preferred
readonly property int radiusSm:    2      // Max subtle rounding
readonly property int radiusMd:    4

// ── Borders (solid, visible) ──
readonly property int borderWidth: 2      // Bold borders!
// border.color: primary or textSecondary

// ── Spacing ──
readonly property int grid:        8
readonly property int marginSm:    8
readonly property int marginMd:    16
readonly property int marginLg:    24
readonly property int marginXl:    32

// ── Typography (large, bold) ──
// Titles: 28-36px, bold weight
// Body: 16-18px, regular
// Labels: 12-14px, all-caps, bold

// ── Animation ──
readonly property int animDuration: 150   // Short, sharp
readonly property string animCurve: "easeOutQuad"  // Simple curve
```

## QML Implementation Pattern

```qml
// Flat white background
Rectangle {
    color: "#ffffff"

    // Flat card — just a colored rectangle
    Rectangle {
        color: "#f8f9fa"
        radius: 2                    // Subtle at most
        // NO border (optional solid accent-left border)
        Rectangle {
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
            width: 4
            color: "#2563eb"        // Left accent stripe
        }
        // NO shadows — depth via color contrast alone
    }

    // Bold primary button
    Rectangle {
        color: "#2563eb"
        radius: 2
        Text { color: "white"; text: "ACTION"; font.bold: true; font.pixelSize: 14 }
        // Hover: switch to darker flat color (#1d4ed8)
        Behavior on color { ColorAnimation { duration: 150 } }
    }

    // Outline button
    Rectangle {
        color: "transparent"
        radius: 2
        border { width: 2; color: "#2563eb" }
        Text { color: "#2563eb"; text: "Cancel"; font.pixelSize: 14 }
    }

    // Text: bold, plain, no shadows
    Text { font.pixelSize: 28; font.bold: true; color: "#111827" }  // H1
    Text { font.pixelSize: 16; color: "#6b7280" }                   // Body
}
```

## Key Principles

1. **Zero shadows** — this is the defining rule of flat design
2. **Bold, saturated colors** — pure hex values, no opacity or gradient
3. **Sharp or near-sharp corners** — radius 0-4px max
4. **Solid borders** — visible, 2px+ when used
5. **Hierarchy = size + weight + color** — not elevation or shadow
6. **Hover = color swap** — deeper shade of the same hue, no lift
7. **Typography is decoration** — large titles, bold labels, clean sans-serif
