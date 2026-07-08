import QtQuick
import QtQuick.Effects

// ═══════════════════════════════════════════════════════════
// GlassCard — 可复用的毛玻璃（Frosted Glass）卡片组件
//
// 设计风格：玻璃态（style/玻璃态.md）
// 设计令牌：
//   卡片背景: rgba(255,255,255,0.10) + 模糊
//   边框:     1px rgba(255,255,255,0.18)
//   高光:     rgba(255,255,255,0.25) 顶部 1px
//   阴影:     偏移 4x8 rgba(0,0,0,0.12)
//   圆角:     16-20px
//
// 技术方案（Qt 6 原生，无需 Qt5Compat）：
//   ShaderEffectSource + MultiEffect（模糊 + 着色一体化）
//   MultiEffect 内置 blur + colorization，单次 GPU pass
//   比 FastBlur + ColorOverlay 链式调用更高效
//
// 使用示例：
//   GlassCard {
//       width: 300; height: 200
//       backgroundSource: window.contentItem
//       Text { anchors.centerIn: parent; text: "Hello" }
//   }
// ═══════════════════════════════════════════════════════════

Item {
    id: root

    // ── 公开属性 ──

    // 模糊半径（0–64，映射到 MultiEffect.blur 0.0–1.0）
    // 默认 32，越大越模糊，也越消耗 GPU 填充率
    property int blurRadius: 32

    // 玻璃叠加颜色（默认半透明白色 40% 不透明度）
    // 玻璃态令牌: Qt.rgba(1, 1, 1, 0.10) — 更通透
    // 用户指定:    "#66FFFFFF" — 约 40% 不透明度
    property color glassColor: "#66FFFFFF"

    // 圆角半径
    property int cardRadius: 20

    // 背景源 Item — 需要模糊的背景（通常是 Image 或 window.contentItem）
    // 必须由使用者设置，否则玻璃面板显示为纯色
    property Item backgroundSource: null

    // 是否显示边框高光
    property bool showBorder: true

    // 是否显示阴影
    property bool showShadow: true

    implicitWidth: 300
    implicitHeight: 200

    // ═══════════════════════════════════════════
    // 核心实现：毛玻璃效果
    // ═══════════════════════════════════════════

    // ── 阴影层（最底层，不被 clip 裁剪）──
    // 使用偏移矩形模拟卡片悬浮阴影，无需 DropShadow 依赖
    Rectangle {
        id: shadowLayer
        // 偏移 4px 右, 8px 下，制造悬浮感
        x: 4
        y: 8
        width: parent.width
        height: parent.height
        radius: root.cardRadius
        color: Qt.rgba(0, 0, 0, 0.12)  // 玻璃态令牌：12% 黑色
        visible: root.showShadow
    }

    // ── 裁剪容器（圆角裁剪在此生效）──
    Rectangle {
        id: clipRect
        anchors.fill: parent
        radius: root.cardRadius
        clip: true   // 关键：防止模糊溢出圆角区域

        // ── 毛玻璃表面：捕获背景 + 模糊 + 着色 ──
        // ShaderEffectSource 捕获背景指定区域
        // MultiEffect 在 GPU 上一次完成模糊+着色
        ShaderEffectSource {
            id: glassSurface
            anchors.fill: parent
            sourceItem: root.backgroundSource

            // sourceRect: 将卡片坐标映射到背景源坐标系
            // 只捕获卡片正下方的背景区域
            sourceRect: {
                if (root.backgroundSource) {
                    var pos = root.mapToItem(root.backgroundSource, 0, 0)
                    return Qt.rect(pos.x, pos.y, root.width, root.height)
                }
                return Qt.rect(0, 0, root.width, root.height)
            }

            // MultiEffect：仅做模糊（Qt 6.11 不支持 colorization 属性）
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blurMax: 64              // 最大模糊半径
                blur: Math.min(root.blurRadius / 64.0, 1.0)  // 0.0–1.0
            }
        }

        // ── 玻璃着色层 ──
        // 半透明矩形叠加在模糊结果之上，替代 ColorOverlay
        Rectangle {
            id: glassTint
            anchors.fill: parent
            color: root.glassColor
        }

        // ── 边框高光（模拟玻璃边缘折射）──
        Rectangle {
            anchors.fill: parent
            radius: root.cardRadius
            color: "transparent"
            visible: root.showBorder
            border {
                width: 1
                color: Qt.rgba(1, 1, 1, 0.18)  // 玻璃态令牌
            }
        }

        // ── 顶部高光线 ──
        // 模拟光线从上方打在玻璃边缘的折射
        Rectangle {
            anchors {
                top: parent.top
                left: parent.left
                right: parent.right
                margins: 1
            }
            height: 1
            radius: root.cardRadius
            visible: root.showBorder
            color: Qt.rgba(1, 1, 1, 0.25)  // 玻璃态令牌：高光
        }
    }

    // ── 内容区域 ──
    // 所有子组件默认填充卡片，放在毛玻璃最上层
    default property alias content: contentItem.data

    Item {
        id: contentItem
        anchors.fill: parent
        anchors.margins: 12   // 内容内边距
    }
}
