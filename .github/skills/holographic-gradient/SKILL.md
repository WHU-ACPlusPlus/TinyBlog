---
name: holographic-gradient
description: 'Apply 全息渐变 (Holographic Gradient) design style to QML UI. Use when: user asks for iridescent gradient, rainbow sheen, holographic film,彩膜,虹彩, or prismatic gradient effect. Keywords: 全息渐变, 虹彩, iridescent, prismatic, rainbow sheen, 彩膜, holographic gradient, 折射.'
---

# 全息渐变 (Holographic Gradient) — QML Design Tokens

Apply this for iridescent, rainbow-sheen gradient effects.

## Design Tokens

```qml
// ── Background ──
// Soft-focus iridescent gradient, large blurred color fields
// Or dark base with floating color washes

// ── Holographic Color Palette ──
// Pink → Purple → Cyan → Silver
readonly property color holoPink:   "#ff6b9d"
readonly property color holoPurple: "#c44dff"
readonly property color holoCyan:   "#4df0ff"
readonly property color holoSilver: "#e8e8f0"

// ── Card ──
readonly property color cardBg:         Qt.rgba(1, 1, 1, 0.08)  // Super transparent
readonly property color cardBgHover:    Qt.rgba(1, 1, 1, 0.14)
readonly property color rainbowBorder:  "transparent"            // Use gradient border

// ── Text ──
readonly property color textPrimary:    "#ffffff"
readonly property color textSecondary:  Qt.rgba(1, 1, 1, 0.60)
readonly property color textAccent:     "#c44dff"    // Purple accent

// ── Rainbow Border Gradient ──
// LinearGradient: pink → purple → cyan → silver across border width
// Or conical gradient for corner accents

// ── Shadows ──
// Very light, avoid heavy: color "#000", opacity 0.10, radius 12, offset (0, 4)
// Add colored glow near edges in accent hue
readonly property color glowPink:   Qt.rgba(1, 0.42, 0.62, 0.3)
readonly property color glowCyan:   Qt.rgba(0.30, 0.94, 1, 0.3)

// ── Radii ──
readonly property int radiusCard:   16
readonly property int radiusButton: 12
readonly property int radiusInput:  10

// ── Noise/Particle ──
// Overlay fine glitter particles — simulate with small semi-transparent circles
// Or ShaderEffect with noise function

// ── Borders ──
readonly property int borderWidth: 1.5   // Rainbow gradient border
// Use Rectangle with gradient fill as border, or border + gradient

// ── Animation ──
readonly property int animDuration: 200  // 150-220ms
readonly property string animCurve: "easeOutCubic"
```

## QML Implementation Pattern

```qml
// Dark background with iridescent washes
Rectangle {
    color: "#0d0d1a"

    // Large soft iridescent wash (using layered radial gradients)
    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 1.2; height: parent.height * 0.8
        rotation: -15
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.78, 0.30, 1, 0.15) }
            GradientStop { position: 0.5; color: Qt.rgba(0.30, 0.94, 1, 0.12) }
            GradientStop { position: 1.0; color: Qt.rgba(1, 0.42, 0.62, 0.10) }
        }
    }

    // Translucent card with rainbow border
    Rectangle {
        color: Qt.rgba(1, 1, 1, 0.08)
        radius: 16

        // Rainbow border (use a slightly larger Rectangle behind)
        Rectangle {
            anchors.fill: parent
            anchors.margins: -1.5
            radius: parent.radius + 1
            z: -1
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#ff6b9d" }
                GradientStop { position: 0.33; color: "#c44dff" }
                GradientStop { position: 0.66; color: "#4df0ff" }
                GradientStop { position: 1.0; color: "#e8e8f0" }
            }
        }
    }

    // Hover: light band shifts position
    // Active: slight sink, highlight converges
}
```

## Key Principles

1. **Multi-stop gradient** — pink/purple/cyan/silver, 4+ stops
2. **Background = soft-focus iridescence** — large blurred color washes
3. **Cards = highly transparent white** — ~8% opacity, lets background colors through
4. **Rainbow border** — gradient border wraps cards/buttons
5. **Glitter particles** — add fine sparkle/dust effect for full immersion
6. **Hover = light band displacement** — not just brightness, but position shift
7. **Keep text high-contrast white** — iridescence is the backdrop, not the content
