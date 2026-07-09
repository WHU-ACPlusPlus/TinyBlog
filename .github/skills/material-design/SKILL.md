---
name: material-design
description: 'Apply Material Design 3 (Google) style to QML UI. Use when: user asks for Material, Material Design, M3, Material You, elevation,卡片阴影,涟漪, or Google-style interface. Keywords: material, material design, M3, elevation, ripple, 涟漪, 卡片, 阴影层级, FAB, paper metaphor.'
---

# Material Design 3 — QML Design Tokens

Apply this for paper-metaphor, elevation-based, Google-style interfaces.

## Design Tokens

```qml
// ── Surface Colors ──
readonly property color surface:          "#ffffff"
readonly property color surfaceVariant:   "#f5f5f5"
readonly property color background:       "#fafafa"
readonly property color surfaceContainer: "#f0f0f0"

// ── Primary/Secondary/Error ──
readonly property color primary:          "#6750a4"    // M3 purple
readonly property color onPrimary:        "#ffffff"
readonly property color primaryContainer: "#e8def8"
readonly property color secondary:        "#625b71"
readonly property color error:            "#ba1a1a"

// ── Text (opacity-based hierarchy) ──
readonly property color textPrimary:      Qt.rgba(0, 0, 0, 0.87)
readonly property color textSecondary:    Qt.rgba(0, 0, 0, 0.60)
readonly property color textDisabled:     Qt.rgba(0, 0, 0, 0.38)

// ── Elevation Shadows ──
// L0 (flat):      no shadow
// L1 (raised):    color "#000", opacity 0.12, radius 2,  offset (0, 1)
// L2 (card):      color "#000", opacity 0.16, radius 6,  offset (0, 3)
// L3 (dialog):    color "#000", opacity 0.20, radius 10, offset (0, 6)
// L4 (FAB/nav):   color "#000", opacity 0.24, radius 16, offset (0, 10)

// ── Radii (small, controlled) ──
readonly property int radiusSm:    8
readonly property int radiusMd:    12
readonly property int radiusLg:    16
readonly property int radiusFAB:   16    // Rounded, not pill

// ── Borders ──
// Outline variant uses 1px border with surfaceVariant color
// Filled variant: no border

// ── Typography Scale ──
// Display: 36px, Headline: 28px, Title: 22px
// Body: 16px, Label: 14px, Caption: 12px
// Weight: regular (400) or medium (500), rarely bold

// ── FAB Size ──
readonly property int fabSize: 56

// ── Animation ──
readonly property int animDuration: 250   // Material standard
readonly property string animCurve: "easeOutCubic"  // M3 easing
// Ripple: expand from touch point, fade over 400ms
```

## QML Implementation Pattern

```qml
// Surface background
Rectangle {
    color: "#fafafa"

    // Card at elevation L2
    Rectangle {
        color: "#ffffff"
        radius: 12
        // Shadow layer (simulate with layered Rectangles)
        Rectangle {
            anchors.fill: parent; anchors.margins: -3; z: -1
            radius: parent.radius + 3
            color: Qt.rgba(0, 0, 0, 0.06)  // Blur radius ~6px equivalent
        }
        Rectangle {
            anchors.fill: parent; anchors.margins: -1; z: -2
            radius: parent.radius + 1
            color: Qt.rgba(0, 0, 0, 0.08)  // Blur radius ~2px equivalent
        }
    }

    // FAB (highest elevation L4)
    Rectangle {
        width: 56; height: 56
        color: "#6750a4"
        radius: 16
        // Deepest shadow
    }

    // Ripple effect on press
    MouseArea {
        anchors.fill: parent
        onPressed: {
            // Create ripple circle at mouse position
            // Animate: scale from 0 → max, opacity 0.3 → 0, 400ms
        }
    }

    // Text hierarchy
    Text { font.pixelSize: 22; font.weight: Font.Medium; color: Qt.rgba(0,0,0,0.87) } // Title
    Text { font.pixelSize: 16; color: Qt.rgba(0,0,0,0.87) }                          // Body
    Text { font.pixelSize: 14; color: Qt.rgba(0,0,0,0.60) }                          // Secondary
}
```

## Key Principles

1. **Paper metaphor** — each surface has an elevation number (0-4+)
2. **Shadow = elevation** — higher = larger, more diffuse shadow
3. **Text opacity, not colors** — 87/60/38% black for hierarchy
4. **M3 color roles** — primary, onPrimary, primaryContainer, error
5. **Ripple from touch point** — the defining Material interaction
6. **Hover = elevation++** — card lifts slightly (shadow deepens)
7. **FAB at highest elevation** — always floats above all content
