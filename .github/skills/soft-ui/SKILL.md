---
name: soft-ui
description: 'Apply Soft UI (Neumorphism/新拟物) design style to QML UI. Use when: user asks for soft UI, neumorphism,新拟物, neumorphic, soft shadows, inset/outset, embossed, debossed, or tactile pill buttons. Keywords: soft ui, neumorphism, 新拟物, 柔和, 浮雕, neumorphic, inset shadow, outset shadow, soft shadow.'
---

# Soft UI (Neumorphism) — QML Design Tokens

Apply this for soft, embossed/debossed tactile interfaces.

## Design Tokens

```qml
// ── Background ──
readonly property color bgColor:         "#e8edf2"   // Pastel, low-saturation
// Alternative: "#f0eef6" (lavender), "#e8efe8" (sage)

// ── Component Colors (same as bg) ──
readonly property color componentBg:     bgColor      // Must match background!

// ── Shadows (the core of Soft UI) ──
// Dark shadow:  color "#a3b1c6", offset (6, 6),  radius 12, opacity 0.4
// Light shadow: color "#ffffff", offset (-6, -6), radius 12, opacity 0.8
// Inset (pressed): dark inner shadow + light inner shadow reversed

// ── Elevation Levels ──
// Level 1 (subtle raise):
//   dark:  (3, 3)   radius 8  opacity 0.25
//   light: (-3, -3) radius 8  opacity 0.7
// Level 2 (card):
//   dark:  (6, 6)   radius 12 opacity 0.30
//   light: (-6, -6) radius 12 opacity 0.8
// Level 3 (floating):
//   dark:  (10, 10) radius 20 opacity 0.25
//   light: (-10,-10) radius 20 opacity 0.9

// ── Text ──
readonly property color textPrimary:     "#2d3436"
readonly property color textSecondary:   "#636e72"
readonly property color accent:          "#6c5ce7"    // Soft purple accent

// ── Radii (large, pill-like) ──
readonly property int radiusSm:    12
readonly property int radiusMd:    16
readonly property int radiusLg:    24
readonly property int radiusPill:  999     // Full pill

// ── Borders ──
// No visible borders — shadows define edges
// Optional: 1px micro-highlight at top edge

// ── Animation ──
readonly property int animDuration: 180  // 150-220ms
readonly property string animCurve: "easeInOutCubic"
```

## QML Implementation Pattern

```qml
// Background — same as component color
Rectangle {
    color: "#e8edf2"

    // Soft UI Card (outset/raised)
    Rectangle {
        color: "#e8edf2"  // SAME as background!
        radius: 16

        // Simulate double shadow with layered Rectangles
        // In Qt/QML, use two shadow Rectangles behind:
        Rectangle {
            anchors.fill: parent; anchors.margins: -8; z: -2
            radius: parent.radius + 8
            color: Qt.rgba(0.64, 0.69, 0.77, 0.3) // dark shadow
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: -6; z: -1
            radius: parent.radius + 6
            color: Qt.rgba(1, 1, 1, 0.8) // light shadow
        }
    }

    // Soft UI Button — pressed state = inset
    Rectangle {
        id: softBtn
        color: "#e8edf2"
        radius: 16

        // Toggle: outset → inset on press
        state: "raised"
        states: [
            State {
                name: "raised"
                PropertyChanges { target: darkShadow; visible: true }
                PropertyChanges { target: lightShadow; visible: true }
            },
            State {
                name: "pressed"
                // Reverse shadows: dark inside, light outside
                PropertyChanges { target: darkShadow; visible: true; /* flip */ }
            }
        ]

        MouseArea {
            anchors.fill: parent
            onPressed: softBtn.state = "pressed"
            onReleased: softBtn.state = "raised"
        }
    }
}
```

## Key Principles

1. **Background = component color** — the defining Soft UI rule
2. **Double shadows always** — dark + light on opposite sides
3. **No visible borders** — shadows ARE the edges
4. **Large radii** — 12px minimum, pill shapes common
5. **Hover = shadows deepen, element rises** — amplify contrast
6. **Active/Pressed = shadows reverse** — dark shadow moves inside, element sinks
7. **Pastel/low-saturation palette** — avoid vivid colors that clash with soft shadows
