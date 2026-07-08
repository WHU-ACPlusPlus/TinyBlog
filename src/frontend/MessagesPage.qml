import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// ═══════════════════════════════════════════════════════
// MessagesPage — 消息页主组件（三栏布局）
// 设计风格：极简主义（style/极简主义.md）
// API信号管理中心：所有 api 信号在此统一处理，子组件仅通过属性接收数据
// ═══════════════════════════════════════════════════════

Rectangle {
id: root
    color: softUIMode ? "#e8edf2" : (glassMode ? "transparent" : "#f5f5f5")

    // ── 风格模式（由 MainPage 传入）──
    property bool glassMode: false
    property bool softUIMode: false

    // ── 自适应文字颜色 ──
    property color textPrimary:   glassMode ? "#ffffff" : (softUIMode ? "#2d3436" : "#222222")
    property color textSecondary: glassMode ? Qt.rgba(1,1,1,0.65) : (softUIMode ? "#636e72" : "#666666")
    property color textTertiary:  glassMode ? Qt.rgba(1,1,1,0.40) : (softUIMode ? "#888888" : "#999999")

    // ── 状态 ──
    property var conversations: []
    property var currentConversation: null
    property var currentMessages: []
    property var searchResults: ({ users: [], groups: [] })
    property var userDetailData: null
    property var groupDetailData: null
    property int currentUserId: 0
    property bool isNarrowMode: width < 700
    property int narrowViewIndex: 0
    property var _contacts: []          // P1: 好友列表
    property var _followedOnly: []      // P1: 单向关注列表
    property var _rawConversations: []  // R5 BUG2: 原始会话数据

    // ── 防重复守卫 ──
    property bool _initialLoadDone: false
    property bool _fetchingConversations: false
    property var _lastFetchConversationsTime: 0

    // ── 定时轮询（30s）──
    property var pollTimer: null

    Component.onCompleted: {
        console.log("[MessagesPage] 加载完成, w=" + width + " narrow=" + isNarrowMode)
        initPollTimer()
    }

    onWidthChanged: {
        console.log("[MessagesPage] 宽度变化: " + width)
    }

    function initPollTimer() {
        if (pollTimer) pollTimer.destroy()
        pollTimer = Qt.createQmlObject(
            'import QtQuick; Timer { interval: 30000; repeat: true; running: true }', root)
        pollTimer.triggered.connect(function() {
            if (api.isLoggedIn && root._initialLoadDone) {
                console.log("[MessagesPage] 定时轮询触发")
                safeFetchConversations("poll")
            }
        })
        console.log("[MessagesPage] 轮询已启动, 间隔30s")
    }

    // ── 防抖：避免短时间内重复请求 ──
    function safeFetchConversations(source) {
        var now = Date.now()
        if (root._fetchingConversations) {
            console.log("[MessagesPage] 跳过重复fetchConversations (source=" + source + ", 正在请求中)")
            return
        }
        if (now - root._lastFetchConversationsTime < 2000) {
            console.log("[MessagesPage] 跳过重复fetchConversations (source=" + source + ", 距上次" + (now - root._lastFetchConversationsTime) + "ms)")
            return
        }
        root._fetchingConversations = true
        root._lastFetchConversationsTime = now
        console.log("[MessagesPage] fetchConversations (source=" + source + ")")

        // BUG3修复: 5秒超时自动解锁，防止死锁
        unlockTimer.interval = 5000
        unlockTimer.restart()

        api.fetchConversations()
    }

    // BUG3修复: 超时解锁定时器
    Timer {
        id: unlockTimer
        interval: 5000; repeat: false
        onTriggered: {
            if (root._fetchingConversations) {
                console.log("[MessagesPage] fetchConversations超时5秒, 强制解锁")
                root._fetchingConversations = false
            }
        }
    }

    // BUG3修复: 页面可见时刷新会话列表
    onVisibleChanged: {
        console.log("[MessagesPage] visible=" + visible + " loggedIn=" + api.isLoggedIn)
        if (visible && api.isLoggedIn && root._initialLoadDone) {
            console.log("[MessagesPage] 页面变为可见, 刷新会话")
            safeFetchConversations("visible")
        }
    }

    // ── BUG2修复: 重置所有状态（登出/切换账号时调用）──
    function resetAllState() {
        console.log("[MessagesPage] resetAllState: 清空所有聊天状态")
        root.conversations = []
        root.currentConversation = null
        root.currentMessages = []
        root.searchResults = ({ users: [], groups: [] })
        root.userDetailData = null
        root.groupDetailData = null
        root.currentUserId = 0
        root.narrowViewIndex = 0
        root._fetchingConversations = false
        root._contacts = []
        root._followedOnly = []
        root._rawConversations = []  // R5 BUG2
    }

    // ── P1+R5 BUG2: 合并联系人到会话列表（原始会话优先 + 联系人追加）──
    function mergeConversationsAndContacts() {
        var merged = (root._rawConversations || []).slice()
        var existingIds = {}
        for (var i = 0; i < merged.length; i++) {
            existingIds["p_" + merged[i].target_id] = true
            existingIds["g_" + merged[i].target_id] = true
        }

        // 追加好友（无消息往来的联系人）
        for (var j = 0; j < root._contacts.length; j++) {
            var c = root._contacts[j]
            var key = "p_" + (c.id || 0)
            if (!existingIds[key]) {
                merged.push({
                    id: -c.id, type: "private", target_id: c.id,
                    target_name: c.nickname || c.username || "",
                    target_avatar: c.avatar || "",
                    last_message: qsTr("好友，暂无消息"),
                    last_message_time: "", unread_count: 0
                })
                existingIds[key] = true
            }
        }

        // 追加单向关注
        for (var k = 0; k < root._followedOnly.length; k++) {
            var fo = root._followedOnly[k]
            var key2 = "p_" + (fo.id || 0)
            if (!existingIds[key2]) {
                merged.push({
                    id: -fo.id, type: "private", target_id: fo.id,
                    target_name: fo.nickname || fo.username || "",
                    target_avatar: fo.avatar || "",
                    last_message: qsTr("已关注，暂无消息"),
                    last_message_time: "", unread_count: 0
                })
                existingIds[key2] = true
            }
        }

        console.log("[MessagesPage] mergeConversationsAndContacts: convs=" + root.conversations.length +
                    " +contacts=" + root._contacts.length + " +followedOnly=" + root._followedOnly.length +
                    " = merged=" + merged.length)
        root.conversations = merged
    }

    // ── P3: 统一搜索入口（单一出口）──
    function doSearch(keyword, type) {
        if (!keyword || keyword.trim().length === 0) {
            console.log("[MessagesPage] doSearch: 空关键词, 跳过")
            return
        }
        console.log("[MessagesPage] doSearch: kw='" + keyword + "' type=" + type)
        api.searchContacts(keyword, type)
    }

    // ── P2: 搜索结果用户点击处理（根据关注状态）──
    function handleSearchUserClick(userData) {
        searchPopup.close()
        root.searchResults = ({ users: [], groups: [] })
        console.log("[MessagesPage] handleSearchUserClick: " + (userData.nickname || userData.username) +
                    " is_following=" + userData.is_following + " is_mutual=" + userData.is_mutual)

        if (!userData.is_following && !userData.is_mutual) {
            // 未关注 → 先关注再聊天
            console.log("[MessagesPage] 未关注用户, 自动follow")
            api.follow(userData.id)
        }
        // 直接打开聊天
        api.fetchPrivateMessages(userData.id, 0, 20)
        if (root.isNarrowMode) root.narrowViewIndex = 1
    }

    // ═══════════════════════════════════════════════════
    // 统一 API 信号处理（唯一入口）
    // ═══════════════════════════════════════════════════
    Connections {
        target: api

        // ── 认证 ──
        function onLoggedInChanged() {
            console.log("[MessagesPage] onLoggedInChanged: isLoggedIn=" + api.isLoggedIn + " initialDone=" + root._initialLoadDone)
            if (api.isLoggedIn) {
                if (!root._initialLoadDone) {
                    console.log("[MessagesPage] 首次登录, 加载数据")
                    root._initialLoadDone = true
                    resetAllState()
                    api.checkCookie()
                    safeFetchConversations("login")
                    api.fetchContacts()    // P1: 加载联系人列表
                }
            } else {
                // BUG2修复: 登出时清空所有状态
                console.log("[MessagesPage] 检测到登出，重置所有状态")
                root._initialLoadDone = false
                resetAllState()
            }
        }
        function onCookieCheckComplete(valid, userId) {
            console.log("[MessagesPage] cookie验证: valid=" + valid + " userId=" + userId)
            if (valid) root.currentUserId = userId
        }

        // ── 会话列表 ──
        function onConversationsFetched(conversations) {
            root._fetchingConversations = false
            console.log("[MessagesPage] conversationsFetched: " + conversations.length + "个")
            // R5 BUG2: 不直接赋值，保存原始数据后统一合并（防止覆盖contacts结果）
            root._rawConversations = conversations
            mergeConversationsAndContacts()
        }

        // ── 私聊消息 ──
        function onPrivateMessagesFetched(messages, hasMore) {
            console.log("[MessagesPage] privateMessagesFetched: " + messages.length + "条 hasMore=" + hasMore)
            root.currentMessages = messages
        }
        function onMessageSent() {
            console.log("[MessagesPage] messageSent")
            safeFetchConversations("msgSent")
        }

        // ── 群聊消息 ──
        function onGroupMessageSent() {
            console.log("[MessagesPage] groupMessageSent")
            safeFetchConversations("groupMsgSent")
        }
        function onGroupMessagesReceived(messages) {
            console.log("[MessagesPage] groupMessagesReceived: " + messages.length + "条 (R4: QVariantList)")
            // R4修复: 数据已为QVariantMap可直接访问，仅补充sender_name+透传avatar
            var result = []
            for (var i = 0; i < messages.length; i++) {
                result.push({
                    id: messages[i].id,
                    sender_id: messages[i].sender_id,
                    sender_name: messages[i].nickname || messages[i].username || "",
                    sender_avatar: messages[i].avatar || "",
                    content: messages[i].content,
                    sent_at: messages[i].sent_at
                })
            }
            root.currentMessages = result
        }

        // ── 群组操作 ──
        function onGroupCreated(groupId) {
            console.log("[MessagesPage] groupCreated: " + groupId)
            safeFetchConversations("groupCreated")
        }
        function onGroupJoined() {
            console.log("[MessagesPage] groupJoined")
            safeFetchConversations("groupJoined")
        }
        function onGroupLeft() {
            console.log("[MessagesPage] groupLeft")
            root.currentConversation = null
            root.currentMessages = []
            safeFetchConversations("groupLeft")
        }

        // ── 会话操作 ──
        function onConversationHidden(conversationId) {
            console.log("[MessagesPage] conversationHidden: " + conversationId)
            var filtered = []
            for (var i = 0; i < root.conversations.length; i++) {
                if (root.conversations[i].id !== conversationId)
                    filtered.push(root.conversations[i])
            }
            root.conversations = filtered
            root.currentConversation = null
            root.currentMessages = []
        }

        // ── 搜索 ──
        function onContactsSearched(users, groups) {
            console.log("[MessagesPage] contactsSearched: users=" + users.length + " groups=" + groups.length)
            root.searchResults = { users: users, groups: groups }
        }

        // ── 详情 ──
        function onUserDetailFetched(detail) {
            console.log("[MessagesPage] userDetailFetched: " + JSON.stringify(detail))
            root.userDetailData = detail
        }
        function onGroupDetailFetched(detail) {
            console.log("[MessagesPage] groupDetailFetched: name=" + (detail.name || ""))
            // R4 BUG C修复: 强制创建新JS对象确保QML检测到引用变化
            root.groupDetailData = JSON.parse(JSON.stringify(detail))
        }

        // ── BUG3修复: 错误恢复，防止_fetchingConversations死锁 ──
        function onErrorOccurred(message) {
            console.log("[MessagesPage] API错误: " + message + ", 重置fetch锁")
            root._fetchingConversations = false
        }

        // ── P1: 联系人列表 ──
        function onContactsFetched(contacts, followedOnly) {
            console.log("[MessagesPage] contactsFetched: contacts=" + contacts.length + " followedOnly=" + followedOnly.length)
            root._contacts = contacts
            root._followedOnly = followedOnly
            mergeConversationsAndContacts()
        }
    }

    // ═══════════════════════════════════════════════════
    // ── 宽屏布局（≥700px）：三栏 ──
    // ═══════════════════════════════════════════════════
    RowLayout {
        anchors.fill: parent
        spacing: 0
        visible: !root.isNarrowMode

        ConversationListPanel {
            id: convListPanelWide
            Layout.preferredWidth: 280
            Layout.fillHeight: true
            glassMode: root.glassMode
            softUIMode: root.softUIMode
            conversations: root.conversations
            selectedConvId: root.currentConversation ? root.currentConversation.id : -1

            onConversationClicked: function(conv) {
                console.log("[MessagesPage] 会话点击: id=" + conv.id + " type=" + conv.type)
                root.currentConversation = conv
                if (conv.type === "private")
                    api.fetchPrivateMessages(conv.target_id, 0, 20)
                else
                    api.receiveGroupMessages(conv.target_id, 20)
            }
            onMenuAction: function(index) { handleMenuAction(index) }
            onSearchRequested: function(keyword) { root.doSearch(keyword, "all") }
            onRefreshRequested: safeFetchConversations("manual")
        }

        Rectangle {
            Layout.preferredWidth: 0.5
            Layout.fillHeight: true
color: root.softUIMode ? Qt.rgba(0.64, 0.69, 0.77, 0.4) : (root.glassMode ? Qt.rgba(1, 1, 1, 0.10) : "#e0e0e0")
        }

        ChatPanel {
            id: chatPanelWide
            Layout.fillWidth: true
            Layout.fillHeight: true
            glassMode: root.glassMode
            softUIMode: root.softUIMode
            currentConversation: root.currentConversation
            messages: root.currentMessages
            currentUserId: root.currentUserId
            userDetailData: root.userDetailData
            groupDetailData: root.groupDetailData

            onRefreshConversationsRequested: safeFetchConversations("chatPanel")
        }
    }

    // ═══════════════════════════════════════════════════
    // ── 窄屏布局（<700px）：StackLayout 切换 ──
    // ═══════════════════════════════════════════════════
    StackLayout {
        anchors.fill: parent
        visible: root.isNarrowMode
        currentIndex: root.narrowViewIndex

        ConversationListPanel {
            id: convListPanelNarrow
            Layout.fillWidth: true
            Layout.fillHeight: true
            glassMode: root.glassMode
            softUIMode: root.softUIMode
            conversations: root.conversations
            selectedConvId: root.currentConversation ? root.currentConversation.id : -1

            onConversationClicked: function(conv) {
                console.log("[MessagesPage.narrow] 会话点击: id=" + conv.id)
                root.currentConversation = conv
                if (conv.type === "private")
                    api.fetchPrivateMessages(conv.target_id, 0, 20)
                else
                    api.receiveGroupMessages(conv.target_id, 20)
                root.narrowViewIndex = 1
            }
            onMenuAction: function(index) { handleMenuAction(index) }
            onSearchRequested: function(keyword) { root.doSearch(keyword, "all") }
            onRefreshRequested: safeFetchConversations("manual")
        }

        ChatPanel {
            id: chatPanelNarrow
            Layout.fillWidth: true
            Layout.fillHeight: true
            glassMode: root.glassMode
            softUIMode: root.softUIMode
            currentConversation: root.currentConversation
            messages: root.currentMessages
            currentUserId: root.currentUserId
            userDetailData: root.userDetailData
            groupDetailData: root.groupDetailData

            onBackButtonClicked: { root.narrowViewIndex = 0 }
            onRefreshConversationsRequested: safeFetchConversations("chatPanelNarrow")
        }
    }

    // ═══════════════════════════════════════════════════
    // ── "+" 菜单 ──
    // ═══════════════════════════════════════════════════
    function handleMenuAction(index) {
        console.log("[MessagesPage] 菜单 index=" + index)
        switch (index) {
            case 0: addFriendDialog.open(); break
            case 1: createGroupDialog.open(); break
            case 2: joinGroupDialog.open(); break
        }
    }

    // ── 搜索群组点击处理 ──
    function handleSearchGroupClick(groupData) {
        console.log("[MessagesPage] handleSearchGroupClick: " + (groupData.name || ""))
        searchPopup.close()
        root.searchResults = ({ users: [], groups: [] })
        if (groupData.is_member) {
            api.receiveGroupMessages(groupData.id, 20)
        } else {
            api.joinGroup(groupData.id)
        }
        if (root.isNarrowMode) root.narrowViewIndex = 1
    }

    // ── 创建群聊 ──
    Dialog {
        id: createGroupDialog
        title: qsTr("创建群聊")
        width: 300
        anchors.centerIn: parent
    }
}

