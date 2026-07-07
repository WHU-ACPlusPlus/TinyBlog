import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    color: "#f5f5f5"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // ── 第一行：头像 + 昵称/用户名 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
            color: "white"
            radius: 10

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 14

                // 头像占位
                Rectangle {
                    Layout.preferredWidth: 52
                    Layout.preferredHeight: 52
                    color: "#ddd"
                    radius: 26

                    Text {
                        anchors.centerIn: parent
                        text: "👤"
                        font.pixelSize: 26
                    }
                }

                // 昵称 + 用户名
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 4

                    Text {
                        text: "昵称"
                        font.pixelSize: 18
                        font.bold: true
                        color: "#222"
                    }
                    Text {
                        text: "@用户名"
                        font.pixelSize: 14
                        color: "#888"
                    }
                }
            }
        }

        // ── 第二行：个性签名 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: "white"
            radius: 10

            Text {
                anchors.fill: parent
                anchors.margins: 14
                text: "这个人很懒，什么都没有留下……"
                color: "#999"
                font.pixelSize: 15
                verticalAlignment: Text.AlignVCenter
            }
        }

        // ── 第三行：登出按钮 ──
        Button {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Layout.topMargin: 8
            text: "登出"

            contentItem: Text {
                text: "登出"
                color: "white"
                font.pixelSize: 16
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                radius: 10
                color: "#e55"
            }

            onClicked: api.clearAuth()
        }

        // 剩余空间填充
        Item { Layout.fillHeight: true }
    }
}
