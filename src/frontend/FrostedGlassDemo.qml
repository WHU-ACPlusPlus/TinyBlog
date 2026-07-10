import QtQuick
import QtQuick.Controls.Basic

// ═══════════════════════════════════════════════════════════
// FrostedGlassDemo — 毛玻璃效果完整演示
//
// 运行方式：
//   将本文件设为 ApplicationWindow 的 source，
//   确保 qrc:/background.jpg 存在，或替换为本地路径。
//
// 演示内容：
//   1. 全屏背景图片
//   2. 中央毛玻璃面板（300×200，圆角 20）
//   3. 模糊 + 半透明白色叠加
//   4. 圆角裁剪、边框高光、阴影
// ═══════════════════════════════════════════════════════════

ApplicationWindow {
    id: window
    width: 900
    height: 600
    visible: true
    title: qsTr("毛玻璃效果演示 — Frosted Glass Demo")

    // ── 第 1 层：背景图片 ──
    // 使用 qrc:/background.jpg 占位，后续替换为实际路径
    // 例如: "file:///C:/Users/xxx/Pictures/bg.jpg"
    //       "https://example.com/background.jpg"（需网络权限）
    Image {
        id: backgroundImage
        anchors.fill: parent
        source: "qrc:/background.jpg"
        fillMode: Image.PreserveAspectCrop  // 保持比例裁剪填充
        // 如果 qrc 资源不存在，用纯色渐变回退
        asynchronous: true  // 异步加载大图，不阻塞 UI

        // 回退方案：纯色渐变背景（当图片不可用时）
        Rectangle {
            anchors.fill: parent
            visible: backgroundImage.status !== Image.Ready
            gradient: Gradient {
                // 玻璃态需要的深色渐变背景
                GradientStop { position: 0.0; color: "#0f0c29" }
                GradientStop { position: 0.5; color: "#302b63" }
                GradientStop { position: 1.0; color: "#24243e" }
            }
        }

        // 图片加载状态提示
        Text {
            anchors.centerIn: parent
            visible: backgroundImage.status === Image.Error
            textFormat: Text.RichText
            text: "<img src=\'qrc:/emoji/26a0.png\' width=12 height=12 /> 背景图片加载失败<br/>请将图片放入 qrc 或替换路径<br/>当前使用渐变回退"
            color: Qt.rgba(1, 1, 1, 0.6)
            font.pixelSize: 14
            horizontalAlignment: Text.AlignHCenter
        }
    }

    // ── 第 2 层：毛玻璃面板 ──
    // 使用 GlassCard 组件，将 backgroundImage 作为背景源
    GlassCard {
        id: glassPanel
        width: 300
        height: 200
        anchors.centerIn: parent
        blurRadius: 32          // 模糊半径
        glassColor: "#66FFFFFF" // 40% 白色叠加
        cardRadius: 20
        backgroundSource: backgroundImage
        showBorder: true
        showShadow: true

        // ── 面板内容 ──
        Text {
            anchors.centerIn: parent
            text: "毛玻璃效果"
            color: "#ffffff"        // 玻璃态令牌：textPrimary
            font.pixelSize: 24
            font.bold: true
        }
    }

    // ── 调试控件：实时调节模糊半径 ──
    // 帮助你找到最佳模糊值
    Rectangle {
        anchors {
            bottom: parent.bottom
            horizontalCenter: parent.horizontalCenter
            margins: 20
        }
        width: 280
        height: 50
        radius: 12
        color: Qt.rgba(0, 0, 0, 0.5)

        Row {
            anchors.centerIn: parent
            spacing: 12

            Text {
                text: "模糊: " + glassPanel.blurRadius
                color: "white"
                font.pixelSize: 14
                anchors.verticalCenter: parent.verticalCenter
            }

            Slider {
                id: blurSlider
                width: 160
                from: 0
                to: 64
                value: 32
                stepSize: 2
                anchors.verticalCenter: parent.verticalCenter
                // 绑定滑块值到面板的模糊半径
                onValueChanged: glassPanel.blurRadius = value
            }
        }
    }
}
