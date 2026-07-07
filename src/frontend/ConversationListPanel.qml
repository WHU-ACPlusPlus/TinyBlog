import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// ═══════════════════════════════════════════════════════
// ConversationListPanel — 会话列表面板
// 设计风格：极简主义（style/极简主义.md）
// 令牌：背景 #f5f5f5, 白色卡片, 圆角 8px, 间距 12px
// ═══════════════════════════════════════════════════════

Rectangle {
    id: root

    // ── 公开属性 ──
    property var conversations: []       // 会话数据列表
    property int selectedConvId: -1      // 当前选中会话ID

    // ── 信号 ──
    signal conversationClicked(var conv)
    signal addButtonClicked()
    signal menuAction(int index)
    signal searchRequested(string keyword)

    color: "#fafafa"
    implicitWidth: 280

    // ── 日志 ──
    Component.onCompleted: {
        console.log("[ConversationListPanel] 面板初始化完成")
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
            color: "white"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                // 搜索框
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    color: "#f0f0f0"
                    radius: 8

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 8
                        spacing: 6

                        Text {
                            text: "🔍"
                            font.pixelSize: 14
                        }

                        TextInput {
                            id: searchInput
                            Layout.fillWidth: true
                            font.pixelSize: 13
                            color: "#333"
                            clip: true

                            Text {
                                anchors.fill: parent
                                text: qsTr("搜索")
                                font.pixelSize: 13
                                color: "#bbb"
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
                    color: addBtnHover.hovered ? "#e8e8e8" : "#f0f0f0"

                    Text {
                        anchors.centerIn: parent
                        text: "+"
                        font.pixelSize: 20
                        font.weight: Font.Light
                        color: "#666"
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
                color: "white"
                radius: 8
                layer.enabled: true
                layer.effect: null  // QtQuick.Controls.Basic uses no shadow
            }

            ColumnLayout {
                anchors.fill: parent
                spacing: 2

                Repeater {
                    model: [
                        { text: qsTr("添加好友"), icon: "👤" },
                        { text: qsTr("创建群聊"), icon: "👥" },
                        { text: qsTr("加入群聊"), icon: "🔗" }
                    ]

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 36
                        color: menuItemHover.hovered ? "#f5f5f5" : "transparent"
                        radius: 4

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            spacing: 8

                            Text {
                                text: modelData.icon
                                font.pixelSize: 14
                            }
                            Text {
                                text: modelData.text
                                font.pixelSize: 13
                                color: "#333"
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
                        text: "💬"
                        font.pixelSize: 40
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("暂无消息")
                        font.pixelSize: 15
                        color: "#bbb"
                    }
                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: qsTr("关注好友或加入群聊开始聊天")
                        font.pixelSize: 12
                        color: "#ccc"
                    }
                }
            }

            delegate: ConversationItem {
                width: conversationList.width
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
    }
}
