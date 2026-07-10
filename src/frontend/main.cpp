#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QLoggingCategory>
#include <QTranslator>
#include <QLocale>
#include <QDir>
#include <QIcon>
#include "api_client.h"

#ifdef Q_OS_WIN
#include <windows.h>
#include <dwmapi.h>
#pragma comment(lib, "dwmapi.lib")
#pragma comment(lib, "user32.lib")
#endif

// ── 窗口操作辅助类 ──
class WindowHelper : public QObject {
    Q_OBJECT
    QQuickWindow *m_window;
public:
    WindowHelper(QQuickWindow *w, QObject *p = nullptr) : QObject(p), m_window(w) {}
    Q_INVOKABLE void minimize() {
        if (m_window) {
#ifdef Q_OS_WIN
            ShowWindow(reinterpret_cast<HWND>(m_window->winId()), SW_MINIMIZE);
#else
            m_window->showMinimized();
#endif
        }
    }
    Q_INVOKABLE void toggleMaximize() {
        if (m_window) {
            if (m_window->visibility() == QWindow::Maximized)
                m_window->showNormal();
            else
                m_window->showMaximized();
        }
    }
    Q_INVOKABLE void closeWindow() { if (m_window) m_window->close(); }
};

int main(int argc, char *argv[])
{
    // 精确分数缩放，避免高分屏下模糊
    QGuiApplication::setHighDpiScaleFactorRoundingPolicy(
        Qt::HighDpiScaleFactorRoundingPolicy::PassThrough);

    QGuiApplication app(argc, argv);
    // 设组织名和应用名，让 QSettings 存到可预期的路径
    app.setOrganizationName("TinyBlog");
    app.setApplicationName("TinyBlog");

    // 设置窗口图标
    app.setWindowIcon(QIcon(":/assets/icon.png"));

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
    // 默认 URL 由 ApiClient 构造函数从 QSettings 加载（首次运行 = "https://api.becharmkon.cn"）
    // 用户可在登录页手动修改并自动保存到 QSettings
    ApiClient api;

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

    // ── 窗口辅助：DWM 圆角 + 最小化/最大化/关闭 ──
    {
        const auto roots = engine.rootObjects();
        if (!roots.isEmpty()) {
            if (auto *window = qobject_cast<QQuickWindow*>(roots.first())) {
#ifdef Q_OS_WIN
                HWND hwnd = reinterpret_cast<HWND>(window->winId());
                const int DWMWA_WINDOW_CORNER_PREFERENCE = 33;
                const int DWMWCP_ROUND = 2;
                DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                                      &DWMWCP_ROUND, sizeof(DWMWCP_ROUND));
                MARGINS margins = {-1, -1, -1, -1};
                DwmExtendFrameIntoClientArea(hwnd, &margins);
                window->setColor(Qt::transparent);
#endif
                engine.rootContext()->setContextProperty("winHelper",
                    new WindowHelper(window, &app));
            }
        }
    }

    return QGuiApplication::exec();
}

#include "main.moc"
