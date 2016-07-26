FILE(GLOB headerfiles "${CMAKE_CURRENT_SOURCE_DIR}/*.h")
INSTALL(FILES ${headerfiles}
  	DESTINATION    ${EMAN_INSTALL_PREFIX}/include/gorgon
)
