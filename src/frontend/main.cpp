#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QLoggingCategory>
#include <QTranslator>
#include <QLocale>
#include <QDir>
#include "api_client.h"

int main(int argc, char *argv[])
{
    // 精确分数缩放，避免高分屏下模糊
    QGuiApplication::setHighDpiScaleFactorRoundingPolicy(
        Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);

    QGuiApplication app(argc, argv);
    // 设组织名和应用名，让 QSettings 存到可预期的路径
    app.setOrganizationName("TinyChat");
    app.setApplicationName("TinyChat");

    // ── 关闭 Qt 调试日志（避免在前端控制台打印 HTTP 请求体和 base64 数据）──
    QLoggingCategory::setFilterRules("*.debug=false");

    // ── 加载翻译 ──
    // 当前系统语言，zh_CN 表示不需要翻译（源码即中文）
    // 如需添加新语言：生成 .ts 文件 → 填写翻译 → lrelease → .qm 放 translations/ 下
    QTranslator translator;
    QString lang = QLocale::system().name();  // e.g. "en_US", "zh_CN"
    if (lang != "zh_CN" && lang != "zh") {
        QString qmPath = QCoreApplication::applicationDirPath()
            + "/translations/appfrontend_" + lang + ".qm";
        if (translator.load(qmPath)) {
            app.installTranslator(&translator);
        }
    }

    // 创建 API 客户端，暴露给 QML 侧使用
    ApiClient api;
    api.setBaseUrl("http://127.0.0.1:18999");

    QQmlApplicationEngine engine;
    api.setQmlEngine(&engine);
    // 将 api 对象注入 QML 上下文，在 QML 中以 api 名称访问
    engine.rootContext()->setContextProperty("api", &api);

    QObject::connect(
        &engine,
        &QQmlApplicationEngine::objectCreationFailed,
        &app,
        []() { QCoreApplication::exit(-1); },
        Qt::QueuedConnection);
    engine.loadFromModule("frontend", "Main");

    return QGuiApplication::exec();
}
