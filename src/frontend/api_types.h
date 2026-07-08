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
    int id = 0;             // 消息ID（新增，用于游标分页）
    int sender_id = 0;
    QString sender_name;    // 发送者昵称（新增）
    QString sent_at;
    QString content;
    bool is_read = false;   // 已读标记（新增）
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
    QString avatar;         // 群头像 base64（新增）
    QString role;
    QString joined_at;
};

// ─── 会话数据（新增：消息功能） ───

struct ConversationInfo {
    int id = 0;
    QString type;           // "private" | "group"
    int target_id = 0;      // 私聊:对方user_id / 群聊:group_id
    QString target_name;    // 对方昵称 或 群名称
    QString target_avatar;  // 对方头像 或 群头像 (base64)
    QString last_message;   // 最后一条消息预览
    QString last_message_time;
    int unread_count = 0;
};

// ─── 搜索结果数据（新增：消息功能） ───

struct ContactSearchResult {
    int id = 0;
    QString username;
    QString nickname;
    QString avatar;
    bool is_following = false;
    bool is_mutual = false;
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
Q_DECLARE_METATYPE(ConversationInfo)
Q_DECLARE_METATYPE(ContactSearchResult)

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
    MessageInfo m;
    m.id = obj["id"].toInt();
    m.sender_id = obj["sender_id"].toInt();
    m.sender_name = obj["sender_name"].toString();
    m.sent_at = obj["sent_at"].toString();
    m.content = obj["content"].toString();
    m.is_read = obj["is_read"].toBool(true);
    return m;
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
    GroupInfo g;
    g.id = obj["id"].toInt();
    g.name = obj["name"].toString();
    g.owner_id = obj["owner_id"].toInt();
    g.avatar = obj["avatar"].toString();
    g.role = obj["role"].toString();
    g.joined_at = obj["joined_at"].toString();
    return g;
}

// ─── 新增：会话 & 搜索 JSON 解析 ───

inline ConversationInfo convFromJson(const QJsonObject &obj) {
    ConversationInfo c;
    c.id = obj["id"].toInt();
    c.type = obj["type"].toString();
    c.target_id = obj["target_id"].toInt();
    c.target_name = obj["target_name"].toString();
    c.target_avatar = obj["target_avatar"].toString();
    c.last_message = obj["last_message"].toString();
    c.last_message_time = obj["last_message_time"].toString();
    c.unread_count = obj["unread_count"].toInt();
    return c;
}

inline ContactSearchResult searchResultFromJson(const QJsonObject &obj) {
    ContactSearchResult r;
    r.id = obj["id"].toInt();
    r.username = obj["username"].toString();
    r.nickname = obj["nickname"].toString();
    r.avatar = obj["avatar"].toString();
    r.is_following = obj["is_following"].toBool();
    r.is_mutual = obj["is_mutual"].toBool();
    return r;
}

#endif // API_TYPES_H
