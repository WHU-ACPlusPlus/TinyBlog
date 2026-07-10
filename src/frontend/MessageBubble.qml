import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtMultimedia

// ═══════════════════════════════════════════════════════
// MessageBubble — 消息气泡组件
// 设计风格：极简主义（style/极简主义.md）
// 令牌：自己气泡 accent白色文字, 对方气泡 bgSurface textPrimary文字
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

    // ── 媒体检测 ──
    readonly property bool hasImage: content.startsWith("data:image/")
    readonly property bool hasVideo: content.startsWith("data:video/")
    // 提取 data URI（"data:<mime>;base64,<b64>"格式）
    readonly property string mediaDataUri: {
        if (!hasImage && !hasVideo) return ""
        var idx = content.indexOf("\n")
        if (idx < 0) idx = content.length
        return content.substring(0, idx)
    }
    // 提取纯文本部分（media 行之后）
    readonly property string textPart: {
        if (!hasImage && !hasVideo) return content
        var idx = content.indexOf("\n")
        if (idx < 0) return ""
        return content.substring(idx + 1).trim()
    }

    // ── 视频辅助属性 ──
    readonly property string videoB64Payload: {
        if (!hasVideo) return ""
        var commaIdx = content.indexOf(";base64,")
        if (commaIdx < 0) return ""
        var nlIdx = content.indexOf("\n")
        var endIdx = nlIdx < 0 ? content.length : nlIdx
        return content.substring(commaIdx + 8, endIdx)
    }
    readonly property string videoExt: {
        if (!hasVideo) return "mp4"
        var slashIdx = content.indexOf("/")
        var semiIdx = content.indexOf(";")
        if (slashIdx < 0 || semiIdx < 0) return "mp4"
        return content.substring(slashIdx + 1, semiIdx)
    }
    property string videoFileUrl: ""     // 临时文件 file:// URL
    property bool videoThumbReady: false
    property string videoThumbB64: ""

    implicitWidth: parent ? parent.width : 300
    implicitHeight: contentLayout.implicitHeight + 18

    // ── 日志 + 视频初始化 ──
    Component.onCompleted: {
        console.log("[MessageBubble] 创建气泡 id=" + messageId +
                    " sender=" + senderName + " isMine=" + isMine +
                    " content_len=" + content.length)
        initVideoIfNeeded()
    }

    // 内容变化时也初始化视频
    onContentChanged: initVideoIfNeeded()

    function initVideoIfNeeded() {
        if (!root.hasVideo || root.videoB64Payload === "") return
        if (root.videoFileUrl !== "") return  // 已初始化

        // 将 base64 写入临时文件（快速，不阻塞）
        var url = api.saveBase64ToTempFile(root.videoB64Payload, root.videoExt)
        if (url === "") {
            console.warn("[MessageBubble] 视频临时文件创建失败")
            return
        }
        root.videoFileUrl = url
        console.log("[MessageBubble] 视频临时文件就绪: " + url.substring(url.lastIndexOf("/") + 1))
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
            color: window.divider
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
                font.pixelSize: 14; color: window.textSecondary
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
                    font.pixelSize: 11; color: window.textSecondary
                    visible: root.senderName !== ""
                }
                Text {
                    text: formatSentTime(root.sentAt)
                    font.pixelSize: 10; color: window.textSecondary
                }
                // 已读标记
                Text {
                    visible: root.isMine
                    text: root.isRead ? "\u2713\u2713" : "\u2713"
                    font.pixelSize: 10
                    color: root.isRead ? window.accent : window.textSecondary
                }
            }

            // 图片预览（在气泡上方）
            Rectangle {
                id: imageContainer
                Layout.alignment: root.isMine ? Qt.AlignRight : Qt.AlignLeft
                Layout.preferredWidth: Math.min(240, (parent ? parent.parent.width : 300) - 80)
                Layout.preferredHeight: visible ? imagePreview.height : 0
                visible: root.hasImage
                radius: 12
                color: window.darkMode ? Qt.rgba(1,1,1,0.04) : Qt.rgba(0,0,0,0.04)
                clip: true
                Image {
                    id: imagePreview
                    source: root.hasImage ? root.mediaDataUri : ""
                    width: parent.width
                    height: visible ? sourceSize.height * parent.width / Math.max(1, sourceSize.width) : 0
                    fillMode: Image.PreserveAspectFit
                    cache: false
                    onStatusChanged: {
                        if (status === Image.Error) console.warn("[MessageBubble] 图片加载失败")
                    }
                }
            }

            // ── 视频播放器 ──
            Rectangle {
                id: videoContainer
                Layout.alignment: root.isMine ? Qt.AlignRight : Qt.AlignLeft
                Layout.preferredWidth: Math.min(240, (parent ? parent.parent.width : 300) - 80)
                Layout.preferredHeight: visible ? Math.min(240 * 9/16, 180) : 0
                visible: root.hasVideo && root.videoFileUrl !== ""
                radius: 12
                color: "#000000"
                clip: true

                // 视频输出层
                VideoOutput {
                    id: videoOutput
                    anchors.fill: parent
                    fillMode: VideoOutput.PreserveAspectFit
                }

                // 缩略图覆盖层（在播放暂停时显示）
                Image {
                    id: videoThumb
                    anchors.fill: parent
                    source: root.videoThumbReady ? "data:image/png;base64," + root.videoThumbB64 : ""
                    fillMode: Image.PreserveAspectFit
                    visible: root.videoThumbReady && mediaPlayer.playbackState !== MediaPlayer.PlayingState
                    cache: false
                }

                // 暗色渐变覆盖（提升按钮可读性）
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop { position: 0.7; color: "#40000000" }
                        GradientStop { position: 1.0; color: "#80000000" }
                    }
                    visible: mediaPlayer.playbackState !== MediaPlayer.PlayingState
                }

                // 中央播放按钮
                Rectangle {
                    anchors.centerIn: parent
                    width: 48; height: 48; radius: 24
                    color: "#ccffffff"
                    visible: mediaPlayer.playbackState !== MediaPlayer.PlayingState
                    Text {
                        anchors.centerIn: parent
                        text: mediaPlayer.playbackState === MediaPlayer.PausedState ? "⏸" : "▶"
                        font.pixelSize: 22
                        color: "#000000"
                    }
                }

                // 进度条
                Rectangle {
                    anchors.bottom: parent.bottom
                    anchors.left: parent.left
                    anchors.right: parent.right
                    height: 3
                    color: "#40ffffff"
                    visible: mediaPlayer.duration > 0
                    Rectangle {
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.bottom: parent.bottom
                        width: mediaPlayer.duration > 0 ? parent.width * mediaPlayer.position / mediaPlayer.duration : 0
                        color: window.accent
                    }
                }

                // 点击交互
                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (mediaPlayer.playbackState === MediaPlayer.PlayingState) {
                            mediaPlayer.pause()
                        } else {
                            mediaPlayer.play()
                        }
                    }
                }

                // 加载中提示
                Text {
                    anchors.centerIn: parent
                    text: "⏳ " + qsTr("加载中...")
                    font.pixelSize: 13; color: "#ffffff"
                    visible: mediaPlayer.status === MediaPlayer.Loading || mediaPlayer.status === MediaPlayer.Buffering
                }
            }

            // 视频未就绪时占位
            Rectangle {
                Layout.alignment: root.isMine ? Qt.AlignRight : Qt.AlignLeft
                Layout.preferredWidth: Math.min(240, (parent ? parent.parent.width : 300) - 80)
                Layout.preferredHeight: visible ? 120 : 0
                visible: root.hasVideo && root.videoFileUrl === ""
                radius: 12
                color: window.darkMode ? Qt.rgba(1,1,1,0.06) : Qt.rgba(0,0,0,0.08)
                border.color: window.darkMode ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.12)
                border.width: 0.5
                Text {
                    anchors.centerIn: parent
                    text: "🎬 " + qsTr("视频加载中...")
                    font.pixelSize: 14; color: window.textSecondary
                }
            }

            // ── 隐藏的 MediaPlayer ──
            MediaPlayer {
                id: mediaPlayer
                source: root.videoFileUrl
                videoOutput: videoOutput
                audioOutput: AudioOutput {
                    volume: 0.8
                }
                onErrorOccurred: function(error, errorString) {
                    console.warn("[MessageBubble] 视频播放错误: " + errorString)
                }
            }

            // 气泡（仅当有文本内容时显示）
            Rectangle {
                id: bubbleBg
                Layout.preferredWidth: Math.min(bubbleText.implicitWidth + 24, (parent ? parent.parent.width : 300) - 80)
                Layout.preferredHeight: bubbleText.implicitHeight + 20
                Layout.alignment: root.isMine ? Qt.AlignRight : Qt.AlignLeft
                visible: root.textPart !== ""
                color: root.isMine
                    ? window.accent
                    : (window.darkMode
                        ? Qt.rgba(1, 1, 1, 0.08)
                        : Qt.rgba(0, 0, 0, 0.04))
                radius: 12

                Rectangle {
                    anchors.fill: parent; radius: 12
                    color: "transparent"
                    border.color: root.isMine
                        ? "transparent"
                        : (window.darkMode
                            ? Qt.rgba(1, 1, 1, 0.12)
                            : Qt.rgba(0, 0, 0, 0.08))
                    border.width: root.isMine ? 0 : 0.5
                }

                Text {
                    id: bubbleText
                    anchors.centerIn: parent
                    width: parent.width - 24
                    // 只对纯文本部分做 Markdown 渲染
                    text: api.markdownToHtml(root.textPart)
                    textFormat: Text.RichText
                    font.pixelSize: 14
                    color: root.isMine ? window.bgSurface : window.textPrimary
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    lineHeight: 1.4
                    onLinkActivated: function(link) {
                        // 拦截 B站视频链接 → 内嵌播放
                        if (link.startsWith("bilibili://")) {
                            var parts = link.substring(11).split("/")  // "bilibili://BVxxx/cid"
                            window.videoPlayBvid = parts[0] || ""
                            window.videoPlayCid = parts[1] || ""
                            console.log("[MessageBubble] 请求内嵌播放 B站: bvid=" + window.videoPlayBvid + " cid=" + window.videoPlayCid)
                            return
                        }
                        Qt.openUrlExternally(link)
                    }
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
