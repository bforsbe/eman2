ADD_SUBDIRECTORY(macimages)

FILE(GLOB pngfiles "${CMAKE_CURRENT_SOURCE_DIR}/*.png")
FILE(GLOB icofiles "${CMAKE_CURRENT_SOURCE_DIR}/*.ico")
INSTALL(FILES ${pngfiles} ${icofiles} DESTINATION    ${CMAKE_INSTALL_PREFIX}/EMAN2/images COMPONENT Programs)
INSTALL(FILES ${pngfiles} ${icofiles} DESTINATION    ${CMAKE_INSTALL_PREFIX}/sparx/images COMPONENT Programs)
INSTALL(FILES Close.txt DESTINATION ${CMAKE_INSTALL_PREFIX}/EMAN2/images                  COMPONENT Programs)
INSTALL(FILES Close.txt DESTINATION ${CMAKE_INSTALL_PREFIX}/sparx/images                  COMPONENT Programs)


# FIXING libpng warning: iCCP: known incorrect sRGB profile
# http://tex.stackexchange.com/questions/125612/warning-pdflatex-libpng-warning-iccp-known-incorrect-srgb-profile
