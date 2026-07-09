---
name: holographic-foil
description: 'Apply 全息箔效果 (Holographic Foil) design style to QML UI. Use when: user asks for holographic, foil, metallic, iridescent, shimmer, luxury card, collectible, or premium shiny effect. Keywords: 全息, 箔, 金属, 闪耀, holographic, foil, metallic, iridescent, shimmer, luxury, 彩箔.'
---

# 全息箔效果 (Holographic Foil) — QML Design Tokens

Apply this for metallic foil, embossed luxury card aesthetics.

## Design Tokens

```qml
// ── Background ──
// Deep dark: "#0a0a0f" or "#12121a"
// Gradient foil area: multi-stop metallic gradient

// ── Foil Gradient ──
// Metallic multi-stop: gold/silver/bronze tones
// Example: "#8a7a5a" → "#d4c8a0" → "#8a7a5a" → "#d4c8a0"
// Or: "#c9a96e" → "#f5e6c8" → "#b8944e" → "#e8d5a0"

// ── Card ──
readonly property color cardBase:        "#1a1a24"     // Dark card base
readonly property color foilPrimary:     "#d4af37"     // Gold foil
readonly property color foilSecondary:   "#c0c0c0"     // Silver accent
readonly property color embossHighlight: Qt.rgba(1, 1, 1, 0.15)

// ── Text ──
readonly property color textPrimary:     "#f0ead6"     // Warm white (parchment)
readonly property color textSecondary:   Qt.rgba(0.94, 0.91, 0.82, 0.65)
readonly property color textFoil:        "#d4af37"     // Gold text for key info

// ── Emboss Lines ──
// Use thin Rectangle lines with mixed opacity for embossed effect:
// Top line: rgba(255,255,255,0.12), Bottom line: rgba(0,0,0,0.3)

// ── Shadows ──
// Card: color "#000", opacity 0.4, radius 16, offset (0, 4)
// Emboss: no shadow, use line-based depth

// ── Radii ──
readonly property int radiusCard:   12
readonly property int radiusBadge:  4     // Sharp for foil badge

// ── Metal Noise ──
// Simulate with overlaid semi-transparent noise pattern
// Or rough gradient with multiple narrow stops

// ── Borders ──
readonly property int borderWidth: 1.5
// border.color: metallic gradient, e.g., "#d4af37" → "#8a7a5a"

// ── Animation ──
readonly property int animDuration: 180  // 150-220ms, crisp
readonly property string animCurve: "easeOutCubic"
```

## QML Implementation Pattern

```qml
// Dark luxurious background
Rectangle {
    color: "#0a0a0f"

    // Foil card
    Rectangle {
        color: "#1a1a24"
        radius: 12
        border {
            width: 1.5
            // Metallic border via gradient
            color: "#d4af37"
        }

        // Embossed decorative line
        Rectangle {
            anchors { left: parent.left; right: parent.right; top: parent.top }
            height: 2
            color: "transparent"
            // Top highlight + bottom shadow = emboss
            Rectangle {
                anchors { left: parent.left; right: parent.right; top: parent.top }
                height: 1; color: Qt.rgba(1, 1, 1, 0.12)
            }
            Rectangle {
                anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                height: 1; color: Qt.rgba(0, 0, 0, 0.3)
            }
        }

        // Foil shimmer area
        Rectangle {
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#8a7a5a" }
                GradientStop { position: 0.3; color: "#d4c8a0" }
                GradientStop { position: 0.6; color: "#8a7a5a" }
                GradientStop { position: 1.0; color: "#c9a96e" }
            }
        }
    }

    // Hover: highlight sweeps across (simulate with gradient shift)
    Behavior on opacity { NumberAnimation { duration: 180 } }
}
```

## Key Principles

1. **Dark background** — foil needs darkness to shine
2. **Metallic gradient stops** — gold/silver/bronze, 3-5 stops with sharp transitions
3. **Embossed lines** — light + dark 1px lines create pressed/raised relief
4. **Metal noise/grain** — avoid flat smooth gradients; add texture
5. **Hover = light sweep** — gradient or brightness shifts, like light moving across foil
6. **Active = slight sink** — card presses down, light band converges
7. **Keep text areas clear** — foil should accent, not overwhelm content
