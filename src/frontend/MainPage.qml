import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root


    // ── 当前页面索引 ──
    property int currentIndex: 0

    // ── 风格模式：0=普通  1=毛玻璃  2=SoftUI ──
    property int styleMode: 0
    property bool glassMode: styleMode === 1
    property bool softUIMode: styleMode === 2

    // 根据模式自动切换背景
    color: {
        if (softUIMode) return "#e8edf2"       // Soft UI 柔和浅灰蓝
        if (glassMode)  return "transparent"    // 毛玻璃透明
        return "white"                          // 普通白色
    }

    // ── 鼠标位置（用于跟随光源）──
    property real mouseX: width / 2
    property real mouseY: height / 2

    // ── 背景图路径（Windows 本地绝对路径，可替换）──
    property string bgImagePath: "file:///D:/SocialAppUI/TinyBlog/image/1.png"

    // ═══════════════════════════════════════════
    // 风格图标映射
    // ═══════════════════════════════════════════
    function styleIcon(mode) {
        switch (mode) { case 1: return "🔮"; case 2: return "🫧"; default: return "🏠" }
    }
    function styleLabel(mode) {
        switch (mode) { case 1: return "玻璃"; case 2: return "柔和"; default: return "普通" }
    }

    // ═══════════════════════════════════════════
    // 背景层（仅在毛玻璃模式下可见）
    // ═══════════════════════════════════════════
    Item {
        id: glassBackground
        anchors.fill: parent
        visible: root.glassMode
        z: -1

        // ── 背景图片 ──
        Image {
            id: bgImage
            anchors.fill: parent
            source: root.bgImagePath
            fillMode: Image.PreserveAspectCrop
            asynchronous: true

            onStatusChanged: {
                if (status === Image.Ready)
                    console.log("[MainPage] 背景图加载: " + implicitWidth + "x" + implicitHeight)
                else if (status === Image.Error)
                    console.warn("[MainPage] 背景图加载失败: " + root.bgImagePath)
            }
        }

        // ── 鼠标跟随光源（柔和径向暖光，仅玻璃模式）──
        // 使用 Canvas + createRadialGradient 实现真正平滑的径向渐变
        // Qt 6 要求 ShaderEffect 使用预编译 .qsb，Canvas 无此限制
        Canvas {
            id: mouseLight
            width: 700; height: 700
            x: root.mouseX - width / 2
            y: root.mouseY - height / 2
            visible: root.glassMode

            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                // 径向渐变：中心暖白 → 边缘透明
                var gradient = ctx.createRadialGradient(
                    width / 2, height / 2, 0,      // 内圆：中心点，半径 0
                    width / 2, height / 2, width / 2 // 外圆：中心点，半径 250
                )
                gradient.addColorStop(0.0, "rgba(255, 235, 209, 0.12)")  // 中心暖白 12%
                gradient.addColorStop(0.4, "rgba(255, 242, 224, 0.06)")  // 中间过渡
                gradient.addColorStop(0.7, "rgba(255, 245, 230, 0.02)")  // 外层微光
                gradient.addColorStop(1.0, "transparent")                  // 边缘透明
                ctx.fillStyle = gradient
                ctx.fillRect(0, 0, width, height)
            }

            Behavior on x { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
            Behavior on y { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
        }
    }

    // ── 鼠标追踪层（仅追踪位置，不拦截点击/滚轮）──
    MouseArea {
        id: mouseTracker
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton  // 不消费任何按键事件，完全透传
        onPositionChanged: function(mouse) {
            root.mouseX = mouse.x
            root.mouseY = mouse.y
        }
    }

    // ═══════════════════════════════════════════
    // 宽屏：左侧边栏 + 内容
    // ═══════════════════════════════════════════
    RowLayout {
        anchors.fill: parent
        spacing: 0
        visible: width >= 700

        // ── 左侧边栏 ──
        Rectangle {
            Layout.preferredWidth: 60
            Layout.fillHeight: true
            // 毛玻璃模式：半透明深色；普通模式：实色深灰
            color: root.glassMode
                    ? Qt.rgba(0.12, 0.12, 0.18, 0.75) : "#2c2c2c"

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 20
                anchors.bottomMargin: 12
                spacing: 8

                // 导航按钮
                Repeater {
                    model: [
                        { icon: "▪", tip: qsTr("广场") },
                        { icon: "≡", tip: qsTr("消息") },
                        { icon: "●", tip: qsTr("我的") }
                    ]

                    Rectangle {
                        Layout.preferredWidth: 48
                        Layout.preferredHeight: 48
                        Layout.alignment: Qt.AlignHCenter
                        color: currentIndex === index
? (root.glassMode
                                    ? Qt.rgba(1, 1, 1, 0.20)
                                    : "#4a4a4a")
                                : "transparent"
                        radius: 12

                        Text {
                            anchors.centerIn: parent
                            text: modelData.icon
                            font.pixelSize: 22
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

                // 弹性空间 — 把切换按钮推到底部
                Item { Layout.fillHeight: true }

                // ── 风格切换按钮（点击循环：普通→玻璃→柔和）──
                Rectangle {
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 48
                    Layout.alignment: Qt.AlignHCenter
                    color: root.styleMode !== 0
                            ? (root.softUIMode ? Qt.rgba(0.64, 0.69, 0.77, 0.30)
                               : root.glassMode ? Qt.rgba(1, 0.6, 0.2, 0.25)
                               : "#4a4a4a")
                            : "transparent"
                    radius: 12

                    Text {
                        anchors.centerIn: parent
                        text: root.styleIcon(root.styleMode)
                        font.pixelSize: 20
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: root.styleMode = (root.styleMode + 1) % 3
                    }

                    HoverHandler { cursorShape: Qt.PointingHandCursor }

                    ToolTip {
                        visible: ttHover.hovered
                        text: "风格: " + root.styleLabel(root.styleMode) + "（点击切换）"
                    }
                    HoverHandler { id: ttHover }
                }
            }
        }

        // ── 内容区 ──
        Item {
            Layout.fillWidth: true; Layout.fillHeight: true

            // GlassCard is not yet available — skipped until the file is created
            // GlassCard {
            //     anchors.fill: parent
            //     anchors.margins: root.glassMode ? 8 : 0
            //     backgroundSource: root.glassMode ? glassBackground : null
            //     blurRadius: 28
            //     cardRadius: root.glassMode ? 16 : 0
            //     glassColor: Qt.rgba(1, 1, 1, 0.06)
            //     showBorder: root.glassMode
            //     showShadow: root.glassMode || root.softUIMode
            //     visible: root.glassMode
            // }

            StackLayout {
                anchors.fill: parent
                anchors.margins: root.glassMode ? 8 : 0
                currentIndex: root.currentIndex

                SquarePage    { glassMode: root.glassMode; softUIMode: root.softUIMode }
                MessagesPage  { glassMode: root.glassMode; softUIMode: root.softUIMode }
                ProfilePage   { glassMode: root.glassMode; softUIMode: root.softUIMode }
            }
        }
    }

    // ═══════════════════════════════════════════
    // 窄屏：内容 + 底栏
    // ═══════════════════════════════════════════
    ColumnLayout {
        anchors.fill: parent; spacing: 0
        visible: width < 700

        Item {
            Layout.fillWidth: true; Layout.fillHeight: true

            // GlassCard is not yet available — skipped until the file is created
            // GlassCard {
            //     anchors.fill: parent
            //     anchors.margins: root.glassMode ? 6 : 0
            //     backgroundSource: root.glassMode ? glassBackground : null
            //     blurRadius: 24
            //     cardRadius: root.glassMode ? 14 : 0
            //     glassColor: Qt.rgba(1, 1, 1, 0.06)
            //     showBorder: root.glassMode
            //     showShadow: root.glassMode || root.softUIMode
            //     visible: root.glassMode
            // }

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
                if (root.softUIMode) return "#dce3e9"
                if (root.glassMode)  return Qt.rgba(0.12, 0.12, 0.18, 0.80)
                return "#2c2c2c"
            }

            RowLayout {
                anchors.fill: parent; spacing: 0

                Repeater {
                    model: [
                        { icon: "▪", label: qsTr("广场") },
                        { icon: "≡", label: qsTr("消息") },
                        { icon: "●", label: qsTr("我的") }
                    ]
                    Item {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        ColumnLayout {
                            anchors.centerIn: parent; spacing: 2
                            Text { Layout.alignment: Qt.AlignHCenter; text: modelData.icon; font.pixelSize: 22 }
                            Text {
Layout.alignment: Qt.AlignHCenter; text: modelData.label; font.pixelSize: 11
                                color: currentIndex === index ? "#6cf" : (root.softUIMode ? "#778" : "#aaa")
                            }
                        }
                        MouseArea { anchors.fill: parent; onClicked: currentIndex = index }
                    }
                }

                // ── 风格切换（窄屏点击循环）──
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    ColumnLayout {
                        anchors.centerIn: parent; spacing: 2
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: root.styleIcon(root.styleMode)
                            font.pixelSize: 22
                        }
                        Text {
                            Layout.alignment: Qt.AlignHCenter
                            text: root.styleLabel(root.styleMode)
                            font.pixelSize: 11
                            color: root.styleMode !== 0 ? "#fa0" : (root.softUIMode ? "#778" : "#aaa")
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
