#ifndef API_CLIENT_H
#define API_CLIENT_H

#include <QCoreApplication>
#include <QDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QObject>
#include <QQmlEngine>
#include <QSettings>
#include <QTextDocument>
#include <QTimer>
#include <QTranslator>

#ifdef Q_OS_ANDROID
#include <QJniObject>
#endif

#include "api_types.h"

/**
 * Tiny Blog 客户端网络层
 *
 * 封装所有 API 端点的 HTTP 请求和 JSON 解析。
 * 所有请求为异步，通过信号返回结果。
 * 登录/注册成功后自动保存 cookie，后续请求自动附带。
 */
class ApiClient : public QObject {
    Q_OBJECT
   public:
    explicit ApiClient(QObject* parent = nullptr);

    // ── 基础设置 ──
    // ── QML 可绑定的属性 ──
    Q_PROPERTY(bool isLoggedIn READ isLoggedIn NOTIFY loggedInChanged)
    Q_PROPERTY(QString baseUrl READ baseUrl WRITE setBaseUrl NOTIFY baseUrlChanged)
    Q_PROPERTY(bool isAndroid READ isAndroid CONSTANT)
    Q_PROPERTY(QString wallpaperPath READ wallpaperPath WRITE setWallpaperPath NOTIFY wallpaperPathChanged)
    Q_PROPERTY(QString videoWallpaperPath READ videoWallpaperPath WRITE setVideoWallpaperPath NOTIFY videoWallpaperPathChanged)

    void setBaseUrl(const QString& url);  // e.g. "http://becharmkon.cn:18999"
    QString baseUrl() const;
    Q_INVOKABLE void setCookie(const QString& token);
    QString cookie() const;
    bool isLoggedIn() const;
    Q_INVOKABLE void clearAuth();
    Q_INVOKABLE void setLanguage(const QString& locale);
    void setQmlEngine(QQmlEngine* engine);                                                                   // 清除 cookie + QSettings
    Q_INVOKABLE QString readFileAsBase64(const QUrl& fileUrl, int maxSizeBytes = 0);                         // 读取文件内容为 base64（可指定最大字节数，超限自动压缩）
    Q_INVOKABLE QString compressImageBase64(const QString& base64Input, int maxSizeBytes = 3145728, int maxDimension = 1920);  // 压缩 base64 图片（目标 ≤3MB base64，最长边 ≤1920px）
    Q_INVOKABLE QString markdownToHtml(const QString& markdown);  // Markdown → HTML 转换
    Q_INVOKABLE QUrl generateVideoThumbnail(const QUrl& videoUrl);                                           // 用 ffmpeg 抽视频第一帧
    Q_INVOKABLE QString videoThumbnailFromBase64(const QString& b64);                                        // 从 base64 视频数据提取缩略图
    Q_INVOKABLE QString saveBase64ToTempFile(const QString& b64, const QString& ext);                        // base64 → 临时文件 → file:// URL
    Q_INVOKABLE void extractVideoThumbnailAsync(const QString& postId, int mediaIndex, const QString& b64);  // 异步抽视频第一帧
    Q_INVOKABLE void fetchVideoPlayUrl(const QString& bvid, const QString& cid);                             // 获取 B站视频直链（→ videoPlayUrlReady 信号）
    bool isAndroid() const;                                                                                     // 编译时判断是否为 Android 平台

    // ── 壁纸 ──
    Q_INVOKABLE void setWallpaperPath(const QString& path);
    QString wallpaperPath() const;
    Q_INVOKABLE void clearWallpaper();

    // ── 视频壁纸 ──
    Q_INVOKABLE void setVideoWallpaperPath(const QString& path);
    QString videoWallpaperPath() const;
    Q_INVOKABLE void clearVideoWallpaper();

   signals:
    void loggedInChanged();
    void baseUrlChanged();
    void languageChanged();
    void wallpaperPathChanged();
    void videoWallpaperPathChanged();

   public slots:

    // ── 请求方法（异步，结果通过信号返回）──

    // 用户
    // 新注册流程三步：startRegister → verifyRegister → completeRegister
    void startRegister(const QString& username, const QString& password,
                       const QString& nickname);
    void verifyRegister(const QString& cookie, const QString& captcha,
                        const QString& email);
    void completeRegister(const QString& cookie, const QString& emailCode);
    // 登录安全三步：startLogin → [verifyCaptcha] → [sendEmailCode+verifyEmail] → completeLogin
    void startLogin(const QString& username, const QString& password);
    void loginVerifyCaptcha(const QString& cookie, const QString& captcha);
    void loginSendEmailCode(const QString& cookie);
    void loginVerifyEmail(const QString& cookie, const QString& emailCode);
    void completeLogin(const QString& cookie);

    // 认证
    void checkCookie();

    // 社交
    void follow(int followee_id);
    void unfollow(int followee_id);
    void fetchFollowList();
    void block(int user_id);
    void unblock(int user_id);
    void fetchBlocked();

    // 帖子
    void publishPost(const QString& text, const QStringList& media = {});
    void fetchTimeline(int count = 20);
    void getPost(int post_id);

    // 互动
    void likePost(int post_id);
    void unlikePost(int post_id);
    void comment(int post_id, const QString& content);
    void fetchComments(int post_id);

    // 私信
    void sendMessage(int to_whom_id, const QString& content);
    void receiveMessages();

    // 头像/签名/个人资料
    void fetchProfile();

#ifdef Q_OS_ANDROID
    Q_INVOKABLE bool pickMediaFiles();  // 启动 Android SAF 文件选择器，返回 true 表示已启动
#endif
    void updateProfile(const QString& nickname = {},
                       const QString& avatar = {},
                       const QString& signature = {});
    void patchAvatar(const QString& avatar = {}, const QString& signature = {});
    void fetchAvatar(int user_id);

    // 群聊
    void createGroup(const QString& name);
    void joinGroup(int group_id);
    void leaveGroup(int group_id);
    void sendGroupMessage(int group_id, const QString& content);
    void receiveGroupMessages(int group_id, int count = 20);
    void fetchGroupMembers(int group_id);
    void fetchMyGroups();

    // ── 消息功能（新增）──
    // 会话
    void fetchConversations();
    void hideConversation(int conversation_id);

    // 聊天历史
    void fetchPrivateMessages(int with_user_id, int before_id = 0, int count = 20);

    // 搜索联系人/群组
    void searchContacts(const QString& keyword, const QString& type = "all");
    void socialSearch(const QString& query, int limit = 20);    // FTS5 全文搜索

    // 联系人列表
    void fetchContacts();

    // 用户自己的帖子
    void fetchUserPosts(int publisher_id);
    void fetchMyPostsDetail(int publisher_id);  // 一次性拉取完整帖子数据

    // 用户/群组详情（侧边面板）
    void fetchUserDetail(int user_id);
    void fetchGroupDetail(int group_id);

    // ── 好友申请 ──
    void sendFriendRequest(int to_user_id);
    void getFriendRequests();
    void handleFriendRequest(int request_id, const QString& action);  // "accept" | "reject"

   signals:
    // ── 通用信号 ──
    void errorOccurred(const QString& message);

    // ── 认证 ──
    void registerSuccess(const QString& cookie);
    void registerStep1Done(const QString& cookie, const QString& captcha);
    void registerStep2Done();
    void loginStep1Done(const QString& cookie, bool needCaptcha, bool needEmail,
                        const QString& captcha, const QString& email);
    void loginStep2Done();
    void loginStep3Done();
    void loginSuccess(const QString& cookie);
    void cookieCheckComplete(bool valid, int userId);

    // ── 社交 ──
    void followListFetched(const QList<UserInfo>& followers,
                           const QList<UserInfo>& followees);
    void userBlocked();
    void userUnblocked();
    void blockedFetched(const QVariantList& blocked);
    void socialSearchDone(const QVariantMap& results);

    // ── 帖子 ──
    void postPublished();
    void timelineFetched(const QList<int>& postIds, int count);
    void postFetched(const QVariantMap& post);  // QML 友好：帖子完整数据

    // ── 互动 ──
    void postLiked();
    void postUnliked();
    void commentPosted();
    void commentsFetched(const QVariantList& comments);

    // ── 媒体 ──
    void videoThumbnailExtracted(const QString& postId, int mediaIndex, const QString& thumbnailB64);
    void videoPlayUrlReady(const QString& bvid, const QString& url, const QString& format);

    // ── Android 文件选择 ──
    void mediaFilesPicked(const QVariantList& files);
    // files: QVariantList of QVariantMap {url, b64, mime, size}

    // ── 私信 ──
    void messageSent();
    void messagesReceived(const QList<MessageInfo>& messages);

    // 头像/签名/个人资料
    void profileFetched(const QVariantMap& profile);
    void profileUpdated();
    void avatarPatched();
    void avatarFetched(int user_id, const QString& avatar, const QString& signature);

    // ── 群聊 ──
    void groupCreated(int group_id);
    void groupJoined();
    void groupLeft();
    void groupMessageSent();
    void groupMessagesReceived(const QVariantList& messages);  // QVariantList使QML可读字段
    void groupMembersFetched(const QList<UserInfo>& members);
    void myGroupsFetched(const QList<GroupInfo>& groups);

    // ── 用户帖子 ──
    void userPostsFetched(const QVariantList& postIds);  // QList<int> wrapped as QVariantList for QML
    void myPostsFetched(const QVariantList& posts);      // 帖子完整数据（QML 友好）

    // ── 关注列表（QML 友好版）──
    void followListFetchedForQml(const QVariantList& followers,
                                 const QVariantList& followees);

    // ── 消息功能（新增）──
    void conversationsFetched(const QVariantList& conversations);  // QVariantList of QVariantMap (QML-friendly)
    void conversationHidden(int conversation_id);
    void privateMessagesFetched(const QVariantList& messages, bool hasMore);  // QVariantList of QVariantMap
    void contactsSearched(const QVariantList& users, const QVariantList& groups);
    void contactsFetched(const QVariantList& contacts, const QVariantList& followedOnly);
    void userDetailFetched(const QVariantMap& detail);
    void groupDetailFetched(const QVariantMap& detail);

    // ── 好友申请 ──
    void friendRequestSent();
    void friendRequestsFetched(const QVariantList& incoming, const QVariantList& outgoing);
    void friendRequestHandled(const QString& result);

   private:
    // 底层工具方法
    QNetworkReply* postJson(const QString& endpoint, const QJsonObject& body);
    bool checkReply(QNetworkReply* reply, QJsonObject& out);
    QString errorFromReply(QNetworkReply* reply) const;

    // 辅助：构建带 cookie 的 JSON body
    QJsonObject withCookie() const;
    QJsonObject withCookie(const QJsonObject& extra) const;
    QString renderLatexToImg(const QString& latex, bool block);

    QNetworkAccessManager* m_manager;
    QString m_baseUrl;
    QString m_cookie;
    QString m_wallpaperPath;
    QString m_videoWallpaperPath;
    int m_checkCookieRetries = 0;
    static constexpr int kMaxCheckCookieRetries = 3;
    QTranslator* m_translator;
    QQmlEngine* m_engine;
    QString m_currentLocale;

#ifdef Q_OS_ANDROID
    void handleMediaPickerResult(int resultCode, const QJniObject& intentData);
    QVariantMap readUriInfo(const QJniObject& uri);
#endif
};

#endif  // API_CLIENT_H
