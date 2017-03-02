FILE(GLOB pngfiles "${CMAKE_CURRENT_SOURCE_DIR}/*.png")
INSTALL(FILES ${pngfiles} 
  DESTINATION    ${EMAN_PY_INSTALL_PREFIX_UP}/images/macimages
)
