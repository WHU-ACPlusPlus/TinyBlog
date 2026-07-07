import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: root
    color: "#f5f5f5"

    // ── 状态：normal / publishing ──
    property bool publishing: false
    property string pubError: ""
    property var selectedMedia: []   // 已选媒体文件的 url[]
    property var mediaThumbnails: [] // 对应的缩略图 url[]（视频为抽帧图，图片为原图）

    // ── 辅助判断 ──
    function isVideo(url) {
        var s = url.toString().toLowerCase()
        return s.endsWith(".mp4") || s.endsWith(".mov") || s.endsWith(".avi")
    }

    // 从 base64 前几个字节推断 MIME 类型
    function detectMimeFromBase64(b64) {
        if (!b64 || b64.length < 4) return "image/jpeg"
        var p = b64.substring(0, 4)
        if (p === "/9j/") return "image/jpeg"
        if (p === "iVBOR") return "image/png"
        if (p === "R0lGOD") return "image/gif"
        if (p === "UklGR") return "image/webp"
        if (p === "AAAA") return "video/mp4"
        return "image/jpeg"
    }

    // 为媒体数组生成 data URI 数据源
    function prepareMediaWithSource(mediaList) {
        console.log("MEDIA: prepareMediaWithSource called, length=", mediaList ? mediaList.length : "null")
        if (!mediaList || mediaList.length === 0) {
            console.log("MEDIA: empty/null, returning []")
            return []
        }
        var result = []
        for (var mi = 0; mi < mediaList.length; mi++) {
            var m = mediaList[mi]
            var b64 = m.content || ""
            console.log("MEDIA: item", mi, "content len=", b64.length, "offset=", m.offset)
            var mime = root.detectMimeFromBase64(b64)
            var isVideo = mime.substring(0, 5) === "video"
            var source = ""
            if (isVideo) {
                // 视频：调用 C++ 方法提取缩略图（同步，单次调用约 100-500ms）
                var thumb = api.videoThumbnailFromBase64(b64)
                if (thumb && thumb.length > 0)
                    source = "data:image/png;base64," + thumb
            } else {
                source = "data:" + mime + ";base64," + b64
            }
            result.push({
                offset: m.offset !== undefined ? m.offset : mi,
                source: source,
                isVideo: isVideo
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
    property string _refreshHint: ""       // 顶栏刷新提示文字（3秒后自动清除）


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
        color: "#f5f5f5"

        // ── 辅助刷新函数 ──
        function doRefresh() {
            console.log("DEBUG: refreshing timeline...")
            if (!api.isLoggedIn) return
            // 如果上次获取卡住了（in-flight 请求因错误未返回），重置状态重新开始
            if (root.isFetching) {
                console.log("WARNING: previous fetch was stuck, force-resetting")
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
            color: "white"
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
                            text: "广场"
                            font.pixelSize: 18
                            font.bold: true
                            color: "#333"
                        }
                        Text {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: root._refreshHint
                            font.pixelSize: 11
                            color: "#4a8cf7"
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

            // 时间线（Flickable + 下拉刷新）
            Flickable {
                id: feedFlick
                anchors.fill: parent
                contentWidth: width
                contentHeight: feedCol.implicitHeight + 80
                boundsBehavior: Flickable.DragOverBounds
                clip: true

                // 下拉刷新指示器
                Rectangle {
                    width: parent.width
                    height: 60
                    y: -60 + Math.min(0, feedFlick.contentY)
                    color: "#f5f5f5"

                    Text {
                        anchors.centerIn: parent
                        text: feedFlick.contentY < -50 ? "释放刷新" : "下拉刷新"
                        color: "#888"
                        font.pixelSize: 14
                    }
                }

                Column {
                    id: feedCol
                    y: Math.max(0, -feedFlick.contentY)
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
                            color: "white"

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
                                        width: 40
                                        height: 40
                                        radius: 20
                                        color: "#ddd"

                                        Text {
                                            anchors.centerIn: parent
                                            text: modelData.nickname[0]
                                            font.pixelSize: 18
                                            color: "#888"
                                        }
                                    }

                                    Column {
                                        anchors.verticalCenter: parent.verticalCenter
                                        spacing: 2

                                        Text {
                                            text: modelData.nickname
                                            font.pixelSize: 16
                                            font.bold: true
                                            color: "#222"
                                        }
                                        Text {
                                            text: "@" + modelData.username
                                            font.pixelSize: 12
                                            color: "#888"
                                        }
                                    }
                                }

                                // ── 文本内容 ──
                                Text {
                                    width: parent.width
                                    text: modelData.content
                                    font.pixelSize: 15
                                    color: "#333"
                                    wrapMode: Text.Wrap
                                }

                                // ── 媒体九宫格 ──
                                GridLayout {
                                    property var mediaArr: modelData.media || []
                                    visible: mediaArr.length > 0
                                    width: parent.width
                                    height: visible ? (parent.width - 2 * 4) / 3 * Math.ceil(mediaArr.length / 3) + (Math.ceil(mediaArr.length / 3) - 1) * 4 : 0
                                    columns: 3
                                    rowSpacing: 4
                                    columnSpacing: 4

                                    Repeater {
                                        model: mediaArr

                                        Rectangle {
                                            required property var modelData
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            Layout.preferredWidth: 1
                                            Layout.preferredHeight: 1
                                            radius: 6
                                            clip: true

                                            // 加载中/失败占位（在缩略图后面，缩略图加载后盖住它）
                                            Rectangle {
                                                anchors.fill: parent
                                                color: "#eee"

                                                Column {
                                                    anchors.centerIn: parent
                                                    spacing: 2

                                                    Text {
                                                        anchors.horizontalCenter: parent.horizontalCenter
                                                        text: modelData.isVideo ? "🎬" : "📷"
                                                        font.pixelSize: 18
                                                        color: "#999"
                                                    }
                                                    Text {
                                                        anchors.horizontalCenter: parent.horizontalCenter
                                                        text: modelData.source
                                                              ? (modelData.source.length > 100
                                                                 ? modelData.source.substring(0, 40) + "…"
                                                                 : modelData.source)
                                                              : "空 source"
                                                        font.pixelSize: 7
                                                        color: "#666"
                                                        visible: true
                                                    }
                                                }
                                            }

                                            // 缩略图（加载完成后覆盖占位，视频为 ffmpeg 抽帧）
                                            Image {
                                                anchors.fill: parent
                                                source: modelData.source || ""
                                                fillMode: Image.PreserveAspectCrop
                                                asynchronous: true
                                                visible: status === Image.Ready
                                            }

                                            // 视频播放按钮
                                            Rectangle {
                                                anchors.bottom: parent.bottom
                                                anchors.right: parent.right
                                                anchors.margins: 4
                                                width: 22
                                                height: 22
                                                radius: 11
                                                color: "#80000000"
                                                visible: modelData.isVideo === true

                                                Text {
                                                    anchors.centerIn: parent
                                                    anchors.leftMargin: 2
                                                    text: "▶"
                                                    font.pixelSize: 11
                                                    color: "white"
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
                                        text: modelData.created_at
                                        font.pixelSize: 12
                                        color: "#aaa"
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
                                        color: "#888"
                                        anchors.verticalCenter: parent.verticalCenter
                                    }
                                }

                                // ── 评论区底框 ──
                                Rectangle {
                                    id: commentSection
                                    width: parent.width
                                    height: commentsCol.implicitHeight + 16
                                    radius: 8
                                    color: "#f7f7f7"

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
                                                color: "white"
                                                border.color: "#e0e0e0"
                                                border.width: 1

                                                TextInput {
                                                    id: commentInput
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 8
                                                    anchors.rightMargin: 8
                                                    verticalAlignment: Text.AlignVCenter
                                                    font.pixelSize: 13
                                                    color: "#333"
                                                }

                                                Text {
                                                    anchors.left: parent.left
                                                    anchors.leftMargin: 8
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    text: "写评论..."
                                                    font.pixelSize: 13
                                                    color: "#bbb"
                                                    visible: commentInput.text.length === 0
                                                }
                                            }

                                            Rectangle {
                                                width: 40
                                                height: 32
                                                radius: 6
                                                color: "#4a8cf7"

                                                Text {
                                                    anchors.centerIn: parent
                                                    text: "发送"
                                                    font.pixelSize: 12
                                                    color: "white"
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
                                            color: "#4a8cf7"
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
                                                    color: "#555"
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

                property bool refreshTriggered: false

                onContentYChanged: {
                    if (!refreshTriggered && contentY < -50) {
                        refreshTriggered = true
                        normalView.doRefresh()
                    }
                }

                onMovementEnded: {
                    if (contentY >= 0 && !root.isFetching)
                        refreshTriggered = false
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
            color: "#4a8cf7"
            z: 2

            Text {
                anchors.centerIn: parent
                text: "+"
                color: "white"
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
            color: "white"

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
                        color: "#4a8cf7"
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
                    text: "发布帖子"
                    font.pixelSize: 18
                    font.bold: true
                    color: "#333"
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
                    color: "#4a8cf7"

                    Text {
                        anchors.centerIn: parent
                        text: "发布"
                        color: "white"
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
                    color: "white"
                    radius: 8
                    border.color: "#ddd"
                    border.width: 1

                    TextArea {
                        id: textInput
                        anchors.fill: parent
                        anchors.margins: 12
                        placeholderText: "分享你的想法……"
                        placeholderTextColor: "#bbb"
                        font.pixelSize: 16
                        color: "#000"
                        wrapMode: TextEdit.Wrap
                        focus: false
                    }
                }

                // ── 多媒体选择区（方形九宫格）──
                GridLayout {
                    id: mediaGrid
                    Layout.fillWidth: false
                    Layout.preferredWidth: (publishScroll.availableWidth - 24) * 2 / 3
                    Layout.preferredHeight: mediaGrid.width
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
                                   ? "transparent" : "#eee"

                            // 已选媒体缩略图（图片原图 / 视频抽帧）
                            Image {
                                anchors.fill: parent
                                visible: index < selectedMedia.length
                                source: index < selectedMedia.length
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
                                    color: "white"
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
                                    color: "white"
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
                                    color: "#999"
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
        title: "选择媒体文件"
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
            console.log("API error:", msg)
            pubError = msg
            // 获取帖子过程中出错 → 跳过这个失败的帖子，继续等待剩余的
            if (isFetching && pendingPostCount > 0) {
                console.log("BANNER: error during fetch, skipping one post")
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

            console.log("BANNER: will fetch", newIds.length, "new posts")
            _newPostIds = newIds
            pendingPostCount = newIds.length
            for (var i = 0; i < newIds.length; i++)
                api.getPost(newIds[i])
            if (pendingPostCount === 0) {
                console.log("BANNER: no new posts at all")
                root._refreshHint = "暂时没有新帖子"
                refreshHintTimer.restart()
                isFetching = false
                if (feedFlick.contentY >= 0)
                    feedFlick.refreshTriggered = false
            }
        }

        function onPostFetched(post) {
            // 跳过过时响应
            if (!isFetching) {
                console.log("onPostFetched: stale, dropped")
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
                comments: [],
                _commentsLoading: false,
                _pendingCommentRefresh: false
            }
            // 暂存到映射中，等待全部获取完毕后按序合并到列表顶部
            _newPostsMap[post.id] = entry
            if (pendingPostCount > 0)
                pendingPostCount--
            if (pendingPostCount <= 0) {
                finishRefresh()
            }
        }

        function finishRefresh() {
            var ordered = []
            for (var i = 0; i < _newPostIds.length; i++) {
                var e = _newPostsMap[_newPostIds[i]]
                if (e) ordered.push(e)
            }
            console.log("BANNER: finishRefresh, got", ordered.length, "new posts")
            posts = ordered.concat(posts)

            if (ordered.length > 0)
                root._refreshHint = "刷新了 " + ordered.length + " 条帖子"
            else
                root._refreshHint = "暂时没有新帖子"
            refreshHintTimer.restart()

            isFetching = false
            _newPostIds = []
            _newPostsMap = ({})
            if (feedFlick.contentY >= 0)
                feedFlick.refreshTriggered = false
        }

        function onPostLiked() {
            // 乐观更新已完成，无需额外操作
        }

        function onPostUnliked() {
            // 乐观更新已完成
        }

        function onCommentPosted() {
            console.log("DEBUG onCommentPosted, posts.length:", posts.length)
            for (var i = 0; i < posts.length; i++) {
                console.log("  post", i, "id:", posts[i].id, "pendingRefresh:", posts[i]._pendingCommentRefresh, "commentsLoading:", posts[i]._commentsLoading)
                if (posts[i]._pendingCommentRefresh) {
                    console.log("  -> matched! fetching comments for post", posts[i].id)
                    posts[i]._pendingCommentRefresh = false
                    api.fetchComments(posts[i].id)
                    return
                }
            }
            console.log("  -> nothing found")
        }

        function onCommentsFetched(comments) {
            console.log("DEBUG onCommentsFetched, comments.length:", comments.length, "posts.length:", posts.length)
            if (comments.length > 0)
                console.log("  first comment:", JSON.stringify(comments[0]))
            for (var i = 0; i < posts.length; i++) {
                console.log("  post", i, "id:", posts[i].id, "commentsLoading:", posts[i]._commentsLoading, "pendingRefresh:", posts[i]._pendingCommentRefresh)
                if (posts[i]._commentsLoading) {
                    console.log("  -> matched! updating post", posts[i].id, "with", comments.length, "comments")
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
                    console.log("  -> done, posts[i].comments.length:", arr.length)
                    return
                }
            }
            console.log("  -> nothing matched")
        }

        function onLoggedInChanged() {
            if (!api.isLoggedIn) {
                // 登出后清空发布页状态
                publishing = false
                textInput.text = ""
                selectedMedia = []
                mediaThumbnails = []
                pubError = ""
            }
        }
    }
}
