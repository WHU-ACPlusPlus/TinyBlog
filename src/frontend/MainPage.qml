import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    id: root
    color: "white"

    // ── 当前页面索引 ──
    property int currentIndex: 0

    // ── 宽屏：左侧边栏 + 内容 ──
    RowLayout {
        anchors.fill: parent
        spacing: 0
        visible: width >= 700

        // 左侧边栏
        Rectangle {
            Layout.preferredWidth: 60
            Layout.fillHeight: true
            color: "#2c2c2c"

            ColumnLayout {
                anchors.fill: parent
                anchors.topMargin: 20
                spacing: 8

                Repeater {
                    model: [
                        { icon: "🗂", tip: "广场" },
                        { icon: "💬", tip: "消息" },
                        { icon: "👤", tip: "我的" }
                    ]

                    Rectangle {
                        Layout.preferredWidth: 48
                        Layout.preferredHeight: 48
                        Layout.alignment: Qt.AlignHCenter
                        color: currentIndex === index
                                ? "#4a4a4a" : "transparent"
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
                            // 悬停高亮（桌面）
                            cursorShape: Qt.PointingHandCursor
                        }
                    }
                }
            }
        }

        // 内容区
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentIndex

            SquarePage    {}
            MessagesPage  {}
            ProfilePage   {}
        }
    }

    // ── 窄屏：内容 + 底栏 ──
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        visible: width < 700

        // 内容区
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentIndex

            SquarePage    {}
            MessagesPage  {}
            ProfilePage   {}
        }

        // 底栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: "#2c2c2c"

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Repeater {
                    model: [
                        { icon: "🗂", label: "广场" },
                        { icon: "💬", label: "消息" },
                        { icon: "👤", label: "我的" }
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
                                        ? "#6cf" : "#aaa"
                            }
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: currentIndex = index
                        }
                    }
                }
            }
        }
    }

}
