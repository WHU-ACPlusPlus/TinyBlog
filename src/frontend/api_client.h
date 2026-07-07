#ifndef API_CLIENT_H
#define API_CLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QSettings>
#include <QTimer>

#include "api_types.h"

/**
 * Tiny Chat 客户端网络层
 *
 * 封装所有 API 端点的 HTTP 请求和 JSON 解析。
 * 所有请求为异步，通过信号返回结果。
 * 登录/注册成功后自动保存 cookie，后续请求自动附带。
 */
class ApiClient : public QObject
{
    Q_OBJECT
public:
    explicit ApiClient(QObject *parent = nullptr);

    // ── 基础设置 ──
    // ── QML 可绑定的属性 ──
    Q_PROPERTY(bool isLoggedIn READ isLoggedIn NOTIFY loggedInChanged)
    Q_PROPERTY(QString baseUrl READ baseUrl WRITE setBaseUrl NOTIFY baseUrlChanged)

    void setBaseUrl(const QString &url);  // e.g. "http://becharmkon.cn:18999"
    QString baseUrl() const;
    Q_INVOKABLE void setCookie(const QString &token);
    QString cookie() const;
    bool isLoggedIn() const;
    Q_INVOKABLE void clearAuth();         // 清除 cookie + QSettings
    Q_INVOKABLE QString readFileAsBase64(const QUrl &fileUrl);  // 读取文件内容为 base64
    Q_INVOKABLE QUrl generateVideoThumbnail(const QUrl &videoUrl);  // 用 ffmpeg 抽视频第一帧

signals:
    void loggedInChanged();
    void baseUrlChanged();

public slots:

    // ── 请求方法（异步，结果通过信号返回）──

    // 用户
    void registerUser(const QString &username, const QString &password,
                      const QString &nickname);
    void login(const QString &username, const QString &password);

    // 认证
    void checkCookie();

    // 社交
    void follow(int followee_id);
    void unfollow(int followee_id);
    void fetchFollowList();

    // 帖子
    void publishPost(const QString &text, const QStringList &media = {});
    void fetchTimeline(int count = 20);
    void getPost(int post_id);

    // 互动
    void likePost(int post_id);
    void unlikePost(int post_id);
    void comment(int post_id, const QString &content);
    void fetchComments(int post_id);

    // 私信
    void sendMessage(int to_whom_id, const QString &content);
    void receiveMessages();

    // 头像/签名
    void patchAvatar(const QString &avatar = {}, const QString &signature = {});
    void fetchAvatar(int user_id);

    // 群聊
    void createGroup(const QString &name);
    void joinGroup(int group_id);
    void leaveGroup(int group_id);
    void sendGroupMessage(int group_id, const QString &content);
    void receiveGroupMessages(int group_id, int count = 20);
    void fetchGroupMembers(int group_id);
    void fetchMyGroups();

signals:
    // ── 通用信号 ──
    void errorOccurred(const QString &message);

    // ── 认证 ──
    void registerSuccess(const QString &cookie);
    void loginSuccess(const QString &cookie);
    void cookieCheckComplete(bool valid, int userId);

    // ── 社交 ──
    void followListFetched(const QList<UserInfo> &followers,
                           const QList<UserInfo> &followees);

    // ── 帖子 ──
    void postPublished();
    void timelineFetched(const QList<int> &postIds, int count);
    void postFetched(const QVariantMap &post);  // QML 友好：帖子完整数据

    // ── 互动 ──
    void postLiked();
    void postUnliked();
    void commentPosted();
    void commentsFetched(const QList<CommentInfo> &comments);

    // ── 私信 ──
    void messageSent();
    void messagesReceived(const QList<MessageInfo> &messages);

    // ── 头像/签名 ──
    void avatarPatched();
    void avatarFetched(int user_id, const QString &avatar, const QString &signature);

    // ── 群聊 ──
    void groupCreated(int group_id);
    void groupJoined();
    void groupLeft();
    void groupMessageSent();
    void groupMessagesReceived(const QList<GroupMessageInfo> &messages);
    void groupMembersFetched(const QList<UserInfo> &members);
    void myGroupsFetched(const QList<GroupInfo> &groups);

private:
    // 底层工具方法
    QNetworkReply *postJson(const QString &endpoint, const QJsonObject &body);
    bool checkReply(QNetworkReply *reply, QJsonObject &out);
    QString errorFromReply(QNetworkReply *reply) const;

    // 辅助：构建带 cookie 的 JSON body
    QJsonObject withCookie() const;
    QJsonObject withCookie(const QJsonObject &extra) const;

    QNetworkAccessManager *m_manager;
    QString m_baseUrl;
    QString m_cookie;
};

#endif // API_CLIENT_H
