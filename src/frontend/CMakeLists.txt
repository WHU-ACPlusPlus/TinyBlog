cmake_minimum_required(VERSION 3.16)

project(frontend VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(QT_QML_GENERATE_QMLLS_INI OFF)

find_package(Qt6 REQUIRED COMPONENTS Quick Network QuickDialogs2 Multimedia LinguistTools)

qt_standard_project_setup(REQUIRES 6.5)

set(QT_ANDROID_PACKAGE_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/android CACHE PATH "Android package source directory")

qt_add_executable(appfrontend
    main.cpp
    api_client.cpp
    api_client.h
    api_types.h
)

set(appfrontend_qrc_srcs "")
qt6_add_resources(appfrontend_qrc_srcs ${CMAKE_CURRENT_SOURCE_DIR}/resources.qrc)
target_sources(appfrontend PRIVATE ${appfrontend_qrc_srcs})

qt_add_resources(appfrontend appfrontend_assets
    PREFIX "/"
    FILES
        assets/icon.png
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
        VideoPlayerOverlay.qml
        VideoWallpaperBg.qml
        GlassCard.qml
        EmojiIcon.qml
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

# Windows: DWM 圆角支持
if(WIN32)
    target_link_libraries(appfrontend PRIVATE dwmapi)
endif()

set_target_properties(appfrontend PROPERTIES
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE

    # ── Android 发布信息 ──
    QT_ANDROID_PACKAGE_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/android"
    QT_ANDROID_VERSION_CODE 1
    QT_ANDROID_VERSION_NAME "1.0.0"
    QT_ANDROID_MIN_SDK_VERSION 26
    QT_ANDROID_TARGET_SDK_VERSION 33
)

install(TARGETS appfrontend
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
