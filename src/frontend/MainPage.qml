import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root

    // ── 当前页面索引 ──
    property int currentIndex: 0

    // ── 风格模式：0=普通（支持深色模式）  1=毛玻璃  2=SoftUI ──
    property int styleMode: 0
    property bool glassMode: styleMode === 1
    property bool softUIMode: styleMode === 2

    // 普通模式下跟随系统主题，其他风格使用固定色板
    color: {
        if (softUIMode) return "#e8edf2"
        if (glassMode)  return "transparent"
        return window.bgSurface
    }

    // 向 window 同步当前风格模式，使 window.* 颜色不受深色模式影响
    onStyleModeChanged: {
        window.activeStyleMode = root.styleMode
    }
    Component.onCompleted: {
        window.activeStyleMode = root.styleMode
    }

    // ── 鼠标位置（用于毛玻璃跟随光源）──
    property real mouseX: width / 2
    property real mouseY: height / 2

    // ── 深色模式图标 ──
    function darkIcon() {
        if (window.darkModeFollowSystem === 1) return "🌙"
        if (window.darkModeFollowSystem === 2) return "☀️"
        return "◐"
    }
    function darkLabel() {
        if (window.darkModeFollowSystem === 1) return qsTr("深色")
        if (window.darkModeFollowSystem === 2) return qsTr("浅色")
        return qsTr("跟随")
    }

    // ═══════════════════════════════════════════
    // 风格图标/标签映射
    // ═══════════════════════════════════════════
    function styleIcon(mode) {
        switch (mode) { case 1: return "🔮"; case 2: return "🫧"; default: return "🏠" }
    }
    function styleLabel(mode) {
        switch (mode) { case 1: return qsTr("玻璃"); case 2: return qsTr("柔和"); default: return qsTr("普通") }
    }

    // ═══════════════════════════════════════════
    // 背景层（仅在毛玻璃模式下可见）
    // ═══════════════════════════════════════════
    Item {
        id: glassBackground
        anchors.fill: parent
        visible: root.glassMode
        z: -1

        Image {
            id: bgImage
            anchors.fill: parent
            source: api.wallpaperPath.length > 0 ? api.wallpaperPath : "qrc:/image/4.png"
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: false

            onStatusChanged: {
                if (status === Image.Error)
                    console.warn("[MainPage] 玻璃背景图加载失败，使用纯色回退")
            }
        }

        // 回退渐变（图片加载失败时显示）
        Rectangle {
            anchors.fill: parent
            visible: bgImage.status !== Image.Ready
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#0f0c29" }
                GradientStop { position: 0.5; color: "#302b63" }
                GradientStop { position: 1.0; color: "#24243e" }
            }
        }

        // 鼠标跟随光源
        Canvas {
            id: mouseLight
            width: 700; height: 700
            x: root.mouseX - width / 2
            y: root.mouseY - height / 2
            visible: root.glassMode

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                var gradient = ctx.createRadialGradient(
                    width / 2, height / 2, 0,
                    width / 2, height / 2, width / 2
                )
                gradient.addColorStop(0.0, "rgba(255, 235, 209, 0.12)")
                gradient.addColorStop(0.4, "rgba(255, 242, 224, 0.06)")
                gradient.addColorStop(0.7, "rgba(255, 245, 230, 0.02)")
                gradient.addColorStop(1.0, "transparent")
                ctx.fillStyle = gradient
                ctx.fillRect(0, 0, width, height)
            }

            Behavior on x { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
        }
    }

    // ═══════════════════════════════════════════
    // 壁纸背景层（所有模式下，当用户设置了壁纸时显示）
    // ═══════════════════════════════════════════
    Item {
        id: wallpaperBackground
        anchors.fill: parent
        visible: api.wallpaperPath.length > 0
        z: -2

        Image {
            id: wallpaperImage
            anchors.fill: parent
            source: api.wallpaperPath
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            cache: false

            onStatusChanged: {
                if (status === Image.Error)
                    console.warn("[MainPage] 壁纸加载失败: " + api.wallpaperPath)
            }
        }

        // 暗色叠加层（保护文字可读性）
        Rectangle {
            anchors.fill: parent
            color: {
                if (root.glassMode) return Qt.rgba(0.05, 0.05, 0.15, 0.35)
                if (root.softUIMode) return Qt.rgba(0.91, 0.93, 0.95, 0.55)
                if (window.darkMode) return Qt.rgba(0, 0, 0, 0.55)
                return Qt.rgba(1, 1, 1, 0.45)
            }
        }
    }

    // ── 鼠标追踪层（不拦截事件）──
    MouseArea {
        id: mouseTracker
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onPositionChanged: function(mouse) {
            root.mouseX = mouse.x
            root.mouseY = mouse.y
        }
    }

    // ═══════════════════════════════════════════
    // 宽屏：内容区（全屏）+ 侧边栏浮动层
    // ═══════════════════════════════════════════
    Item {
        anchors.fill: parent
        visible: width >= 700

        // ── 内容区（z:1，全屏）──
        Item {
            anchors.fill: parent
            z: 1

            // 毛玻璃层（仅在玻璃模式下可见）
            GlassCard {
                anchors.fill: parent
                anchors.margins: root.glassMode ? 8 : 0
                backgroundSource: root.glassMode ? glassBackground : null
                blurRadius: 28
                cardRadius: root.glassMode ? 16 : 0
                glassColor: Qt.rgba(1, 1, 1, 0.06)
                showBorder: root.glassMode
                showShadow: root.glassMode || root.softUIMode
                visible: root.glassMode
            }

            StackLayout {
                id: wideContentStack
                anchors.fill: parent
                anchors.margins: root.glassMode ? 8 : 0
                currentIndex: root.currentIndex

                // 广场页：左边距60px避开侧边栏
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    SquarePage {
                        anchors.fill: parent
                        anchors.leftMargin: 74
                        glassMode: root.glassMode
                        softUIMode: root.softUIMode
                    }
                }

                // 消息页：无左边距，延伸到侧边栏下方（供会话列表面板滑入用）
                MessagesPage {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    glassMode: root.glassMode
                    softUIMode: root.softUIMode
                }

                // 我的页：左边距60px避开侧边栏
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    ProfilePage {
                        anchors.fill: parent
                        anchors.leftMargin: 74
                        glassMode: root.glassMode
                        softUIMode: root.softUIMode
                    }
                }
            }
        }

        // ── 侧边栏浮动层（z:2，遮挡下方内容）──
        Rectangle {
            id: sidebarRect
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 70
            z: 2
            color: {
                if (softUIMode) return Qt.rgba(0.84, 0.89, 0.93, 0.92)
                if (glassMode) return "transparent"
                if (window.darkMode) return "#1a1a1a"
                if (api.wallpaperPath.length > 0) return Qt.rgba(0.96, 0.96, 0.96, 0.80)
                return "#f5f5f5"
            }

            // ═══════════════════════════════════════
            // 导航图标组 — 磨砂玻璃底框
            // ═══════════════════════════════════════
            Rectangle {
                id: navGlassCard
                width: 48
                height: 156    // 3×44 + 2×8 + 12 padding
                x: 16
                y: 14
                radius: 16
                z: -1
                color: window.darkMode
                    ? Qt.rgba(1, 1, 1, 0.06)
                    : Qt.rgba(0, 0, 0, 0.04)
                border.color: window.darkMode
                    ? Qt.rgba(1, 1, 1, 0.10)
                    : Qt.rgba(0, 0, 0, 0.06)
                border.width: 0.5
            }

            // ═══════════════════════════════════════
            // 液态玻璃滑动指示器
            // ═══════════════════════════════════════
            Rectangle {
                id: navIndicator
                width: 44
                height: 44
                radius: 14
                x: 18            // 18 + (48-44)/2  居中于玻璃底框
                y: 21 + currentIndex * 52   // topMargin + index × (44+8)
                z: 0

                color: {
                    if (glassMode) return Qt.rgba(1, 1, 1, 0.18)
                    if (softUIMode) return Qt.rgba(0.48, 0.53, 0.66, 0.28)
                    return window.selectedBg
                }

                // ── 弹簧滑动动画（2x加速）──
                Behavior on y {
                    SpringAnimation {
                        spring: 5.5
                        damping: 0.80
                        epsilon: 0.25
                    }
                }
            }

            ColumnLayout {
                anchors.left: parent.left
                anchors.leftMargin: 16
                anchors.top: parent.top
                anchors.topMargin: 21
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 10
                width: 48
                spacing: 8

                // ═══════════════════════════════════════
                // 导航图标
                // ═══════════════════════════════════════
                Repeater {
                    model: [
                        { icon: "▪", tip: qsTr("广场") },
                        { icon: "≡", tip: qsTr("消息") },
                        { icon: "●", tip: qsTr("我的") }
                    ]

                    Rectangle {
                        id: navItem
                        Layout.preferredWidth: 44
                        Layout.preferredHeight: 44
                        Layout.alignment: Qt.AlignHCenter
                        color: "transparent"
                        radius: 14
                        z: 1

                        Text {
                            id: navIcon
                            anchors.centerIn: parent
                            text: modelData.icon
                            font.pixelSize: 20
                            color: currentIndex === index
                                    ? (glassMode ? "#ffffff"
                                       : softUIMode ? "#2d3436"
                                       : window.bgSurface)
                                    : (glassMode ? Qt.rgba(1,1,1,0.45)
                                       : softUIMode ? "#888888"
                                       : window.textSecondary)
                            Behavior on color {
                                ColorAnimation { duration: 200 }
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: currentIndex = index
                        }

                        HoverHandler {
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }

                // 弹性空间
                Item { Layout.fillHeight: true }

                // ── 深色模式切换按钮（仅普通模式下可见）──
                Rectangle {
                    Layout.preferredWidth: 44
                    Layout.preferredHeight: 44
                    Layout.alignment: Qt.AlignHCenter
                    color: window.darkModeFollowSystem !== 0
                            ? window.selectedBg : "transparent"
                    radius: 14
                    visible: root.styleMode === 0

                    Text {
                        anchors.centerIn: parent
                        text: root.darkIcon()
                        font.pixelSize: 20
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            window.darkModeFollowSystem = (window.darkModeFollowSystem + 1) % 3
                        }
                    }

                    HoverHandler { cursorShape: Qt.PointingHandCursor }

                    ToolTip {
                        visible: darkTip.hovered
                        text: qsTr("主题: ") + root.darkLabel()
                    }
                    HoverHandler { id: darkTip }
                }

                // ═══════════════════════════════════════
                // 风格切换按钮
                // ═══════════════════════════════════════
                Rectangle {
                    Layout.preferredWidth: 40
                    Layout.preferredHeight: 40
                    Layout.alignment: Qt.AlignLeft
                    Layout.leftMargin: 2
                    Layout.bottomMargin: 4
                    radius: 12
                    color: root.styleMode !== 0
                            ? (softUIMode ? Qt.rgba(0.64, 0.69, 0.77, 0.30)
                               : glassMode ? Qt.rgba(1, 0.6, 0.2, 0.25)
                               : window.selectedBg)
                            : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: root.styleIcon(root.styleMode)
                        font.pixelSize: 18
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.styleMode = (root.styleMode + 1) % 3
                    }

                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    HoverHandler { id: styleTip }

                    ToolTip {
                        visible: styleTip.hovered
                        text: qsTr("风格: ") + root.styleLabel(root.styleMode)
                    }
                }
            }
        }

    }

    // ═══════════════════════════════════════════
    // 窄屏：内容 + 底栏
    // ═══════════════════════════════════════════
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        visible: width < 700

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true

            // 毛玻璃层（仅在玻璃模式下可见）
            GlassCard {
                anchors.fill: parent
                anchors.margins: root.glassMode ? 6 : 0
                backgroundSource: root.glassMode ? glassBackground : null
                blurRadius: 24
                cardRadius: root.glassMode ? 14 : 0
                glassColor: Qt.rgba(1, 1, 1, 0.06)
                showBorder: root.glassMode
                showShadow: root.glassMode || root.softUIMode
                visible: root.glassMode
            }

            StackLayout {
                anchors.fill: parent
                anchors.margins: root.glassMode ? 6 : 0
                currentIndex: root.currentIndex

                SquarePage    { glassMode: root.glassMode; softUIMode: root.softUIMode }
                MessagesPage  { glassMode: root.glassMode; softUIMode: root.softUIMode }
                ProfilePage   { glassMode: root.glassMode; softUIMode: root.softUIMode }
            }
        }

        // 底栏
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 56
            color: {
                if (softUIMode) return "#dce3e9"
                if (glassMode)  return Qt.rgba(0.12, 0.12, 0.18, 0.80)
                return window.bgSidebar
            }

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Repeater {
                    model: [
                        { icon: "▪", label: qsTr("广场") },
                        { icon: "≡", label: qsTr("消息") },
                        { icon: "●", label: qsTr("我的") }
                    ]

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        ColumnLayout {
                            anchors.centerIn: parent
                            spacing: 2

                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: modelData.icon
                                font.pixelSize: 22
                            }
                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: modelData.label
                                font.pixelSize: 11
                                color: currentIndex === index
                                        ? window.accent
                                        : (softUIMode ? "#778" : glassMode ? Qt.rgba(1,1,1,0.6) : window.textSecondary)
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: currentIndex = index
                        }
                    }
                }

                // ── 深色模式切换（窄屏）──
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    visible: root.styleMode === 0

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: root.darkIcon()
                            font.pixelSize: 22
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: root.darkLabel()
                            font.pixelSize: 11
                            color: window.darkModeFollowSystem !== 0 ? "#fa0" : window.textSecondary
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            window.darkModeFollowSystem = (window.darkModeFollowSystem + 1) % 3
                        }
                    }
                }

                // ── 风格切换（窄屏，始终在最右边缘）──
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2

                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: root.styleIcon(root.styleMode)
                            font.pixelSize: 22
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: root.styleLabel(root.styleMode)
                            font.pixelSize: 11
                            color: root.styleMode !== 0 ? "#fa0" : (softUIMode ? "#778" : window.textSecondary)
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.styleMode = (root.styleMode + 1) % 3
                    }
                }
            }
        }
    }
}
