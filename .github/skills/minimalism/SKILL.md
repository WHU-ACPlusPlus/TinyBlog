---
name: minimalism
description: 'Apply 极简主义 (Minimalism) design style to QML UI. Use when: user asks for minimal, clean, content-first, black-and-white, grid-based, simple, or elegant design. Keywords: 极简, 简约, 简洁, 少即是多, minimal, minimalist.'
---

# 极简主义 (Minimalism) — QML Design Tokens

Apply this style when the user wants a clean, content-first interface with minimal decoration.

## Design Tokens

```qml
// ── Colors ──
readonly property color bgPrimary:     "#ffffff"
readonly property color bgSecondary:   "#f5f5f5"
readonly property color bgTertiary:    "#eeeeee"
readonly property color textPrimary:   "#111111"
readonly property color textSecondary: "#666666"
readonly property color textTertiary:  "#999999"
readonly property color accent:        "#333333"    // Single accent, used sparingly
readonly property color borderColor:   "#e0e0e0"    // Fine separators
readonly property color divider:       "#eeeeee"

// ── Spacing (grid-based, multiples of 4px/8px) ──
readonly property int grid:       4
readonly property int marginXs:   4
readonly property int marginSm:   8
readonly property int marginMd:   16
readonly property int marginLg:   24
readonly property int marginXl:   32
readonly property int margin2xl:  48

// ── Radii ──
readonly property int radiusSm:   2     // Subtle rounding
readonly property int radiusMd:   4
readonly property int radiusLg:   6     // Max: avoid large curves

// ── Shadows (very subtle, if any) ──
// No box shadows on most elements. If needed:
// color: "black", opacity: 0.04, radius: 4, offset: (0, 1)
// Never use heavy shadows — rely on spacing for hierarchy.

// ── Borders (thin, consistent) ──
readonly property int borderWidth: 1
// border.color: borderColor

// ── Animation ──
readonly property int animDuration: 200    // ms, slightly slower for calm feel
readonly property string animCurve: "easeOutCubic"  // or Easing.OutCubic
```

## QML Implementation Pattern

```qml
Rectangle {
    // White background, no gradient
    color: "#ffffff"

    // Light card with subtle border, no shadow
    Rectangle {
        color: "#fafafa"
        radius: 4
        border { width: 1; color: "#eeeeee" }
    }

    // Text hierarchy: size + weight + color, no shadow
    Text { font.pixelSize: 22; font.bold: true;  color: "#111" }  // H1
    Text { font.pixelSize: 16; font.bold: false; color: "#333" }  // Body
    Text { font.pixelSize: 13; font.bold: false; color: "#999" }  // Caption

    // Button: border color change on hover, no scale
    Behavior on border.color { ColorAnimation { duration: 200 } }
}
```

## Key Principles

1. **No gradients, no textures, no heavy shadows** — hierarchy via spacing and typography
2. **Single accent color** — use for primary actions only
3. **Generous whitespace** — margins grow with importance
4. **Thin, consistent border widths** — 1px throughout
5. **Typography is the texture** — vary size, weight, and color; never add text shadows
6. **Hover = subtle** — border color or opacity change only, no scaling
