---
name: fluent-design
description: 'Apply Fluent Design 2.0 (Microsoft) style to QML UI. Use when: user asks for Fluent, Fluent 2, Windows 11 style, acrylic, Mica, soft gradients, system feel, or Microsoft design language. Keywords: fluent, fluent2, acrylic, mica, Windows 11, 微软, 亚克力, 系统风格.'
---

# Fluent Design 2.0 — QML Design Tokens

Apply this for a Windows 11-like, soft-gradient, acrylic-card interface.

## Design Tokens

```qml
// ── Background ──
// Soft light gradient or subtle texture (not flat white)
// Light mode: "#f0f0f3" → "#e8e8ec" → "#f5f5f8"
// Dark mode: "#202020" → "#2d2d2d" → "#1a1a1a"

// ── Acrylic Card ──
readonly property color acrylicBg:       Qt.rgba(1, 1, 1, 0.75)    // Light mode
readonly property color acrylicBgDark:   Qt.rgba(0.125, 0.125, 0.125, 0.70) // Dark
readonly property color acrylicBorder:   Qt.rgba(1, 1, 1, 0.60)    // High-gloss edge
readonly property color acrylicHighlight: Qt.rgba(1, 1, 1, 0.85)   // Top sheen

// ── Accent Colors (Fluent Blue family) ──
readonly property color accentPrimary:   "#0078d4"    // Fluent blue
readonly property color accentHover:     "#106ebe"
readonly property color accentPressed:   "#005a9e"
readonly property color accentLight:     "#c7e0f4"    // Light tint background

// ── Text ──
readonly property color textPrimary:     "#1a1a1a"
readonly property color textSecondary:   "#616161"
readonly property color textTertiary:    "#a0a0a0"
readonly property color textOnAccent:    "#ffffff"

// ── Shadows (gentle, layered) ──
// Card rest:   color "#000", opacity 0.04, radius 8,  offset (0, 2)
// Card hover:  color "#000", opacity 0.08, radius 16, offset (0, 4)
// Card active: color "#000", opacity 0.12, radius 4,  offset (0, 1)

// ── Radii (consistent rounded system) ──
readonly property int radiusSm:    4
readonly property int radiusMd:    8
readonly property int radiusLg:    12
readonly property int radiusButton: 6    // Pill-shaped at max

// ── Borders ──
readonly property int borderWidth: 1
// border.color: acrylicBorder (or transparent on cards)

// ── Animation ──
readonly property int animDuration: 250   // 150-300ms Fluent range
readonly property string animCurve: "easeOutCubic"  // Fluent standard curve
```

## QML Implementation Pattern

```qml
// Soft gradient background
Rectangle {
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#f0f0f3" }
        GradientStop { position: 0.5; color: "#e8e8ec" }
        GradientStop { position: 1.0; color: "#f5f5f8" }
    }

    // Acrylic card
    Rectangle {
        color: Qt.rgba(1, 1, 1, 0.75)
        radius: 12
        border { width: 1; color: Qt.rgba(1, 1, 1, 0.6) }
        // Top highlight
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: parent.radius * 0.5
            radius: parent.radius
            color: Qt.rgba(1, 1, 1, 0.85)
        }

        // Hover: slight lift
        Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
        // Hover: scale 1.005, shadow deepens
    }

    // Accent button
    Rectangle {
        color: "#0078d4"
        radius: 6
        Text { text: "Action"; color: "white"; font.pixelSize: 14 }
        // Hover: darken to #106ebe
        Behavior on color { ColorAnimation { duration: 200 } }
    }
}
```

## Key Principles

1. **Soft gradient background** — never flat, always subtle tone shift
2. **Acrylic = high-opacity translucent + blur** — ~75% opacity in light mode
3. **Fluent blue accent** — `#0078d4` primary, with hover/pressed darkening
4. **Consistent rounded corners** — 4/8/12px system
5. **Hover = subtle lift + shadow deepen** — not dramatic, "system feel"
6. **Active = slight scale-down + shadow flatten** — simulate press
7. **Top highlight on cards** — key Fluent identity
