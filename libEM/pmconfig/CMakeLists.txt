FILE(GLOB pmfiles "${CMAKE_CURRENT_SOURCE_DIR}/*.*")
INSTALL(FILES ${pmfiles}
  DESTINATION    ${SETUP_DIR}/lib/pmconfig
)
