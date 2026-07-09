---
name: glassmorphism
description: 'Apply 玻璃态 (Glassmorphism) design style to QML UI. Use when: user asks for glass, frosted glass,毛玻璃, translucent cards, blur background, glassmorphism, or transparent layered design. Keywords: 玻璃, 毛玻璃, 磨砂, glass, frosted, blur, translucent, 通透.'
---

# 玻璃态 (Glassmorphism) — QML Design Tokens

Apply this style for frosted glass cards floating over gradient backgrounds.

## Design Tokens

```qml
// ── Background ──
// Deep gradient background: dark or colorful, NOT white
// Example: LinearGradient from "#0f0c29" → "#302b63" → "#24243e"

// ── Glass Card ──
readonly property color glassBg:         Qt.rgba(1, 1, 1, 0.10)   // 10% white
readonly property color glassBgHover:    Qt.rgba(1, 1, 1, 0.15)   // 15% on hover
readonly property color glassBorder:     Qt.rgba(1, 1, 1, 0.18)   // Soft glow border
readonly property color glassHighlight:  Qt.rgba(1, 1, 1, 0.25)   // Top-edge highlight

// ── Text ──
readonly property color textPrimary:     "#ffffff"     // High contrast on dark bg
readonly property color textSecondary:   Qt.rgba(1, 1, 1, 0.65)
readonly property color textTertiary:    Qt.rgba(1, 1, 1, 0.40)

// ── Shadows ──
// Card shadow: color "#000000", opacity: 0.15, radius: 20, offset: (0, 8)
// Inner glow: subtle radial gradient from center-top

// ── Radii ──
readonly property int radiusCard:  16    // Generous rounding
readonly property int radiusButton: 10
readonly property int radiusInput:  8

// ── Blur ──
// In QML: use ShaderEffectSource for backdrop blur, or layer.enabled + blur
// Or simulate with semi-transparent bg + layer effect

// ── Borders ──
readonly property int borderWidth: 1     // 1-2px highlight border
// border.color: glassBorder

// ── Animation ──
readonly property int animDuration: 200  // 150-250ms range
readonly property string animCurve: "easeOutCubic"
```

## QML Implementation Pattern

```qml
// Background — deep gradient
Rectangle {
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#0f0c29" }
        GradientStop { position: 0.5; color: "#302b63" }
        GradientStop { position: 1.0; color: "#24243e" }
    }

    // Glass card
    Rectangle {
        color: Qt.rgba(1, 1, 1, 0.10)
        radius: 16
        border { width: 1; color: Qt.rgba(1, 1, 1, 0.18) }
        // Top highlight line
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 1
            color: Qt.rgba(1, 1, 1, 0.20)
        }

        // Hover: rise + deepen
        Behavior on scale { NumberAnimation { duration: 200 } }
        MouseArea {
            hoverEnabled: true
            onEntered: parent.color = Qt.rgba(1, 1, 1, 0.15)
            onExited:  parent.color = Qt.rgba(1, 1, 1, 0.10)
        }
    }
}
```

## Key Principles

1. **Dark/colorful background only** — glass needs rich backdrop to show translucency
2. **Transparency gradient** — 0.05–0.20 opacity; lower layers more transparent
3. **1px glow border** — lighter than card fill, simulates edge refraction
4. **Hover = opacity + shadow deepen** — card rises slightly
5. **Active = scale 0.98** — subtle press, never bounce
6. **No heavy textures** — keep it clean and lightweight
