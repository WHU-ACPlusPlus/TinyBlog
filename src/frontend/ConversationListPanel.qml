import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// ═══════════════════════════════════════════════════════
// ConversationListPanel — 会话列表面板
// 设计风格：极简主义（style/极简主义.md）
// 令牌：背景 bgPage, bgSurface 卡片, 圆角 8px, 间距 12px
// ═══════════════════════════════════════════════════════

Rectangle {
    id: root

    // ── 公开属性 ──
    property var conversations: []       // 会话数据列表
    property int selectedConvId: -1      // 当前选中会话ID
    property int slideInTrigger: 0       // 外部递增此值来触发滑入动画

    // ── 风格模式（由 MessagesPage 传入）──
    property bool glassMode: false
    property bool softUIMode: false

    // ── 自适应文字颜色 ──
    property color textPrimary:   glassMode ? "#ffffff" : (softUIMode ? "#2d3436" : (window.darkMode ? "#e0e0e0" : "#222222"))
    property color textSecondary: glassMode ? Qt.rgba(1,1,1,0.60) : (softUIMode ? "#636e72" : (window.darkMode ? "#999999" : "#555555"))

    // ── 信号 ──
    signal conversationClicked(var conv)
    signal addButtonClicked()
    signal menuAction(int index)
    signal searchRequested(string keyword)
    signal refreshRequested()

color: {
    if (softUIMode) return "#e8edf2"
    if (glassMode) return "transparent"
    if (window.darkMode) return "#1e1e1e"
    if (api.wallpaperPath.length > 0) return Qt.rgba(0.98, 0.98, 0.98, 0.70)
    return "#fafafa"
}
    implicitWidth: 280

    // ── 从左侧滑入动画 ──
    transform: Translate {
        id: slideTransform
        x: -root.width  // 初始在左侧屏幕外
    }

    // 监听 slideInTrigger 变化，每次递增触发滑入
    onSlideInTriggerChanged: {
        if (slideInTrigger > 0) {
            slideAnim.start()
        }
    }

    // 首次加载时自动滑入
    Component.onCompleted: {
        console.log("[ConversationListPanel] 面板初始化完成")
        slideAnim.start()
    }

    // 滑入动画
    NumberAnimation {
        id: slideAnim
        target: slideTransform
        property: "x"
        from: -root.width
        to: 0
        duration: 350
        easing.type: Easing.OutCubic
    }

    onConversationsChanged: {
        console.log("[ConversationListPanel] 会话列表更新, 数量=" + conversations.length)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── 顶栏：搜索框 + 添加按钮 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
color: root.softUIMode ? "#dce3e9" : (root.glassMode ? Qt.rgba(1, 1, 1, 0.06) : (window.darkMode ? "#2d2d2d" : "white"))

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                // 搜索框
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
color: root.softUIMode ? "#c8d0d8" : (root.glassMode ? Qt.rgba(1, 1, 1, 0.10) : (window.darkMode ? "#3a3a3a" : "#f0f0f0"))
                    radius: 8

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 8
                        spacing: 6

                        Image {
                            source: "qrc:/emoji/1f50d.svg"
                            sourceSize.width: 14
                            sourceSize.height: 14
                            fillMode: Image.PreserveAspectFit
                        }

                        TextInput {
                            id: searchInput
                            Layout.fillWidth: true
                            font.pixelSize: 13
                            color: window.textPrimary
                            clip: true

                            Text {
                                anchors.fill: parent
                                text: qsTr("搜索")
                                font.pixelSize: 13
                                color: window.textSecondary
                                visible: searchInput.text === "" && !searchInput.activeFocus
                            }

                            // ── 防抖搜索 500ms ──
                            property var searchTimer: null

                            onTextChanged: {
                                if (!searchTimer) {
                                    searchTimer = Qt.createQmlObject(
                                        'import QtQuick; Timer { interval: 500; repeat: false }', searchInput)
                                    searchTimer.triggered.connect(function() {
                                        var kw = searchInput.text.trim()
                                        console.log("[ConversationListPanel] 搜索关键词: '" + kw + "'")
                                        if (kw.length > 0) {
                                            root.searchRequested(kw)  // P3: 通过信号通知MessagesPage
                                        }
                                    })
                                }
                                searchTimer.stop()
                                searchTimer.restart()
                            }

                            Keys.onReturnPressed: {
                                var kw = searchInput.text.trim()
                                console.log("[ConversationListPanel] 回车搜索: '" + kw + "'")
                                if (kw.length > 0) {
                                    root.searchRequested(kw)  // P3: 通过信号通知MessagesPage
                                }
                            }
                        }
                    }
                }

                // "+" 添加按钮
                Rectangle {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    radius: 8
                    color: addBtnHover.hovered ? window.divider : window.bgInput

                    Text {
                        anchors.centerIn: parent
                        text: "+"
                        font.pixelSize: 20
                        font.weight: Font.Light
                        color: window.textSecondary
                    }

                    MouseArea {
                        id: addBtnMouse
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[ConversationListPanel] '+' 按钮被点击")
                            addMenu.open()
                        }
                    }

                    HoverHandler {
                        id: addBtnHover
                        cursorShape: Qt.PointingHandCursor
                    }
                }
            }
        }

        // ── "+" 弹出菜单 ──
        Popup {
            id: addMenu
            x: parent.width - width - 10
            y: 60
            width: 160
            padding: 4
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

            background: Rectangle {
color: root.softUIMode ? "#f0f2f5" : (root.glassMode ? Qt.rgba(1, 1, 1, 0.12) : (window.darkMode ? "#2d2d2d" : "white"))
                radius: 8
                layer.enabled: true
                layer.effect: null  // QtQuick.Controls.Basic uses no shadow
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 2

                Repeater {
                    model: [
                        { text: qsTr("添加好友"), icon: "＋" },
                        { text: qsTr("创建群聊"), icon: "emoji/1f465.svg" },
                        { text: qsTr("加入群聊"), icon: "emoji/1f517.svg" }
                    ]

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
color: root.softUIMode
                               ? (menuItemHover.hovered ? Qt.rgba(0.64, 0.69, 0.77, 0.2) : "transparent")
                               : root.glassMode
                                 ? (menuItemHover.hovered ? Qt.rgba(1, 1, 1, 0.10) : "transparent")
                                 : (menuItemHover.hovered ? "#f5f5f5" : "transparent")
                        radius: 4

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            Image {
                                anchors.centerIn: parent
                                source: "qrc:/" + modelData.icon
                                sourceSize.width: 14
                                sourceSize.height: 14
                                fillMode: Image.PreserveAspectFit
                            }
                            Text {
                                text: modelData.text
                                font.pixelSize: 13
                                color: window.textPrimary
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                console.log("[ConversationListPanel] 菜单项被点击: " + modelData.text)
                                addMenu.close()
                                root.addButtonClicked()
                                root.menuAction(index)
                            }
                        }

                        HoverHandler {
                            id: menuItemHover
                        }
                    }
                }
            }
        }

        // BUG1修复: 搜索弹窗已移至 MessagesPage 统一管理

        // ── 会话列表 ──
        ListView {
            id: conversationList
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.conversations
            clip: true

            // 空状态
            Rectangle {
                anchors.fill: parent
                color: "transparent"
                visible: conversationList.count === 0

                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 12

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "≡"
                        font.pixelSize: 40
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("暂无消息")
                        font.pixelSize: 15
color: root.textSecondary
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("关注好友或加入群聊开始聊天")
                        font.pixelSize: 12
color: root.textSecondary
                    }
                }
            }

            delegate: ConversationItem {
                width: conversationList.width
                glassMode: root.glassMode
                softUIMode: root.softUIMode
                conversationId: modelData.id || 0
                convType: modelData.type || "private"
                targetId: modelData.target_id || 0
                targetName: modelData.target_name || ""
                targetAvatar: modelData.target_avatar || ""
                lastMessage: modelData.last_message || ""
                lastMessageTime: modelData.last_message_time || ""
                unreadCount: modelData.unread_count || 0
                isSelected: conversationId === root.selectedConvId

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        console.log("[ConversationListPanel] 会话被点击 id=" +
                                    conversationId + " type=" + convType)
                        root.conversationClicked(modelData)
                    }
                }
            }

            // 滚动日志
            onContentYChanged: {
                // 仅在大幅滚动时记录（减少日志噪音）
                if (Math.abs(contentY - (contentY > 0 ? contentY : 0)) > 200) {
                    // 不做频繁日志
                }
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }
        }

        // ── 底部刷新按钮 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 40
            color: root.softUIMode ? "#dce3e9" : (root.glassMode ? Qt.rgba(1, 1, 1, 0.06) : (window.darkMode ? "#1e1e1e" : "#fafafa"))

            Rectangle {
                anchors.centerIn: parent
                width: refreshBtnRow.implicitWidth + 24
                height: 32
                radius: 6
                color: refreshBtnHover.hovered
                       ? (root.softUIMode ? "#c8d0d8" : (root.glassMode ? Qt.rgba(1, 1, 1, 0.12) : (window.darkMode ? "#444444" : "#e8e8e8")))
                       : "transparent"

                Behavior on color { ColorAnimation { duration: 150 } }

                RowLayout {
                    id: refreshBtnRow
                    anchors.centerIn: parent
                    spacing: 6

                    Image {
                        source: "qrc:/emoji/1f504.svg"
                        sourceSize.width: 14
                        sourceSize.height: 14
                        fillMode: Image.PreserveAspectFit
                    }
                    Text {
                        text: qsTr("刷新")
                        font.pixelSize: 12
                        color: root.textSecondary
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        console.log("[ConversationListPanel] 刷新按钮被点击")
                        root.refreshRequested()
                    }
                }

                HoverHandler {
                    id: refreshBtnHover
                    cursorShape: Qt.PointingHandCursor
                }
            }
        }
    }
}
