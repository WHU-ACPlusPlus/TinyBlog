import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// ═══════════════════════════════════════════════════════
// MessageBubble — 消息气泡组件
// 设计风格：极简主义（style/极简主义.md）
// 令牌：自己气泡 #4a8cf7白色文字, 对方气泡 white #333文字
//       圆角 12px, 间距 8px/12px
// ═══════════════════════════════════════════════════════

Item {
    id: root

    // ── 公开属性 ──
    property int messageId: 0
    property int senderId: 0
    property string senderName: ""
    property string content: ""
    property string sentAt: ""
    property bool isMine: false       // 是否为自己发的消息
    property bool isRead: false
    property string senderAvatar: ""  // R4 BUG B: base64头像数据

    implicitWidth: parent ? parent.width : 300
    implicitHeight: contentLayout.implicitHeight + 18

    // ── 日志 ──
    Component.onCompleted: {
        console.log("[MessageBubble] 创建气泡 id=" + messageId +
                    " sender=" + senderName + " isMine=" + isMine +
                    " content_len=" + content.length)
    }

    // ── BUG6修复：重新设计气泡布局 ──
    // 布局: [头像] [名称 时间]          (对方左对齐)
    //             [气泡内容]
    //                     [时间 名称(我)] [头像]  (自己右对齐)
    //                     [气泡内容]
    Row {
        anchors.fill: parent
        anchors.leftMargin: root.isMine ? 0 : 8
        anchors.rightMargin: root.isMine ? 8 : 0
        layoutDirection: root.isMine ? Qt.RightToLeft : Qt.LeftToRight

        // ── 头像（最外端）──
        Rectangle {
            width: 36
            height: 36
            radius: 18
            color: "#e0e0e0"
            anchors.verticalCenter: parent.verticalCenter
            clip: true  // R4: 裁剪圆形头像

            // R4 BUG B: Image优先，无头像时Text回落
            Image {
                anchors.fill: parent
                source: root.senderAvatar ? "data:image/png;base64," + root.senderAvatar : ""
                fillMode: Image.PreserveAspectCrop
                visible: root.senderAvatar !== ""
            }
            Text {
                anchors.centerIn: parent
                text: root.senderName ? root.senderName.charAt(0) : "?"
                font.pixelSize: 14; color: "#888"
                visible: root.senderAvatar === ""
            }
        }

        Item { width: root.isMine ? 8 : 10; height: 1 }

        // ── 内容区（名称行 + 气泡行）──
        ColumnLayout {
            id: contentLayout
            spacing: 4
            Layout.alignment: Qt.AlignVCenter

            // 名称 + 时间 行（气泡上方）
            RowLayout {
                Layout.alignment: root.isMine ? Qt.AlignRight : Qt.AlignLeft
                spacing: 6
                layoutDirection: root.isMine ? Qt.RightToLeft : Qt.LeftToRight

                Text {
                    text: root.isMine ? (root.senderName + qsTr("(我)")) : root.senderName
                    font.pixelSize: 11; color: "#999"
                    visible: root.senderName !== ""
                }
                Text {
                    text: formatSentTime(root.sentAt)
                    font.pixelSize: 10; color: "#bbb"
                }
                // 已读标记
                Text {
                    visible: root.isMine
                    text: root.isRead ? "\u2713\u2713" : "\u2713"
                    font.pixelSize: 10
                    color: root.isRead ? "#4a8cf7" : "#ccc"
                }
            }

            // 气泡
            Rectangle {
                id: bubbleBg
                Layout.preferredWidth: Math.min(bubbleText.implicitWidth + 24, (parent ? parent.parent.width : 300) - 80)
                Layout.preferredHeight: bubbleText.implicitHeight + 20
                Layout.alignment: root.isMine ? Qt.AlignRight : Qt.AlignLeft
                color: root.isMine ? "#4a8cf7" : "white"
                radius: 12

                Rectangle {
                    anchors.fill: parent; radius: 12
                    color: "transparent"
                    border.color: root.isMine ? "transparent" : "#e8e8e8"
                    border.width: root.isMine ? 0 : 0.5
                }

                Text {
                    id: bubbleText
                    anchors.centerIn: parent
                    width: parent.width - 24
                    text: root.content
                    font.pixelSize: 14
                    color: root.isMine ? "white" : "#333"
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    lineHeight: 1.4
                }
            }
        }

        Item { width: 8; height: 1 }
    }

    // ── 时间格式化 ──
    function formatSentTime(dateTimeStr) {
        if (!dateTimeStr || dateTimeStr.length < 16) return ""
        var now = new Date()
        var datePart = dateTimeStr.substring(0, 10)
        var timePart = dateTimeStr.substring(11, 16)
        var todayStr = now.getFullYear() + "-" +
                       String(now.getMonth() + 1).padStart(2, '0') + "-" +
                       String(now.getDate()).padStart(2, '0')
        if (datePart === todayStr) {
            return timePart
        }
        return datePart.substring(5) + " " + timePart  // "07-07 14:30"
    }
}
