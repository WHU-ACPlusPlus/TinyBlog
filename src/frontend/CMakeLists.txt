cmake_minimum_required(VERSION 3.16)

project(frontend VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(QT_QML_GENERATE_QMLLS_INI OFF)

find_package(Qt6 REQUIRED COMPONENTS Quick Network QuickDialogs2 Multimedia LinguistTools)

qt_standard_project_setup(REQUIRES 6.5)

# ── Android 自定义资源（图标、应用名等）──
set(QT_ANDROID_PACKAGE_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/android CACHE PATH "Android package source directory")

qt_add_executable(appfrontend
    main.cpp
    api_client.cpp
    api_client.h
    api_types.h
    resources.qrc
)

# androiddeployqt 6.5.x 需要通过 JSON 中的 android-package-source-directory
# 定位自定义 AndroidManifest.xml 和图标。CMake 不自动写入该字段,
# 在编译完成后、APK 打包前补上。
add_custom_command(TARGET appfrontend POST_BUILD
    COMMAND python3 ${CMAKE_CURRENT_SOURCE_DIR}/patch-deploy-json.py
        ${CMAKE_CURRENT_BINARY_DIR}/android-appfrontend-deployment-settings.json
        ${CMAKE_CURRENT_SOURCE_DIR}/android
    COMMENT "Patching Android deployment JSON with custom package source"
)

# 注册 QML 模块 —— QML 文件放到 qml/ 目录下
qt_add_qml_module(appfrontend
    URI frontend
    VERSION 1.0
    NO_CACHEGEN
    QML_FILES
        Main.qml
        LoginFlow.qml
        MainPage.qml
        SquarePage.qml
        MessagesPage.qml
        ProfilePage.qml
        ConversationListPanel.qml
        ConversationItem.qml
        ChatPanel.qml
        MessageBubble.qml
        GlassCard.qml
)

# ── 国际化 / 翻译 ──
set(TS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/translations)
file(MAKE_DIRECTORY ${TS_DIR})

qt_add_translations(appfrontend
    TS_FILES
        ${TS_DIR}/appfrontend_zh_CN.ts
        ${TS_DIR}/appfrontend_en_US.ts
    QM_FILES_OUTPUT_VARIABLE appfrontend_qm_files
)

target_link_libraries(appfrontend
    PRIVATE Qt6::Quick Qt6::Network Qt6::QuickDialogs2 Qt6::Multimedia Qt6::Core
)

set_target_properties(appfrontend PROPERTIES
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)

install(TARGETS appfrontend
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
