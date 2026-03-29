#
#
#
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
#Geographic location for specifics in the analysis
geo_code <- "US"
#keywords
categories_keywords <-
  readRDS(here::here("data", "nails_keywords.RDS"))
#Unused or negative keywords
unused_nail_terms <-
  readRDS(here::here("data", "unused_nail_trends.RDS"))
#Creating the search categories and their corresponding batches
sc_tform <-
  search_category_batches(terms = categories_keywords, unused_terms = unused_nail_terms)

start <- Sys.time()
all_gtrends_usa <-
  batch_trends(
    sc_tform,
    out_dir = here::here("data", "batch-search-us"),
    suffix = "batch-bsg",
    geo_code = "US",
    sleep_time = NULL,
    time_span = time_span
  )
#Top searched results, likely a bad read on the category intention, need's an overlay
monthly_trends<-trend_aggregate(all_gtrends_usa, "month", "id", "value")

# Get the top ranked items from the top batches

top_items<-top_batch(monthly_trends,10,2)

top_search_trends <-
  batch_trends(
    top_items,
    out_dir = here::here("data", "batch-search-us"),
    suffix = "batch-bsg-top-terms-",
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

if (exists("unused_nail_terms")) {
  unused_nail_terms <-
    unique(
      c(
        unused_nail_terms,
        monthly_trends %>% dplyr::filter(tot_val == 0) %>% dplyr::pull(id) %>% unique(.)
      )
    )
} else{
  unused_nail_terms <-
    monthly_trends %>% dplyr::filter(tot_val == 0) %>% dplyr::pull(id) %>% unique(.)
}

if (!file.exists(here::here("data", "unused_nail_trends.RDS"))) {
  saveRDS(unused_nail_terms,
          file = here::here("data", "unused_nail_trends.RDS"))
} else{
  saveRDS(unique(c(append(
    readRDS(here::here("data", "unused_nail_trends.RDS")), unused_nail_terms
  ))), here::here("data", "unused_nail_trends.RDS"))
}
#Least searched results, likely a bad read on the category intention, need's an overlay
search_trends %>%
  group_by(id, mth = lubridate::month(time)) %>%
  summarise(value = sum(value, na.rm = T), .groups = "drop") %>%
  arrange(value) %>%
  group_by(id) %>%
  dplyr::mutate(tot_val = sum(value, na.rm = T)) %>%
  ungroup(.) %>%
  dplyr::mutate(rank = dense_rank(tot_val))
