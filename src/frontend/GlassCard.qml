import QtQuick
import QtQuick.Effects

// ═══════════════════════════════════════════════════════════
// GlassCard — 可复用的毛玻璃（Frosted Glass）卡片组件
//
// 设计风格：玻璃态
//   卡片背景: rgba(255,255,255,0.10) + 模糊
//   边框:     1px rgba(255,255,255,0.18)
//   高光:     rgba(255,255,255,0.25) 顶部 1px
//   阴影:     偏移 4x8 rgba(0,0,0,0.12)
//   圆角:     16-20px
//
// 技术方案（Qt 6 原生）：
//   ShaderEffectSource + MultiEffect（模糊 + 着色一体化）
// ═══════════════════════════════════════════════════════════

Item {
    id: root

    // ── 公开属性 ──
    property int blurRadius: 32
    property color glassColor: "#66FFFFFF"
    property int cardRadius: 20
    property Item backgroundSource: null
    property bool showBorder: true
    property bool showShadow: true

    implicitWidth: 300
    implicitHeight: 200

    // ── 阴影层 ──
    Rectangle {
        id: shadowLayer
        x: 4; y: 8
        width: parent.width; height: parent.height
        radius: root.cardRadius
        color: Qt.rgba(0, 0, 0, 0.12)
        visible: root.showShadow
    }

    // ── 裁剪容器 ──
    Rectangle {
        id: clipRect
        anchors.fill: parent
        radius: root.cardRadius
        clip: true

        // 毛玻璃表面：捕获背景 + 模糊
        ShaderEffectSource {
            id: glassSurface
            anchors.fill: parent
            sourceItem: root.backgroundSource
            sourceRect: {
                if (root.backgroundSource) {
                    var pos = root.mapToItem(root.backgroundSource, 0, 0)
                    return Qt.rect(pos.x, pos.y, root.width, root.height)
                }
                return Qt.rect(0, 0, root.width, root.height)
            }
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blurMax: 64
                blur: Math.min(root.blurRadius / 64.0, 1.0)
            }
        }

        // 玻璃着色层
        Rectangle {
            anchors.fill: parent
            color: root.glassColor
        }

        // 边框高光
        Rectangle {
            anchors.fill: parent
            radius: root.cardRadius
            color: "transparent"
            visible: root.showBorder
            border {
                width: 1
                color: Qt.rgba(1, 1, 1, 0.18)
            }
        }

        // 顶部高光线
        Rectangle {
            anchors { top: parent.top; left: parent.left; right: parent.right; margins: 1 }
            height: 1
            radius: root.cardRadius
            visible: root.showBorder
            color: Qt.rgba(1, 1, 1, 0.25)
        }
    }

    // ── 内容区域 ──
    default property alias content: contentItem.data
    Item {
        id: contentItem
        anchors.fill: parent
        anchors.margins: 12
    }
}
