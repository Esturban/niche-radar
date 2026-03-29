#Unused or negative keywords
unused_terms <-
  function(terms_rds_loc = here::here("data", "eva-data-us", "unused_trends.RDS")) {
    if (!file.exists(terms_rds_loc)) {
      if (!dir.exists(dirname(terms_rds_loc)))
        dir.create(dirname(terms_rds_loc))
      return(NULL)
    } else{
      return(readRDS(terms_rds_loc))
    }
  }