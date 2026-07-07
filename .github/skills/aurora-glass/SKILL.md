---
name: aurora-glass
description: 'Apply 极光玻璃 (Aurora Glass) design style to QML UI. Use when: user asks for aurora, northern lights,极光, flowing colors, neon glass, or futuristic translucent design with colored gradients behind glass. Keywords: 极光, 极光玻璃, aurora, northern lights, neon glass, 流动色带.'
---

# 极光玻璃 (Aurora Glass) — QML Design Tokens

Apply this for glass cards floating over slowly flowing aurora gradient bands.

## Design Tokens

```qml
// ── Aurora Background ──
// 3-5 color horizontal/diagonal bands, opacity 0.2-0.6
// Colors: teal, purple, cyan, magenta
// Example palette: "#00d2ff", "#7b2ff7", "#ff2d95", "#00d2ff"

// ── Glass Card ──
readonly property color glassBg:        Qt.rgba(1, 1, 1, 0.12)
readonly property color glassBgHover:   Qt.rgba(1, 1, 1, 0.18)
readonly property color glassBorder:    Qt.rgba(1, 1, 1, 0.22)   // Brighter than plain glass
readonly property color glassHighlight: Qt.rgba(1, 1, 1, 0.28)

// ── Text ──
readonly property color textPrimary:    "#ffffff"
readonly property color textSecondary:  Qt.rgba(1, 1, 1, 0.65)
readonly property color textAccent:     "#00d2ff"    // Neon cyan accent

// ── Shadows ──
// Card: color "#000", opacity 0.18, radius 24, offset (0, 10)
// Add subtle glow near edges in accent hue

// ── Radii ──
readonly property int radiusCard:   16
readonly property int radiusButton: 12
readonly property int radiusInput:  10

// ── Aurora Animation ──
// Background flow: 10-16 second loop, horizontal shift
// Use SequentialAnimation on x offset of gradient rectangle
// Or ShaderEffect with time uniform for smooth drift

// ── Borders ──
readonly property int borderWidth: 1.5  // Slightly thicker glow
// border.color: gradient from cyan → purple

// ── Animation ──
readonly property int animDuration: 220  // Smooth, slightly slower
readonly property string animCurve: "easeInOutCubic"
readonly property int auroraPeriod: 12000 // 12s background cycle
```

## QML Implementation Pattern

```qml
// Aurora background — flowing bands
Rectangle {
    clip: true

    // Aurora gradient band (animate x position)
    Rectangle {
        width: parent.width * 2; height: parent.height
        x: auroraOffset  // Animate -width → 0 loop

        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0, 0.82, 1, 0.3) }     // cyan
            GradientStop { position: 0.3; color: Qt.rgba(0.48, 0.18, 0.97, 0.4) } // purple
            GradientStop { position: 0.6; color: Qt.rgba(1, 0.18, 0.58, 0.3) }   // pink
            GradientStop { position: 1.0; color: Qt.rgba(0, 0.82, 1, 0.15) }
        }
    }

    // Glass card on top
    Rectangle {
        color: Qt.rgba(1, 1, 1, 0.12)
        radius: 16
        border { width: 1.5; color: Qt.rgba(1, 1, 1, 0.22) }
    }
}

// Aurora animation:
NumberAnimation on auroraOffset {
    from: -bgWidth; to: 0; duration: 12000
    loops: Animation.Infinite; easing.type: Easing.InOutCubic
}
```

## Key Principles

1. **3-5 aurora colors** — teal/cyan, purple, magenta/pink are canonical
2. **Opacity 0.2–0.6** for bands — never opaque, always translucent
3. **Background flows 10-16s** — slow, infinite loop
4. **Glass cards brighter than plain glassmorphism** — neon glow border
5. **Add light noise** to prevent color banding on gradients
6. **Hover = border brightness up** — accent the glow
7. **Active = scale 0.98** — subtle press, shadow converges
