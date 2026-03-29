# sem_eva

invisible(lapply(
  list.files(
    here::here("src", "fns"),
    pattern = "*.R",
    full.names = T,
    include.dirs = F
  ),
  source
))

#Load all of the libraries needed for the runtime
load_libs(c("trendecon", "magrittr", "dplyr", "chatgpt"))

#Declaration of the timespan for the analysis
date_start <- "2022-01-01"
date_end <- "2022-12-31"
time_span <- paste(date_start, date_end)
folder_loc <- here::here("data", "eva-batch-usa")
#Geographic location for specifics in the analysis
geo_code <- "US"
# saveRDS(ck_clean, here::here("data", "eva-batch-usa", "keywords.RDS"))
categories_keywords<-readRDS(here::here("data", "eva-batch-usa", "keywords.RDS"))

ck_clean <-categories_keywords%>%.[nchar(.)>0]
unused_client_terms <- unused_terms(terms_rds_loc = here::here("data","eva-batch-usa","unused_trends.RDS"))
#Creating the search categories and their corresponding batches
sc_tform <-
  search_category_batches(terms = ck_clean, unused_terms = unused_client_terms)

start <- Sys.time()
all_gtrends_usa <-
  batch_trends(
    sc_tform,
    out_dir = here::here("data", "eva-batch-usa"),
    suffix = "batch-eva",
    geo_code = "US",
    sleep_time = NULL,
    verbose=T,
    time_span = time_span
  )
#Top searched results, likely a bad read on the category intention, need's an overlay
monthly_trends <-
  trend_aggregate(all_gtrends_usa, "month", "id", "value")

monthly_trends%>%print(n=100)


# Get the top ranked items from the top batches

top_items <- top_batch(monthly_trends, 10, 2)

top_search_trends <-
  batch_trends(
    top_items,
    out_dir = here::here("data", "eva-batch-usa"),
    suffix = "batch-eva-top-terms-",
    geo_code = "US",
    sleep_time = NULL,
    time_span = time_span
  )

#Top searched results, likely a bad read on the category intention, need's an overlay
top_search_trends %>%
  group_by(id, mth = lubridate::month(time)) %>%
  summarise(value = sum(value, na.rm = T), .groups = "drop") %>%
  arrange(desc(value)) %>%
  group_by(id) %>%
  dplyr::mutate(tot_val = sum(value, na.rm = T)) %>%
  ungroup(.) %>%
  dplyr::mutate(rank = dense_rank(desc(tot_val))) -> top_monthly_trends
top_monthly_trends %>% pull(id) %>% unique(.) %>% print(.)
top_monthly_trends %>% select(id, rank) %>% unique(.) %>% arrange(rank) %>%
  DT::datatable(., rownames = F)

if (exists("unused_client_terms")) {
  unused_client_terms <-
    unique(
      c("Data Validation",
        unused_client_terms,
        monthly_trends %>% dplyr::filter(tot_val == 0) %>% dplyr::pull(search_terms) %>% unique(.)
      )
    )
} else{
  unused_client_terms <-
    monthly_trends %>% dplyr::filter(tot_val == 0) %>% dplyr::pull(search_terms) %>% unique(.)
}

if (!file.exists(here::here("data", "eva-batch-usa", "unused_trends.RDS"))) {
  saveRDS(unused_client_terms,
          file = here::here("data", "eva-batch-usa", "unused_trends.RDS"))
} else{
  saveRDS(unique(c(append(
    readRDS(here::here(
      "data", "eva-batch-usa", "unused_trends.RDS"
    )), unused_client_terms
  ))),
  here::here("data", "eva-batch-usa", "unused_trends.RDS"))
}
  
