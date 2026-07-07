cmake_minimum_required(VERSION 3.16)

project(frontend VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(QT_QML_GENERATE_QMLLS_INI ON)

find_package(Qt6 REQUIRED COMPONENTS Quick Network QuickDialogs2 Multimedia LinguistTools)

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

# ── 国际化 / 翻译 ──
set(TS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/translations)
file(MAKE_DIRECTORY ${TS_DIR})

qt_add_translations(appfrontend
    TS_FILES
        ${TS_DIR}/appfrontend_zh_CN.ts
        ${TS_DIR}/appfrontend_en_US.ts
    QM_FILES_OUTPUT_VARIABLE appfrontend_qm_files
)

# Copy .qm files next to the binary so runtime translation loading works
foreach(qm_file ${appfrontend_qm_files})
    get_filename_component(qm_name ${qm_file} NAME)
    add_custom_command(TARGET appfrontend POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${qm_file}"
            "$<TARGET_FILE_DIR:appfrontend>/${qm_name}"
        COMMENT "Copying ${qm_name} to binary dir"
    )
endforeach()

target_link_libraries(appfrontend
    PRIVATE Qt6::Quick Qt6::Network Qt6::QuickDialogs2 Qt6::Multimedia Qt6::Core
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
