#include "api_client.h"

#include <QDebug>
#include <QFile>
#include <QProcess>
#include <QStandardPaths>
#include <QUuid>
#include <QNetworkRequest>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QUrl>
#include <QUrlQuery>
#include <QMediaPlayer>
#include <QVideoSink>
#include <QVideoFrame>
#include <QVideoFrameFormat>
#include <QImage>
#include <QBuffer>

// ─── 构造与基础设置 ───

ApiClient::ApiClient(QObject *parent)
    : QObject(parent)
    , m_manager(new QNetworkAccessManager(this))
    , m_baseUrl("http://127.0.0.1:18999")
{
    // 启动时从本地存储加载 cookie
    QSettings settings;
    m_cookie = settings.value("auth/cookie").toString();
    QString savedUrl = settings.value("auth/baseUrl").toString();
    if (!savedUrl.isEmpty())
        m_baseUrl = savedUrl;

    // Cookie 存在时异步验证服务器端是否仍然有效
    if (!m_cookie.isEmpty())
        QTimer::singleShot(0, this, &ApiClient::checkCookie);
}

void ApiClient::setBaseUrl(const QString &url)
{
    m_baseUrl = url;
    while (m_baseUrl.endsWith('/'))
        m_baseUrl.chop(1);
    QSettings settings;
    settings.setValue("auth/baseUrl", m_baseUrl);
    emit baseUrlChanged();
}

QString ApiClient::baseUrl() const { return m_baseUrl; }

void ApiClient::setCookie(const QString &token)
{
    m_cookie = token;
    QSettings settings;
    settings.setValue("auth/cookie", token);
    emit loggedInChanged();
}

QString ApiClient::cookie() const { return m_cookie; }

bool ApiClient::isLoggedIn() const { return !m_cookie.isEmpty(); }

void ApiClient::clearAuth()
{
    m_cookie.clear();
    QSettings settings;
    settings.remove("auth/cookie");
    emit loggedInChanged();
}

QString ApiClient::readFileAsBase64(const QUrl &fileUrl)
{
    QString localPath;

#ifdef Q_OS_ANDROID
    // Android content:// URI → Qt 6 的 QFile 可以直接打开
    localPath = fileUrl.toString();
#else
    localPath = fileUrl.toLocalFile();
#endif

    QFile file(localPath);
    if (!file.open(QIODevice::ReadOnly)) {
        emit errorOccurred(QStringLiteral("无法打开文件: %1").arg(file.errorString()));
        return {};
    }

    QByteArray data = file.readAll();
    file.close();

    return QString::fromLatin1(data.toBase64());
}

QUrl ApiClient::generateVideoThumbnail(const QUrl &videoUrl)
{
    QString localPath = videoUrl.toLocalFile();

    QString thumbPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
                        + "/chat_thumb_" + QUuid::createUuid().toString(QUuid::Id128)
                        + ".png";

    QProcess ffmpeg;
    ffmpeg.start("ffmpeg", {
        "-y",
        "-i", localPath,
        "-vframes", "1",
        "-q:v", "2",
        thumbPath
    });
    ffmpeg.waitForFinished(10000);

    if (ffmpeg.exitCode() != 0 || !QFile::exists(thumbPath))
        return {};

    return QUrl::fromLocalFile(thumbPath);
}

QString ApiClient::videoThumbnailFromBase64(const QString &b64)
{
    // 将 base64 视频数据写入临时文件
    QByteArray data = QByteArray::fromBase64(b64.toLatin1());
    QString inputPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
                        + "/chat_vid_" + QUuid::createUuid().toString(QUuid::Id128)
                        + ".mp4";
    QFile inputFile(inputPath);
    if (!inputFile.open(QIODevice::WriteOnly)) {
        qWarning() << "Failed to write temp video file";
        return {};
    }
    inputFile.write(data);
    inputFile.close();

    QString thumbPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
                        + "/chat_thumb_" + QUuid::createUuid().toString(QUuid::Id128)
                        + ".png";

    QProcess ffmpeg;
    ffmpeg.start("ffmpeg", {
        "-y",
        "-i", inputPath,
        "-vframes", "1",
        "-q:v", "2",
        thumbPath
    });
    ffmpeg.waitForFinished(15000);

    // 清理输入临时文件
    QFile::remove(inputPath);

    if (ffmpeg.exitCode() != 0 || !QFile::exists(thumbPath)) {
        qWarning() << "ffmpeg thumbnail extraction failed";
        return {};
    }

    QFile thumbFile(thumbPath);
    if (!thumbFile.open(QIODevice::ReadOnly)) {
        qWarning() << "Failed to read thumbnail file";
        QFile::remove(thumbPath);
        return {};
    }
    QByteArray thumbData = thumbFile.readAll();
    thumbFile.close();
    QFile::remove(thumbPath);

    return QString::fromLatin1(thumbData.toBase64());
}

QString ApiClient::saveBase64ToTempFile(const QString &b64, const QString &ext)
{
    if (b64.isEmpty())
        return {};

    QByteArray data = QByteArray::fromBase64(b64.toLatin1());
    if (data.isEmpty())
        return {};

    QString path = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
                   + "/chat_media_" + QUuid::createUuid().toString(QUuid::Id128)
                   + "." + ext;

    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        qWarning() << "Failed to write temp media file" << path;
        return {};
    }
    file.write(data);
    file.close();

    return QUrl::fromLocalFile(path).toString();
}

void ApiClient::extractVideoThumbnailAsync(const QString &postId, int mediaIndex, const QString &b64)
{
    if (b64.isEmpty()) {
        emit videoThumbnailExtracted(postId, mediaIndex, {});
        return;
    }

    // 将 base64 视频数据写入临时文件
    QByteArray data = QByteArray::fromBase64(b64.toLatin1());
    if (data.isEmpty()) {
        emit videoThumbnailExtracted(postId, mediaIndex, {});
        return;
    }

    QString inputPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation)
                        + "/chat_vid_" + QUuid::createUuid().toString(QUuid::Id128)
                        + ".mp4";
    QFile inputFile(inputPath);
    if (!inputFile.open(QIODevice::WriteOnly)) {
        qWarning() << "Failed to write temp video file" << inputPath;
        emit videoThumbnailExtracted(postId, mediaIndex, {});
        return;
    }
    inputFile.write(data);
    inputFile.close();

    // ── 用 Qt Multimedia 抽第一帧 ──
    QMediaPlayer *player = new QMediaPlayer(this);
    QVideoSink *sink = new QVideoSink(player);
    player->setVideoOutput(sink);

    player->setProperty("inputPath", inputPath);
    player->setProperty("postId", postId);
    player->setProperty("mediaIndex", mediaIndex);
    player->setProperty("captured", false);

    // 5 秒超时
    QTimer *timeout = new QTimer(this);
    timeout->setSingleShot(true);
    connect(timeout, &QTimer::timeout, this, [this, player, timeout, inputPath, postId, mediaIndex]() {
        if (!player->property("captured").toBool()) {
            qWarning() << "Thumbnail timeout for post" << postId;
            player->setProperty("captured", true);
            QFile::remove(inputPath);
            player->stop();
            player->deleteLater();
            timeout->deleteLater();
            emit videoThumbnailExtracted(postId, mediaIndex, {});
        }
    });
    timeout->start(5000);

    // 帧转 QImage（带 map fallback）
    struct {
        QImage operator()(const QVideoFrame &frame) const {
            QImage img = frame.toImage();
            if (!img.isNull()) return img;
            QVideoFrame mapped = frame;
            if (!mapped.map(QVideoFrame::ReadOnly)) return {};
            QImage::Format fmt = QVideoFrameFormat::imageFormatFromPixelFormat(mapped.pixelFormat());
            if (fmt != QImage::Format_Invalid)
                img = QImage(mapped.bits(0), mapped.width(), mapped.height(),
                             mapped.bytesPerLine(0), fmt).copy();
            else
                img = QImage(mapped.bits(0), mapped.width(), mapped.height(),
                             mapped.bytesPerLine(0), QImage::Format_RGB32).copy();
            mapped.unmap();
            return img;
        }
    } frameToImage;

    connect(sink, &QVideoSink::videoFrameChanged, this,
        [this, player, timeout, frameToImage](const QVideoFrame &frame) {
            // 忽略无效帧和已捕获
            if (player->property("captured").toBool()) return;
            if (frame.width() <= 0 || frame.height() <= 0) return;

            QString inputPath = player->property("inputPath").toString();
            QString postId = player->property("postId").toString();
            int mediaIndex = player->property("mediaIndex").toInt();

            QImage image = frameToImage(frame);
            if (image.isNull()) {
                qWarning() << "Failed to convert video frame for post" << postId;
                player->setProperty("captured", true);
                QFile::remove(inputPath);
                player->stop();
                player->deleteLater();
                timeout->deleteLater();
                emit videoThumbnailExtracted(postId, mediaIndex, {});
                return;
            }

            // 缩略图缩放到合理大小（最大 320px）
            if (image.width() > 320 || image.height() > 320)
                image = image.scaled(320, 320, Qt::KeepAspectRatio, Qt::SmoothTransformation);

            QByteArray pngData;
            QBuffer buf(&pngData);
            buf.open(QIODevice::WriteOnly);
            image.save(&buf, "PNG");
            buf.close();
            QString thumbB64 = QString::fromLatin1(pngData.toBase64());

            player->setProperty("captured", true);
            QFile::remove(inputPath);
            player->stop();
            player->deleteLater();
            timeout->deleteLater();

            emit videoThumbnailExtracted(postId, mediaIndex, thumbB64);
        });

    player->setSource(QUrl::fromLocalFile(inputPath));
    player->play();
}

// ─── 私有工具方法 ───

QJsonObject ApiClient::withCookie() const
{
    return {{"cookie", m_cookie}};
}

QJsonObject ApiClient::withCookie(const QJsonObject &extra) const
{
    QJsonObject obj = extra;
    obj["cookie"] = m_cookie;
    return obj;
}

QNetworkReply *ApiClient::postJson(const QString &endpoint,
                                   const QJsonObject &body)
{
    QNetworkRequest req(QUrl(m_baseUrl + endpoint));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setTransferTimeout(15000); // 15s 超时

    QJsonDocument doc(body);
    QByteArray json = doc.toJson(QJsonDocument::Compact);
    return m_manager->post(req, json);
}

bool ApiClient::checkReply(QNetworkReply *reply, QJsonObject &out)
{
    if (reply->error() != QNetworkReply::NoError) {
        emit errorOccurred(
            QStringLiteral("网络错误: %1").arg(reply->errorString()));
        reply->deleteLater();
        return false;
    }

    QByteArray data = reply->readAll();
    reply->deleteLater();

    QJsonParseError parseErr;
    QJsonDocument doc = QJsonDocument::fromJson(data, &parseErr);
    if (parseErr.error != QJsonParseError::NoError) {
        emit errorOccurred(
            QStringLiteral("JSON 解析失败: %1").arg(parseErr.errorString()));
        return false;
    }

    out = doc.object();

    // 检查服务端返回的错误
    if (out.contains("error")) {
        emit errorOccurred(out["error"].toString());
        return false;
    }

    return true;
}

// ─── 认证 ───

void ApiClient::checkCookie()
{
    if (m_cookie.isEmpty())
        return;

    QJsonObject body{{"cookie", m_cookie}};
    QNetworkReply *reply = postJson("/check-cookie", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() != QNetworkReply::NoError) {
            emit errorOccurred(QStringLiteral("网络错误: %1").arg(reply->errorString()));
            reply->deleteLater();
            return;
        }
        QByteArray data = reply->readAll();
        reply->deleteLater();

        QJsonParseError parseErr;
        QJsonDocument doc = QJsonDocument::fromJson(data, &parseErr);
        if (parseErr.error != QJsonParseError::NoError) {
            emit errorOccurred(QStringLiteral("JSON 解析失败: %1").arg(parseErr.errorString()));
            return;
        }

        QJsonObject obj = doc.object();
        if (obj.contains("error")) {
            emit errorOccurred(obj["error"].toString());
            return;
        }

        bool valid = obj["valid"].toBool();
        if (valid) {
            emit cookieCheckComplete(true, obj["user_id"].toInt());
        } else {
            // Cookie 在服务器端已失效，清除本地认证状态
            clearAuth();
            emit cookieCheckComplete(false, 0);

            // 检查过程中可能已经有过网络错误提示，覆盖为更友好的消息
            emit errorOccurred("登录已过期，请重新登录");
        }
    });
}

void ApiClient::registerUser(const QString &username, const QString &password,
                             const QString &nickname)
{
    QJsonObject body{{"username", username},
                     {"password", password},
                     {"nickname", nickname}};

    QNetworkReply *reply = postJson("/register-request", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        setCookie(obj["cookie"].toString());
        emit registerSuccess(m_cookie);
    });
}

void ApiClient::login(const QString &username, const QString &password)
{
    QJsonObject body{{"username", username}, {"password", password}};

    QNetworkReply *reply = postJson("/login-request", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        setCookie(obj["cookie"].toString());
        emit loginSuccess(m_cookie);
    });
}

// ─── 社交 ───

void ApiClient::follow(int followee_id)
{
    QJsonObject body = withCookie({{"followee_id", followee_id}});
    QNetworkReply *reply = postJson("/follow", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit errorOccurred("follow: " + QString::number(obj["follow_id"].toInt()));
    });
}

void ApiClient::unfollow(int followee_id)
{
    QJsonObject body = withCookie({{"followee_id", followee_id}});
    QNetworkReply *reply = postJson("/unfollow", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        (void)obj;
        if (!checkReply(reply, obj))
            return;
        emit errorOccurred("unfollow: " + QString::number(obj["follow_id"].toInt()));
    });
}

void ApiClient::fetchFollowList()
{
    QJsonObject body = withCookie();
    QNetworkReply *reply = postJson("/get-follow-list", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<UserInfo> followers;
        QList<UserInfo> followees;
        for (const auto &v : obj["followers"].toArray())
            followers.append(userFromJson(v.toObject()));
        for (const auto &v : obj["followees"].toArray())
            followees.append(userFromJson(v.toObject()));

        emit followListFetched(followers, followees);
    });
}

// ─── 帖子 ───

void ApiClient::publishPost(const QString &text, const QStringList &media)
{
    QJsonArray arr;
    for (const auto &m : media)
        arr.append(m);
    QJsonObject body = withCookie({{"text", text}, {"media", arr}});
    QNetworkReply *reply = postJson("/pub-post", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postPublished();
    });
}

void ApiClient::fetchTimeline(int count)
{
    QJsonObject body = withCookie({{"count", count}});
    QNetworkReply *reply = postJson("/post-fetch", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<int> ids;
        for (const auto &v : obj["posts"].toArray())
            ids.append(v.toInt());
        emit timelineFetched(ids, obj["count"].toInt());
    });
}

void ApiClient::getPost(int post_id)
{
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply *reply = postJson("/get-post", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postFetched(obj.toVariantMap());
    });
}

// ─── 互动 ───

void ApiClient::likePost(int post_id)
{
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply *reply = postJson("/like", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postLiked();
    });
}

void ApiClient::unlikePost(int post_id)
{
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply *reply = postJson("/unlike", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postUnliked();
    });
}

void ApiClient::comment(int post_id, const QString &content)
{
    QJsonObject body = withCookie({{"post_id", post_id}, {"content", content}});
    QNetworkReply *reply = postJson("/comment", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit commentPosted();
    });
}

void ApiClient::fetchComments(int post_id)
{
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply *reply = postJson("/get-comments", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QVariantList comments;
        for (const auto &v : obj["comments"].toArray())
            comments.append(v.toObject().toVariantMap());
        emit commentsFetched(comments);
    });
}

// ─── 私信 ───

void ApiClient::sendMessage(int to_whom_id, const QString &content)
{
    QJsonObject body =
        withCookie({{"to_whom_id", to_whom_id}, {"content", content}});
    QNetworkReply *reply = postJson("/send-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit messageSent();
    });
}

void ApiClient::receiveMessages()
{
    QJsonObject body = withCookie();
    QNetworkReply *reply = postJson("/recv-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<MessageInfo> msgs;
        for (const auto &v : obj["msgs"].toArray())
            msgs.append(msgFromJson(v.toObject()));
        emit messagesReceived(msgs);
    });
}

// ─── 头像/签名 ───

void ApiClient::patchAvatar(const QString &avatar, const QString &signature)
{
    QJsonObject body = withCookie();
    if (!avatar.isEmpty())
        body["avatar"] = avatar;
    if (!signature.isEmpty())
        body["signature"] = signature;
    QNetworkReply *reply = postJson("/avatar", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit avatarPatched();
    });
}

void ApiClient::fetchAvatar(int user_id)
{
    QUrl url(m_baseUrl + "/avatar");
    QUrlQuery query;
    query.addQueryItem("user_id", QString::number(user_id));
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);

    QNetworkReply *reply = m_manager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() != QNetworkReply::NoError) {
            emit errorOccurred(QStringLiteral("网络错误: %1").arg(reply->errorString()));
            reply->deleteLater();
            return;
        }
        QByteArray data = reply->readAll();
        reply->deleteLater();

        QJsonParseError err;
        QJsonDocument doc = QJsonDocument::fromJson(data, &err);
        if (err.error != QJsonParseError::NoError) {
            emit errorOccurred(QStringLiteral("JSON 解析失败: %1").arg(err.errorString()));
            return;
        }
        QJsonObject obj = doc.object();
        if (obj.contains("error")) {
            emit errorOccurred(obj["error"].toString());
            return;
        }
        emit avatarFetched(obj["user_id"].toInt(),
                           obj["avatar"].toString(),
                           obj["signature"].toString());
    });
}

// ─── 群聊 ───

void ApiClient::createGroup(const QString &name)
{
    QJsonObject body = withCookie({{"name", name}});
    QNetworkReply *reply = postJson("/create-group", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupCreated(obj["group_id"].toInt());
    });
}

void ApiClient::joinGroup(int group_id)
{
    QJsonObject body = withCookie({{"group_id", group_id}});
    QNetworkReply *reply = postJson("/join-group", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupJoined();
    });
}

void ApiClient::leaveGroup(int group_id)
{
    QJsonObject body = withCookie({{"group_id", group_id}});
    QNetworkReply *reply = postJson("/leave-group", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupLeft();
    });
}

void ApiClient::sendGroupMessage(int group_id, const QString &content)
{
    QJsonObject body =
        withCookie({{"group_id", group_id}, {"content", content}});
    QNetworkReply *reply = postJson("/send-group-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupMessageSent();
    });
}

void ApiClient::receiveGroupMessages(int group_id, int count)
{
    QJsonObject body = withCookie({{"group_id", group_id}, {"count", count}});
    QNetworkReply *reply = postJson("/recv-group-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<GroupMessageInfo> msgs;
        for (const auto &v : obj["messages"].toArray())
            msgs.append(groupMsgFromJson(v.toObject()));
        emit groupMessagesReceived(msgs);
    });
}

void ApiClient::fetchGroupMembers(int group_id)
{
    QJsonObject body = withCookie({{"group_id", group_id}});
    QNetworkReply *reply = postJson("/get-group-members", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<UserInfo> members;
        for (const auto &v : obj["members"].toArray())
            members.append(userFromJson(v.toObject()));
        emit groupMembersFetched(members);
    });
}

void ApiClient::fetchMyGroups()
{
    QJsonObject body = withCookie();
    QNetworkReply *reply = postJson("/get-my-groups", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<GroupInfo> groups;
        for (const auto &v : obj["groups"].toArray())
            groups.append(groupFromJson(v.toObject()));
        emit myGroupsFetched(groups);
    });
}
