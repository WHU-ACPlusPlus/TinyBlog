import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// ═══════════════════════════════════════════════════════
// ConversationItem — 会话列表中的单个会话项
// 设计风格：极简主义（style/极简主义.md）
// 令牌：背景 bgSurface, 圆角 8px, 间距 8px/12px
// ═══════════════════════════════════════════════════════

Item {
    id: root

    // ── 公开属性 ──
    property int conversationId: 0
    property string convType: "private"       // "private" | "group"
    property int targetId: 0
    property string targetName: ""
    property string targetAvatar: ""          // base64
    property string lastMessage: ""
    property string lastMessageTime: ""
    property int unreadCount: 0
    property bool isSelected: false

    // ── 风格模式（由 ConversationListPanel 传入）──
    property bool glassMode: false
    property bool softUIMode: false

    // ── 自适应文字颜色 ──
    property color textPrimary:   glassMode ? "#ffffff" : (softUIMode ? "#2d3436" : "#222222")
    property color textSecondary: glassMode ? Qt.rgba(1,1,1,0.55) : (softUIMode ? "#636e72" : "#555555")
    property color textMuted:     glassMode ? Qt.rgba(1,1,1,0.35) : (softUIMode ? "#888888" : "#999999")

    implicitWidth: 280
    implicitHeight: 64

    // ── 日志 ──
    Component.onCompleted: {
        console.log("[ConversationItem] 创建 id=" + conversationId +
                    " type=" + convType + " name=" + targetName +
                    " unread=" + unreadCount)
    }

    // ── 背景 ──
    Rectangle {
        anchors.fill: parent
        anchors.margins: 4
color: root.softUIMode
               ? (root.isSelected ? Qt.rgba(0.64, 0.69, 0.77, 0.25) : "#e8edf2")
               : root.glassMode
                 ? (root.isSelected ? Qt.rgba(0.5, 0.7, 1.0, 0.15) : Qt.rgba(1, 1, 1, 0.06))
                 : (root.isSelected ? "#e8f0fe" : "white")
        radius: 8

        Behavior on color {
            ColorAnimation { duration: 150; easing.type: Easing.OutCubic }
        }

        // ── 行布局：头像 | 文字区 | 时间+红点 ──
        RowLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            // ── 头像 40x40 圆形 ──
            Rectangle {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                radius: 20
                color: root.convType === "group" ? window.accent : window.divider

                // 群聊图标 / 用户头像文字
                Text {
                    anchors.centerIn: parent
                    text: root.convType === "group" ? "👥" :
                          (root.targetName ? root.targetName.charAt(0) : "?")
                    font.pixelSize: root.convType === "group" ? 18 : 16
                    color: window.textSecondary
                }
            }

            // ── 中间文字区（名称 + 最后消息预览）──
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                // 名称
                Text {
                    Layout.fillWidth: true
                    text: root.targetName || qsTr("未知")
                    font.pixelSize: 14
                    font.weight: root.unreadCount > 0 ? Font.DemiBold : Font.Normal
color: root.textPrimary
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                // 最后消息预览（单行截断）
                Text {
                    Layout.fillWidth: true
                    text: root.lastMessage || qsTr("暂无消息")
                    font.pixelSize: 12
color: root.unreadCount > 0 ? root.textSecondary : root.textMuted
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
            }

            // ── 右侧：时间 + 未读红点 ──
            ColumnLayout {
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                spacing: 4

                // 时间
                Text {
                    Layout.alignment: Qt.AlignRight
                    text: root.lastMessageTime ? formatTime(root.lastMessageTime) : ""
                    font.pixelSize: 11
color: root.textMuted
                }

                // 未读红点
                Rectangle {
                    Layout.alignment: Qt.AlignRight
                    width: root.unreadCount > 0 ? (root.unreadCount > 99 ? 26 : 18) : 0
                    height: root.unreadCount > 0 ? 18 : 0
                    radius: 9
                    color: "#ff4d4f"
                    visible: root.unreadCount > 0

                    Text {
                        anchors.centerIn: parent
                        text: root.unreadCount > 99 ? "99+" : String(root.unreadCount)
                        font.pixelSize: 10
                        color: window.bgSurface
                    }
                }
            }
        }
    }

    // ── 底部细线分隔 ──
    Rectangle {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width - 20
        height: 0.5
        color: window.divider
    }

    // ── 时间格式化辅助函数 ──
    function formatTime(dateTimeStr) {
        // 输入："2026-07-07 14:30:00"
        // 输出："14:30" (今天) 或 "07-07" (更早)
        if (!dateTimeStr || dateTimeStr.length < 16) return ""
        var now = new Date()
        var datePart = dateTimeStr.substring(0, 10)  // "2026-07-07"
        var timePart = dateTimeStr.substring(11, 16) // "14:30"
        var todayStr = now.getFullYear() + "-" +
                       String(now.getMonth() + 1).padStart(2, '0') + "-" +
                       String(now.getDate()).padStart(2, '0')
        if (datePart === todayStr) {
            return timePart  // 今天只显示时分
        }
        return datePart.substring(5)  // "07-07"
    }
}
