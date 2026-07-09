import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: root
    color: softUIMode ? "#e8edf2" : (glassMode ? "transparent" : window.bgPage)

    property bool glassMode: false
    property bool softUIMode: false

    // ── 自适应文字颜色 ──
    property color textPrimary:   glassMode ? "#ffffff" : (softUIMode ? "#2d3436" : window.textPrimary)
    property color textSecondary: glassMode ? Qt.rgba(1,1,1,0.65) : (softUIMode ? "#636e72" : window.textSecondary)
    property color textTertiary:  glassMode ? Qt.rgba(1,1,1,0.40) : (softUIMode ? "#888888" : window.textSecondary)
    property var profileData: ({})
    property bool editing: false
    property bool saving: false
    property string newNickname: ""
    property string newAvatar: ""
    property string newAvatarMime: "image/png"
    property string newSignature: ""

    // ── 子页面导航 ──
    property string subPage: "profile"  // "profile" | "posts" | "followers" | "following"
    property var myPosts: []       // 帖子数据列表
    property var myFollowers: []
    property var myFollowees: []

    // ── 进入某个子页面 ──
    function showSubPage(page) {
        subPage = page
        if (page === "posts") {
            loadMyPosts()
        } else if (page === "followers") {
            api.fetchFollowList()
        } else if (page === "following") {
            api.fetchFollowList()
        }
    }

    // 返回个人主页
    function backToProfile() {
        subPage = "profile"
    }

    // ── 加载我的帖子 ──
    function loadMyPosts() {
        var uid = root.profileData.user_id
        if (!uid) return
        api.fetchMyPostsDetail(uid)
    }

    // ── 格式化时间（同 SquarePage） ──
    function formatTime(utcStr) {
        if (!utcStr) return ""
        var d = new Date(utcStr + "Z")
        if (isNaN(d.getTime())) return utcStr
        var now = new Date()
        var diff = (now - d) / 1000
        if (diff < 60) return qsTr("刚刚")
        if (diff < 3600) return Math.floor(diff / 60) + qsTr("分钟前")
        if (diff < 86400) return Math.floor(diff / 3600) + qsTr("小时前")
        var y = d.getFullYear()
        var m = String(d.getMonth() + 1).padStart(2, "0")
        var day = String(d.getDate()).padStart(2, "0")
        var h = String(d.getHours()).padStart(2, "0")
        var min = String(d.getMinutes()).padStart(2, "0")
        if (y === now.getFullYear()) return m + "-" + day + " " + h + ":" + min
        return y + "-" + m + "-" + day
    }

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

    // 每次页面显示时刷新资料（但保存进行中时不刷新，避免竞态条件）
    onVisibleChanged: {
        if (visible && !root.saving) {
            api.fetchProfile()
        }
    }

    // 监听 API 信号
    Connections {
        target: api

        function onProfileFetched(profile) {
            if (root.saving) return
            root.profileData = profile
            root.newNickname = profile.nickname || ""
            root.newSignature = profile.signature || ""
            root.newAvatar = ""
            root.newAvatarMime = root.detectMime(profile.avatar || "")
            root.editing = false
        }

        function onProfileUpdated() {
            root.saving = false
            root.editing = false
            var merged = Object.assign({}, root.profileData)
            if (root.newNickname)
                merged.nickname = root.newNickname
            if (root.newSignature)
                merged.signature = root.newSignature
            if (root.newAvatar)
                merged.avatar = root.newAvatar
            root.profileData = merged
        }

        function onErrorOccurred(message) {
            root.saving = false
            root.editing = false
            console.log("Profile error:", message)
        }

        // ── 帖子列表（一次性拉取完整数据）──
        function onMyPostsFetched(posts) {
            root.myPosts = posts || []
        }

        // ── 关注/粉丝列表 ──
        function onFollowListFetchedForQml(followers, followees) {
            root.myFollowers = followers
            root.myFollowees = followees
        }
    }

    // ── 头像选择对话框 ──
    FileDialog {
        id: avatarPicker
        title: qsTr("选择头像")
        nameFilters: ["图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"]
        onAccepted: {
            var b64 = api.readFileAsBase64(selectedFile, 1048576)
            if (b64.length > 0) {
                var mime = "image/png"
                var path = String(selectedFile).toLowerCase()
                if (path.endsWith(".jpg") || path.endsWith(".jpeg"))
                    mime = "image/jpeg"
                else if (path.endsWith(".gif"))
                    mime = "image/gif"
                else if (path.endsWith(".webp"))
                    mime = "image/webp"
                else if (path.endsWith(".bmp"))
                    mime = "image/bmp"
                root.newAvatarMime = mime
                root.newAvatar = "data:" + mime + ";base64," + b64
            }
        }
    }

    // ── 壁纸选择对话框 ──
    FileDialog {
        id: wallpaperPicker
        title: qsTr("选择聊天壁纸")
        nameFilters: ["图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.bmp)"]
        onAccepted: {
            // 将本地文件路径转为 file:// URL
            var filePath = String(selectedFile)
            // Qt 的 selectedFile 已经是 file:// URL 格式
            api.setWallpaperPath(filePath)
            console.log("[ProfilePage] 壁纸已设置: " + filePath)
        }
    }

    // ── 头像大图预览弹窗 ──
    Popup {
        id: avatarPreview
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        anchors.centerIn: Overlay.overlay
        background: Rectangle { color: "#00000000" }

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

    // ════════════════════════════════════════════════════════════
    // 个人主页视图（subPage === "profile"）
    // ════════════════════════════════════════════════════════════
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        visible: root.subPage === "profile"

        // ── 顶部：头像 + 昵称/用户名 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            color: root.glassMode
                ? Qt.rgba(1, 1, 1, 0.08)
                : window.bgSurface
            radius: 12
            border.color: root.glassMode ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
            border.width: root.glassMode ? 0.5 : 0

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 14

                Item {
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: 64

                    Rectangle {
                        id: avatarBg
                        anchors.fill: parent
                        color: window.textOnDark
                        radius: 32

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
                                    if (!av) return ""
                                    if (av.indexOf("data:") === 0) return av
                                    return "data:" + root.newAvatarMime + ";base64," + av
                                }
                                fillMode: Image.PreserveAspectCrop
                                visible: source.toString().length > 0
                            }
                        }

                        Text {
                            anchors.centerIn: parent
                            text: "👤"
                            font.pixelSize: 32
                            visible: !avatarImg.visible
                        }

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

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 4

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

                    Text {
                        text: "@" + (root.profileData.username || qsTr("用户名"))
                        font.pixelSize: 14
                        color: window.textSecondary
                    }
                }
            }
        }

        // ── 个性签名 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: signatureField.implicitHeight + 24
            color: root.glassMode
                ? Qt.rgba(1, 1, 1, 0.08)
                : window.bgSurface
            radius: 10
            border.color: root.glassMode ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
            border.width: root.glassMode ? 0.5 : 0

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

        // ── 资料统计（可点击进入子页面） ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 60
            color: root.glassMode
                ? Qt.rgba(1, 1, 1, 0.08)
                : window.bgSurface
            radius: 10
            border.color: root.glassMode ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
            border.width: root.glassMode ? 0.5 : 0

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Item { Layout.fillWidth: true }

                // 帖子数（可点击）
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text { text: (root.profileData.post_count ?? "---"); font.bold: true; font.pixelSize: 18; color: root.textPrimary; Layout.alignment: Qt.AlignHCenter }
                        Text { text: qsTr("帖子"); font.pixelSize: 13; color: root.textTertiary; Layout.alignment: Qt.AlignHCenter }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showSubPage("posts")
                    }
                }

                Item { Layout.fillWidth: true }

                // 粉丝数（可点击）
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text { text: (root.profileData.follower_count ?? "---"); font.bold: true; font.pixelSize: 18; color: root.textPrimary; Layout.alignment: Qt.AlignHCenter }
                        Text { text: qsTr("粉丝"); font.pixelSize: 13; color: root.textTertiary; Layout.alignment: Qt.AlignHCenter }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showSubPage("followers")
                    }
                }

                Item { Layout.fillWidth: true }

                // 关注数（可点击）
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    ColumnLayout {
                        anchors.centerIn: parent
                        spacing: 2
                        Text { text: (root.profileData.followee_count ?? "---"); font.bold: true; font.pixelSize: 18; color: root.textPrimary; Layout.alignment: Qt.AlignHCenter }
                        Text { text: qsTr("关注"); font.pixelSize: 13; color: root.textTertiary; Layout.alignment: Qt.AlignHCenter }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showSubPage("following")
                    }
                }

                Item { Layout.fillWidth: true }
            }
        }

        // ── 壁纸设置 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 80
            color: root.glassMode
                ? Qt.rgba(1, 1, 1, 0.08)
                : window.bgSurface
            radius: 10
            border.color: root.glassMode ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
            border.width: root.glassMode ? 0.5 : 0

            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12

                // 壁纸预览缩略图
                Rectangle {
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                    radius: 8
                    color: window.divider
                    clip: true

                    Image {
                        id: wallpaperPreview
                        anchors.fill: parent
                        source: api.wallpaperPath
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        cache: false
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "🖼️"
                        font.pixelSize: 24
                        visible: api.wallpaperPath.length === 0 || wallpaperPreview.status === Image.Error
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        text: qsTr("聊天壁纸")
                        font.pixelSize: 14
                        font.bold: true
                        color: root.textPrimary
                    }
                    Text {
                        text: api.wallpaperPath.length > 0
                              ? qsTr("已设置自定义壁纸")
                              : qsTr("未设置，使用默认背景")
                        font.pixelSize: 12
                        color: root.textTertiary
                        elide: Text.ElideMiddle
                        Layout.fillWidth: true
                    }
                }

                // 清除壁纸按钮（仅在有壁纸时显示）
                Button {
                    Layout.preferredWidth: 60
                    Layout.preferredHeight: 32
                    visible: api.wallpaperPath.length > 0
                    text: qsTr("清除")
                    contentItem: Text {
                        text: parent.text
                        color: "#e55"
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 6
                        color: "transparent"
                        border.color: "#e55"
                        border.width: 1
                    }
                    onClicked: api.clearWallpaper()
                }

                // 选择壁纸按钮
                Button {
                    Layout.preferredWidth: 60
                    Layout.preferredHeight: 32
                    text: qsTr("选择")
                    contentItem: Text {
                        text: parent.text
                        color: window.bgSurface
                        font.pixelSize: 12
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 6
                        color: "#4a90d9"
                    }
                    onClicked: wallpaperPicker.open()
                }
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
                    color: "#4a90d9"
                }
                onClicked: {
                    if (root.editing) {
                        root.saving = true
                        api.updateProfile(
                            root.newNickname !== root.profileData.nickname ? root.newNickname : "",
                            root.newAvatar,
                            root.newSignature !== root.profileData.signature ? root.newSignature : ""
                        )
                    } else {
                        root.editing = true
                        root.newNickname = root.profileData.nickname || ""
                        root.newSignature = root.profileData.signature || ""
                        root.newAvatar = ""
                    }
                }
            }

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
                    root.saving = false
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

        Item { Layout.fillHeight: true }
    }

    // ════════════════════════════════════════════════════════════
    // 子页面：帖子列表（subPage === "posts"）
    // ════════════════════════════════════════════════════════════
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        visible: root.subPage === "posts"

        // 顶部栏：返回按钮 + 标题
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                spacing: 8

                Button {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    flat: true
                    contentItem: Text {
                        text: "←"
                        font.pixelSize: 22
                        color: window.textPrimary
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 18
                        color: mouseArea.containsMouse ? window.divider : "transparent"
                    }
                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.backToProfile()
                    }
                }

                Text {
                    text: qsTr("我的帖子")
                    font.pixelSize: 18
                    font.bold: true
                    color: window.textPrimary
                }

                Item { Layout.fillWidth: true }
            }
        }

        // 帖子列表
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: root.glassMode
                ? Qt.rgba(1, 1, 1, 0.06)
                : window.bgSurface
            radius: 10
            border.color: root.glassMode ? Qt.rgba(1, 1, 1, 0.10) : "transparent"
            border.width: root.glassMode ? 0.5 : 0
            clip: true

            Flickable {
                anchors.fill: parent
                anchors.margins: 2
                contentWidth: width
                contentHeight: postsColumn.implicitHeight + 20
                boundsBehavior: Flickable.DragOverBounds
                clip: true

                Column {
                    id: postsColumn
                    width: parent.width
                    spacing: 8
                    topPadding: 10
                    bottomPadding: 10

                    // 提示
                    Text {
                        width: parent.width
                        text: root.myPosts.length === 0 ? qsTr("暂无帖子") : ""
                        color: window.textSecondary
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        visible: text.length > 0
                        topPadding: 20
                    }

                    // 帖子列表
                    Repeater {
                        model: root.myPosts

                        Rectangle {
                            required property var modelData
                            width: parent.width
                            height: postItemColumn.implicitHeight + 20
                            radius: 8
                            color: window.bgPage

                            Column {
                                id: postItemColumn
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6

                                // 发布者信息
                                Row {
                                    width: parent.width
                                    spacing: 8

                                    Rectangle {
                                        width: 32
                                        height: 32
                                        radius: 16
                                        color: window.border
                                        clip: true
                                        // 「我的帖子」都是当前用户所发，头像即当前用户头像
                                        // （来自 fetchProfile 的 profileData.avatar）
                                        Image {
                                            id: postAvatarImg
                                            anchors.fill: parent
                                            fillMode: Image.PreserveAspectCrop
                                            source: {
                                                var av = root.profileData.avatar || ""
                                                if (!av) return ""
                                                if (av.indexOf("data:") === 0) return av
                                                return "data:image/png;base64," + av
                                            }
                                            visible: status === Image.Ready
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            text: "👤"
                                            font.pixelSize: 16
                                            visible: !postAvatarImg.visible
                                        }
                                    }

                                    Column {
                                        spacing: 2
                                        Text {
                                            text: modelData.nickname || modelData.username || qsTr("用户")
                                            font.pixelSize: 14
                                            font.bold: true
                                            color: window.textPrimary
                                        }
                                        Text {
                                            text: root.formatTime(modelData.created_at || "")
                                            font.pixelSize: 11
                                            color: window.textSecondary
                                        }
                                    }
                                }

                                // 帖子正文
                                Text {
                                    width: parent.width
                                    text: modelData.content || ""
                                    font.pixelSize: 14
                                    color: window.textPrimary
                                    wrapMode: Text.Wrap
                                    lineHeight: 1.4
                                }

                                // 媒体附件（如果有）
                                Row {
                                    spacing: 4
                                    visible: modelData.media && modelData.media.length > 0
                                    Repeater {
                                        model: modelData.media || []
                                        Rectangle {
                                            required property var modelData
                                            width: 120
                                            height: 120
                                            radius: 6
                                            color: window.border
                                            clip: true
                                            Image {
                                                  anchors.fill: parent
                                                  fillMode: Image.PreserveAspectCrop
                                                  source: {
                                                      var m = modelData
                                                      if (typeof m === "object" && m.content)
                                                          return "data:image/jpeg;base64," + m.content
                                                      return ""
                                                  }
                                                  visible: status === Image.Ready
                                              }
                                          }
                                      }
                                  }
                              }
                          }
                      }
                  }
              }
          }
      }

    // ════════════════════════════════════════════════════════════
    // 子页面：粉丝列表（subPage === "followers"）
    // ════════════════════════════════════════════════════════════
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        visible: root.subPage === "followers"

        // 顶部栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                spacing: 8

                Button {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    flat: true
                    contentItem: Text {
                        text: "←"
                        font.pixelSize: 22
                        color: window.textPrimary
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 18
                        color: btnMouse.containsMouse ? window.divider : "transparent"
                    }
                    MouseArea {
                        id: btnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.backToProfile()
                    }
                }

                Text {
                    text: qsTr("粉丝")
                    font.pixelSize: 18
                    font.bold: true
                    color: window.textPrimary
                }

                Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: root.glassMode
                ? Qt.rgba(1, 1, 1, 0.06)
                : window.bgSurface
            radius: 10
            border.color: root.glassMode ? Qt.rgba(1, 1, 1, 0.10) : "transparent"
            border.width: root.glassMode ? 0.5 : 0
            clip: true

            Flickable {
                anchors.fill: parent
                anchors.margins: 2
                contentWidth: width
                contentHeight: followersCol.implicitHeight + 20
                boundsBehavior: Flickable.DragOverBounds
                clip: true

                Column {
                    id: followersCol
                    width: parent.width
                    spacing: 4
                    topPadding: 10
                    bottomPadding: 10

                    Text {
                        width: parent.width
                        text: root.myFollowers.length === 0 ? qsTr("暂无粉丝") : ""
                        color: window.textSecondary
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        visible: text.length > 0
                        topPadding: 20
                    }

                    Repeater {
                        model: root.myFollowers

                        Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 48
                            color: "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                Rectangle {
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    radius: 16
                                    color: window.border
                                    Image {
                                        anchors.fill: parent
                                        fillMode: Image.PreserveAspectCrop
                                        source: modelData.avatar
                                                 ? "data:image/jpeg;base64," + modelData.avatar
                                                 : ""
                                        visible: status === Image.Ready
                                    }
                                    Text {
                                        anchors.centerIn: parent
                                        text: "👤"
                                        font.pixelSize: 16
                                        visible: !parent.children[0].visible
                                    }
                                }

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text {
                                        text: modelData.nickname || modelData.username || qsTr("用户")
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: window.textPrimary
                                    }
                                    Text {
                                        text: "@" + (modelData.username || "")
                                        font.pixelSize: 11
                                        color: window.textSecondary
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ════════════════════════════════════════════════════════════
    // 子页面：关注列表（subPage === "following"）
    // ════════════════════════════════════════════════════════════
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12
        visible: root.subPage === "following"

        // 顶部栏
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                spacing: 8

                Button {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    flat: true
                    contentItem: Text {
                        text: "←"
                        font.pixelSize: 22
                        color: window.textPrimary
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        radius: 18
                        color: followingBtnMouse.containsMouse ? window.divider : "transparent"
                    }
                    MouseArea {
                        id: followingBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.backToProfile()
                    }
                }

                Text {
                    text: qsTr("关注")
                    font.pixelSize: 18
                    font.bold: true
                    color: window.textPrimary
                }

                Item { Layout.fillWidth: true }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: root.glassMode
                ? Qt.rgba(1, 1, 1, 0.06)
                : window.bgSurface
            radius: 10
            border.color: root.glassMode ? Qt.rgba(1, 1, 1, 0.10) : "transparent"
            border.width: root.glassMode ? 0.5 : 0
            clip: true

            Flickable {
                anchors.fill: parent
                anchors.margins: 2
                contentWidth: width
                contentHeight: followingCol.implicitHeight + 20
                boundsBehavior: Flickable.DragOverBounds
                clip: true

                Column {
                    id: followingCol
                    width: parent.width
                    spacing: 4
                    topPadding: 10
                    bottomPadding: 10

                    Text {
                        width: parent.width
                        text: root.myFollowees.length === 0 ? qsTr("暂未关注任何人") : ""
                        color: window.textSecondary
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        visible: text.length > 0
                        topPadding: 20
                    }

                    Repeater {
                        model: root.myFollowees

                        Rectangle {
                            required property var modelData
                            width: parent.width
                            height: 48
                            color: "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10

                                Rectangle {
                                    Layout.preferredWidth: 32
                                    Layout.preferredHeight: 32
                                    radius: 16
                                    color: window.border
                                    Image {
                                        anchors.fill: parent
                                        fillMode: Image.PreserveAspectCrop
                                        source: modelData.avatar
                                                 ? "data:image/jpeg;base64," + modelData.avatar
                                                 : ""
                                        visible: status === Image.Ready
                                    }
                                    Text {
                                        anchors.centerIn: parent
                                        text: "👤"
                                        font.pixelSize: 16
                                        visible: !parent.children[0].visible
                                    }
                                }

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Text {
                                        text: modelData.nickname || modelData.username || qsTr("用户")
                                        font.pixelSize: 14
                                        font.bold: true
                                        color: window.textPrimary
                                    }
                                    Text {
                                        text: "@" + (modelData.username || "")
                                        font.pixelSize: 11
                                        color: window.textSecondary
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
