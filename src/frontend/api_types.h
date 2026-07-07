#ifndef API_TYPES_H
#define API_TYPES_H

#include <QString>
#include <QJsonObject>
#include <QJsonArray>
#include <QDateTime>
#include <QMetaType>
#include <optional>

// ─── 建⽤户数据 ───

struct UserInfo {
    int id = 0;
    QString username;
    QString nickname;
    QString avatar;
    QString signature;
    QString role;       // 群成员角色（非群成员留空）
    QString joined_at;  // 入群时间（非群成员留空）
};

// ─── 帖子数据 ───

struct MediaItem {
    int offset = 0;
    QString content;    // base64 编码的媒体数据
};

struct PostInfo {
    int id = 0;
    int publisher_id = 0;
    QString username;
    QString nickname;
    QString content;
    int like_num = 0;
    QString created_at;
    QList<MediaItem> media;
};

// ─── 评论数据 ───

struct CommentInfo {
    int id = 0;
    QString username;
    QString nickname;
    QString content;
    QString commented_at;
};

// ─── 私信数据 ───

struct MessageInfo {
    int sender_id = 0;
    QString sent_at;
    QString content;
};

// ─── 群消息数据 ───

struct GroupMessageInfo {
    int id = 0;
    int sender_id = 0;
    QString username;
    QString nickname;
    QString content;
    QString sent_at;
};

// ─── 群组数据 ───

struct GroupInfo {
    int id = 0;
    QString name;
    int owner_id = 0;
    QString role;
    QString joined_at;
};

// ─── 请求/响应辅助 ───

// 通用错误响应
struct ApiError {
    QString message;
    bool hasError = false;
};

Q_DECLARE_METATYPE(UserInfo)
Q_DECLARE_METATYPE(MediaItem)
Q_DECLARE_METATYPE(PostInfo)
Q_DECLARE_METATYPE(CommentInfo)
Q_DECLARE_METATYPE(MessageInfo)
Q_DECLARE_METATYPE(GroupMessageInfo)
Q_DECLARE_METATYPE(GroupInfo)

// ─── JSON 序列化辅助 ───

inline QJsonObject toJson(const UserInfo &u) {
    return {{"id", u.id}, {"username", u.username}, {"nickname", u.nickname},
            {"avatar", u.avatar}, {"signature", u.signature},
            {"role", u.role}, {"joined_at", u.joined_at}};
}

inline UserInfo userFromJson(const QJsonObject &obj) {
    return {obj["id"].toInt(),          obj["username"].toString(),
            obj["nickname"].toString(), obj["avatar"].toString(),
            obj["signature"].toString(), obj["role"].toString(),
            obj["joined_at"].toString()};
}

inline QJsonObject toJson(const MediaItem &m) {
    return {{"offset", m.offset}, {"content", m.content}};
}

inline MediaItem mediaFromJson(const QJsonObject &obj) {
    return {obj["offset"].toInt(), obj["content"].toString()};
}

inline PostInfo postFromJson(const QJsonObject &obj) {
    PostInfo p;
    p.id = obj["id"].toInt();
    p.publisher_id = obj["publisher_id"].toInt();
    p.username = obj["username"].toString();
    p.nickname = obj["nickname"].toString();
    p.content = obj["content"].toString();
    p.like_num = obj["like_num"].toInt();
    p.created_at = obj["created_at"].toString();
    for (const auto &m : obj["media"].toArray())
        p.media.append(mediaFromJson(m.toObject()));
    return p;
}

inline CommentInfo commentFromJson(const QJsonObject &obj) {
    return {obj["id"].toInt(),       obj["username"].toString(),
            obj["nickname"].toString(), obj["content"].toString(),
            obj["commented_at"].toString()};
}

inline MessageInfo msgFromJson(const QJsonObject &obj) {
    return {obj["sender_id"].toInt(), obj["sent_at"].toString(),
            obj["content"].toString()};
}

inline GroupMessageInfo groupMsgFromJson(const QJsonObject &obj) {
    GroupMessageInfo m;
    m.id = obj["id"].toInt();
    m.sender_id = obj["sender_id"].toInt();
    m.username = obj["username"].toString();
    m.nickname = obj["nickname"].toString();
    m.content = obj["content"].toString();
    m.sent_at = obj["sent_at"].toString();
    return m;
}

inline GroupInfo groupFromJson(const QJsonObject &obj) {
    return {obj["id"].toInt(),     obj["name"].toString(),
            obj["owner_id"].toInt(), obj["role"].toString(),
            obj["joined_at"].toString()};
}

#endif // API_TYPES_H
