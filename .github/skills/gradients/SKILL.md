---
name: gradients
description: 'Apply Gradients (渐变) design techniques to QML UI. Use when: user asks for gradients,渐变, mesh gradient, conic gradient, multi-stop, atmospheric blend, or gradient backgrounds. Keywords: 渐变, gradient, mesh, conic, multi-stop, 渐变色, atmospheric, blend, 过渡色.'
---

# Gradients (渐变) — QML Design Tokens

Apply this for sophisticated gradient backgrounds and elements. **Often combined with other styles.**

## Design Tokens

```qml
// ── Gradient Types ──
// 1. Linear: 45° or 135° angle, 3-4 color stops
// 2. Radial: centered light/dark halo
// 3. Conic (Qt 6.7+): angle-based color wheel
// NOTE: QML Gradient only supports linear. For radial/conic use
// ShaderEffect or layered RadialGradient rectangles.

// ── Sample Palettes (3-4 colors each) ──

// Sunset:  "#ff7e5f" → "#feb47b" → "#ff6b6b"
// Ocean:   "#2193b0" → "#6dd5ed" → "#13547a"
// Forest:  "#11998e" → "#38ef7d" → "#0b5e2d"
// Berry:   "#8e2de2" → "#4a00e0" → "#fc6767"
// Aurora:  "#00d2ff" → "#7b2ff7" → "#ff2d95"

// ── Stop Positions ──
// Default: evenly spaced (0, 0.5, 1)
// Atmospheric: cluster stops (0, 0.3, 0.7, 1) for mood shifts

// ── Overlay Techniques ──
// Layer 1: Large gradient background (linear, subtle)
// Layer 2: Radial glow overlay at center-top
// Layer 3: Subtle noise/grain (optional, prevents banding)
// Cards: solid or faint gradient, contrasting with bg

// ── Text on Gradients ──
// Light gradient bg → dark text (#111)
// Dark gradient bg → white text
// Mid-tone → use semi-transparent backdrop behind text

// ── Noise (anti-banding) ──
// Overlay a semi-transparent noise image or
// Use ShaderEffect with noise function

// ── Animation ──
readonly property int animDuration: 250   // 200-300ms for gradient transitions
readonly property string animCurve: "easeInOutCubic"
```

## QML Implementation Pattern

```qml
// Linear gradient background
Rectangle {
    gradient: Gradient {
        GradientStop { position: 0.0; color: "#ff7e5f" }
        GradientStop { position: 0.5; color: "#feb47b" }
        GradientStop { position: 1.0; color: "#ff6b6b" }
    }

    // Optional: radial light overlay (simulate with centered Rectangle)
    Rectangle {
        anchors.centerIn: parent
        width: parent.width * 1.5; height: width
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.15) }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }

    // Solid card on gradient background
    Rectangle {
        color: "white"
        radius: 12
        // Or faint gradient card:
        // gradient: Gradient { ... subtle stops ... }
    }

    // Gradient border button
    Rectangle {
        color: "transparent"
        radius: 8
        // Use a slightly larger gradient-filled Rectangle behind
        Rectangle {
            anchors.fill: parent
            anchors.margins: -2
            radius: parent.radius + 2
            z: -1
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#8e2de2" }
                GradientStop { position: 1.0; color: "#fc6767" }
            }
        }
    }
}

// Animate gradient (shift stop positions or colors)
PropertyAnimation {
    target: gradientBackground
    property: "rotation"  // Rotate gradient angle
    from: 0; to: 360; duration: 20000
    loops: Animation.Infinite
}
```

## Key Principles

1. **3-4 colors, not rainbow** — constrained palette prevents chaos
2. **Background = gradient, cards = solid/faint gradient** — contrast creates depth
3. **Avoid banding with noise** — add subtle grain overlay on large gradients
4. **135° is the golden angle** — top-left to bottom-right for natural light feel
5. **Radial overlays add atmosphere** — center glow on large backgrounds
6. **Gradient borders on buttons** — filled gradient behind transparent solid
7. **Animate gradient rotation slowly** — subtle movement keeps it alive
