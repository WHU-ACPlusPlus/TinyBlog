/****************************************************************************
** Meta object code from reading C++ file 'api_client.h'
**
** Created by: The Qt Meta Object Compiler version 69 (Qt 6.11.1)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include "../../../api_client.h"
#include <QtNetwork/QSslError>
#include <QtCore/qmetatype.h>
#include <QtCore/QList>

#include <QtCore/qtmochelpers.h>

#include <memory>


#include <QtCore/qxptype_traits.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'api_client.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 69
#error "This file was generated using the moc from 6.11.1. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

#ifndef Q_CONSTINIT
#define Q_CONSTINIT
#endif

QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
QT_WARNING_DISABLE_GCC("-Wuseless-cast")
namespace {
struct qt_meta_tag_ZN9ApiClientE_t {};
} // unnamed namespace

template <> constexpr inline auto ApiClient::qt_create_metaobjectdata<qt_meta_tag_ZN9ApiClientE_t>()
{
    namespace QMC = QtMocConstants;
    QtMocHelpers::StringRefStorage qt_stringData {
        "ApiClient",
        "loggedInChanged",
        "",
        "baseUrlChanged",
        "languageChanged",
        "errorOccurred",
        "message",
        "registerSuccess",
        "cookie",
        "registerStep1Done",
        "captcha",
        "registerStep2Done",
        "loginStep1Done",
        "needCaptcha",
        "needEmail",
        "email",
        "loginStep2Done",
        "loginStep3Done",
        "loginSuccess",
        "cookieCheckComplete",
        "valid",
        "userId",
        "followListFetched",
        "QList<UserInfo>",
        "followers",
        "followees",
        "postPublished",
        "timelineFetched",
        "QList<int>",
        "postIds",
        "count",
        "postFetched",
        "QVariantMap",
        "post",
        "postLiked",
        "postUnliked",
        "commentPosted",
        "commentsFetched",
        "QVariantList",
        "comments",
        "videoThumbnailExtracted",
        "postId",
        "mediaIndex",
        "thumbnailB64",
        "mediaFilesPicked",
        "files",
        "messageSent",
        "messagesReceived",
        "QList<MessageInfo>",
        "messages",
        "profileFetched",
        "profile",
        "profileUpdated",
        "avatarPatched",
        "avatarFetched",
        "user_id",
        "avatar",
        "signature",
        "groupCreated",
        "group_id",
        "groupJoined",
        "groupLeft",
        "groupMessageSent",
        "groupMessagesReceived",
        "QList<GroupMessageInfo>",
        "groupMembersFetched",
        "members",
        "myGroupsFetched",
        "QList<GroupInfo>",
        "groups",
        "userPostsFetched",
        "myPostsFetched",
        "posts",
        "followListFetchedForQml",
        "conversationsFetched",
        "conversations",
        "conversationHidden",
        "conversation_id",
        "privateMessagesFetched",
        "hasMore",
        "contactsSearched",
        "users",
        "contactsFetched",
        "contacts",
        "followedOnly",
        "userDetailFetched",
        "detail",
        "groupDetailFetched",
        "startRegister",
        "username",
        "password",
        "nickname",
        "verifyRegister",
        "completeRegister",
        "emailCode",
        "startLogin",
        "loginVerifyCaptcha",
        "loginSendEmailCode",
        "loginVerifyEmail",
        "completeLogin",
        "checkCookie",
        "follow",
        "followee_id",
        "unfollow",
        "fetchFollowList",
        "publishPost",
        "text",
        "media",
        "fetchTimeline",
        "getPost",
        "post_id",
        "likePost",
        "unlikePost",
        "comment",
        "content",
        "fetchComments",
        "sendMessage",
        "to_whom_id",
        "receiveMessages",
        "fetchProfile",
        "updateProfile",
        "patchAvatar",
        "fetchAvatar",
        "createGroup",
        "name",
        "joinGroup",
        "leaveGroup",
        "sendGroupMessage",
        "receiveGroupMessages",
        "fetchGroupMembers",
        "fetchMyGroups",
        "fetchConversations",
        "hideConversation",
        "fetchPrivateMessages",
        "with_user_id",
        "before_id",
        "searchContacts",
        "keyword",
        "type",
        "fetchContacts",
        "fetchUserPosts",
        "publisher_id",
        "fetchMyPostsDetail",
        "fetchUserDetail",
        "fetchGroupDetail",
        "setCookie",
        "token",
        "clearAuth",
        "setLanguage",
        "locale",
        "readFileAsBase64",
        "QUrl",
        "fileUrl",
        "maxSizeBytes",
        "generateVideoThumbnail",
        "videoUrl",
        "videoThumbnailFromBase64",
        "b64",
        "saveBase64ToTempFile",
        "ext",
        "extractVideoThumbnailAsync",
        "isLoggedIn",
        "baseUrl",
        "isAndroid"
    };

    QtMocHelpers::UintData qt_methods {
        // Signal 'loggedInChanged'
        QtMocHelpers::SignalData<void()>(1, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'baseUrlChanged'
        QtMocHelpers::SignalData<void()>(3, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'languageChanged'
        QtMocHelpers::SignalData<void()>(4, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'errorOccurred'
        QtMocHelpers::SignalData<void(const QString &)>(5, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 6 },
        }}),
        // Signal 'registerSuccess'
        QtMocHelpers::SignalData<void(const QString &)>(7, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 },
        }}),
        // Signal 'registerStep1Done'
        QtMocHelpers::SignalData<void(const QString &, const QString &)>(9, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 }, { QMetaType::QString, 10 },
        }}),
        // Signal 'registerStep2Done'
        QtMocHelpers::SignalData<void()>(11, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'loginStep1Done'
        QtMocHelpers::SignalData<void(const QString &, bool, bool, const QString &, const QString &)>(12, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 }, { QMetaType::Bool, 13 }, { QMetaType::Bool, 14 }, { QMetaType::QString, 10 },
            { QMetaType::QString, 15 },
        }}),
        // Signal 'loginStep2Done'
        QtMocHelpers::SignalData<void()>(16, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'loginStep3Done'
        QtMocHelpers::SignalData<void()>(17, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'loginSuccess'
        QtMocHelpers::SignalData<void(const QString &)>(18, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 },
        }}),
        // Signal 'cookieCheckComplete'
        QtMocHelpers::SignalData<void(bool, int)>(19, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Bool, 20 }, { QMetaType::Int, 21 },
        }}),
        // Signal 'followListFetched'
        QtMocHelpers::SignalData<void(const QList<UserInfo> &, const QList<UserInfo> &)>(22, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 23, 24 }, { 0x80000000 | 23, 25 },
        }}),
        // Signal 'postPublished'
        QtMocHelpers::SignalData<void()>(26, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'timelineFetched'
        QtMocHelpers::SignalData<void(const QList<int> &, int)>(27, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 28, 29 }, { QMetaType::Int, 30 },
        }}),
        // Signal 'postFetched'
        QtMocHelpers::SignalData<void(const QVariantMap &)>(31, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 32, 33 },
        }}),
        // Signal 'postLiked'
        QtMocHelpers::SignalData<void()>(34, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'postUnliked'
        QtMocHelpers::SignalData<void()>(35, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'commentPosted'
        QtMocHelpers::SignalData<void()>(36, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'commentsFetched'
        QtMocHelpers::SignalData<void(const QVariantList &)>(37, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 39 },
        }}),
        // Signal 'videoThumbnailExtracted'
        QtMocHelpers::SignalData<void(const QString &, int, const QString &)>(40, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 41 }, { QMetaType::Int, 42 }, { QMetaType::QString, 43 },
        }}),
        // Signal 'mediaFilesPicked'
        QtMocHelpers::SignalData<void(const QVariantList &)>(44, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 45 },
        }}),
        // Signal 'messageSent'
        QtMocHelpers::SignalData<void()>(46, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'messagesReceived'
        QtMocHelpers::SignalData<void(const QList<MessageInfo> &)>(47, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 48, 49 },
        }}),
        // Signal 'profileFetched'
        QtMocHelpers::SignalData<void(const QVariantMap &)>(50, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 32, 51 },
        }}),
        // Signal 'profileUpdated'
        QtMocHelpers::SignalData<void()>(52, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'avatarPatched'
        QtMocHelpers::SignalData<void()>(53, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'avatarFetched'
        QtMocHelpers::SignalData<void(int, const QString &, const QString &)>(54, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 55 }, { QMetaType::QString, 56 }, { QMetaType::QString, 57 },
        }}),
        // Signal 'groupCreated'
        QtMocHelpers::SignalData<void(int)>(58, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 59 },
        }}),
        // Signal 'groupJoined'
        QtMocHelpers::SignalData<void()>(60, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'groupLeft'
        QtMocHelpers::SignalData<void()>(61, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'groupMessageSent'
        QtMocHelpers::SignalData<void()>(62, 2, QMC::AccessPublic, QMetaType::Void),
        // Signal 'groupMessagesReceived'
        QtMocHelpers::SignalData<void(const QList<GroupMessageInfo> &)>(63, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 64, 49 },
        }}),
        // Signal 'groupMembersFetched'
        QtMocHelpers::SignalData<void(const QList<UserInfo> &)>(65, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 23, 66 },
        }}),
        // Signal 'myGroupsFetched'
        QtMocHelpers::SignalData<void(const QList<GroupInfo> &)>(67, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 68, 69 },
        }}),
        // Signal 'groupMessagesReceived'
        QtMocHelpers::SignalData<void(const QVariantList &)>(63, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 49 },
        }}),
        // Signal 'userPostsFetched'
        QtMocHelpers::SignalData<void(const QVariantList &)>(70, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 29 },
        }}),
        // Signal 'myPostsFetched'
        QtMocHelpers::SignalData<void(const QVariantList &)>(71, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 72 },
        }}),
        // Signal 'followListFetchedForQml'
        QtMocHelpers::SignalData<void(const QVariantList &, const QVariantList &)>(73, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 24 }, { 0x80000000 | 38, 25 },
        }}),
        // Signal 'conversationsFetched'
        QtMocHelpers::SignalData<void(const QVariantList &)>(74, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 75 },
        }}),
        // Signal 'conversationHidden'
        QtMocHelpers::SignalData<void(int)>(76, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 77 },
        }}),
        // Signal 'privateMessagesFetched'
        QtMocHelpers::SignalData<void(const QVariantList &, bool)>(78, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 49 }, { QMetaType::Bool, 79 },
        }}),
        // Signal 'contactsSearched'
        QtMocHelpers::SignalData<void(const QVariantList &, const QVariantList &)>(80, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 81 }, { 0x80000000 | 38, 69 },
        }}),
        // Signal 'contactsFetched'
        QtMocHelpers::SignalData<void(const QVariantList &, const QVariantList &)>(82, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 38, 83 }, { 0x80000000 | 38, 84 },
        }}),
        // Signal 'userDetailFetched'
        QtMocHelpers::SignalData<void(const QVariantMap &)>(85, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 32, 86 },
        }}),
        // Signal 'groupDetailFetched'
        QtMocHelpers::SignalData<void(const QVariantMap &)>(87, 2, QMC::AccessPublic, QMetaType::Void, {{
            { 0x80000000 | 32, 86 },
        }}),
        // Slot 'startRegister'
        QtMocHelpers::SlotData<void(const QString &, const QString &, const QString &)>(88, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 89 }, { QMetaType::QString, 90 }, { QMetaType::QString, 91 },
        }}),
        // Slot 'verifyRegister'
        QtMocHelpers::SlotData<void(const QString &, const QString &, const QString &)>(92, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 }, { QMetaType::QString, 10 }, { QMetaType::QString, 15 },
        }}),
        // Slot 'completeRegister'
        QtMocHelpers::SlotData<void(const QString &, const QString &)>(93, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 }, { QMetaType::QString, 94 },
        }}),
        // Slot 'startLogin'
        QtMocHelpers::SlotData<void(const QString &, const QString &)>(95, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 89 }, { QMetaType::QString, 90 },
        }}),
        // Slot 'loginVerifyCaptcha'
        QtMocHelpers::SlotData<void(const QString &, const QString &)>(96, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 }, { QMetaType::QString, 10 },
        }}),
        // Slot 'loginSendEmailCode'
        QtMocHelpers::SlotData<void(const QString &)>(97, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 },
        }}),
        // Slot 'loginVerifyEmail'
        QtMocHelpers::SlotData<void(const QString &, const QString &)>(98, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 }, { QMetaType::QString, 94 },
        }}),
        // Slot 'completeLogin'
        QtMocHelpers::SlotData<void(const QString &)>(99, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 8 },
        }}),
        // Slot 'checkCookie'
        QtMocHelpers::SlotData<void()>(100, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'follow'
        QtMocHelpers::SlotData<void(int)>(101, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 102 },
        }}),
        // Slot 'unfollow'
        QtMocHelpers::SlotData<void(int)>(103, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 102 },
        }}),
        // Slot 'fetchFollowList'
        QtMocHelpers::SlotData<void()>(104, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'publishPost'
        QtMocHelpers::SlotData<void(const QString &, const QStringList &)>(105, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 106 }, { QMetaType::QStringList, 107 },
        }}),
        // Slot 'publishPost'
        QtMocHelpers::SlotData<void(const QString &)>(105, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::QString, 106 },
        }}),
        // Slot 'fetchTimeline'
        QtMocHelpers::SlotData<void(int)>(108, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 30 },
        }}),
        // Slot 'fetchTimeline'
        QtMocHelpers::SlotData<void()>(108, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Slot 'getPost'
        QtMocHelpers::SlotData<void(int)>(109, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 110 },
        }}),
        // Slot 'likePost'
        QtMocHelpers::SlotData<void(int)>(111, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 110 },
        }}),
        // Slot 'unlikePost'
        QtMocHelpers::SlotData<void(int)>(112, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 110 },
        }}),
        // Slot 'comment'
        QtMocHelpers::SlotData<void(int, const QString &)>(113, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 110 }, { QMetaType::QString, 114 },
        }}),
        // Slot 'fetchComments'
        QtMocHelpers::SlotData<void(int)>(115, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 110 },
        }}),
        // Slot 'sendMessage'
        QtMocHelpers::SlotData<void(int, const QString &)>(116, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 117 }, { QMetaType::QString, 114 },
        }}),
        // Slot 'receiveMessages'
        QtMocHelpers::SlotData<void()>(118, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'fetchProfile'
        QtMocHelpers::SlotData<void()>(119, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'updateProfile'
        QtMocHelpers::SlotData<void(const QString &, const QString &, const QString &)>(120, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 91 }, { QMetaType::QString, 56 }, { QMetaType::QString, 57 },
        }}),
        // Slot 'updateProfile'
        QtMocHelpers::SlotData<void(const QString &, const QString &)>(120, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::QString, 91 }, { QMetaType::QString, 56 },
        }}),
        // Slot 'updateProfile'
        QtMocHelpers::SlotData<void(const QString &)>(120, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::QString, 91 },
        }}),
        // Slot 'updateProfile'
        QtMocHelpers::SlotData<void()>(120, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Slot 'patchAvatar'
        QtMocHelpers::SlotData<void(const QString &, const QString &)>(121, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 56 }, { QMetaType::QString, 57 },
        }}),
        // Slot 'patchAvatar'
        QtMocHelpers::SlotData<void(const QString &)>(121, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::QString, 56 },
        }}),
        // Slot 'patchAvatar'
        QtMocHelpers::SlotData<void()>(121, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void),
        // Slot 'fetchAvatar'
        QtMocHelpers::SlotData<void(int)>(122, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 55 },
        }}),
        // Slot 'createGroup'
        QtMocHelpers::SlotData<void(const QString &)>(123, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 124 },
        }}),
        // Slot 'joinGroup'
        QtMocHelpers::SlotData<void(int)>(125, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 59 },
        }}),
        // Slot 'leaveGroup'
        QtMocHelpers::SlotData<void(int)>(126, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 59 },
        }}),
        // Slot 'sendGroupMessage'
        QtMocHelpers::SlotData<void(int, const QString &)>(127, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 59 }, { QMetaType::QString, 114 },
        }}),
        // Slot 'receiveGroupMessages'
        QtMocHelpers::SlotData<void(int, int)>(128, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 59 }, { QMetaType::Int, 30 },
        }}),
        // Slot 'receiveGroupMessages'
        QtMocHelpers::SlotData<void(int)>(128, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::Int, 59 },
        }}),
        // Slot 'fetchGroupMembers'
        QtMocHelpers::SlotData<void(int)>(129, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 59 },
        }}),
        // Slot 'fetchMyGroups'
        QtMocHelpers::SlotData<void()>(130, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'fetchConversations'
        QtMocHelpers::SlotData<void()>(131, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'hideConversation'
        QtMocHelpers::SlotData<void(int)>(132, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 77 },
        }}),
        // Slot 'fetchPrivateMessages'
        QtMocHelpers::SlotData<void(int, int, int)>(133, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 134 }, { QMetaType::Int, 135 }, { QMetaType::Int, 30 },
        }}),
        // Slot 'fetchPrivateMessages'
        QtMocHelpers::SlotData<void(int, int)>(133, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::Int, 134 }, { QMetaType::Int, 135 },
        }}),
        // Slot 'fetchPrivateMessages'
        QtMocHelpers::SlotData<void(int)>(133, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::Int, 134 },
        }}),
        // Slot 'searchContacts'
        QtMocHelpers::SlotData<void(const QString &, const QString &)>(136, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 137 }, { QMetaType::QString, 138 },
        }}),
        // Slot 'searchContacts'
        QtMocHelpers::SlotData<void(const QString &)>(136, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::Void, {{
            { QMetaType::QString, 137 },
        }}),
        // Slot 'fetchContacts'
        QtMocHelpers::SlotData<void()>(139, 2, QMC::AccessPublic, QMetaType::Void),
        // Slot 'fetchUserPosts'
        QtMocHelpers::SlotData<void(int)>(140, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 141 },
        }}),
        // Slot 'fetchMyPostsDetail'
        QtMocHelpers::SlotData<void(int)>(142, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 141 },
        }}),
        // Slot 'fetchUserDetail'
        QtMocHelpers::SlotData<void(int)>(143, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 55 },
        }}),
        // Slot 'fetchGroupDetail'
        QtMocHelpers::SlotData<void(int)>(144, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::Int, 59 },
        }}),
        // Method 'setCookie'
        QtMocHelpers::MethodData<void(const QString &)>(145, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 146 },
        }}),
        // Method 'clearAuth'
        QtMocHelpers::MethodData<void()>(147, 2, QMC::AccessPublic, QMetaType::Void),
        // Method 'setLanguage'
        QtMocHelpers::MethodData<void(const QString &)>(148, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 149 },
        }}),
        // Method 'readFileAsBase64'
        QtMocHelpers::MethodData<QString(const QUrl &, int)>(150, 2, QMC::AccessPublic, QMetaType::QString, {{
            { 0x80000000 | 151, 152 }, { QMetaType::Int, 153 },
        }}),
        // Method 'readFileAsBase64'
        QtMocHelpers::MethodData<QString(const QUrl &)>(150, 2, QMC::AccessPublic | QMC::MethodCloned, QMetaType::QString, {{
            { 0x80000000 | 151, 152 },
        }}),
        // Method 'generateVideoThumbnail'
        QtMocHelpers::MethodData<QUrl(const QUrl &)>(154, 2, QMC::AccessPublic, 0x80000000 | 151, {{
            { 0x80000000 | 151, 155 },
        }}),
        // Method 'videoThumbnailFromBase64'
        QtMocHelpers::MethodData<QString(const QString &)>(156, 2, QMC::AccessPublic, QMetaType::QString, {{
            { QMetaType::QString, 157 },
        }}),
        // Method 'saveBase64ToTempFile'
        QtMocHelpers::MethodData<QString(const QString &, const QString &)>(158, 2, QMC::AccessPublic, QMetaType::QString, {{
            { QMetaType::QString, 157 }, { QMetaType::QString, 159 },
        }}),
        // Method 'extractVideoThumbnailAsync'
        QtMocHelpers::MethodData<void(const QString &, int, const QString &)>(160, 2, QMC::AccessPublic, QMetaType::Void, {{
            { QMetaType::QString, 41 }, { QMetaType::Int, 42 }, { QMetaType::QString, 157 },
        }}),
    };
    QtMocHelpers::UintData qt_properties {
        // property 'isLoggedIn'
        QtMocHelpers::PropertyData<bool>(161, QMetaType::Bool, QMC::DefaultPropertyFlags, 0),
        // property 'baseUrl'
        QtMocHelpers::PropertyData<QString>(162, QMetaType::QString, QMC::DefaultPropertyFlags | QMC::Writable | QMC::StdCppSet, 1),
        // property 'isAndroid'
        QtMocHelpers::PropertyData<bool>(163, QMetaType::Bool, QMC::DefaultPropertyFlags | QMC::Constant),
    };
    QtMocHelpers::UintData qt_enums {
    };
    return QtMocHelpers::metaObjectData<ApiClient, qt_meta_tag_ZN9ApiClientE_t>(QMC::MetaObjectFlag{}, qt_stringData,
            qt_methods, qt_properties, qt_enums);
}
Q_CONSTINIT const QMetaObject ApiClient::staticMetaObject = { {
    QMetaObject::SuperData::link<QObject::staticMetaObject>(),
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN9ApiClientE_t>.stringdata,
    qt_staticMetaObjectStaticContent<qt_meta_tag_ZN9ApiClientE_t>.data,
    qt_static_metacall,
    nullptr,
    qt_staticMetaObjectRelocatingContent<qt_meta_tag_ZN9ApiClientE_t>.metaTypes,
    nullptr
} };

void ApiClient::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    auto *_t = static_cast<ApiClient *>(_o);
    if (_c == QMetaObject::InvokeMetaMethod) {
        switch (_id) {
        case 0: _t->loggedInChanged(); break;
        case 1: _t->baseUrlChanged(); break;
        case 2: _t->languageChanged(); break;
        case 3: _t->errorOccurred((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 4: _t->registerSuccess((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 5: _t->registerStep1Done((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 6: _t->registerStep2Done(); break;
        case 7: _t->loginStep1Done((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<bool>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<bool>>(_a[3])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[4])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[5]))); break;
        case 8: _t->loginStep2Done(); break;
        case 9: _t->loginStep3Done(); break;
        case 10: _t->loginSuccess((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 11: _t->cookieCheckComplete((*reinterpret_cast<std::add_pointer_t<bool>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2]))); break;
        case 12: _t->followListFetched((*reinterpret_cast<std::add_pointer_t<QList<UserInfo>>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QList<UserInfo>>>(_a[2]))); break;
        case 13: _t->postPublished(); break;
        case 14: _t->timelineFetched((*reinterpret_cast<std::add_pointer_t<QList<int>>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2]))); break;
        case 15: _t->postFetched((*reinterpret_cast<std::add_pointer_t<QVariantMap>>(_a[1]))); break;
        case 16: _t->postLiked(); break;
        case 17: _t->postUnliked(); break;
        case 18: _t->commentPosted(); break;
        case 19: _t->commentsFetched((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1]))); break;
        case 20: _t->videoThumbnailExtracted((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        case 21: _t->mediaFilesPicked((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1]))); break;
        case 22: _t->messageSent(); break;
        case 23: _t->messagesReceived((*reinterpret_cast<std::add_pointer_t<QList<MessageInfo>>>(_a[1]))); break;
        case 24: _t->profileFetched((*reinterpret_cast<std::add_pointer_t<QVariantMap>>(_a[1]))); break;
        case 25: _t->profileUpdated(); break;
        case 26: _t->avatarPatched(); break;
        case 27: _t->avatarFetched((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        case 28: _t->groupCreated((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 29: _t->groupJoined(); break;
        case 30: _t->groupLeft(); break;
        case 31: _t->groupMessageSent(); break;
        case 32: _t->groupMessagesReceived((*reinterpret_cast<std::add_pointer_t<QList<GroupMessageInfo>>>(_a[1]))); break;
        case 33: _t->groupMembersFetched((*reinterpret_cast<std::add_pointer_t<QList<UserInfo>>>(_a[1]))); break;
        case 34: _t->myGroupsFetched((*reinterpret_cast<std::add_pointer_t<QList<GroupInfo>>>(_a[1]))); break;
        case 35: _t->groupMessagesReceived((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1]))); break;
        case 36: _t->userPostsFetched((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1]))); break;
        case 37: _t->myPostsFetched((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1]))); break;
        case 38: _t->followListFetchedForQml((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[2]))); break;
        case 39: _t->conversationsFetched((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1]))); break;
        case 40: _t->conversationHidden((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 41: _t->privateMessagesFetched((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<bool>>(_a[2]))); break;
        case 42: _t->contactsSearched((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[2]))); break;
        case 43: _t->contactsFetched((*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QVariantList>>(_a[2]))); break;
        case 44: _t->userDetailFetched((*reinterpret_cast<std::add_pointer_t<QVariantMap>>(_a[1]))); break;
        case 45: _t->groupDetailFetched((*reinterpret_cast<std::add_pointer_t<QVariantMap>>(_a[1]))); break;
        case 46: _t->startRegister((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        case 47: _t->verifyRegister((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        case 48: _t->completeRegister((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 49: _t->startLogin((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 50: _t->loginVerifyCaptcha((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 51: _t->loginSendEmailCode((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 52: _t->loginVerifyEmail((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 53: _t->completeLogin((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 54: _t->checkCookie(); break;
        case 55: _t->follow((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 56: _t->unfollow((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 57: _t->fetchFollowList(); break;
        case 58: _t->publishPost((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QStringList>>(_a[2]))); break;
        case 59: _t->publishPost((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 60: _t->fetchTimeline((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 61: _t->fetchTimeline(); break;
        case 62: _t->getPost((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 63: _t->likePost((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 64: _t->unlikePost((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 65: _t->comment((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 66: _t->fetchComments((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 67: _t->sendMessage((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 68: _t->receiveMessages(); break;
        case 69: _t->fetchProfile(); break;
        case 70: _t->updateProfile((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        case 71: _t->updateProfile((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 72: _t->updateProfile((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 73: _t->updateProfile(); break;
        case 74: _t->patchAvatar((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 75: _t->patchAvatar((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 76: _t->patchAvatar(); break;
        case 77: _t->fetchAvatar((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 78: _t->createGroup((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 79: _t->joinGroup((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 80: _t->leaveGroup((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 81: _t->sendGroupMessage((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 82: _t->receiveGroupMessages((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2]))); break;
        case 83: _t->receiveGroupMessages((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 84: _t->fetchGroupMembers((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 85: _t->fetchMyGroups(); break;
        case 86: _t->fetchConversations(); break;
        case 87: _t->hideConversation((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 88: _t->fetchPrivateMessages((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[3]))); break;
        case 89: _t->fetchPrivateMessages((*reinterpret_cast<std::add_pointer_t<int>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2]))); break;
        case 90: _t->fetchPrivateMessages((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 91: _t->searchContacts((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2]))); break;
        case 92: _t->searchContacts((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 93: _t->fetchContacts(); break;
        case 94: _t->fetchUserPosts((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 95: _t->fetchMyPostsDetail((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 96: _t->fetchUserDetail((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 97: _t->fetchGroupDetail((*reinterpret_cast<std::add_pointer_t<int>>(_a[1]))); break;
        case 98: _t->setCookie((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 99: _t->clearAuth(); break;
        case 100: _t->setLanguage((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1]))); break;
        case 101: { QString _r = _t->readFileAsBase64((*reinterpret_cast<std::add_pointer_t<QUrl>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2])));
            if (_a[0]) *reinterpret_cast<QString*>(_a[0]) = std::move(_r); }  break;
        case 102: { QString _r = _t->readFileAsBase64((*reinterpret_cast<std::add_pointer_t<QUrl>>(_a[1])));
            if (_a[0]) *reinterpret_cast<QString*>(_a[0]) = std::move(_r); }  break;
        case 103: { QUrl _r = _t->generateVideoThumbnail((*reinterpret_cast<std::add_pointer_t<QUrl>>(_a[1])));
            if (_a[0]) *reinterpret_cast<QUrl*>(_a[0]) = std::move(_r); }  break;
        case 104: { QString _r = _t->videoThumbnailFromBase64((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])));
            if (_a[0]) *reinterpret_cast<QString*>(_a[0]) = std::move(_r); }  break;
        case 105: { QString _r = _t->saveBase64ToTempFile((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[2])));
            if (_a[0]) *reinterpret_cast<QString*>(_a[0]) = std::move(_r); }  break;
        case 106: _t->extractVideoThumbnailAsync((*reinterpret_cast<std::add_pointer_t<QString>>(_a[1])),(*reinterpret_cast<std::add_pointer_t<int>>(_a[2])),(*reinterpret_cast<std::add_pointer_t<QString>>(_a[3]))); break;
        default: ;
        }
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        switch (_id) {
        default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
        case 12:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 1:
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< QList<UserInfo> >(); break;
            }
            break;
        case 14:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< QList<int> >(); break;
            }
            break;
        case 23:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< QList<MessageInfo> >(); break;
            }
            break;
        case 32:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< QList<GroupMessageInfo> >(); break;
            }
            break;
        case 33:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< QList<UserInfo> >(); break;
            }
            break;
        case 34:
            switch (*reinterpret_cast<int*>(_a[1])) {
            default: *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType(); break;
            case 0:
                *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType::fromType< QList<GroupInfo> >(); break;
            }
            break;
        }
    }
    if (_c == QMetaObject::IndexOfMethod) {
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::loggedInChanged, 0))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::baseUrlChanged, 1))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::languageChanged, 2))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QString & )>(_a, &ApiClient::errorOccurred, 3))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QString & )>(_a, &ApiClient::registerSuccess, 4))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QString & , const QString & )>(_a, &ApiClient::registerStep1Done, 5))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::registerStep2Done, 6))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QString & , bool , bool , const QString & , const QString & )>(_a, &ApiClient::loginStep1Done, 7))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::loginStep2Done, 8))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::loginStep3Done, 9))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QString & )>(_a, &ApiClient::loginSuccess, 10))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(bool , int )>(_a, &ApiClient::cookieCheckComplete, 11))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QList<UserInfo> & , const QList<UserInfo> & )>(_a, &ApiClient::followListFetched, 12))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::postPublished, 13))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QList<int> & , int )>(_a, &ApiClient::timelineFetched, 14))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantMap & )>(_a, &ApiClient::postFetched, 15))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::postLiked, 16))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::postUnliked, 17))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::commentPosted, 18))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & )>(_a, &ApiClient::commentsFetched, 19))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QString & , int , const QString & )>(_a, &ApiClient::videoThumbnailExtracted, 20))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & )>(_a, &ApiClient::mediaFilesPicked, 21))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::messageSent, 22))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QList<MessageInfo> & )>(_a, &ApiClient::messagesReceived, 23))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantMap & )>(_a, &ApiClient::profileFetched, 24))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::profileUpdated, 25))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::avatarPatched, 26))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(int , const QString & , const QString & )>(_a, &ApiClient::avatarFetched, 27))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(int )>(_a, &ApiClient::groupCreated, 28))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::groupJoined, 29))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::groupLeft, 30))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)()>(_a, &ApiClient::groupMessageSent, 31))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QList<GroupMessageInfo> & )>(_a, &ApiClient::groupMessagesReceived, 32))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QList<UserInfo> & )>(_a, &ApiClient::groupMembersFetched, 33))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QList<GroupInfo> & )>(_a, &ApiClient::myGroupsFetched, 34))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & )>(_a, &ApiClient::groupMessagesReceived, 35))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & )>(_a, &ApiClient::userPostsFetched, 36))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & )>(_a, &ApiClient::myPostsFetched, 37))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & , const QVariantList & )>(_a, &ApiClient::followListFetchedForQml, 38))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & )>(_a, &ApiClient::conversationsFetched, 39))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(int )>(_a, &ApiClient::conversationHidden, 40))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & , bool )>(_a, &ApiClient::privateMessagesFetched, 41))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & , const QVariantList & )>(_a, &ApiClient::contactsSearched, 42))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantList & , const QVariantList & )>(_a, &ApiClient::contactsFetched, 43))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantMap & )>(_a, &ApiClient::userDetailFetched, 44))
            return;
        if (QtMocHelpers::indexOfMethod<void (ApiClient::*)(const QVariantMap & )>(_a, &ApiClient::groupDetailFetched, 45))
            return;
    }
    if (_c == QMetaObject::ReadProperty) {
        void *_v = _a[0];
        switch (_id) {
        case 0: *reinterpret_cast<bool*>(_v) = _t->isLoggedIn(); break;
        case 1: *reinterpret_cast<QString*>(_v) = _t->baseUrl(); break;
        case 2: *reinterpret_cast<bool*>(_v) = _t->isAndroid(); break;
        default: break;
        }
    }
    if (_c == QMetaObject::WriteProperty) {
        void *_v = _a[0];
        switch (_id) {
        case 1: _t->setBaseUrl(*reinterpret_cast<QString*>(_v)); break;
        default: break;
        }
    }
}

const QMetaObject *ApiClient::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *ApiClient::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_staticMetaObjectStaticContent<qt_meta_tag_ZN9ApiClientE_t>.strings))
        return static_cast<void*>(this);
    return QObject::qt_metacast(_clname);
}

int ApiClient::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QObject::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 107)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 107;
    }
    if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 107)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 107;
    }
    if (_c == QMetaObject::ReadProperty || _c == QMetaObject::WriteProperty
            || _c == QMetaObject::ResetProperty || _c == QMetaObject::BindableProperty
            || _c == QMetaObject::RegisterPropertyMetaType) {
        qt_static_metacall(this, _c, _id, _a);
        _id -= 3;
    }
    return _id;
}

// SIGNAL 0
void ApiClient::loggedInChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 0, nullptr);
}

// SIGNAL 1
void ApiClient::baseUrlChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 1, nullptr);
}

// SIGNAL 2
void ApiClient::languageChanged()
{
    QMetaObject::activate(this, &staticMetaObject, 2, nullptr);
}

// SIGNAL 3
void ApiClient::errorOccurred(const QString & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 3, nullptr, _t1);
}

// SIGNAL 4
void ApiClient::registerSuccess(const QString & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 4, nullptr, _t1);
}

// SIGNAL 5
void ApiClient::registerStep1Done(const QString & _t1, const QString & _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 5, nullptr, _t1, _t2);
}

// SIGNAL 6
void ApiClient::registerStep2Done()
{
    QMetaObject::activate(this, &staticMetaObject, 6, nullptr);
}

// SIGNAL 7
void ApiClient::loginStep1Done(const QString & _t1, bool _t2, bool _t3, const QString & _t4, const QString & _t5)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 7, nullptr, _t1, _t2, _t3, _t4, _t5);
}

// SIGNAL 8
void ApiClient::loginStep2Done()
{
    QMetaObject::activate(this, &staticMetaObject, 8, nullptr);
}

// SIGNAL 9
void ApiClient::loginStep3Done()
{
    QMetaObject::activate(this, &staticMetaObject, 9, nullptr);
}

// SIGNAL 10
void ApiClient::loginSuccess(const QString & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 10, nullptr, _t1);
}

// SIGNAL 11
void ApiClient::cookieCheckComplete(bool _t1, int _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 11, nullptr, _t1, _t2);
}

// SIGNAL 12
void ApiClient::followListFetched(const QList<UserInfo> & _t1, const QList<UserInfo> & _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 12, nullptr, _t1, _t2);
}

// SIGNAL 13
void ApiClient::postPublished()
{
    QMetaObject::activate(this, &staticMetaObject, 13, nullptr);
}

// SIGNAL 14
void ApiClient::timelineFetched(const QList<int> & _t1, int _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 14, nullptr, _t1, _t2);
}

// SIGNAL 15
void ApiClient::postFetched(const QVariantMap & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 15, nullptr, _t1);
}

// SIGNAL 16
void ApiClient::postLiked()
{
    QMetaObject::activate(this, &staticMetaObject, 16, nullptr);
}

// SIGNAL 17
void ApiClient::postUnliked()
{
    QMetaObject::activate(this, &staticMetaObject, 17, nullptr);
}

// SIGNAL 18
void ApiClient::commentPosted()
{
    QMetaObject::activate(this, &staticMetaObject, 18, nullptr);
}

// SIGNAL 19
void ApiClient::commentsFetched(const QVariantList & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 19, nullptr, _t1);
}

// SIGNAL 20
void ApiClient::videoThumbnailExtracted(const QString & _t1, int _t2, const QString & _t3)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 20, nullptr, _t1, _t2, _t3);
}

// SIGNAL 21
void ApiClient::mediaFilesPicked(const QVariantList & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 21, nullptr, _t1);
}

// SIGNAL 22
void ApiClient::messageSent()
{
    QMetaObject::activate(this, &staticMetaObject, 22, nullptr);
}

// SIGNAL 23
void ApiClient::messagesReceived(const QList<MessageInfo> & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 23, nullptr, _t1);
}

// SIGNAL 24
void ApiClient::profileFetched(const QVariantMap & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 24, nullptr, _t1);
}

// SIGNAL 25
void ApiClient::profileUpdated()
{
    QMetaObject::activate(this, &staticMetaObject, 25, nullptr);
}

// SIGNAL 26
void ApiClient::avatarPatched()
{
    QMetaObject::activate(this, &staticMetaObject, 26, nullptr);
}

// SIGNAL 27
void ApiClient::avatarFetched(int _t1, const QString & _t2, const QString & _t3)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 27, nullptr, _t1, _t2, _t3);
}

// SIGNAL 28
void ApiClient::groupCreated(int _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 28, nullptr, _t1);
}

// SIGNAL 29
void ApiClient::groupJoined()
{
    QMetaObject::activate(this, &staticMetaObject, 29, nullptr);
}

// SIGNAL 30
void ApiClient::groupLeft()
{
    QMetaObject::activate(this, &staticMetaObject, 30, nullptr);
}

// SIGNAL 31
void ApiClient::groupMessageSent()
{
    QMetaObject::activate(this, &staticMetaObject, 31, nullptr);
}

// SIGNAL 32
void ApiClient::groupMessagesReceived(const QList<GroupMessageInfo> & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 32, nullptr, _t1);
}

// SIGNAL 33
void ApiClient::groupMembersFetched(const QList<UserInfo> & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 33, nullptr, _t1);
}

// SIGNAL 34
void ApiClient::myGroupsFetched(const QList<GroupInfo> & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 34, nullptr, _t1);
}

// SIGNAL 35
void ApiClient::groupMessagesReceived(const QVariantList & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 35, nullptr, _t1);
}

// SIGNAL 36
void ApiClient::userPostsFetched(const QVariantList & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 36, nullptr, _t1);
}

// SIGNAL 37
void ApiClient::myPostsFetched(const QVariantList & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 37, nullptr, _t1);
}

// SIGNAL 38
void ApiClient::followListFetchedForQml(const QVariantList & _t1, const QVariantList & _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 38, nullptr, _t1, _t2);
}

// SIGNAL 39
void ApiClient::conversationsFetched(const QVariantList & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 39, nullptr, _t1);
}

// SIGNAL 40
void ApiClient::conversationHidden(int _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 40, nullptr, _t1);
}

// SIGNAL 41
void ApiClient::privateMessagesFetched(const QVariantList & _t1, bool _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 41, nullptr, _t1, _t2);
}

// SIGNAL 42
void ApiClient::contactsSearched(const QVariantList & _t1, const QVariantList & _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 42, nullptr, _t1, _t2);
}

// SIGNAL 43
void ApiClient::contactsFetched(const QVariantList & _t1, const QVariantList & _t2)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 43, nullptr, _t1, _t2);
}

// SIGNAL 44
void ApiClient::userDetailFetched(const QVariantMap & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 44, nullptr, _t1);
}

// SIGNAL 45
void ApiClient::groupDetailFetched(const QVariantMap & _t1)
{
    QMetaObject::activate<void>(this, &staticMetaObject, 45, nullptr, _t1);
}
QT_WARNING_POP
