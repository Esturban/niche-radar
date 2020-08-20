# find the source directory from which the Rscript is called:
sourceDirectory <- function() {
  cmdArgs <- commandArgs(trailingOnly = FALSE)
  needle <- "--file="
  match <- grep(needle, cmdArgs)
  if (length(match) > 0) {
    # Rscript
    return(dirname(normalizePath(sub(needle, "", cmdArgs[match]),winslash = "/")))
  } else {
    # 'source'd via R console
    return(dirname(normalizePath(sys.frames()[[1]]$ofile,winslash = "/")))
  }
}

# set this as the working directory (unless fails i.e. during testing)
WD <- tryCatch(
  expr = {
    sourceDirectory()
  },
  error = function(err){
    return(getwd())
  }
)
setwd(WD)

# control variables:
c_config_success <- FALSE
c_lib_and_db     <- FALSE
c_email_output   <- FALSE
c_transform_data <- FALSE
c_create_report  <- FALSE
c_send_report    <- FALSE

# CONFIG (source the config file and attach the functions/objects to the SP)
.config <- new.env(parent = emptyenv())
try(expr = {
  sys.source(file = '../_config/config.R', env=attach(.config,name=".config"))
  rm(WD,sourceDirectory)}
  # if(!grepl("evalencia",WD)){Sys.setenv(JAVA_HOME = 'C:\\Program Files\\Java\\jdk1.8.0_191\\jre')# for 64-bit version
  # }else{Sys.setenv(JAVA_HOME = 'C:\\Program Files\\Java\\jdk1.8.0_181\\jre')}}
)


# source('C:/Users/Este/OneDrive/01_dataprojects/sendmail_proj/functions/email_header.R',echo = F)

# update.packages('dplyr',ask = F)
if(c_config_success)
{
  
  pkgs <-
    c(
      'purrr',
      'dplyr',
      'tidyr',
      'magrittr',
      'reshape2',
      'gtrendsR',
      'GGally',
      'ggmap',
      'rvest'
    )
  
  invisible(suppressPackageStartupMessages(sapply(pkgs, require, character.only = T))) ->
    lib.out
  # pgConnect()
  # source('../../sendmail_proj/functions/email_header.R',echo = F)
  
  c_lib_and_db <- ifelse(abs(sum(lib.out) - length(lib.out)), {
    tryCatch({
      install.packages(names(lib.out)[!lib.out], dependencies = T)
      return(T)
    }, error = function(err)
      F)
  }, T)
  
  source("adwords_fn.R")
}

# dplyr::src_pos
if(c_lib_and_db)
  {
  # source('../_config/tq_fns.R',echo = F)
  # source("edgar_dir.R")
}
  
# pgConnect()
