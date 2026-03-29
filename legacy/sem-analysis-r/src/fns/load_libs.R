#' Load or Install Required Libraries
#'
#' This function checks if the specified libraries are installed, and loads them if they are. If a library is not
#' installed, it will be installed and then loaded.
#'
#' @param libs A character vector of library names.
#'
#' @return The specified libraries will be loaded.
#'
#' @examples
#' load_libs(c("trendecon", "chatgpt", "tidyverse", "magrittr", "dplyr"))
#'
#' @importFrom utils install.packages
#' @importFrom pacman p_load
#' @export
load_libs <- function(libs) {
  # Check if the library is installed and load it if it is
  for (lib in libs) {
    if (!require(lib, character.only = TRUE)) {
      # Install and load the library if it's not installed
      message(paste0(lib, " library not found. Installing..."))
      install.packages(lib, dependencies = TRUE)
      p_load(lib)
      message(paste0(lib, " installed and loaded."))
    }
  }
}
