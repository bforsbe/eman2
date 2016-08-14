FILE(GLOB headerfiles "${CMAKE_CURRENT_SOURCE_DIR}/*.h")
INSTALL(FILES ${headerfiles}
  	DESTINATION    ${CMAKE_INSTALL_PREFIX}/EMAN2/include/gorgon
)
