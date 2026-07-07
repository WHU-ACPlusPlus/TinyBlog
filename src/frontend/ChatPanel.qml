import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// ═══════════════════════════════════════════════════════
// ChatPanel — 聊天区域面板
// 设计风格：极简主义（style/极简主义.md）
// 令牌：背景 #f5f5f5, 气泡圆角 12px, 间距 8px/12px
// 自己气泡 #4a8cf7, 对方气泡 white
// ═══════════════════════════════════════════════════════

Rectangle {
    id: root

    // ── 公开属性 ──
    property var currentConversation: null   // 当前会话数据
    property var messages: []                // 消息列表（从外部绑定，勿直接修改）
    property var _displayMessages: []        // BUG2修复: 内部显示用数组（合并真实消息+乐观消息）
    property bool hasMoreMessages: false     // 是否有更多历史消息
    property int currentUserId: 0            // 当前登录用户ID
    property var userDetailData: null        // 用户详情（来自MessagesPage）
    property var groupDetailData: null       // 群组详情（来自MessagesPage）

    // ── BUG2修复: 监听外部messages变化，同步到_displayMessages ──
    onMessagesChanged: {
        console.log("[ChatPanel] messages绑定更新: " + messages.length + "条, 同步到_displayMessages")
        root._displayMessages = root.messages
    }

    // ── 信号 ──
    signal sendButtonClicked(string text)
    signal backButtonClicked()
    signal infoPanelRequested()

    // ── BUG5修复: 监听群组详情变化，更新成员列表 ──
    onGroupDetailDataChanged: {
        console.log("[ChatPanel] groupDetailData changed: " + JSON.stringify(groupDetailData))
        groupMembersModel.clear()
        // R4 BUG C修复: 改用length检查替代Array.isArray (QVariantList兼容)
        if (groupDetailData && groupDetailData.members && groupDetailData.members.length > 0) {
            for (var i = 0; i < groupDetailData.members.length; i++) {
                var m = groupDetailData.members[i]
                // R4: 增加id有效性检查
                if (m) {
                    groupMembersModel.append({
                        id: m.id || 0,
                        username: m.username || "",
                        nickname: m.nickname || "",
                        avatar: m.avatar || "",
                        role: m.role || "member",
                        joined_at: m.joined_at || ""
                    })
                }
            }
            console.log("[ChatPanel] 群成员列表更新: " + groupMembersModel.count + "人")
        }
    }

    // ── E1修复: 监听用户详情变化，更新私聊面板 ──
    onUserDetailDataChanged: {
        console.log("[ChatPanel] userDetailData changed: " + JSON.stringify(userDetailData))
        if (userDetailData) {
            privateUsername.text = userDetailData.username || ""
            if (userDetailData.is_mutual) {
                privateFollowText.text = qsTr("互相关注（好友）")
            } else if (userDetailData.is_following) {
                privateFollowText.text = qsTr("已关注")
            } else {
                privateFollowText.text = qsTr("+ 关注")
            }
        }
    }

    color: "#f5f5f5"

    // ── 日志 ──
    Component.onCompleted: {
        console.log("[ChatPanel] 面板初始化完成")
    }

    onCurrentConversationChanged: {
        if (currentConversation) {
            console.log("[ChatPanel] 当前会话变更: id=" + currentConversation.id +
                        " type=" + currentConversation.type +
                        " name=" + currentConversation.target_name)
        } else {
            console.log("[ChatPanel] 当前会话清空（无选中）")
        }
    }

    // ── 无选中会话时：空状态 ──
    Rectangle {
        anchors.fill: parent
        color: "#f5f5f5"
        visible: !root.currentConversation

        ColumnLayout {
            anchors.centerIn: parent
            spacing: 16

            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "💬"
                font.pixelSize: 56
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("选择一个会话开始聊天")
                font.pixelSize: 17
                color: "#999"
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: qsTr("从左侧列表选择一个联系人或群组")
                font.pixelSize: 13
                color: "#bbb"
            }
        }
    }

    // ── 有选中会话时：聊天界面 ──
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        visible: root.currentConversation !== null

        // ── 聊天头部栏 ──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            color: "white"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                // 返回按钮（窄屏用）
                Rectangle {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    radius: 16
                    color: backBtnHover.hovered ? "#f0f0f0" : "transparent"
                    visible: typeof root.width !== "undefined" && root.width < 700

                    Text {
                        anchors.centerIn: parent
                        text: "←"
                        font.pixelSize: 18
                        color: "#666"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[ChatPanel] 返回按钮被点击")
                            root.backButtonClicked()
                        }
                    }

                    HoverHandler { id: backBtnHover }
                }

                // 对方头像 36x36
                Rectangle {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    radius: 18
                    color: root.currentConversation && root.currentConversation.type === "group"
                           ? "#c4e0e5" : "#e0e0e0"

                    Text {
                        anchors.centerIn: parent
                        text: root.currentConversation && root.currentConversation.type === "group"
                              ? "👥" : (root.currentConversation && root.currentConversation.target_name
                                       ? root.currentConversation.target_name.charAt(0) : "?")
                        font.pixelSize: root.currentConversation && root.currentConversation.type === "group"
                                       ? 16 : 14
                        color: "#666"
                    }
                }

                // 对方名称
                Text {
                    Layout.fillWidth: true
                    text: root.currentConversation ? (root.currentConversation.target_name || qsTr("未知")) : ""
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    color: "#222"
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                // "⋯" 省略号按钮 → 打开侧边信息面板
                Rectangle {
                    Layout.preferredWidth: 32
                    Layout.preferredHeight: 32
                    radius: 16
                    color: infoBtnHover.hovered ? "#f0f0f0" : "transparent"

                    Text {
                        anchors.centerIn: parent
                        text: "⋯"
                        font.pixelSize: 18
                        font.weight: Font.Bold
                        color: "#666"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[ChatPanel] '⋯' 信息按钮被点击")
                            root.infoPanelRequested()
                            infoDrawer.open()
                        }
                    }

                    HoverHandler { id: infoBtnHover }
                }
            }

            // 底部分隔线
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 0.5
                color: "#e8e8e8"
            }
        }

        // ── 消息列表（Flickable + Column）──
        Flickable {
            id: messageFlickable
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: width
            contentHeight: messageColumn.implicitHeight + 16
            boundsBehavior: Flickable.StopAtBounds
            flickableDirection: Flickable.VerticalFlick

            // 滚动到底部
            function scrollToBottom() {
                contentY = Math.max(0, contentHeight - height)
            }

            Component.onCompleted: {
                console.log("[ChatPanel] 消息Flickable初始化完成")
            }

            ColumnLayout {
                id: messageColumn
                width: parent.width
                spacing: 8
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 8

                // 加载更多历史消息
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.hasMoreMessages ? 32 : 0
                    color: "transparent"
                    visible: root.hasMoreMessages

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("↑ 加载更早的消息")
                        font.pixelSize: 12
                        color: "#4a8cf7"

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                console.log("[ChatPanel] 请求加载更早消息")
                                loadEarlierMessages()
                            }
                        }
                    }
                }

                // BUG2修复: 使用_displayMessages而非直接绑定messages
                Repeater {
                    model: root._displayMessages

                    MessageBubble {
                        Layout.fillWidth: true
                        messageId: modelData.id || 0
                        senderId: modelData.sender_id || 0
                        senderName: modelData.sender_name || ""
                        senderAvatar: modelData.sender_avatar || modelData.avatar || ""  // R4 BUG B
                        content: modelData.content || ""
                        sentAt: modelData.sent_at || ""
                        isMine: modelData.sender_id === root.currentUserId
                        isRead: modelData.is_read !== undefined ? modelData.is_read : true
                    }
                }
            }

            ScrollBar.vertical: ScrollBar {
                policy: ScrollBar.AsNeeded
            }
        }

        // ── 消息列表滚动到底部（消息更新时）──
        Connections {
            target: root
            function onMessagesChanged() {
                console.log("[ChatPanel] 消息变更，滚动到底部")
                messageFlickable.scrollToBottom()
            }
        }

        // ── 输入区（底部）──
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: inputArea.implicitHeight + 16
            color: "white"

            RowLayout {
                id: inputArea
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8
                implicitHeight: Math.min(sendTextArea.implicitHeight + 16, 112)

                // 多行输入框（最大4行）
                ScrollView {
                    Layout.fillWidth: true
                    Layout.preferredHeight: Math.min(sendTextArea.implicitHeight + 8, 88)

                    TextArea {
                        id: sendTextArea
                        font.pixelSize: 14
                        color: "#333"
                        wrapMode: TextArea.Wrap
                        placeholderText: qsTr("输入消息...")
                        placeholderTextColor: "#ccc"
                        background: Rectangle {
                            color: "#f5f5f5"
                            radius: 8
                        }
                        padding: 10
                        clip: true

                        // 日志
                        onTextChanged: {
                            // 不频繁记录文本变更以避免日志泛滥
                            // 仅在发送时记录
                        }

                        // Shift+Enter 换行, Enter 发送
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
                                if (event.modifiers & Qt.ShiftModifier) {
                                    // Shift+Enter: 允许换行（默认行为）
                                    console.log("[ChatPanel] Shift+Enter 换行")
                                } else {
                                    // Enter: 发送
                                    event.accepted = true
                                    console.log("[ChatPanel] Enter 发送消息")
                                    sendMessage()
                                }
                            }
                        }
                    }
                }

                // 发送按钮
                Rectangle {
                    Layout.preferredWidth: 64
                    Layout.preferredHeight: 36
                    Layout.alignment: Qt.AlignBottom
                    radius: 8
                    color: sendBtnHover.hovered ? "#3d7ce8" : "#4a8cf7"

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("发送")
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        color: "white"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[ChatPanel] 发送按钮被点击")
                            sendMessage()
                        }
                    }

                    HoverHandler { id: sendBtnHover }
                }
            }

            // 顶部分隔线
            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 0.5
                color: "#e8e8e8"
            }
        }
    }

    // ═══════════════════════════════════════════════════
    // ── 侧边信息面板（Drawer 从右侧滑入, 300px）──
    // ═══════════════════════════════════════════════════
    Drawer {
        id: infoDrawer
        width: 300
        height: parent.height
        edge: Qt.RightEdge
        dragMargin: 0
        interactive: true

        onOpened: {
            console.log("[ChatPanel] 信息面板已打开")
            // 加载详情
            if (root.currentConversation) {
                if (root.currentConversation.type === "private") {
                    console.log("[ChatPanel] 请求用户详情 user_id=" + root.currentConversation.target_id)
                    api.fetchUserDetail(root.currentConversation.target_id)
                } else {
                    console.log("[ChatPanel] 请求群组详情 group_id=" + root.currentConversation.target_id)
                    api.fetchGroupDetail(root.currentConversation.target_id)
                }
            }
        }

        onClosed: {
            console.log("[ChatPanel] 信息面板已关闭")
        }

        background: Rectangle {
            color: "white"
        }

        // 面板内容
        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // 标题栏
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 48
                color: "#fafafa"

                Text {
                    anchors.centerIn: parent
                    text: qsTr("详情")
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    color: "#333"
                }

                // 底部分隔线
                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 0.5
                    color: "#e8e8e8"
                }
            }

            // ── 私聊面板 ──
            ColumnLayout {
                Layout.fillWidth: true
                Layout.topMargin: 20
                spacing: 12
                visible: root.currentConversation && root.currentConversation.type === "private"

                // 大头像 80x80
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 80
                    radius: 40
                    color: "#e0e0e0"

                    Text {
                        anchors.centerIn: parent
                        text: root.currentConversation && root.currentConversation.target_name
                              ? root.currentConversation.target_name.charAt(0) : "?"
                        font.pixelSize: 32
                        color: "#999"
                    }
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: root.currentConversation ? (root.currentConversation.target_name || "") : ""
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    color: "#222"
                }

                // 用户名（从API获取后显示）
                Text {
                    id: privateUsername
                    Layout.alignment: Qt.AlignHCenter
                    text: ""
                    font.pixelSize: 13
                    color: "#999"
                }

                // 关注状态
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 160
                    Layout.preferredHeight: 36
                    radius: 18
                    color: privateFollowBtnHover.hovered ? "#e8f0fe" : "#f0f7ff"

                    Text {
                        id: privateFollowText
                        anchors.centerIn: parent
                        text: qsTr("+ 关注")
                        font.pixelSize: 13
                        color: "#4a8cf7"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[ChatPanel] 关注按钮被点击")
                            // P2修复: 实现关注/取消关注逻辑
                            if (root.userDetailData && root.currentConversation) {
                                var targetId = root.currentConversation.target_id
                                if (root.userDetailData.is_mutual) {
                                    console.log("[ChatPanel] 已是好友，不操作")
                                } else if (root.userDetailData.is_following) {
                                    console.log("[ChatPanel] 取消关注 user_id=" + targetId)
                                    api.unfollow(targetId)
                                    root.userDetailData.is_following = false
                                    privateFollowText.text = qsTr("+ 关注")
                                } else {
                                    console.log("[ChatPanel] 关注 user_id=" + targetId)
                                    api.follow(targetId)
                                    root.userDetailData.is_following = true
                                    privateFollowText.text = qsTr("已关注")
                                }
                            }
                        }
                    }

                    HoverHandler { id: privateFollowBtnHover }
                }

                // ── E1修复: 用户详情现在由root.userDetailData统一管理 ──

                // 分隔线
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 0.5
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    color: "#eee"
                }

                // "删除会话" 按钮（红色）
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 40
                    Layout.topMargin: 12
                    radius: 8
                    color: deleteBtnHover.hovered ? "#e84040" : "#ff4d4f"

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("删除会话")
                        font.pixelSize: 14
                        color: "white"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[ChatPanel] 删除会话按钮被点击 conv_id=" +
                                        (root.currentConversation ? root.currentConversation.id : -1))
                            if (root.currentConversation) {
                                api.hideConversation(root.currentConversation.id)
                            }
                            infoDrawer.close()
                        }
                    }

                    HoverHandler { id: deleteBtnHover }
                }
            }

            // ── 群聊面板 ──
            ColumnLayout {
                Layout.fillWidth: true
                Layout.topMargin: 20
                spacing: 12
                visible: root.currentConversation && root.currentConversation.type === "group"

                // 群头像 80x80
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 80
                    radius: 40
                    color: "#c4e0e5"

                    Text {
                        anchors.centerIn: parent
                        text: "👥"
                        font.pixelSize: 32
                    }
                }

                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: root.currentConversation ? (root.currentConversation.target_name || "") : ""
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    color: "#222"
                }

                // 群号
                Text {
                    id: groupIdText
                    Layout.alignment: Qt.AlignHCenter
                    text: root.currentConversation ? ("#" + root.currentConversation.target_id) : ""
                    font.pixelSize: 13
                    color: "#999"
                }

                // 分隔线
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 0.5
                    Layout.leftMargin: 20
                    Layout.rightMargin: 20
                    color: "#eee"
                }

                // 群成员标签
                Text {
                    Layout.leftMargin: 20
                    text: qsTr("群成员")
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    color: "#555"
                }

                // 群成员列表
                ListView {
                    id: groupMemberList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 80     // R4 BUG C: 防止Drawer中高度塌缩
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    clip: true
                    model: groupMembersModel

                    delegate: Rectangle {
                        width: groupMemberList.width
                        height: 44
                        color: "transparent"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            spacing: 10

                            Rectangle {
                                Layout.preferredWidth: 32
                                Layout.preferredHeight: 32
                                radius: 16
                                color: "#e0e0e0"

                                Text {
                                    anchors.centerIn: parent
                                    // R5 BUG3: ListModel用直接角色名而非modelData
                                    text: nickname ? nickname.charAt(0) : "?"
                                    font.pixelSize: 12
                                    color: "#888"
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    // R5 BUG3: ListModel用直接角色名
                                    text: nickname || username || ""
                                    font.pixelSize: 13
                                    color: "#333"
                                }

                                Text {
                                    // R5 BUG3: ListModel用直接角色名
                                    text: role === "owner" ? qsTr("群主") :
                                          role === "admin" ? qsTr("管理员") : qsTr("成员")
                                    font.pixelSize: 10
                                    color: "#aaa"
                                }
                            }
                        }
                    }
                }

                ListModel {
                    id: groupMembersModel
                }

                // "退出群聊" 按钮（红色）
                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 200
                    Layout.preferredHeight: 40
                    Layout.topMargin: 12
                    Layout.bottomMargin: 20
                    radius: 8
                    color: leaveBtnHover.hovered ? "#e84040" : "#ff4d4f"

                    Text {
                        anchors.centerIn: parent
                        text: qsTr("退出群聊")
                        font.pixelSize: 14
                        color: "white"
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            console.log("[ChatPanel] 退出群聊按钮被点击 group_id=" +
                                        (root.currentConversation ? root.currentConversation.target_id : -1))
                            if (root.currentConversation) {
                                api.leaveGroup(root.currentConversation.target_id)
                            }
                            infoDrawer.close()
                        }
                    }

                    HoverHandler { id: leaveBtnHover }
                }
            }
        }
    }

    // ── BUG6修复: 乐观更新消息列表 ──
    function sendMessage() {
        var text = sendTextArea.text.trim()
        if (text.length === 0) {
            console.log("[ChatPanel] 消息为空，忽略发送")
            return
        }
        if (!root.currentConversation) {
            console.log("[ChatPanel] 无当前会话，无法发送")
            return
        }

        console.log("[ChatPanel] 发送消息: type=" + root.currentConversation.type +
                    " target_id=" + root.currentConversation.target_id +
                    " text_len=" + text.length)

        // BUG2修复: 乐观追加到_displayMessages（不破坏messages绑定）
        var now = new Date()
        var timeStr = now.getFullYear() + "-" +
                      String(now.getMonth() + 1).padStart(2, '0') + "-" +
                      String(now.getDate()).padStart(2, '0') + " " +
                      String(now.getHours()).padStart(2, '0') + ":" +
                      String(now.getMinutes()).padStart(2, '0') + ":" +
                      String(now.getSeconds()).padStart(2, '0')
        var optimisticMsg = {
            id: -Date.now(),                    // 临时负数ID
            sender_id: root.currentUserId,
            sender_name: "\u6211",              // "我"
            content: text,
            sent_at: timeStr,
            is_read: false
        }
        var newMsgs = root._displayMessages.slice()
        newMsgs.push(optimisticMsg)
        root._displayMessages = newMsgs
        console.log("[ChatPanel] 乐观追加到_displayMessages id=" + optimisticMsg.id + " total=" + newMsgs.length)

        // 清空输入框
        sendTextArea.text = ""

        // 异步发送
        if (root.currentConversation.type === "private") {
            api.sendMessage(root.currentConversation.target_id, text)
        } else if (root.currentConversation.type === "group") {
            api.sendGroupMessage(root.currentConversation.target_id, text)
        }

        console.log("[ChatPanel] API发送请求已发出")
    }

    // ── 加载更早消息 ──
    function loadEarlierMessages() {
        if (!root.currentConversation) return
        if (root.messages.length === 0) return

        var oldestMsg = root.messages[0]  // 数组第一个是最旧的消息
        var beforeId = oldestMsg.id || 0
        console.log("[ChatPanel] 加载更早消息 before_id=" + beforeId)

        if (root.currentConversation.type === "private") {
            api.fetchPrivateMessages(root.currentConversation.target_id, beforeId, 20)
        } else if (root.currentConversation.type === "group") {
            // 群聊历史使用现有的 receiveGroupMessages（目前不支持before_id）
            // TODO: 后端需要增强recv-group-msg支持before_id翻页
            console.log("[ChatPanel] 群聊翻页暂不支持（需要后端增强recv-group-msg端点）")
        }
    }

    // ═══════════════════════════════════════════════════
    // API 信号统一由 MessagesPage 管理，ChatPanel 仅通过属性接收数据
    // 如需刷新会话列表，通过信号通知父组件
    // ═══════════════════════════════════════════════════
    signal refreshConversationsRequested()
}
