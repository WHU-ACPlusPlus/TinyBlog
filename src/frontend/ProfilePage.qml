import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: root
    color: window.bgPage

    property var profileData: ({})
    property bool editing: false
    property string newNickname: ""
    property string newAvatar: ""
    property string newAvatarMime: "image/png"
    property string newSignature: ""

    // 从 base64 前几个字符推断 MIME 类型
    function detectMime(b64) {
        if (!b64 || b64.length < 4) return "image/png"
        var s = b64.substring(0, 10)
        if (s.startsWith("/9j/") || s.startsWith("/9j/4")) return "image/jpeg"
        if (s.startsWith("R0lGODdh") || s.startsWith("R0lGODlh")) return "image/gif"
        if (s.startsWith("UklGR")) return "image/webp"
        if (s.startsWith("Qk")) return "image/bmp"
        return "image/png"  // 默认 PNG / 或未知
    }

    // 每次页面显示时刷新资料
    onVisibleChanged: {
        if (visible) {
            api.fetchProfile()
        }
    }

    // 监听 profileFetched 信号
    Connections {
        target: api

        function onProfileFetched(profile) {
            root.profileData = profile
            root.newNickname = profile.nickname || ""
            root.newSignature = profile.signature || ""
            root.newAvatar = ""
            root.newAvatarMime = root.detectMime(profile.avatar || "")
            root.editing = false
        }

        function onProfileUpdated() {
            // 更新成功后重新加载
            api.fetchProfile()
        }

        function onErrorOccurred(message) {
            // 显示错误提示（可选）
            console.log("Profile error:", message)
        }
    }

    // 头像选择对话框
    FileDialog {
        id: avatarPicker
        title: qsTr("选择头像")
        nameFilters: ["图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"]
        onAccepted: {
            var b64 = api.readFileAsBase64(selectedFile)
            if (b64.length > 0) {
                root.newAvatar = b64
                root.newAvatarMime = root.detectMime(b64)
            }
        }
    }

    // 头像大图预览弹窗
    Popup {
        id: avatarPreview
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        anchors.centerIn: Overlay.overlay
        background: Rectangle {
            color: "#00000000"
        }

        contentItem: Item {
            implicitWidth: Math.min(300, root.width - 40)
            implicitHeight: implicitWidth

            Rectangle {
                anchors.fill: parent
                radius: 12
                color: window.bgSurface

                Image {
                    id: previewImg
                    anchors.fill: parent
                    anchors.margins: 4
                    source: avatarImg.visible ? avatarImg.source : ""
                    fillMode: Image.PreserveAspectFit
                }

                // 关闭按钮
                Rectangle {
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 4
                    width: 28
                    height: 28
                    radius: 14
                    color: "#00000066"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: window.bgSurface
                        font.pixelSize: 16
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: avatarPreview.close()
                    }
                }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        // ── 顶部：头像 + 昵称/用户名 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            color: window.bgSurface
            radius: 12

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 14

                // 头像
                Item {
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: 64

                    Rectangle {
                        id: avatarBg
                        anchors.fill: parent
                        color: window.textOnDark
                        radius: 32

                        // 头像图片（base64 或 默认占位）
                        Rectangle {
                            id: avatarClip
                            anchors.fill: parent
                            radius: 32
                            clip: true
                            color: "transparent"

                            Image {
                                id: avatarImg
                                anchors.fill: parent
                                source: {
                                    var av = root.newAvatar.length > 0
                                            ? root.newAvatar
                                            : (root.profileData.avatar || "")
                                    if (av)
                                        return "data:" + root.newAvatarMime + ";base64," + av
                                    return ""
                                }
                                fillMode: Image.PreserveAspectCrop
                                visible: source.toString().length > 0
                            }
                        }

                        // 无头像时的默认图标
                        Text {
                            anchors.centerIn: parent
                            text: "👤"
                            font.pixelSize: 30
                            visible: !avatarImg.visible
                        }

                        // 点击头像：预览大图 / 编辑模式下更换
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root.editing) {
                                    avatarPicker.open()
                                } else if (avatarImg.visible) {
                                    avatarPreview.open()
                                }
                            }
                        }

                        // 编辑模式下显示"更换"提示
                        Rectangle {
                            anchors.fill: parent
                            radius: 32
                            clip: true
                            visible: root.editing
                            color: "transparent"

                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.left: parent.left
                                anchors.right: parent.right
                                height: 22
                                color: "#00000088"
                                Text {
                                    anchors.centerIn: parent
                                    text: qsTr("更换")
                                    color: window.bgSurface
                                    font.pixelSize: 11
                                }
                            }
                        }
                    }
                }

                // 昵称 + 用户名
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 4

                    // 昵称（可编辑或显示模式）
                    TextField {
                        id: nicknameField
                        Layout.fillWidth: true
                        text: root.editing ? root.newNickname : (root.profileData.nickname || "")
                        font.pixelSize: 20
                        font.bold: true
                        color: window.textPrimary
                        readOnly: !root.editing
                        selectByMouse: true
                        background: Rectangle {
                            radius: 6
                            color: root.editing ? window.bgInput : "transparent"
                            border.color: root.editing ? window.accent : "transparent"
                            border.width: root.editing ? 1 : 0
                        }
                        onTextChanged: {
                            if (root.editing)
                                root.newNickname = text
                        }
                    }

                    // 用户名（只读）
                    Text {
                        text: "@" + (root.profileData.username || qsTr("用户名"))
                        font.pixelSize: 14
                        color: window.textSecondary
                    }
                }
            }
        }

        // ── 个性签名（自适应高度） ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: signatureField.implicitHeight + 24
            color: window.bgSurface
            radius: 10

            TextArea {
                id: signatureField
                anchors.fill: parent
                anchors.margins: 10
                text: root.editing ? root.newSignature : (root.profileData.signature || qsTr("这个人很懒，什么都没有留下……"))
                color: root.editing ? window.textPrimary : window.textSecondary
                font.pixelSize: 14
                readOnly: !root.editing
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                background: Rectangle {
                    radius: 6
                    color: root.editing ? window.bgInput : "transparent"
                    border.color: root.editing ? window.accent : "transparent"
                    border.width: root.editing ? 1 : 0
                }
                onTextChanged: {
                    if (root.editing)
                        root.newSignature = text
                }
            }
        }

        // ── 资料统计 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: window.bgSurface
            radius: 10

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Item { Layout.fillWidth: true }
                ColumnLayout {
                    Layout.alignment: Qt.AlignCenter
                    spacing: 2
                    Text { text: root.profileData.post_count || "---"; font.bold: true; font.pixelSize: 18; color: window.textPrimary; Layout.alignment: Qt.AlignHCenter }
                    Text { text: qsTr("帖子"); font.pixelSize: 13; color: window.textSecondary; Layout.alignment: Qt.AlignHCenter }
                }
                Item { Layout.fillWidth: true }
                ColumnLayout {
                    Layout.alignment: Qt.AlignCenter
                    spacing: 2
                    Text { text: root.profileData.follower_count || "---"; font.bold: true; font.pixelSize: 18; color: window.textPrimary; Layout.alignment: Qt.AlignHCenter }
                    Text { text: qsTr("粉丝"); font.pixelSize: 13; color: window.textSecondary; Layout.alignment: Qt.AlignHCenter }
                }
                Item { Layout.fillWidth: true }
                ColumnLayout {
                    Layout.alignment: Qt.AlignCenter
                    spacing: 2
                    Text { text: root.profileData.followee_count || "---"; font.bold: true; font.pixelSize: 18; color: window.textPrimary; Layout.alignment: Qt.AlignHCenter }
                    Text { text: qsTr("关注"); font.pixelSize: 13; color: window.textSecondary; Layout.alignment: Qt.AlignHCenter }
                }
                Item { Layout.fillWidth: true }
            }
        }

        // ── 编辑/保存 按钮 ──
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                text: root.editing ? qsTr("保存") : qsTr("编辑资料")

                contentItem: Text {
                    text: parent.text
                    color: window.bgSurface
                    font.pixelSize: 16
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 10
                    color: root.editing ? "#4a90d9" : "#4a90d9"
                }

                onClicked: {
                    if (root.editing) {
                        // 保存修改
                        api.updateProfile(
                            root.newNickname !== root.profileData.nickname ? root.newNickname : "",
                            root.newAvatar,
                            root.newSignature !== root.profileData.signature ? root.newSignature : ""
                        )
                        root.editing = false
                    } else {
                        root.editing = true
                        root.newNickname = root.profileData.nickname || ""
                        root.newSignature = root.profileData.signature || ""
                        root.newAvatar = ""
                    }
                }
            }

            // 取消按钮（编辑模式下显示）
            Button {
                Layout.preferredWidth: root.editing ? 80 : 0
                Layout.preferredHeight: 44
                text: qsTr("取消")
                clip: true
                visible: root.editing

                contentItem: Text {
                    text: qsTr("取消")
                    color: window.textSecondary
                    font.pixelSize: 16
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 10
                    color: window.divider
                }

                onClicked: {
                    root.editing = false
                    root.newNickname = root.profileData.nickname || ""
                    root.newSignature = root.profileData.signature || ""
                    root.newAvatar = ""
                }
            }
        }

        // ── 登出按钮 ──
        Button {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            Layout.topMargin: 8
            text: qsTr("登出")

            contentItem: Text {
                text: qsTr("登出")
                color: window.bgSurface
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

        // 填充剩余空间
        Item { Layout.fillHeight: true }
    }
}
