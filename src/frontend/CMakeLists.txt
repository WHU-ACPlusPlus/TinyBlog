cmake_minimum_required(VERSION 3.16)

project(frontend VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(QT_QML_GENERATE_QMLLS_INI ON)

find_package(Qt6 REQUIRED COMPONENTS Quick Network QuickDialogs2 Multimedia)

qt_standard_project_setup(REQUIRES 6.5)

qt_add_executable(appfrontend
    main.cpp
    api_client.cpp
    api_client.h
    api_types.h
)

# 注册 QML 模块 —— QML 文件放到 qml/ 目录下
qt_add_qml_module(appfrontend
    URI frontend
    VERSION 1.0
    QML_FILES
        Main.qml
        LoginFlow.qml
        MainPage.qml
        SquarePage.qml
        MessagesPage.qml
        ProfilePage.qml
)

target_link_libraries(appfrontend
    PRIVATE Qt6::Quick Qt6::Network Qt6::QuickDialogs2 Qt6::Multimedia
)

set_target_properties(appfrontend PROPERTIES
    MACOSX_BUNDLE_BUNDLE_VERSION ${PROJECT_VERSION}
    MACOSX_BUNDLE_SHORT_VERSION_STRING ${PROJECT_VERSION_MAJOR}.${PROJECT_VERSION_MINOR}
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE FALSE
)

install(TARGETS appfrontend
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
