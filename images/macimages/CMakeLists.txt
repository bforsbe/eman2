FILE(GLOB pngfiles "${CMAKE_CURRENT_SOURCE_DIR}/*.png")
INSTALL(FILES ${pngfiles} 
  	DESTINATION    ${CMAKE_INSTALL_PREFIX}/EMAN2/images/macimages
)
INSTALL(FILES ${pngfiles} 
  	DESTINATION    ${CMAKE_INSTALL_PREFIX}/sparx/images/macimages
)
