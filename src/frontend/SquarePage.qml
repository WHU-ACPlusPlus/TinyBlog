import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia

Rectangle {
    id: root
    color: window.bgPage

    // ── 状态：normal / publishing ──
    property bool publishing: false
    property string pubError: ""
    property var selectedMedia: []   // 已选媒体文件的 url[]
    property var mediaThumbnails: [] // 对应的缩略图 url[]（视频为抽帧图，图片为原图）

    property int _timeTick: 0

    // ── 定时刷新时间显示 ──
    Timer {
        interval: 60000  // 每分钟刷新一次
        running: visible
        repeat: true
        onTriggered: root._timeTick++
    }

    // ── 辅助判断 ──
    function detectMimeFromBase64(b64) {
        if (!b64) return "image/jpeg"
        var p = b64.substring(0, 6)
        if (p === "iVBORw") return "image/png"
        if (p.substring(0, 4) === "/9j/") return "image/jpeg"
        if (p === "R0lGOD") return "image/gif"
        if (p.substring(0, 4) === "UklGR") return "image/webp"
        if (p.substring(0, 3) === "Qk1") return "image/bmp"
        if (p === "AAAAKG") return "video/mp4"
        if (p === "AAAAFG") return "video/mp4"
        return "image/jpeg"
    }

    function formatTime(utcStr) {
        if (!utcStr) return ""
        // Parse UTC string "2026-07-07 14:30:00" as UTC
        var d = new Date(utcStr + "Z")
        if (isNaN(d.getTime())) return utcStr
        var now = new Date()
        var diffMs = now.getTime() - d.getTime()
        var diffSec = Math.floor(diffMs / 1000)
        if (diffSec < 60) return qsTr("刚刚")
        var diffMin = Math.floor(diffSec / 60)
        if (diffMin < 60) return qsTr("%1 分钟前").arg(diffMin)
        var diffHour = Math.floor(diffMin / 60)
        if (diffHour < 24) return qsTr("%1 小时前").arg(diffHour)
        var diffDay = Math.floor(diffHour / 24)
        if (diffDay < 2) return qsTr("昨天")
        if (diffDay < 7) return qsTr("%1 天前").arg(diffDay)
        // Older: show date
        var month = d.getMonth() + 1
        var day = d.getDate()
        var year = d.getFullYear()
        var curYear = now.getFullYear()
        if (year === curYear) {
            return month + "/" + day
        }
        return year + "/" + month + "/" + day
    }

    function isVideo(url) {
        var s = url.toString().toLowerCase()
        return s.endsWith(".mp4") || s.endsWith(".mov") || s.endsWith(".avi")
    }

    function prepareMediaWithSource(mediaList) {
        if (!mediaList || mediaList.length === 0) return []
        var result = []
        for (var mi = 0; mi < mediaList.length; mi++) {
            var m = mediaList[mi]
            var mime = root.detectMimeFromBase64(m.content)
            var isVideo = mime.substring(0, 5) === "video"
            var source = ""
            if (!isVideo) {
                source = "data:" + mime + ";base64," + m.content
            }
            result.push({
                offset: m.offset !== undefined ? m.offset : mi,
                source: source,
                isVideo: isVideo,
                content: isVideo ? m.content : ""
            })
        }
        return result
    }

    // ── 帖子数据（从 API 获取）──
    property var posts: []
    property int pendingPostCount: 0
    property bool isFetching: false       // 防止重复/交错拉取

    // 增量刷新：暂存新帖直至全部获取完毕
    property var _newPostIds: []           // onTimelineFetched 返回的原始排序
    property var _newPostsMap: ({})        // postId → entry 映射
    property string _refreshHint: ""       // 顶栏刷新提示文字（1秒后自动清除）


    // 乐观更新点赞，创建新对象确保 Repeater 检测到变化
    function toggleLike(postId) {
        for (var i = 0; i < posts.length; i++) {
            if (posts[i].id === postId) {
                var p = posts[i]
                if (p.liked) {
                    var updated = Object.assign({}, p, {
                        liked: false,
                        like_num: Math.max(0, (p.like_num || 0) - 1)
                    })
                    var newPosts = posts.slice()
                    newPosts[i] = updated
                    posts = newPosts
                    api.unlikePost(postId)
                } else {
                    updated = Object.assign({}, p, {
                        liked: true,
                        like_num: (p.like_num || 0) + 1
                    })
                    newPosts = posts.slice()
                    newPosts[i] = updated
                    posts = newPosts
                    api.likePost(postId)
                }
                return
            }
        }
    }

    // ── 普通视图（广场时间线）──
    Rectangle {
        id: normalView
        anchors.fill: parent
        visible: !publishing
        color: window.bgPage

        // ── 辅助刷新函数 ──
        function doRefresh() {
            if (!api.isLoggedIn) return
            // 如果上次获取卡住了（in-flight 请求因错误未返回），重置状态重新开始
            if (root.isFetching) {
                root._newPostIds = []
                root._newPostsMap = ({})
                pendingPostCount = 0
                root.isFetching = false
            }
            root.isFetching = true
            root._newPostIds = []
            root._newPostsMap = ({})
            api.fetchTimeline(20)
        }

        // 顶栏
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 48
            color: window.bgSurface
            z: 1

            Row {
                anchors.fill: parent
                spacing: 0

                Item { width: 48; height: 1 }  // 左侧占位，保持标题居中

                Item {
                    width: parent.width - 96
                    height: parent.height

                    Column {
                        anchors.centerIn: parent
                        spacing: 0

                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: qsTr("广场")
                            font.pixelSize: 18
                            font.bold: true
                            color: window.textPrimary
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: root._refreshHint
                            font.pixelSize: 11
                            color: window.accent
                            visible: text.length > 0
                        }

                    }
                }

                // 刷新按钮
                Rectangle {
                    width: 48
                    height: 48
                    color: "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "🔄"
                        font.pixelSize: 20
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: normalView.doRefresh()
                    }
                }
            }
        }

        // 居中容器
        Item {
            anchors.top: parent.top
            anchors.topMargin: 48
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: Math.max(0, (parent.width - 480) / 2)
            anchors.rightMargin: Math.max(0, (parent.width - 480) / 2)
            clip: true

            // 时间线（Flickable）
            Flickable {
                id: feedFlick
                anchors.fill: parent
                contentWidth: width
                contentHeight: feedCol.implicitHeight + 80
                boundsBehavior: Flickable.DragOverBounds
                clip: true

                Column {
                    id: feedCol
                    width: parent.width
                    spacing: 10
                    topPadding: 10
                    bottomPadding: 70

                    Repeater {
                        model: posts

                        Rectangle {
                            required property var modelData
                            width: parent.width
                            height: postColumn.implicitHeight + 20
                            radius: 10
                            color: window.bgSurface

                            Column {
                                id: postColumn
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 8

                                // ── 头像 + 昵称/用户名 ──
                                Row {
                                    width: parent.width
                                    spacing: 10

                                    Rectangle {
                                        id: avatarBox
                                        width: 40
                                        height: 40
                                        radius: 20
                                        color: window.border

                                        Image {
                                            anchors.fill: parent
                                            fillMode: Image.PreserveAspectCrop
                                            source: modelData.avatar
                                                     ? "data:image/jpeg;base64," + modelData.avatar
                                                     : ""
                                            visible: status === Image.Ready
                                        }

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
                                            text: modelData.nickname[0]
                                            font.pixelSize: 18
                                            color: window.textSecondary
                                            visible: !modelData.avatar
                                        }
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2

                                        Text {
                                            text: modelData.nickname
                                            font.pixelSize: 16
                                            font.bold: true
                                            color: window.textPrimary
                                        }
                                        Text {
                                            text: "@" + modelData.username
                                            font.pixelSize: 12
                                            color: window.textSecondary
                                        }
                                    }
                                }

                                // ── 文本内容 ──
                                Text {
                                    width: parent.width
                                    text: modelData.content
                                    font.pixelSize: 15
                                    color: window.textPrimary
                                    wrapMode: Text.Wrap
                                }

                                // ── 媒体九宫格 ──
                                Grid {
                                    id: mediaGrid
                                    visible: modelData.media && modelData.media.length > 0
                                    width: parent.width
                                    columns: 3
                                    columnSpacing: 4
                                    rowSpacing: 4

                                    Repeater {
                                        model: modelData.media

                                        Rectangle {
                                            required property var modelData
                                            property real cellSize: (mediaGrid.width - mediaGrid.columnSpacing * (mediaGrid.columns - 1)) / mediaGrid.columns
                                            width: cellSize
                                            height: cellSize
                                            radius: 6
                                            clip: true
                                            color: modelData.source ? "#000" : window.divider

                                            Image {
                                                anchors.fill: parent
                                                source: modelData.source || ""
                                                fillMode: Image.PreserveAspectCrop
                                                visible: modelData.source.length > 0
                                                layer.mipmap: true
                                            }

                                            Text {
                                                anchors.centerIn: parent
                                                text: "📷"
                                                font.pixelSize: 18
                                                color: window.textSecondary
                                                visible: !modelData.source || modelData.source.length === 0
                                            }

                                            // 视频三角图标
                                            Rectangle {
                                                anchors.bottom: parent.bottom
                                                anchors.right: parent.right
                                                anchors.margins: 4
                                                width: 22
                                                height: 22
                                                radius: 11
                                                color: "#80000000"
                                                visible: modelData.isVideo

                                                Text {
                                                    anchors.centerIn: parent
                                                    anchors.leftMargin: 2
                                                    text: "▶"
                                                    font.pixelSize: 11
                                                    color: window.bgSurface
                                                }
                                            }

                                            // 点击查看大图
                                            MouseArea {
                                                anchors.fill: parent
                                                visible: modelData.source && modelData.source.length > 0
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    mediaViewer.viewerSource = modelData.source
                                                    mediaViewer.viewerIsVideo = modelData.isVideo || false
                                                    mediaViewer.viewerContent = modelData.isVideo ? (modelData.content || "") : ""
                                                    mediaViewer.visible = true
                                                }
                                            }

                                            // 点击查看大图
                                            MouseArea {
                                                anchors.fill: parent
                                                visible: modelData.source && modelData.source.length > 0
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    mediaViewer.viewerSource = modelData.source
                                                    mediaViewer.viewerIsVideo = modelData.isVideo || false
                                                    mediaViewer.viewerContent = modelData.isVideo ? (modelData.content || "") : ""
                                                    mediaViewer.visible = true
                                                }
                                            }
                                        }
                                    }
                                }

                                // ── 日期 + 点赞 ──
                                Row {
                                    width: parent.width
                                    spacing: 6

                                    Text {
                                        text: {
                root._timeTick;  // bind to tick so it refreshes
                return root.formatTime(modelData.created_at)}
                                        font.pixelSize: 12
                                        color: window.textSecondary
                                        anchors.verticalCenter: parent.verticalCenter
                                    }

                                    Item { width: 1; height: 1; Layout.fillWidth: true }

                                    // 点赞按钮
                                    Rectangle {
                                        width: 32
                                        height: 26
                                        radius: 13
                                        color: modelData.liked ? "#ffe0e0" : "transparent"
                                        anchors.verticalCenter: parent.verticalCenter

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.liked ? "❤️" : "🤍"
                                            font.pixelSize: 14
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: root.toggleLike(modelData.id)
                                        }
                                    }

                                    Text {
                                        text: String(modelData.like_num || 0)
                                        font.pixelSize: 13
                                        color: window.textSecondary
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                // ── 评论区底框 ──
                                Rectangle {
                                    id: commentSection
                                    width: parent.width
                                    height: commentsCol.implicitHeight + 16
                                    radius: 8
                                    color: window.bgCard

                                    Column {
                                        id: commentsCol
                                        x: 8
                                        y: 8
                                        width: parent.width - 16
                                        spacing: 8

                                        // 评论输入框 + 发送按钮
                                        Row {
                                            width: parent.width
                                            height: 32
                                            spacing: 6

                                            Rectangle {
                                                width: parent.width - 40 - 6
                                                height: 32
                                                radius: 6
                                                color: window.bgSurface
                                                border.color: window.textOnDark
                                                border.width: 1

                                                TextInput {
                                                    id: commentInput
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 8
                                                    anchors.rightMargin: 8
                                                    verticalAlignment: Text.AlignVCenter
                                                    font.pixelSize: 13
                                                    color: window.textPrimary
                                                }

                                                Text {
                                                    anchors.left: parent.left
                                                    anchors.leftMargin: 8
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: qsTr("写评论...")
                                                    font.pixelSize: 13
                                                    color: window.textSecondary
                                                    visible: commentInput.text.length === 0
                                                }
                                            }

                                            Rectangle {
                                                width: 40
                                                height: 32
                                                radius: 6
                                                color: window.accent

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: qsTr("发送")
                                                    font.pixelSize: 12
                                                    color: window.bgSurface
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    onClicked: {
                                                        var txt = commentInput.text.trim()
                                                        if (!txt) return
                                                        commentInput.text = ""
                                                        var postId = modelData.id
                                                        // 在 root.posts 数组中按 ID 设置标记，
                                                        // 因为 Repeater 的 modelData 可能是副本
                                                        for (var pi = 0; pi < root.posts.length; pi++) {
                                                            if (root.posts[pi].id === postId) {
                                                                root.posts[pi]._pendingCommentRefresh = true
                                                                root.posts[pi]._commentsLoading = true
                                                                break
                                                            }
                                                        }
                                                        api.comment(postId, txt)
                                                    }
                                                }
                                            }
                                        }

                                        // 评论加载按钮
                                        Text {
                                            text: modelData.comments && modelData.comments.length > 0
                                                   ? "🧵 %1 条评论".arg(modelData.comments.length)
                                                   : "💬 加载评论"
                                            font.pixelSize: 12
                                            color: window.accent
                                            visible: !modelData._commentsLoading

                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    var postId = modelData.id
                                                    for (var pi = 0; pi < root.posts.length; pi++) {
                                                        if (root.posts[pi].id === postId) {
                                                            root.posts[pi]._commentsLoading = true
                                                            break
                                                        }
                                                    }
                                                    api.fetchComments(postId)
                                                }
                                            }
                                        }

                                        // 评论列表
                                        Repeater {
                                            model: modelData.comments || []

                                            Rectangle {
                                                required property var modelData
                                                width: parent.width
                                                height: 24
                                                color: "transparent"

                                                                 Text {
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: "<b>" + modelData.nickname + "</b> " + modelData.content
                                                    font.pixelSize: 12
                                                    color: window.textPrimary
                                                    elide: Text.ElideRight
                                                    width: parent.width
                                                    wrapMode: Text.Wrap
                                                    maximumLineCount: 2
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

        // ── 悬浮发布按钮 ──
        Rectangle {
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 20
            width: 52
            height: 52
            radius: 26
            color: window.accent
            z: 2

            Text {
                anchors.centerIn: parent
                text: "+"
                color: window.bgSurface
                font.pixelSize: 30
                font.bold: true
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    pubError = ""
                    publishing = true
                }
            }
        }
    }

    // ── 发布视图 ──
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        visible: publishing

        // 顶栏（固定，不随滚动移动）
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 48
            color: window.bgSurface

            RowLayout {
                anchors.fill: parent
                spacing: 0

                // 返回按钮
                Rectangle {
                    Layout.preferredWidth: 48
                    Layout.preferredHeight: 48
                    color: "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "←"
                        font.pixelSize: 22
                        color: window.accent
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: publishing = false
                    }
                }

                // 标题
                Text {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    verticalAlignment: Text.AlignVCenter
                    text: qsTr("发布帖子")
                    font.pixelSize: 18
                    font.bold: true
                    color: window.textPrimary
                }

                // 错误提示
                Text {
                    visible: pubError !== ""
                    text: pubError
                    color: "red"
                    font.pixelSize: 11
                    Layout.alignment: Qt.AlignVCenter
                    Layout.rightMargin: 6
                }

                // 发布按钮
                Rectangle {
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignVCenter
                    Layout.rightMargin: 12
                    radius: 6
                    color: window.accent

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("发布")
                        color: window.bgSurface
                        font.pixelSize: 14
                        font.bold: true
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (!textInput.text.trim() && selectedMedia.length === 0) {
                                pubError = "请输入文字或选择媒体"
                                return
                            }
                            pubError = ""

                            // 将已选媒体转为 base64
                            var b64List = []
                            for (var i = 0; i < selectedMedia.length; i++)
                                b64List.push(api.readFileAsBase64(selectedMedia[i]))

                            api.publishPost(textInput.text, b64List)
                        }
                    }
                }
            }
        }

        // ── 可滚动内容区 ──
        ScrollView {
            id: publishScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: publishScroll.availableWidth
                spacing: 0

                // ── 文本输入区 ──
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 200
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    Layout.topMargin: 10
                    color: window.bgSurface
                    radius: 8
                    border.color: window.border
                    border.width: 1

                    TextArea {
                        id: textInput
                        anchors.fill: parent
                        anchors.margins: 12
                        placeholderText: qsTr("分享你的想法……")
                        placeholderTextColor: window.textSecondary
                        font.pixelSize: 16
                        color: window.textPrimary
                        wrapMode: TextEdit.Wrap
                        focus: false
                    }
                }

                // ── 多媒体选择区（方形九宫格）──
                GridLayout {
                    id: publishMediaGrid
                    Layout.fillWidth: false
                    Layout.preferredWidth: (publishScroll.availableWidth - 24) * 2 / 3
                    Layout.preferredHeight: publishMediaGrid.width
                    Layout.leftMargin: 12
                    Layout.topMargin: 10
                    Layout.bottomMargin: 12
                    columns: 3
                    rowSpacing: 8
                    columnSpacing: 8

                    Repeater {
                        model: 9

                        Rectangle {
                            required property int index

                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.preferredWidth: 1
                            Layout.preferredHeight: 1
                            radius: 8
                            clip: true
                            color: index < selectedMedia.length
                                   ? "transparent" : window.divider

                            // 已选媒体缩略图（图片原图 / 视频抽帧）
                            Image {
                                anchors.fill: parent
                                visible: index < selectedMedia.length
                                source: (index < selectedMedia.length && mediaThumbnails[index])
                                        ? mediaThumbnails[index] : ""
                                fillMode: Image.PreserveAspectCrop
                            }

                            // 视频盖一个三角图标
                            Rectangle {
                                anchors.bottom: parent.bottom
                                anchors.right: parent.right
                                anchors.margins: 4
                                width: 22
                                height: 22
                                radius: 11
                                color: "#80000000"
                                visible: index < selectedMedia.length
                                        && isVideo(selectedMedia[index])

                                Text {
                                    anchors.centerIn: parent
                                    anchors.leftMargin: 2
                                    text: "▶"
                                    font.pixelSize: 11
                                    color: window.bgSurface
                                }
                            }

                            // 删除按钮
                            Rectangle {
                                anchors.top: parent.top
                                anchors.right: parent.right
                                anchors.margins: 4
                                width: 20
                                height: 20
                                radius: 10
                                color: "#cc3333"
                                visible: index < selectedMedia.length

                                Text {
                                    anchors.centerIn: parent
                                    text: "✕"
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: window.bgSurface
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: {
                                        var newUrls = []
                                        var newThumbs = []
                                        for (var j = 0; j < selectedMedia.length; j++) {
                                            if (j !== index) {
                                                newUrls.push(selectedMedia[j])
                                                newThumbs.push(mediaThumbnails[j])
                                            }
                                        }
                                        selectedMedia = newUrls
                                        mediaThumbnails = newThumbs
                                    }
                                }
                            }

                            // 加号按钮：仅在下一个空位显示
                            Rectangle {
                                anchors.fill: parent
                                visible: index === selectedMedia.length
                                         && selectedMedia.length < 9
                                color: "transparent"

                                Text {
                                    anchors.centerIn: parent
                                    text: "+"
                                    font.pixelSize: 28
                                    font.bold: true
                                    color: window.textSecondary
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: mediaPicker.open()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── 文件选择器 ──
    FileDialog {
        id: mediaPicker
        title: qsTr("选择媒体文件")
        fileMode: FileDialog.OpenFiles
        nameFilters: [
            "图片 / 视频 (*.jpg *.jpeg *.png *.mp4)"
        ]

        onAccepted: {
            var newUrls = []
            var newThumbs = []
            for (var i = 0; i < selectedFiles.length; i++) {
                if (newUrls.length >= 9) break
                var url = selectedFiles[i]
                newUrls.push(url)
                if (isVideo(url)) {
                    var thumb = api.generateVideoThumbnail(url)
                    newThumbs.push(thumb.toString() !== "" ? thumb : url)
                } else {
                    newThumbs.push(url)
                }
            }
            selectedMedia = selectedMedia.concat(newUrls).slice(0, 9)
            mediaThumbnails = mediaThumbnails.concat(newThumbs).slice(0, 9)
        }
    }

    // ── 刷新提示自动清除定时器 ──
    Timer {
        id: refreshHintTimer
        interval: 1000
        running: false
        repeat: false
        onTriggered: root._refreshHint = ""
    }

    // ── API 信号处理 ──
    Connections {
        target: api

        function onPostPublished() {
            // 发布成功 → 回到广场视图，清空输入
            publishing = false
            textInput.text = ""
            selectedMedia = []
            mediaThumbnails = []
            pubError = ""
        }

        function onErrorOccurred(msg) {
            pubError = msg
            // 获取帖子过程中出错 → 跳过这个失败的帖子，继续等待剩余的
            if (isFetching && pendingPostCount > 0) {
                pendingPostCount--
                if (pendingPostCount <= 0) {
                    finishRefresh()
                }
            }
        }

        function onTimelineFetched(postIds, count) {
            // 只拉取尚未加载的帖子
            var existingIds = {}
            for (var i = 0; i < posts.length; i++)
                existingIds[posts[i].id] = true

            var newIds = []
            for (var i = 0; i < postIds.length; i++) {
                if (!existingIds[postIds[i]])
                    newIds.push(postIds[i])
            }

            _newPostIds = newIds
            pendingPostCount = newIds.length
            for (var i = 0; i < newIds.length; i++)
                api.getPost(newIds[i])
            if (pendingPostCount === 0) {
                root._refreshHint = qsTr("暂时没有新帖子")
                refreshHintTimer.restart()
                isFetching = false
            }
        }

        function onPostFetched(post) {
            // 跳过过时响应
            if (!isFetching) {
                return
            }

            // post 是 QVariantMap → QML 中为 JS 对象
            var entry = {
                id: post.id,
                publisher_id: post.publisher_id,
                username: post.username,
                nickname: post.nickname,
                content: post.content || "",
                like_num: post.like_num || 0,
                created_at: post.created_at || "",
                media: root.prepareMediaWithSource(post.media),
                liked: post.liked === true,
                avatar: "",
                comments: [],
                _commentsLoading: false,
                _pendingCommentRefresh: false
            }
            // 暂存到映射中，等待全部获取完毕后按序合并到列表顶部
            // 拉取发帖人头像
            api.fetchAvatar(post.publisher_id)
            _newPostsMap[post.id] = entry
            if (pendingPostCount > 0)
                pendingPostCount--
            if (pendingPostCount <= 0) {
                finishRefresh()
            }
        }

        function onAvatarFetched(userId, avatar, signature) {
            // 遍历所有帖子，更新该用户的头像
            for (var i = 0; i < posts.length; i++) {
                if (posts[i].publisher_id === userId && posts[i].avatar !== avatar) {
                    var updated = Object.assign({}, posts[i], {avatar: avatar})
                    var newPosts = posts.slice()
                    newPosts[i] = updated
                    posts = newPosts
                }
            }
        }

        function finishRefresh() {
            var ordered = []
            for (var i = 0; i < _newPostIds.length; i++) {
                var e = _newPostsMap[_newPostIds[i]]
                if (e) ordered.push(e)
            }
            posts = ordered.concat(posts)

            // 为所有视频异步提取缩略图
            for (var pi = 0; pi < ordered.length; pi++) {
                var postEntry = ordered[pi]
                if (postEntry.media) {
                    for (var mi = 0; mi < postEntry.media.length; mi++) {
                        if (postEntry.media[mi].isVideo && postEntry.media[mi].content) {
                            api.extractVideoThumbnailAsync(
                                String(postEntry.id),
                                mi,
                                postEntry.media[mi].content
                            )
                        }
                    }
                }
            }

            if (ordered.length > 0)
                root._refreshHint = qsTr("刷新了 %1 条帖子").arg(ordered.length)
            else
                root._refreshHint = qsTr("暂时没有新帖子")
            refreshHintTimer.restart()

            isFetching = false
            _newPostIds = []
            _newPostsMap = ({})
        }

        function onPostLiked() {
            // 乐观更新已完成，无需额外操作
        }

        function onPostUnliked() {
            // 乐观更新已完成
        }

        function onCommentPosted() {
            for (var i = 0; i < posts.length; i++) {
                if (posts[i]._pendingCommentRefresh) {
                    posts[i]._pendingCommentRefresh = false
                    api.fetchComments(posts[i].id)
                    return
                }
            }
        }

        function onCommentsFetched(comments) {
            if (comments.length > 0)
            for (var i = 0; i < posts.length; i++) {
                if (posts[i]._commentsLoading) {
                    var arr = []
                    for (var j = 0; j < comments.length; j++) {
                        arr.push({
                            id: comments[j].id,
                            nickname: comments[j].nickname,
                            content: comments[j].content
                        })
                    }
                    var updated = Object.assign({}, posts[i], {
                        comments: arr,
                        _commentsLoading: false
                    })
                    var newPosts = posts.slice()
                    newPosts[i] = updated
                    posts = newPosts
                    return
                }
            }
        }

        function onLoggedInChanged() {
            if (!api.isLoggedIn) {
                // 登出后清空所有用户数据，防止不同用户串台
                posts = []
                _newPostIds = []
                _newPostsMap = ({})
                publishing = false
                textInput.text = ""
                selectedMedia = []
                mediaThumbnails = []
                pubError = ""
            }
        }

        function onVideoThumbnailExtracted(postId, mediaIndex, thumbnailB64) {
            if (!thumbnailB64) return
            var pid = Number(postId)
            var mi = Number(mediaIndex)
            for (var i = 0; i < root.posts.length; i++) {
                if (root.posts[i].id === pid) {
                    var p = root.posts[i]
                    if (!p.media || mi >= p.media.length) break
                    var newMedia = p.media.slice()
                    newMedia[mi] = Object.assign({}, newMedia[mi], {
                        source: "data:image/png;base64," + thumbnailB64
                    })
                    var newPosts = root.posts.slice()
                    newPosts[i] = Object.assign({}, p, { media: newMedia })
                    root.posts = newPosts
                    return
                }
            }
        }
    }

    // ── 全屏媒体查看器 ──
    Rectangle {
        id: mediaViewer
        anchors.fill: parent
        visible: false
        color: "#e0000000"
        z: 200
        focus: visible

        property string viewerSource: ""
        property bool viewerIsVideo: false
        property string viewerContent: ""   // 视频 base64 原始数据
        property real zoomLevel: 1.0
        property string viewerTempFile: ""  // 视频临时文件路径

        // Esc 关闭
        Keys.onEscapePressed: visible = false

        // 打开时处理视频
        onVisibleChanged: {
            if (!visible) {
                // 关闭时清理
                if (videoPlayer.playbackState !== MediaPlayer.StoppedState)
                    videoPlayer.stop()
                if (viewerTempFile) {
                    // QML 无法直接删文件，交给下次打开覆盖
                    viewerTempFile = ""
                }
            } else if (viewerIsVideo && viewerContent) {
                // 打开视频时保存并开始播放
                var url = api.saveBase64ToTempFile(viewerContent, "mp4")
                if (url) {
                    viewerTempFile = url
                    videoPlayer.source = url
                    videoPlayer.audioOutput.volume = 1.0
                    videoPlayer.play()
                }
            }
        }

        // 点击空白区关闭（图片支持缩放，视频不缩放）
        MouseArea {
            id: viewerBg
            anchors.fill: parent
            enabled: !mediaViewer.viewerIsVideo
            onClicked: mediaViewer.visible = false

            onWheel: function(wheel) {
                if (mediaViewer.viewerIsVideo) return
                var oldZoom = mediaViewer.zoomLevel
                var factor = wheel.angleDelta.y > 0 ? 1.15 : 0.87
                var newZoom = Math.max(1.0, Math.min(5.0, oldZoom * factor))
                if (oldZoom === newZoom) { wheel.accepted = true; return }

                var mx = wheel.x - viewerContainer.x
                var my = wheel.y - viewerContainer.y
                var ratio = newZoom / oldZoom

                var baseW = viewerContainer.baseW
                var baseH = viewerContainer.baseH
                var cw = viewerContainer.width
                var ch = viewerContainer.height
                var cxOld = (cw - baseW * oldZoom) / 2
                var cyOld = (ch - baseH * oldZoom) / 2
                var cxNew = (cw - baseW * newZoom) / 2
                var cyNew = (ch - baseH * newZoom) / 2

                var relX = mx - (cxOld + viewerImg.panX)
                var relY = my - (cyOld + viewerImg.panY)

                viewerImg.panX = mx - cxNew - relX * ratio
                viewerImg.panY = my - cyNew - relY * ratio

                mediaViewer.zoomLevel = newZoom
                wheel.accepted = true
            }
        }

        // 关闭按钮
        Rectangle {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.margins: 16
            width: 36
            height: 36
            radius: 18
            color: "#80000000"
            z: 10

            Text {
                anchors.centerIn: parent
                text: "✕"
                font.pixelSize: 20
                color: window.bgSurface
            }

            MouseArea {
                anchors.fill: parent
                onClicked: mediaViewer.visible = false
            }
        }

        // ── 图片查看模式 ──
        Item {
            id: viewerContainer
            anchors.fill: parent
            anchors.margins: 10
            clip: true
            visible: !mediaViewer.viewerIsVideo

            readonly property real baseW: Math.min(viewerContainer.width, viewerImg.implicitWidth)
            readonly property real baseH: Math.min(viewerContainer.height, viewerImg.implicitHeight)
            property real renderW: baseW * mediaViewer.zoomLevel
            property real renderH: baseH * mediaViewer.zoomLevel

            Image {
                id: viewerImg
                source: mediaViewer.viewerSource
                asynchronous: true
                fillMode: Image.PreserveAspectFit
                width: viewerContainer.renderW
                height: viewerContainer.renderH

                property real panX: 0
                property real panY: 0
                x: (viewerContainer.width - width) / 2 + panX
                y: (viewerContainer.height - height) / 2 + panY

                DragHandler {
                    id: imgDrag
                    target: null
                    enabled: mediaViewer.zoomLevel > 1.01
                    onTranslationChanged: function(delta) {
                        viewerImg.panX += delta.x
                        viewerImg.panY += delta.y
                    }
                }
            }

            TapHandler {
                id: viewerTap
                onTapped: {
                    if (awaitDouble.running) {
                        awaitDouble.stop()
                        if (mediaViewer.zoomLevel > 1.0)
                            mediaViewer.zoomLevel = 1.0
                        else
                            mediaViewer.zoomLevel = 2.5
                    } else {
                        awaitDouble.restart()
                    }
                }
            }

            Timer {
                id: awaitDouble
                interval: 200
                onTriggered: mediaViewer.visible = false
            }

            PinchHandler {
                minimumScale: 1.0
                maximumScale: 5.0
                onScaleChanged: {
                    mediaViewer.zoomLevel = Math.max(1.0, Math.min(5.0, scale))
                    awaitDouble.stop()
                }
            }
        }

        // ── 视频播放模式 ──
        Item {
            id: videoContainer
            anchors.fill: parent
            anchors.margins: 10
            clip: true
            visible: mediaViewer.viewerIsVideo

            VideoOutput {
                id: videoOutput
                anchors.fill: parent
                fillMode: VideoOutput.PreserveAspectFit
            }

            // 单击视频切换暂停/播放
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    if (videoPlayer.playbackState === MediaPlayer.PlayingState)
                        videoPlayer.pause()
                    else
                        videoPlayer.play()
                }
            }

            // 底部控制栏
            Rectangle {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: 48
                color: "#c0000000"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 8

                    // 暂停/播放
                    Rectangle {
                        Layout.preferredWidth: 32
                        Layout.preferredHeight: 32
                        Layout.alignment: Qt.AlignVCenter
                        radius: 16
                        color: window.bgSurface

                        Text {
                            anchors.centerIn: parent
                            text: videoPlayer.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                            font.pixelSize: 16
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                if (videoPlayer.playbackState === MediaPlayer.PlayingState)
                                    videoPlayer.pause()
                                else
                                    videoPlayer.play()
                            }
                        }
                    }

                    // 播放进度文字
                    Text {
                        Layout.preferredWidth: 110
                        Layout.alignment: Qt.AlignVCenter
                        font.pixelSize: 12
                        font.family: "monospace"
                        color: window.bgSurface
                        text: {
                            var p = Math.floor((videoPlayer.position || 0) / 1000)
                            var d = Math.floor((videoPlayer.duration || 0) / 1000)
                            var pm = Math.floor(p / 60), ps = p % 60
                            var dm = Math.floor(d / 60), ds = d % 60
                            return (pm < 10 ? "0" : "") + pm + ":" + (ps < 10 ? "0" : "") + ps
                                 + " / "
                                 + (dm < 10 ? "0" : "") + dm + ":" + (ds < 10 ? "0" : "") + ds
                        }
                    }

                    // 进度条
                    Slider {
                        id: progressSlider
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        height: 20
                        from: 0
                        to: videoPlayer.duration || 1
                        value: videoPlayer.position
                        onMoved: videoPlayer.position = value

                        background: Rectangle {
                            x: progressSlider.leftPadding
                            y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                            width: progressSlider.availableWidth
                            height: 4
                            radius: 2
                            color: window.textSecondary

                            Rectangle {
                                width: progressSlider.visualPosition * parent.width
                                height: parent.height
                                radius: 2
                                color: window.accent
                            }
                        }

                        handle: Rectangle {
                            x: progressSlider.leftPadding + progressSlider.visualPosition * (progressSlider.availableWidth - width)
                            y: progressSlider.topPadding + progressSlider.availableHeight / 2 - height / 2
                            width: 14
                            height: 14
                            radius: 7
                            color: window.bgSurface
                        }
                    }

                    // 静音按钮
                    Text {
                        Layout.alignment: Qt.AlignVCenter
                        text: "M"
                        font.pixelSize: 18
                        font.bold: true
                        color: videoPlayer.audioOutput.muted ? "#ff4444" : "white"

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                videoPlayer.audioOutput.muted = !videoPlayer.audioOutput.muted
                            }
                        }
                    }

                    // 音量滑块
                    Slider {
                        id: volumeSlider
                        Layout.preferredWidth: 80
                        Layout.alignment: Qt.AlignVCenter
                        height: 20
                        from: 0
                        to: 1.0
                        value: videoPlayer.audioOutput.volume
                        onMoved: videoPlayer.audioOutput.volume = value

                        background: Rectangle {
                            x: volumeSlider.leftPadding
                            y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                            width: volumeSlider.availableWidth
                            height: 4
                            radius: 2
                            color: window.textSecondary

                            Rectangle {
                                width: volumeSlider.visualPosition * parent.width
                                height: parent.height
                                radius: 2
                                color: window.bgSurface
                            }
                        }

                        handle: Rectangle {
                            x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                            y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                            width: 14
                            height: 14
                            radius: 7
                            color: window.bgSurface
                        }
                    }
                }
            }
        }

        // ── 媒体播放器（全局唯一，视频模式才激活）──
        MediaPlayer {
            id: videoPlayer
            videoOutput: videoOutput
            audioOutput: AudioOutput {}
        }
    }
}
