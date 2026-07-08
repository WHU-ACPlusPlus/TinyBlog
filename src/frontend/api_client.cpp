#include "api_client.h"

#include <QBuffer>
#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFile>
#include <QHash>
#include <QImage>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QMediaPlayer>
#include <QNetworkRequest>
#include <QProcess>
#include <QQmlEngine>
#include <QStandardPaths>
#include <QTranslator>
#include <QUrl>
#include <QUrlQuery>
#include <QUuid>
#include <QVideoFrame>
#include <QVideoFrameFormat>
#include <QVideoSink>
#include <cmath>

// ─── 后端英文错误 → 中文翻译 ───
static QString trBackendError(const QString& msg) {
    static const QHash<QString, QString> map = {
        {QStringLiteral("Bad cookie."), ApiClient::tr("登录已过期，请重新登录")},
        {QStringLiteral("Bad username."), ApiClient::tr("无效的用户名")},
        {QStringLiteral("Bad nickname."), ApiClient::tr("无效的昵称")},
        {QStringLiteral("Bad password."), ApiClient::tr("无效的密码")},
        {QStringLiteral("Username occupied."), ApiClient::tr("用户名已被占用")},
        {QStringLiteral("User not exist."), ApiClient::tr("用户不存在")},
        {QStringLiteral("Incorrect password."), ApiClient::tr("密码错误")},
        {QStringLiteral("Empty post not allowed."), ApiClient::tr("内容不能为空")},
        {QStringLiteral("Too many media."), ApiClient::tr("媒体文件过多")},
        {QStringLiteral("Media cannot be larger than 16MiB."), ApiClient::tr("媒体文件不能超过 16MiB")},
        {QStringLiteral("Post not exist."), ApiClient::tr("帖子不存在")},
        {QStringLiteral("Post not found."), ApiClient::tr("帖子不存在")},
        {QStringLiteral("Empty comment not allowed."), ApiClient::tr("评论不能为空")},
        {QStringLiteral("Cannot follow yourself."), ApiClient::tr("不能关注自己")},
        {QStringLiteral("Not your post."), ApiClient::tr("不能删除他人的帖子")},
        {QStringLiteral("Not your comment."), ApiClient::tr("不能删除他人的评论")},
        {QStringLiteral("Cannot repost your own post."), ApiClient::tr("不能转发自己的帖子")},
        {QStringLiteral("Group name cannot be empty."), ApiClient::tr("群组名称不能为空")},
        {QStringLiteral("Group not exist."), ApiClient::tr("群组不存在")},
        {QStringLiteral("You are not in this group."), ApiClient::tr("你不在该群组中")},
        {QStringLiteral("Empty message not allowed."), ApiClient::tr("消息不能为空")},
        {QStringLiteral("You are already in this group."), ApiClient::tr("你已在该群组中")},
        {QStringLiteral("Bad `to_whom_id`"), ApiClient::tr("无效的收信人")},
    };
    return map.value(msg, msg);
}

// ─── 构造与基础设置 ───

ApiClient::ApiClient(QObject* parent)
    : QObject(parent), m_manager(new QNetworkAccessManager(this)), m_baseUrl("http://127.0.0.1:18999"), m_translator(nullptr), m_engine(nullptr), m_currentLocale() {
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

void ApiClient::setBaseUrl(const QString& url) {
    m_baseUrl = url;
    // 未指明协议时默认为 http
    if (!m_baseUrl.startsWith("http://") && !m_baseUrl.startsWith("https://"))
        m_baseUrl.prepend("http://");
    while (m_baseUrl.endsWith('/'))
        m_baseUrl.chop(1);
    QSettings settings;
    settings.setValue("auth/baseUrl", m_baseUrl);
    emit baseUrlChanged();
}

QString ApiClient::baseUrl() const { return m_baseUrl; }

void ApiClient::setCookie(const QString& token) {
    m_cookie = token;
    QSettings settings;
    settings.setValue("auth/cookie", token);
    emit loggedInChanged();
}

QString ApiClient::cookie() const { return m_cookie; }

bool ApiClient::isLoggedIn() const { return !m_cookie.isEmpty(); }

void ApiClient::clearAuth() {
    m_cookie.clear();
    QSettings settings;
    settings.remove("auth/cookie");
    emit loggedInChanged();
}

void ApiClient::setQmlEngine(QQmlEngine* engine) {
    m_engine = engine;
}

void ApiClient::setLanguage(const QString& locale) {
    if (locale == m_currentLocale) return;
    m_currentLocale = locale;

    if (m_translator) {
        QCoreApplication::removeTranslator(m_translator);
        delete m_translator;
        m_translator = nullptr;
    }

    // Don't install translator for zh_CN (source language)
    if (locale != "zh_CN") {
        m_translator = new QTranslator(this);
        QStringList searchPaths = {
            QCoreApplication::applicationDirPath() + "/appfrontend_" + locale + ".qm",               // dev: build/
            QCoreApplication::applicationDirPath() + "/translations/appfrontend_" + locale + ".qm",  // installed
        };
        bool loaded = false;
        for (const auto& path : searchPaths) {
            if (m_translator->load(path)) {
                loaded = true;
                break;
            }
        }
        if (!loaded) {
            delete m_translator;
            m_translator = nullptr;
            emit errorOccurred(QStringLiteral("Failed to load translation: %1").arg(locale));
            return;
        }
        QCoreApplication::installTranslator(m_translator);
    }

    if (m_engine)
        m_engine->retranslate();
    emit languageChanged();
}

QString ApiClient::readFileAsBase64(const QUrl& fileUrl, int maxSizeBytes) {
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

    // 如果指定了最大大小且文件超过限制，自动压缩
    if (maxSizeBytes > 0 && data.size() > maxSizeBytes) {
        QImage img;
        if (img.loadFromData(data)) {
            // 计算缩放比例：面积比例 ≈ 目标文件大小 / 实际文件大小
            double scale = std::sqrt(static_cast<double>(maxSizeBytes) / data.size());
            // 同时限制最大边长不超过 1024px（头像不需要太大）
            int maxDim = 1024;
            if (img.width() > maxDim || img.height() > maxDim) {
                double dimScale = static_cast<double>(maxDim) / std::max(img.width(), img.height());
                scale = std::min(scale, dimScale);
            }

            int newW = qMax(1, static_cast<int>(img.width() * scale));
            int newH = qMax(1, static_cast<int>(img.height() * scale));

            QImage scaled = img.scaled(newW, newH,
                                       Qt::KeepAspectRatio,
                                       Qt::SmoothTransformation);

            QByteArray compressed;
            QBuffer buf(&compressed);
            buf.open(QIODevice::WriteOnly);
            // 先尝试 PNG 无损压缩
            scaled.save(&buf, "PNG");
            buf.close();

            // 如果 PNG 仍然超限，改用 JPEG（更小但会有质量损失）
            if (compressed.size() > maxSizeBytes) {
                compressed.clear();
                buf.open(QIODevice::WriteOnly);
                scaled.save(&buf, "JPEG", 85);
                buf.close();
            }

            return QString::fromLatin1(compressed.toBase64());
        }
        // 图片加载失败，回退到原始数据
    }

    return QString::fromLatin1(data.toBase64());
}

QUrl ApiClient::generateVideoThumbnail(const QUrl& videoUrl) {
    QString localPath = videoUrl.toLocalFile();

    QString thumbPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation) + "/chat_thumb_" + QUuid::createUuid().toString(QUuid::Id128) + ".png";

    QProcess ffmpeg;
    ffmpeg.start("ffmpeg", {"-y",
                            "-i", localPath,
                            "-vframes", "1",
                            "-q:v", "2",
                            thumbPath});
    ffmpeg.waitForFinished(10000);

    if (ffmpeg.exitCode() != 0 || !QFile::exists(thumbPath))
        return {};

    return QUrl::fromLocalFile(thumbPath);
}

QString ApiClient::videoThumbnailFromBase64(const QString& b64) {
    // 将 base64 视频数据写入临时文件
    QByteArray data = QByteArray::fromBase64(b64.toLatin1());
    QString inputPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation) + "/chat_vid_" + QUuid::createUuid().toString(QUuid::Id128) + ".mp4";
    QFile inputFile(inputPath);
    if (!inputFile.open(QIODevice::WriteOnly)) {
        qWarning() << "Failed to write temp video file";
        return {};
    }
    inputFile.write(data);
    inputFile.close();

    QString thumbPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation) + "/chat_thumb_" + QUuid::createUuid().toString(QUuid::Id128) + ".png";

    QProcess ffmpeg;
    ffmpeg.start("ffmpeg", {"-y",
                            "-i", inputPath,
                            "-vframes", "1",
                            "-q:v", "2",
                            thumbPath});
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

QString ApiClient::saveBase64ToTempFile(const QString& b64, const QString& ext) {
    if (b64.isEmpty())
        return {};

    QByteArray data = QByteArray::fromBase64(b64.toLatin1());
    if (data.isEmpty())
        return {};

    QString path = QStandardPaths::writableLocation(QStandardPaths::TempLocation) + "/chat_media_" + QUuid::createUuid().toString(QUuid::Id128) + "." + ext;

    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        qWarning() << "Failed to write temp media file" << path;
        return {};
    }
    file.write(data);
    file.close();

    return QUrl::fromLocalFile(path).toString();
}

void ApiClient::extractVideoThumbnailAsync(const QString& postId, int mediaIndex, const QString& b64) {
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

    QString inputPath = QStandardPaths::writableLocation(QStandardPaths::TempLocation) + "/chat_vid_" + QUuid::createUuid().toString(QUuid::Id128) + ".mp4";
    QFile inputFile(inputPath);
    if (!inputFile.open(QIODevice::WriteOnly)) {
        qWarning() << "Failed to write temp video file" << inputPath;
        emit videoThumbnailExtracted(postId, mediaIndex, {});
        return;
    }
    inputFile.write(data);
    inputFile.close();

    // ── 用 Qt Multimedia 抽第一帧 ──
    QMediaPlayer* player = new QMediaPlayer(this);
    QVideoSink* sink = new QVideoSink(player);
    player->setVideoOutput(sink);

    player->setProperty("inputPath", inputPath);
    player->setProperty("postId", postId);
    player->setProperty("mediaIndex", mediaIndex);
    player->setProperty("captured", false);

    // 5 秒超时
    QTimer* timeout = new QTimer(this);
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
        QImage operator()(const QVideoFrame& frame) const {
            QImage img = frame.toImage();
            if (!img.isNull()) return img;
            QVideoFrame mapped = frame;
            if (!mapped.map(QVideoFrame::ReadOnly)) return {};
            QImage::Format fmt = QVideoFrameFormat::imageFormatFromPixelFormat(mapped.pixelFormat());
            if (fmt != QImage::Format_Invalid)
                img = QImage(mapped.bits(0), mapped.width(), mapped.height(),
                             mapped.bytesPerLine(0), fmt)
                          .copy();
            else
                img = QImage(mapped.bits(0), mapped.width(), mapped.height(),
                             mapped.bytesPerLine(0), QImage::Format_RGB32)
                          .copy();
            mapped.unmap();
            return img;
        }
    } frameToImage;

    connect(sink, &QVideoSink::videoFrameChanged, this,
            [this, player, timeout, frameToImage](const QVideoFrame& frame) {
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

QJsonObject ApiClient::withCookie() const {
    return {{"cookie", m_cookie}};
}

QJsonObject ApiClient::withCookie(const QJsonObject& extra) const {
    QJsonObject obj = extra;
    obj["cookie"] = m_cookie;
    return obj;
}

QNetworkReply* ApiClient::postJson(const QString& endpoint,
                                   const QJsonObject& body) {
    QNetworkRequest req(QUrl(m_baseUrl + endpoint));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setTransferTimeout(15000);  // 15s 超时

    QJsonDocument doc(body);
    QByteArray json = doc.toJson(QJsonDocument::Compact);
    return m_manager->post(req, json);
}

bool ApiClient::checkReply(QNetworkReply* reply, QJsonObject& out) {
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
        QString errMsg = out["error"].toString();
        // 检测到 cookie 失效 → 清除本地认证状态，UI 自动切回登录页
        if (errMsg == "Bad cookie.") {
            clearAuth();
        }
        emit errorOccurred(trBackendError(errMsg));
        return false;
    }

    return true;
}

// ─── 认证 ───

void ApiClient::checkCookie() {
    if (m_cookie.isEmpty())
        return;

    QJsonObject body{{"cookie", m_cookie}};
    QNetworkReply* reply = postJson("/check-cookie", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() != QNetworkReply::NoError) {
            emit errorOccurred(tr("网络错误: %1").arg(reply->errorString()));
            reply->deleteLater();
            return;
        }
        QByteArray data = reply->readAll();
        reply->deleteLater();

        QJsonParseError parseErr;
        QJsonDocument doc = QJsonDocument::fromJson(data, &parseErr);
        if (parseErr.error != QJsonParseError::NoError) {
            emit errorOccurred(tr("JSON 解析失败: %1").arg(parseErr.errorString()));
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

void ApiClient::startRegister(const QString& username, const QString& password,
                              const QString& nickname) {
    QJsonObject body{{"username", username},
                     {"password", password},
                     {"nickname", nickname}};

    QNetworkReply* reply = postJson("/register-request", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit registerStep1Done(
            obj["cookie"].toString(),
            obj["captcha"].toString());
    });
}

void ApiClient::verifyRegister(const QString& cookie, const QString& captcha,
                               const QString& email) {
    QJsonObject body{{"cookie", cookie},
                     {"captcha", captcha},
                     {"email", email}};

    QNetworkReply* reply = postJson("/register-verify", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit registerStep2Done();
    });
}

void ApiClient::completeRegister(const QString& cookie, const QString& emailCode) {
    QJsonObject body{{"cookie", cookie},
                     {"email_code", emailCode}};

    QNetworkReply* reply = postJson("/register-finish", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        setCookie(obj["cookie"].toString());
        emit registerSuccess(m_cookie);
    });
}

void ApiClient::startLogin(const QString& username, const QString& password) {
    QJsonObject body{{"username", username}, {"password", password}};

    QNetworkReply* reply = postJson("/login-request", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        // 如有 error 字段由 checkReply 处理
        emit loginStep1Done(
            obj["cookie"].toString(),
            obj["need_captcha"].toBool(),
            obj["need_email"].toBool(),
            obj["captcha"].toString(),
            obj["email"].toString());
    });
}

void ApiClient::loginVerifyCaptcha(const QString& cookie, const QString& captcha) {
    QJsonObject body{{"cookie", cookie}, {"captcha", captcha}};
    QNetworkReply* reply = postJson("/login-verify-captcha", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit loginStep2Done();
    });
}

void ApiClient::loginSendEmailCode(const QString& cookie) {
    QJsonObject body{{"cookie", cookie}};
    QNetworkReply* reply = postJson("/login-send-email-code", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit loginStep3Done();
    });
}

void ApiClient::loginVerifyEmail(const QString& cookie, const QString& emailCode) {
    QJsonObject body{{"cookie", cookie}, {"email_code", emailCode}};
    QNetworkReply* reply = postJson("/login-verify-email", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit loginStep3Done();
    });
}

void ApiClient::completeLogin(const QString& cookie) {
    QJsonObject body{{"cookie", cookie}};
    QNetworkReply* reply = postJson("/login-finish", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        setCookie(obj["cookie"].toString());
        emit loginSuccess(m_cookie);
    });
}

// ─── 社交 ───

void ApiClient::follow(int followee_id) {
    QJsonObject body = withCookie({{"followee_id", followee_id}});
    QNetworkReply* reply = postJson("/follow", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        // 关注成功，不发射全局errorOccurred
    });
}

void ApiClient::unfollow(int followee_id) {
    QJsonObject body = withCookie({{"followee_id", followee_id}});
    QNetworkReply* reply = postJson("/unfollow", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        (void)obj;
        if (!checkReply(reply, obj))
            return;
        // 取消关注成功，不发射全局errorOccurred
    });
}

void ApiClient::fetchFollowList() {
    QJsonObject body = withCookie();
    QNetworkReply* reply = postJson("/get-follow-list", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<UserInfo> followers;
        QList<UserInfo> followees;
        for (const auto& v : obj["followers"].toArray())
            followers.append(userFromJson(v.toObject()));
        for (const auto& v : obj["followees"].toArray())
            followees.append(userFromJson(v.toObject()));

        emit followListFetched(followers, followees);
    });
}

// ─── 帖子 ───

void ApiClient::publishPost(const QString& text, const QStringList& media) {
    QJsonArray arr;
    for (const auto& m : media)
        arr.append(m);
    QJsonObject body = withCookie({{"text", text}, {"media", arr}});
    QNetworkReply* reply = postJson("/pub-post", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postPublished();
    });
}

void ApiClient::fetchTimeline(int count) {
    QJsonObject body = withCookie({{"count", count}});
    QNetworkReply* reply = postJson("/post-fetch", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<int> ids;
        for (const auto& v : obj["posts"].toArray())
            ids.append(v.toInt());
        emit timelineFetched(ids, obj["count"].toInt());
    });
}

void ApiClient::getPost(int post_id) {
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply* reply = postJson("/get-post", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postFetched(obj.toVariantMap());
    });
}

// ─── 互动 ───

void ApiClient::likePost(int post_id) {
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply* reply = postJson("/like", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postLiked();
    });
}

void ApiClient::unlikePost(int post_id) {
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply* reply = postJson("/unlike", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit postUnliked();
    });
}

void ApiClient::comment(int post_id, const QString& content) {
    QJsonObject body = withCookie({{"post_id", post_id}, {"content", content}});
    QNetworkReply* reply = postJson("/comment", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit commentPosted();
    });
}

void ApiClient::fetchComments(int post_id) {
    QJsonObject body = withCookie({{"post_id", post_id}});
    QNetworkReply* reply = postJson("/get-comments", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QVariantList comments;
        for (const auto& v : obj["comments"].toArray())
            comments.append(v.toObject().toVariantMap());
        emit commentsFetched(comments);
    });
}

// ─── 私信 ───

void ApiClient::sendMessage(int to_whom_id, const QString& content) {
    QJsonObject body =
        withCookie({{"to_whom_id", to_whom_id}, {"content", content}});
    QNetworkReply* reply = postJson("/send-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit messageSent();
    });
}

void ApiClient::receiveMessages() {
    QJsonObject body = withCookie();
    QNetworkReply* reply = postJson("/recv-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<MessageInfo> msgs;
        for (const auto& v : obj["msgs"].toArray())
            msgs.append(msgFromJson(v.toObject()));
        emit messagesReceived(msgs);
    });
}

// ─── 头像/签名/个人资料 ───

void ApiClient::fetchProfile() {
    QJsonObject body = withCookie();
    QNetworkReply* reply = postJson("/check-cookie", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit profileFetched(obj.toVariantMap());
    });
}

void ApiClient::updateProfile(const QString& nickname,
                              const QString& avatar,
                              const QString& signature) {
    auto pending = std::make_shared<int>(0);
    auto failed = std::make_shared<bool>(false);

    auto checkDone = [this, pending, failed]() {
        if (*pending == 0 && !*failed) {
            emit profileUpdated();
        }
    };

    // 更新昵称
    if (!nickname.isEmpty()) {
        (*pending)++;
        QJsonObject body = withCookie({{"nickname", nickname}});
        QNetworkReply* reply = postJson("/edit-profile", body);
        connect(reply, &QNetworkReply::finished, this, [this, reply, pending, failed, checkDone]() {
            QJsonObject obj;
            if (!checkReply(reply, obj)) {
                *failed = true;
            }
            (*pending)--;
            checkDone();
        });
    }
    // 更新头像和签名
    if (!avatar.isEmpty() || !signature.isEmpty()) {
        (*pending)++;
        QJsonObject body = withCookie();
        if (!avatar.isEmpty()) body["avatar"] = avatar;
        if (!signature.isEmpty()) body["signature"] = signature;
        QNetworkReply* reply = postJson("/avatar", body);
        connect(reply, &QNetworkReply::finished, this, [this, reply, pending, failed, checkDone]() {
            QJsonObject obj;
            if (!checkReply(reply, obj)) {
                *failed = true;
            }
            (*pending)--;
            checkDone();
        });
    }
    // 没有要更新的内容
    checkDone();
}

void ApiClient::patchAvatar(const QString& avatar, const QString& signature) {
    QJsonObject body = withCookie();
    if (!avatar.isEmpty())
        body["avatar"] = avatar;
    if (!signature.isEmpty())
        body["signature"] = signature;
    QNetworkReply* reply = postJson("/avatar", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit avatarPatched();
    });
}

void ApiClient::fetchAvatar(int user_id) {
    QUrl url(m_baseUrl + "/avatar");
    QUrlQuery query;
    query.addQueryItem("user_id", QString::number(user_id));
    url.setQuery(query);

    QNetworkRequest req(url);
    req.setTransferTimeout(15000);

    QNetworkReply* reply = m_manager->get(req);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        if (reply->error() != QNetworkReply::NoError) {
            emit errorOccurred(tr("网络错误: %1").arg(reply->errorString()));
            reply->deleteLater();
            return;
        }
        QByteArray data = reply->readAll();
        reply->deleteLater();

        QJsonParseError err;
        QJsonDocument doc = QJsonDocument::fromJson(data, &err);
        if (err.error != QJsonParseError::NoError) {
            emit errorOccurred(tr("JSON 解析失败: %1").arg(err.errorString()));
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

void ApiClient::createGroup(const QString& name) {
    QJsonObject body = withCookie({{"name", name}});
    QNetworkReply* reply = postJson("/create-group", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupCreated(obj["group_id"].toInt());
    });
}

void ApiClient::joinGroup(int group_id) {
    QJsonObject body = withCookie({{"group_id", group_id}});
    QNetworkReply* reply = postJson("/join-group", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupJoined();
    });
}

void ApiClient::leaveGroup(int group_id) {
    QJsonObject body = withCookie({{"group_id", group_id}});
    QNetworkReply* reply = postJson("/leave-group", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupLeft();
    });
}

void ApiClient::sendGroupMessage(int group_id, const QString& content) {
    QJsonObject body =
        withCookie({{"group_id", group_id}, {"content", content}});
    QNetworkReply* reply = postJson("/send-group-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;
        emit groupMessageSent();
    });
}

void ApiClient::receiveGroupMessages(int group_id, int count) {
    QJsonObject body = withCookie({{"group_id", group_id}, {"count", count}});
    QNetworkReply* reply = postJson("/recv-group-msg", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::receiveGroupMessages] 请求失败";
            return;
        }

        QList<GroupMessageInfo> msgs;
        for (const auto& v : obj["messages"].toArray())
            msgs.append(groupMsgFromJson(v.toObject()));
        emit groupMessagesReceived(msgs);
    });
}

void ApiClient::fetchGroupMembers(int group_id) {
    QJsonObject body = withCookie({{"group_id", group_id}});
    QNetworkReply* reply = postJson("/get-group-members", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<UserInfo> members;
        for (const auto& v : obj["members"].toArray())
            members.append(userFromJson(v.toObject()));
        emit groupMembersFetched(members);
    });
}

void ApiClient::fetchMyGroups() {
    QJsonObject body = withCookie();
    QNetworkReply* reply = postJson("/get-my-groups", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj))
            return;

        QList<GroupInfo> groups;
        for (const auto& v : obj["groups"].toArray())
            groups.append(groupFromJson(v.toObject()));
        emit myGroupsFetched(groups);
    });
}

// ═══════════════════════════════════════════════════════════════
// ── 消息功能（新增）──
// 以下方法依赖后端新增端点，当前为桩实现。
// 后端完成后取消注释实际逻辑即可。
// ═══════════════════════════════════════════════════════════════

void ApiClient::fetchConversations() {
    qDebug() << "[ApiClient::fetchConversations] 请求会话列表...";
    QJsonObject body = withCookie();
    QNetworkReply* reply = postJson("/get-conversations", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::fetchConversations] 请求失败";
            return;
        }

        QVariantList conversations;
        for (const auto& v : obj["conversations"].toArray())
            conversations.append(v.toObject().toVariantMap());
        qDebug() << "[ApiClient::fetchConversations] 成功获取" << conversations.size() << "个会话";
        emit conversationsFetched(conversations);
    });
}

void ApiClient::hideConversation(int conversation_id) {
    qDebug() << "[ApiClient::hideConversation] 隐藏会话 id=" << conversation_id;
    QJsonObject body = withCookie({{"conversation_id", conversation_id}});
    QNetworkReply* reply = postJson("/hide-conversation", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply, conversation_id]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::hideConversation] 隐藏失败 id=" << conversation_id;
            return;
        }
        qDebug() << "[ApiClient::hideConversation] 成功隐藏 id=" << conversation_id;
        emit conversationHidden(conversation_id);
    });
}

void ApiClient::fetchPrivateMessages(int with_user_id, int before_id, int count) {
    qDebug() << "[ApiClient::fetchPrivateMessages] 请求私聊历史 with_user_id=" << with_user_id
             << "before_id=" << before_id << "count=" << count;
    QJsonObject body = withCookie({{"with_user_id", with_user_id},
                                   {"before_id", before_id},
                                   {"count", count}});
    QNetworkReply* reply = postJson("/get-private-messages", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::fetchPrivateMessages] 请求失败";
            return;
        }

        QVariantList messages;
        for (const auto& v : obj["messages"].toArray())
            messages.append(v.toObject().toVariantMap());
        bool hasMore = obj["has_more"].toBool(false);
        qDebug() << "[ApiClient::fetchPrivateMessages] 成功获取" << messages.size()
                 << "条消息, hasMore=" << hasMore;
        emit privateMessagesFetched(messages, hasMore);
    });
}

void ApiClient::searchContacts(const QString& keyword, const QString& type) {
    qDebug() << "[ApiClient::searchContacts] 搜索 keyword=" << keyword << "type=" << type;

    // ── 输入校验 ──
    QString trimmed = keyword.trimmed();
    if (trimmed.isEmpty()) {
        qDebug() << "[ApiClient::searchContacts] 关键词为空，跳过请求";
        emit contactsSearched({}, {});
        return;
    }
    if (trimmed.length() > 100) {
        qDebug() << "[ApiClient::searchContacts] 关键词过长(" << trimmed.length() << ")，截断至100字符";
        trimmed = trimmed.left(100);
    }

    QJsonObject body = withCookie({{"keyword", trimmed}, {"type", type}});
    QNetworkReply* reply = postJson("/search-contacts", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::searchContacts] 搜索失败";
            return;
        }

        QVariantList users;
        for (const auto& v : obj["users"].toArray())
            users.append(v.toObject().toVariantMap());
        QVariantList groups;
        for (const auto& v : obj["groups"].toArray())
            groups.append(v.toObject().toVariantMap());
        qDebug() << "[ApiClient::searchContacts] 搜索结果: users=" << users.size()
                 << "groups=" << groups.size();
        emit contactsSearched(users, groups);
    });
}

void ApiClient::fetchContacts() {
    qDebug() << "[ApiClient::fetchContacts] 请求联系人列表...";
    QJsonObject body = withCookie();
    QNetworkReply* reply = postJson("/get-contacts", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::fetchContacts] 请求失败";
            return;
        }

        QVariantList contacts;
        for (const auto& v : obj["contacts"].toArray())
            contacts.append(v.toObject().toVariantMap());
        QVariantList followedOnly;
        for (const auto& v : obj["followed_only"].toArray())
            followedOnly.append(v.toObject().toVariantMap());
        qDebug() << "[ApiClient::fetchContacts] 成功: contacts=" << contacts.size()
                 << "followedOnly=" << followedOnly.size();
        emit contactsFetched(contacts, followedOnly);
    });
}

void ApiClient::fetchUserDetail(int user_id) {
    qDebug() << "[ApiClient::fetchUserDetail] 请求用户详情 user_id=" << user_id;
    QJsonObject body = withCookie({{"user_id", user_id}});
    QNetworkReply* reply = postJson("/get-user-detail", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::fetchUserDetail] 请求失败 user_id="
                     << reply->property("req_user_id").toInt();
            return;
        }
        qDebug() << "[ApiClient::fetchUserDetail] 成功获取用户详情";
        emit userDetailFetched(obj.toVariantMap());
    });
}

void ApiClient::fetchGroupDetail(int group_id) {
    qDebug() << "[ApiClient::fetchGroupDetail] 请求群组详情 group_id=" << group_id;
    QJsonObject body = withCookie({{"group_id", group_id}});
    QNetworkReply* reply = postJson("/get-group-detail", body);
    connect(reply, &QNetworkReply::finished, this, [this, reply]() {
        QJsonObject obj;
        if (!checkReply(reply, obj)) {
            qDebug() << "[ApiClient::fetchGroupDetail] 请求失败 group_id="
                     << reply->property("req_group_id").toInt();
            return;
        }
        qDebug() << "[ApiClient::fetchGroupDetail] 成功获取群组详情";
        emit groupDetailFetched(obj.toVariantMap());
    });
}
